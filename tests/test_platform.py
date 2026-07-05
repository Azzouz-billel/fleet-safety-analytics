import pytest
from fastapi.testclient import TestClient

from fleetsafety.platform.api import create_app

# Two drivers, three trips across two ISO weeks (2026-06-29 and 2026-07-06
# both start weeks). drv_a drives clean+dirty, drv_b one clean trip.


def make_result(trip_id, driver, day, score_events):
    events = [
        {
            "type": kind,
            "start": "10:00:00",
            "end": "10:00:10",
            "start_s": 60.0,
            "end_s": 70.0,
            "lat": 35.71,
            "lon": -0.63,
            "severity": severity,
        }
        for kind, severity in score_events
    ]
    counts = {"speeding": 0, "harsh_braking": 0, "harsh_accel": 0, "tailgating": 0}
    for kind, _ in score_events:
        counts[kind] += 1
    return {
        "trip_id": trip_id,
        "driver_id": driver,
        "vehicle_id": "veh_1",
        "start_time": f"2026-07-{day:02d}T10:00:00Z",
        "route": [[35.71, -0.63], [35.72, -0.62], [35.73, -0.61]],
        "summary": {
            "distance_km": 50.0,
            "duration_min": 45.0,
            "max_speed_kmh": 90.0,
            "avg_speed_kmh": 60.0,
            "event_counts": counts,
        },
        "events": events,
        "score": {"value": 90.0, "breakdown": {}},
    }


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    app = create_app(tmp_path_factory.mktemp("db") / "fleet.db")
    client = TestClient(app)
    client.post("/api/trips", json=make_result("trip_a1", "drv_a", 1, []))
    client.post("/api/trips", json=make_result(
        "trip_a2", "drv_a", 7, [("speeding", "high"), ("harsh_braking", "medium")]))
    client.post("/api/trips", json=make_result("trip_b1", "drv_b", 7, []))
    return client


def test_ingest_returns_created(client):
    response = client.post("/api/trips", json=make_result("trip_x", "drv_x", 8, []))
    assert response.status_code == 201


def test_reposting_a_trip_is_idempotent(client):
    client.post("/api/trips", json=make_result("trip_b1", "drv_b", 7, []))
    trips = client.get("/api/drivers/drv_b").json()["trips"]
    assert len(trips) == 1


def test_drivers_sorted_worst_first(client):
    drivers = [d["driver_id"] for d in client.get("/api/drivers").json()]
    assert drivers.index("drv_a") < drivers.index("drv_b")


def test_driver_detail_has_weekly_scores_per_week(client):
    detail = client.get("/api/drivers/drv_a").json()
    assert len(detail["weekly_scores"]) == 2


def test_clean_week_scores_100(client):
    detail = client.get("/api/drivers/drv_a").json()
    assert detail["weekly_scores"][0]["score"] == 100.0


def test_dirty_week_scores_documented_penalty(client):
    # speeding high (2*3) + harsh_braking medium (3*2) = 12 per 100 km,
    # over 50 km with the 50 km floor → 100 - 12*2 = 76
    detail = client.get("/api/drivers/drv_a").json()
    assert detail["weekly_scores"][1]["score"] == 76.0


def test_trip_detail_round_trips_the_result(client):
    assert client.get("/api/trips/trip_a2").json()["trip_id"] == "trip_a2"


def test_unknown_driver_is_404(client):
    assert client.get("/api/drivers/ghost").status_code == 404


def test_hotspots_aggregate_events_at_same_location(client):
    spots = client.get("/api/map/hotspots").json()
    assert spots[0]["count"] == 2


def test_fleet_dashboard_renders(client):
    assert "drv_a" in client.get("/").text


def test_driver_dashboard_renders_bilingual_labels(client):
    assert "درجة السلامة" in client.get("/drivers/drv_a").text


def test_map_page_renders(client):
    assert client.get("/map").status_code == 200


def test_trip_replay_page_renders_route_map(client):
    assert "iframe" in client.get("/trips/trip_a2").text


def test_trip_replay_lists_the_trip_events(client):
    assert "10:00:00" in client.get("/trips/trip_a2").text


def test_unknown_trip_replay_is_404(client):
    assert client.get("/trips/ghost").status_code == 404
