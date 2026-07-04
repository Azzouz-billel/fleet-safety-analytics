"""Harsh-acceleration detection — the positive-side mirror of harsh braking."""

import pandas as pd

from .. import config
from ..schemas import Event, Meta
from . import clock, find_runs, merge_runs, severity_from

MPS_TO_KMH = 3.6


def detect_harsh_accel(gps: pd.DataFrame, meta: Meta, accel: pd.Series) -> list[Event]:
    """Detect harsh-acceleration events on a processed GPS frame."""
    harsh = (accel >= config.HARSH_ACCEL_MPS2).to_numpy()

    events = []
    for start, end in merge_runs(find_runs(harsh), gps["t"], config.HARSH_MERGE_GAP_S):
        window = slice(start, end + 1)
        peak = float(accel.iloc[window].max())
        events.append(
            Event(
                type="harsh_accel",
                start=clock(meta, gps["t"].iloc[start]),
                end=clock(meta, gps["t"].iloc[end]),
                start_s=float(gps["t"].iloc[start]),
                end_s=float(gps["t"].iloc[end]),
                lat=float(gps["lat"].iloc[window].mean()),
                lon=float(gps["lon"].iloc[window].mean()),
                speed_kmh=round(float(gps["speed_raw_mps"].iloc[start]) * MPS_TO_KMH, 1),
                peak_mps2=round(peak, 2),
                severity=severity_from(peak, config.HARSH_ACCEL_SEVERITY_BOUNDS),
            )
        )
    return events
