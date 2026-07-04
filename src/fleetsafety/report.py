"""One-page HTML trip report.

Self-contained file: the matplotlib speed chart is embedded as a base64
PNG and the folium map as an inline iframe, so the report opens offline
and can be emailed as a single artifact. (PDF export can come later via
weasyprint/HTML-to-PDF; HTML covers the Phase 1 acceptance.)
"""

import base64
import html
import io
from pathlib import Path

import folium
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .schemas import Meta, TripResult

MPS_TO_KMH = 3.6

SEVERITY_COLORS = {"low": "#2b7de9", "medium": "#e6a100", "high": "#d63031"}


def generate_report(result: TripResult, meta: Meta, gps: pd.DataFrame, out_path: Path) -> Path:
    """Render the one-page HTML report for a processed trip."""
    chart_b64 = _speed_chart_b64(result, meta, gps)
    map_html = _event_map_html(result, gps)
    out_path.write_text(_render_page(result, meta, chart_b64, map_html))
    return out_path


def _speed_chart_b64(result: TripResult, meta: Meta, gps: pd.DataFrame) -> str:
    minutes = gps["t"] / 60.0
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=110)
    ax.plot(minutes, gps["speed_smooth_mps"] * MPS_TO_KMH, color="#1a4f8b", lw=1.6, label="speed")
    ax.axhline(meta.default_speed_limit_kmh, color="#d63031", ls="--", lw=1.2, label="limit")
    for event in result.events:
        if event.type == "speeding" and event.start_s is not None:
            ax.axvspan(event.start_s / 60.0, event.end_s / 60.0, color="#d63031", alpha=0.15)
    ax.set_xlabel("trip time (min)")
    ax.set_ylabel("km/h")
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode()


def _event_map_html(result: TripResult, gps: pd.DataFrame) -> str:
    center = [float(gps["lat"].mean()), float(gps["lon"].mean())]
    fmap = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap")
    route = list(zip(gps["lat"][::5], gps["lon"][::5]))
    folium.PolyLine(route, color="#1a4f8b", weight=3, opacity=0.8).add_to(fmap)
    for event in result.events:
        folium.CircleMarker(
            location=[event.lat, event.lon],
            radius=8,
            color=SEVERITY_COLORS[event.severity],
            fill=True,
            fill_opacity=0.9,
            tooltip=f"{event.type} ({event.severity}) {event.start}–{event.end}",
        ).add_to(fmap)
    rendered = fmap.get_root().render()
    return (
        f'<iframe srcdoc="{html.escape(rendered, quote=True)}" '
        'style="width:100%;height:340px;border:1px solid #ddd;border-radius:6px;"></iframe>'
    )


def _render_page(result: TripResult, meta: Meta, chart_b64: str, map_html: str) -> str:
    summary = result.summary
    penalty_rows = "".join(
        f"<tr><td>{html.escape(kind)}</td><td>−{points:.2f}</td></tr>"
        for kind, points in result.score.breakdown.items()
    ) or '<tr><td colspan="2">no penalties — clean trip</td></tr>'

    event_rows = "".join(
        "<tr>"
        f"<td>{html.escape(event.type)}</td>"
        f"<td>{event.start}–{event.end}</td>"
        f"<td>{event.lat:.5f}, {event.lon:.5f}</td>"
        f"<td>{_event_detail(event)}</td>"
        f'<td><span class="sev sev-{event.severity}">{event.severity}</span></td>'
        "</tr>"
        for event in result.events
    ) or '<tr><td colspan="5">no events detected</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Trip report — {html.escape(result.trip_id)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 24px auto; max-width: 920px; color: #222; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .meta {{ color: #666; margin-bottom: 16px; }}
  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .card {{ border: 1px solid #ddd; border-radius: 6px; padding: 10px 16px; }}
  .card .label {{ font-size: 0.75rem; color: #666; text-transform: uppercase; }}
  .card .value {{ font-size: 1.3rem; font-weight: 600; }}
  .score {{ background: #1a4f8b; color: #fff; border-color: #1a4f8b; }}
  .score .label {{ color: #cfe0f5; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0 20px; font-size: 0.9rem; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
  th {{ background: #f5f7fa; }}
  .sev {{ padding: 2px 8px; border-radius: 10px; color: #fff; font-size: 0.8rem; }}
  .sev-low {{ background: {SEVERITY_COLORS['low']}; }}
  .sev-medium {{ background: {SEVERITY_COLORS['medium']}; }}
  .sev-high {{ background: {SEVERITY_COLORS['high']}; }}
  img.chart {{ max-width: 100%; }}
  h2 {{ font-size: 1.05rem; margin-top: 24px; }}
</style>
</head>
<body>
<h1>Driver safety report — trip {html.escape(result.trip_id)}</h1>
<div class="meta">
  Driver {html.escape(result.driver_id)} · Vehicle {html.escape(result.vehicle_id)} ·
  {meta.start_time.strftime("%Y-%m-%d %H:%M %Z")}
</div>

<div class="cards">
  <div class="card score"><div class="label">Safety score</div><div class="value">{result.score.value:.0f}/100</div></div>
  <div class="card"><div class="label">Distance</div><div class="value">{summary.distance_km:.1f} km</div></div>
  <div class="card"><div class="label">Duration</div><div class="value">{summary.duration_min:.0f} min</div></div>
  <div class="card"><div class="label">Max speed</div><div class="value">{summary.max_speed_kmh:.0f} km/h</div></div>
  <div class="card"><div class="label">Avg speed</div><div class="value">{summary.avg_speed_kmh:.0f} km/h</div></div>
</div>

<h2>Speed over time (shaded = speeding)</h2>
<img class="chart" src="data:image/png;base64,{chart_b64}" alt="speed chart">

<h2>Event map</h2>
{map_html}

<h2>Events</h2>
<table>
<tr><th>Type</th><th>Time</th><th>Location</th><th>Detail</th><th>Severity</th></tr>
{event_rows}
</table>

<h2>Score breakdown (100 − penalties, per 100 km)</h2>
<table>
<tr><th>Event type</th><th>Penalty</th></tr>
{penalty_rows}
</table>
</body>
</html>
"""


def _event_detail(event) -> str:
    if event.type == "speeding":
        return f"{event.speed_kmh:.0f} km/h in a {event.limit_kmh:.0f} zone"
    return f"peak {event.peak_mps2:.1f} m/s²"
