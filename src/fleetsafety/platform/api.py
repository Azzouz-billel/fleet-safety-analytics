"""FastAPI app: JSON API (Task 3.2) + server-rendered dashboard (3.4, 3.5).

JSON under /api/*; HTML dashboard at /, /drivers/{id}, /map. The API
accepts canonical result.json documents — the same artifact `fleetsafety
process` writes — so field devices and the CLI share one ingest path.
"""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..schemas import TripResult
from . import charts
from .db import init_db, make_engine, session_factory
from .i18n import label, label_fr
from .models import Driver, PeriodScore, Trip, TripEvent
from .periods import recompute_period_scores
from .store import store_trip_result

logger = logging.getLogger(__name__)

HOTSPOT_GRID_DECIMALS = 3  # ~110 m cells
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def create_app(db_path: str | Path = "fleet.db") -> FastAPI:
    engine = make_engine(db_path)
    init_db(engine)
    make_session = session_factory(engine)

    app = FastAPI(title="Fleet Safety Analytics")
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    templates.env.globals["L"] = label
    templates.env.globals["LF"] = label_fr

    def get_session():
        session = make_session()
        try:
            yield session
        finally:
            session.close()

    # ---- JSON API --------------------------------------------------------

    @app.post("/api/trips", status_code=201)
    def ingest_trip(result: TripResult, session: Session = Depends(get_session)):
        trip = store_trip_result(session, result)
        recompute_period_scores(session, "week")
        return {"trip_id": trip.id, "score": trip.score}

    @app.get("/api/drivers")
    def list_drivers(session: Session = Depends(get_session)):
        return _driver_rows(session)

    @app.get("/api/drivers/{driver_id}")
    def driver_detail(driver_id: str, session: Session = Depends(get_session)):
        detail = _driver_detail(session, driver_id)
        if detail is None:
            raise HTTPException(404, f"unknown driver {driver_id}")
        return detail

    @app.get("/api/reports/{driver_id}")
    def driver_report(driver_id: str, session: Session = Depends(get_session)):
        return driver_detail(driver_id, session)

    @app.get("/api/trips/{trip_id}")
    def trip_detail(trip_id: str, session: Session = Depends(get_session)):
        trip = session.get(Trip, trip_id)
        if trip is None:
            raise HTTPException(404, f"unknown trip {trip_id}")
        return json.loads(trip.result_json)

    @app.get("/api/map/hotspots")
    def hotspots(session: Session = Depends(get_session)):
        return _hotspots(session)

    # ---- Dashboard -------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def fleet_page(request: Request, session: Session = Depends(get_session)):
        rows = _driver_rows(session)
        for row in rows:
            row["sparkline"] = charts.svg_sparkline(row.pop("trend"))
        weekly = _fleet_weekly(session)
        return templates.TemplateResponse(
            request,
            "fleet.html",
            {
                "rows": rows,
                "fleet_chart": charts.trend_chart_uri(
                    [w["week"] for w in weekly],
                    [w["score"] for w in weekly],
                    label_fr("safety_score"),
                ),
            },
        )

    @app.get("/drivers/{driver_id}", response_class=HTMLResponse)
    def driver_page(driver_id: str, request: Request, session: Session = Depends(get_session)):
        detail = _driver_detail(session, driver_id)
        if detail is None:
            raise HTTPException(404, f"unknown driver {driver_id}")
        chart = charts.trend_chart_uri(
            [w["week"] for w in detail["weekly_scores"]],
            [w["score"] for w in detail["weekly_scores"]],
            label_fr("safety_score"),
        )
        return templates.TemplateResponse(
            request, "driver.html", {"d": detail, "trend_chart": chart}
        )

    @app.get("/map", response_class=HTMLResponse)
    def map_page(request: Request, session: Session = Depends(get_session)):
        return templates.TemplateResponse(
            request, "map.html", {"map_html": _heatmap_html(session)}
        )

    @app.get("/trips/{trip_id}", response_class=HTMLResponse)
    def trip_page(trip_id: str, request: Request, session: Session = Depends(get_session)):
        trip = session.get(Trip, trip_id)
        if trip is None:
            raise HTTPException(404, f"unknown trip {trip_id}")
        result = json.loads(trip.result_json)
        return templates.TemplateResponse(
            request,
            "trip.html",
            {
                "trip": trip,
                "events": result["events"],
                "map_html": _trip_map_html(result),
            },
        )

    return app


# ---- Query helpers (shared by JSON API and dashboard) ---------------------


def _driver_rows(session: Session) -> list[dict]:
    """One row per driver, sorted worst score first (coaching priority).

    The headline score is the distance-weighted mean of the last 8 driven
    weeks — one clean latest week must not hide a bad month.
    """
    rows = []
    for driver in session.query(Driver).all():
        weekly = (
            session.query(PeriodScore)
            .filter_by(driver_id=driver.id, period="week")
            .order_by(PeriodScore.period_start)
            .all()
        )
        recent = weekly[-8:]
        recent_km = sum(w.distance_km for w in recent)
        trips = session.query(Trip).filter_by(driver_id=driver.id).all()
        rows.append(
            {
                "driver_id": driver.id,
                "score": round(
                    sum(w.score * w.distance_km for w in recent) / recent_km, 1
                )
                if recent_km > 0
                else None,
                "trend": [w.score for w in recent],
                "trip_count": len(trips),
                "distance_km": round(sum(t.distance_km for t in trips), 1),
                "event_count": sum(len(t.events) for t in trips),
            }
        )
    rows.sort(key=lambda r: (r["score"] is None, r["score"]))
    return rows


def _driver_detail(session: Session, driver_id: str) -> dict | None:
    driver = session.get(Driver, driver_id)
    if driver is None:
        return None
    weekly = (
        session.query(PeriodScore)
        .filter_by(driver_id=driver_id, period="week")
        .order_by(PeriodScore.period_start)
        .all()
    )
    trips = (
        session.query(Trip)
        .filter_by(driver_id=driver_id)
        .order_by(Trip.start_time.desc())
        .all()
    )
    event_types = Counter(e.type for t in trips for e in t.events)
    return {
        "driver_id": driver_id,
        "weekly_scores": [
            {
                "week": w.period_start,
                "score": w.score,
                "distance_km": w.distance_km,
                "trip_count": w.trip_count,
                "event_count": w.event_count,
            }
            for w in weekly
        ],
        "event_types": dict(event_types),
        "trips": [
            {
                "trip_id": t.id,
                "start_time": t.start_time,
                "distance_km": t.distance_km,
                "score": t.score,
                "event_count": len(t.events),
            }
            for t in trips
        ],
        "worst_trips": sorted(
            (
                {"trip_id": t.id, "score": t.score, "start_time": t.start_time}
                for t in trips
            ),
            key=lambda t: t["score"],
        )[:5],
    }


def _fleet_weekly(session: Session) -> list[dict]:
    """Distance-weighted mean weekly score across all drivers."""
    buckets = defaultdict(list)
    for row in session.query(PeriodScore).filter_by(period="week").all():
        buckets[row.period_start].append(row)
    return [
        {
            "week": week,
            "score": round(
                sum(r.score * r.distance_km for r in rows)
                / max(sum(r.distance_km for r in rows), 0.001),
                1,
            ),
        }
        for week, rows in sorted(buckets.items())
    ]


def _hotspots(session: Session) -> list[dict]:
    """Events aggregated on a ~110 m grid, riskiest cells first."""
    cells: dict[tuple[float, float], list[TripEvent]] = defaultdict(list)
    for event in session.query(TripEvent).all():
        key = (round(event.lat, HOTSPOT_GRID_DECIMALS), round(event.lon, HOTSPOT_GRID_DECIMALS))
        cells[key].append(event)
    spots = [
        {
            "lat": lat,
            "lon": lon,
            "count": len(events),
            "worst_severity": max(events, key=lambda e: SEVERITY_ORDER[e.severity]).severity,
            "types": dict(Counter(e.type for e in events)),
        }
        for (lat, lon), events in cells.items()
    ]
    spots.sort(key=lambda s: -s["count"])
    return spots[:200]


SEVERITY_COLORS = {"low": "#2b7de9", "medium": "#e6a100", "high": "#d63031"}


def _trip_map_html(result: dict) -> str:
    """Replay map for one stored trip: route polyline + event pins."""
    import html as html_mod

    import folium

    route = result.get("route") or []
    events = result.get("events", [])
    points = route or [[e["lat"], e["lon"]] for e in events]
    if not points:
        return f"<p>{label('no_data')}</p>"

    fmap = folium.Map(tiles="OpenStreetMap")
    fmap.fit_bounds(
        [
            [min(p[0] for p in points), min(p[1] for p in points)],
            [max(p[0] for p in points), max(p[1] for p in points)],
        ]
    )
    if route:
        folium.PolyLine(route, color="#1a4f8b", weight=3, opacity=0.8).add_to(fmap)
    for event in events:
        folium.CircleMarker(
            location=[event["lat"], event["lon"]],
            radius=8,
            color=SEVERITY_COLORS[event["severity"]],
            fill=True,
            fill_opacity=0.9,
            tooltip=f"{event['type']} ({event['severity']}) {event['start']}–{event['end']}",
        ).add_to(fmap)
    rendered = fmap.get_root().render()
    return (
        f'<iframe srcdoc="{html_mod.escape(rendered, quote=True)}" '
        'style="width:100%;height:420px;border:1px solid #ddd;border-radius:6px;"></iframe>'
    )


def _heatmap_html(session: Session) -> str:
    import html as html_mod

    import folium
    from folium.plugins import HeatMap

    events = session.query(TripEvent).all()
    if not events:
        return f"<p>{label('no_data')}</p>"
    # open on the #1 hotspot: the map's job is "where do events repeat",
    # and fitting all events zooms out to continent scale once a fleet
    # spans cities
    top = _hotspots(session)[0]
    fmap = folium.Map(location=[top["lat"], top["lon"]], zoom_start=13, tiles="OpenStreetMap")
    HeatMap(
        [(e.lat, e.lon, 1 + SEVERITY_ORDER[e.severity]) for e in events],
        radius=18,
    ).add_to(fmap)
    rendered = fmap.get_root().render()
    return (
        f'<iframe srcdoc="{html_mod.escape(rendered, quote=True)}" '
        'style="width:100%;height:75vh;border:1px solid #ddd;border-radius:6px;"></iframe>'
    )
