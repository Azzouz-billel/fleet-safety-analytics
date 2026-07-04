"""Event detectors and shared run-grouping helpers.

Detectors consume a processed GPS frame (see gps.process_gps) and return
schemas.Event lists. Shared here: boolean-mask run finding, run merging,
severity banding, and wall-clock formatting.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from ..schemas import Meta, Severity


def find_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) index pairs of consecutive True runs."""
    padded = np.concatenate([[False], mask, [False]])
    edges = np.flatnonzero(np.diff(padded.astype(int)))
    return [(int(edges[i]), int(edges[i + 1] - 1)) for i in range(0, len(edges), 2)]


def merge_runs(runs: list[tuple[int, int]], t: pd.Series, max_gap_s: float) -> list[tuple[int, int]]:
    """Merge runs whose time gap is below max_gap_s (one physical event
    often splits into several samples of threshold crossing)."""
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged and t.iloc[start] - t.iloc[merged[-1][1]] <= max_gap_s:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def severity_from(value: float, bounds: dict[str, float]) -> Severity:
    """Band a magnitude into low/medium/high using config bounds."""
    if value < bounds["low"]:
        return "low"
    if value < bounds["medium"]:
        return "medium"
    return "high"


def clock(meta: Meta, t_s: float) -> str:
    """Wall-clock HH:MM:SS for a shared-clock offset."""
    return (meta.start_time + timedelta(seconds=float(t_s))).strftime("%H:%M:%S")
