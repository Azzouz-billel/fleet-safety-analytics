"""Harsh-braking detection.

Flags where deceleration magnitude exceeds the configured threshold.
The acceleration series comes from the caller (IMU ax preferred, GPS
derived otherwise — see gps.accel_source); nearby spikes merge into one
event with peak decel, location, and severity from peak magnitude.
"""

import pandas as pd

from .. import config
from ..schemas import Event, Meta
from . import clock, find_runs, merge_runs, severity_from

MPS_TO_KMH = 3.6


def detect_harsh_braking(gps: pd.DataFrame, meta: Meta, accel: pd.Series) -> list[Event]:
    """Detect harsh-braking events on a processed GPS frame."""
    harsh = (accel <= -config.HARSH_BRAKING_MPS2).to_numpy()

    events = []
    for start, end in merge_runs(find_runs(harsh), gps["t"], config.HARSH_MERGE_GAP_S):
        window = slice(start, end + 1)
        peak = float(accel.iloc[window].abs().max())
        events.append(
            Event(
                type="harsh_braking",
                start=clock(meta, gps["t"].iloc[start]),
                end=clock(meta, gps["t"].iloc[end]),
                start_s=float(gps["t"].iloc[start]),
                end_s=float(gps["t"].iloc[end]),
                lat=float(gps["lat"].iloc[window].mean()),
                lon=float(gps["lon"].iloc[window].mean()),
                speed_kmh=round(float(gps["speed_raw_mps"].iloc[start]) * MPS_TO_KMH, 1),
                peak_mps2=round(peak, 2),
                severity=severity_from(peak, config.HARSH_BRAKING_SEVERITY_BOUNDS),
            )
        )
    return events
