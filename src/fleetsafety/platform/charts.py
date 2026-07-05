"""Tiny server-side charts for the dashboard: inline SVG sparklines for
lists and a matplotlib data-URI for the driver trend (same pattern as
report.py, keeps pages self-contained with zero client JS)."""

import base64
import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def svg_sparkline(values: list[float], width: int = 120, height: int = 28) -> str:
    """Inline SVG polyline of scores (0–100 scale)."""
    if len(values) < 2:
        return ""
    step = width / (len(values) - 1)
    points = " ".join(
        f"{i * step:.1f},{height - (v / 100.0) * (height - 4) - 2:.1f}"
        for i, v in enumerate(values)
    )
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<polyline points="{points}" fill="none" stroke="#1a4f8b" stroke-width="2"/>'
        "</svg>"
    )


def trend_chart_uri(dates: list[date], scores: list[float], title: str) -> str:
    """Score-over-time chart as a data: URI (empty string if no data)."""
    if not dates:
        return ""
    fig, ax = plt.subplots(figsize=(8, 2.6), dpi=110)
    ax.plot(dates, scores, marker="o", color="#1a4f8b", lw=1.8)
    ax.set_ylim(0, 105)
    ax.set_ylabel(title)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
