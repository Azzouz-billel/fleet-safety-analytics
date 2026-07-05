"""Tailgating detection (Task 2.4).

Per analyzed frame: pick the lead vehicle (box near the horizontal center,
in the near field), estimate its distance with a pinhole model
(assumed car width × focal / box width), divide by own GPS speed to get a
time-gap, and flag sustained gaps under the configured threshold.

The distance estimate is deliberately simple — MVP per the build guide;
comma2k19 radar or camera calibration can refine it later without
changing the event contract.
"""

import logging
import math

import numpy as np
import pandas as pd

from .. import config
from ..events import clock, find_runs, merge_runs
from ..schemas import Event, Meta, Severity
from .detect import FrameDetections

logger = logging.getLogger(__name__)

MPS_TO_KMH = 3.6


def detect_tailgating(
    tracked: list[FrameDetections],
    gps: pd.DataFrame,
    meta: Meta,
    frame_width: int,
    frame_height: int,
    focal_px: float | None = None,
) -> list[Event]:
    """Detect tailgating events from tracked frames + processed GPS."""
    if not tracked:
        return []
    focal = focal_px or config.CAMERA_FOCAL_WIDTH_RATIO * frame_width

    times = np.array([f.t_s for f in tracked])
    speeds = np.interp(times, gps["t"], gps["speed_smooth_mps"])
    gaps = np.array(
        [
            _time_gap(frame, speed, frame_width, frame_height, focal)
            for frame, speed in zip(tracked, speeds)
        ]
    )

    t_series = pd.Series(times)
    close = gaps < config.TAILGATING_MAX_GAP_S
    events = []
    for start, end in merge_runs(find_runs(close), t_series, config.HARSH_MERGE_GAP_S):
        duration = times[end] - times[start]
        if duration < config.TAILGATING_MIN_DURATION_S:
            continue
        min_gap = float(np.min(gaps[start : end + 1]))
        lat = float(np.interp(times[start], gps["t"], gps["lat"]))
        lon = float(np.interp(times[start], gps["t"], gps["lon"]))
        events.append(
            Event(
                type="tailgating",
                start=clock(meta, times[start]),
                end=clock(meta, times[end]),
                start_s=float(times[start]),
                end_s=float(times[end]),
                lat=lat,
                lon=lon,
                speed_kmh=round(float(speeds[start]) * MPS_TO_KMH, 1),
                gap_s=round(min_gap, 2),
                severity=_severity_from_gap(min_gap),
            )
        )
    logger.info("tailgating: %d event(s) over %d analyzed frames", len(events), len(tracked))
    return events


def _time_gap(
    frame: FrameDetections, speed_mps: float, frame_width: int, frame_height: int, focal: float
) -> float:
    """Seconds to reach the lead vehicle; inf when there is none to worry about."""
    if speed_mps < config.TAILGATING_MIN_SPEED_MPS:
        return math.inf
    lead_width_px = _lead_box_width(frame, frame_width, frame_height)
    if lead_width_px is None:
        return math.inf
    distance_m = config.LEAD_VEHICLE_WIDTH_M * focal / lead_width_px
    return distance_m / speed_mps


def _lead_box_width(frame: FrameDetections, frame_width: int, frame_height: int) -> float | None:
    """Widest (= nearest) vehicle box near the center of our lane, in the
    near field (its bottom edge below mid-frame). None if no candidate."""
    candidates = [
        box.xywh[2]
        for box in frame.boxes
        if abs(box.xywh[0] - frame_width / 2) < frame_width / 6
        and box.xywh[1] + box.xywh[3] / 2 > frame_height / 2
    ]
    return max(candidates) if candidates else None


def _severity_from_gap(gap_s: float) -> Severity:
    if gap_s < config.TAILGATING_SEVERITY_BOUNDS_S["high"]:
        return "high"
    if gap_s < config.TAILGATING_SEVERITY_BOUNDS_S["medium"]:
        return "medium"
    return "low"
