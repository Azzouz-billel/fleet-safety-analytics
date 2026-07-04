"""Speeding detection.

Flags stretches where smoothed speed exceeds limit * (1 + tolerance) for
at least the configured minimum duration; each stretch becomes one Event
with peak speed, mean location, and severity from peak fraction over.
"""

import pandas as pd

from .. import config
from ..schemas import Event, Meta
from ..speed import limit_series_kmh
from . import clock, find_runs, severity_from

MPS_TO_KMH = 3.6


def detect_speeding(gps: pd.DataFrame, meta: Meta) -> list[Event]:
    """Detect speeding events on a processed GPS frame."""
    speed_kmh = gps["speed_smooth_mps"] * MPS_TO_KMH
    limits = limit_series_kmh(gps, meta.default_speed_limit_kmh)
    over = (speed_kmh > limits * (1.0 + config.SPEEDING_TOLERANCE)).to_numpy()

    events = []
    for start, end in find_runs(over):
        duration = gps["t"].iloc[end] - gps["t"].iloc[start]
        if duration < config.SPEEDING_MIN_DURATION_S:
            continue
        window = slice(start, end + 1)
        peak_kmh = float(speed_kmh.iloc[window].max())
        limit_kmh = float(limits.iloc[window].median())
        fraction_over = peak_kmh / limit_kmh - 1.0
        events.append(
            Event(
                type="speeding",
                start=clock(meta, gps["t"].iloc[start]),
                end=clock(meta, gps["t"].iloc[end]),
                start_s=float(gps["t"].iloc[start]),
                end_s=float(gps["t"].iloc[end]),
                lat=float(gps["lat"].iloc[window].mean()),
                lon=float(gps["lon"].iloc[window].mean()),
                speed_kmh=round(peak_kmh, 1),
                limit_kmh=round(limit_kmh, 1),
                severity=severity_from(fraction_over, config.SPEEDING_SEVERITY_BOUNDS),
            )
        )
    return events
