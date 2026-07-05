import math

import numpy as np
import pandas as pd
import pytest

from fleetsafety.schemas import Meta
from fleetsafety.vision.detect import Box, FrameDetections
from fleetsafety.vision.tailgating import detect_tailgating

# Synthetic staging: 1000×600 frame, focal 700 px, own speed 20 m/s.
# A lead car (real width 1.8 m) at distance d shows as a centered box of
# width 1.8*700/d px, so d=24 m → gap 1.2 s (medium), d=60 m → gap 3 s.

FRAME_W, FRAME_H, FOCAL = 1000, 600, 700.0
SPEED_MPS = 20.0


def make_meta() -> Meta:
    return Meta(
        trip_id="t1",
        vehicle_id="v1",
        driver_id="d1",
        start_time="2026-07-05T09:00:00Z",
        default_speed_limit_kmh=100,
    )


def make_gps(duration_s: float) -> pd.DataFrame:
    t = np.arange(duration_s + 1)
    return pd.DataFrame(
        {"t": t, "lat": 35.71 + t * 1e-4, "lon": -0.63, "speed_smooth_mps": SPEED_MPS}
    )


def lead_frame(t_s: float, distance_m: float) -> FrameDetections:
    width_px = 1.8 * FOCAL / distance_m
    box = Box(cls="car", conf=0.9, xywh=(FRAME_W / 2, 400.0, width_px, width_px * 0.8))
    return FrameDetections(frame_index=int(t_s * 10), t_s=t_s, boxes=[box])


def staged_frames(close_from_s: float, close_to_s: float, hz: float = 5.0) -> list[FrameDetections]:
    return [
        lead_frame(t, 24.0 if close_from_s <= t <= close_to_s else 60.0)
        for t in np.arange(0.0, 30.0, 1.0 / hz)
    ]


@pytest.fixture(scope="module")
def close_follow_events():
    frames = staged_frames(close_from_s=10.0, close_to_s=20.0)
    return detect_tailgating(frames, make_gps(30), make_meta(), FRAME_W, FRAME_H, FOCAL)


def test_close_following_yields_exactly_one_event(close_follow_events):
    assert len(close_follow_events) == 1


def test_event_spans_the_staged_close_interval(close_follow_events):
    event = close_follow_events[0]
    assert (event.start_s, event.end_s) == pytest.approx((10.0, 20.0), abs=1.0)


def test_min_gap_matches_staged_distance(close_follow_events):
    assert close_follow_events[0].gap_s == pytest.approx(24.0 / SPEED_MPS, abs=0.05)


def test_gap_of_1_2s_is_medium_severity(close_follow_events):
    assert close_follow_events[0].severity == "medium"


def test_large_gaps_yield_no_events():
    frames = [lead_frame(t, 80.0) for t in np.arange(0.0, 30.0, 0.2)]
    events = detect_tailgating(frames, make_gps(30), make_meta(), FRAME_W, FRAME_H, FOCAL)
    assert events == []


def test_brief_close_pass_is_not_sustained_tailgating():
    frames = staged_frames(close_from_s=10.0, close_to_s=11.0)
    events = detect_tailgating(frames, make_gps(30), make_meta(), FRAME_W, FRAME_H, FOCAL)
    assert events == []


def test_offcenter_vehicles_are_not_leads():
    frames = [
        FrameDetections(
            frame_index=i,
            t_s=t,
            boxes=[Box(cls="car", conf=0.9, xywh=(100.0, 400.0, 60.0, 50.0))],
        )
        for i, t in enumerate(np.arange(0.0, 30.0, 0.2))
    ]
    events = detect_tailgating(frames, make_gps(30), make_meta(), FRAME_W, FRAME_H, FOCAL)
    assert events == []


def test_low_speed_queueing_is_ignored():
    frames = staged_frames(close_from_s=0.0, close_to_s=30.0)
    gps = make_gps(30).assign(speed_smooth_mps=2.0)
    events = detect_tailgating(frames, gps, make_meta(), FRAME_W, FRAME_H, FOCAL)
    assert events == []
