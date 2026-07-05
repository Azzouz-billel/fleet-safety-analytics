"""Data contracts for the whole pipeline.

Everything downstream (ingest, events, scoring, report, API) depends on
these models. Input contract: a trip package on disk (gps.csv, meta.json,
optional imu.csv/video.mp4). Output contract: TripResult, serialized as
the canonical result.json.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EventType = Literal["speeding", "harsh_braking", "harsh_accel", "tailgating"]
Severity = Literal["low", "medium", "high"]


class Meta(BaseModel):
    """Contents of meta.json in a trip package."""

    trip_id: str
    vehicle_id: str
    driver_id: str
    start_time: datetime
    fps: Optional[int] = None
    resolution: Optional[tuple[int, int]] = None
    camera_focal_px: Optional[float] = None  # for tailgating distance; else estimated
    default_speed_limit_kmh: float = 100.0


class GpsSample(BaseModel):
    """One row of gps.csv. `t` is seconds from trip start (shared clock)."""

    t: float
    lat: float
    lon: float
    speed_mps: Optional[float] = None
    heading: Optional[float] = None


class ImuSample(BaseModel):
    """One row of imu.csv. Accelerations m/s², gyro rad/s."""

    t: float
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float


class Event(BaseModel):
    """A detected safety event.

    `start`/`end` are wall-clock HH:MM:SS for the report; `start_s`/`end_s`
    are seconds from trip start (the shared clock, used for clip export
    in Phase 2). `peak_mps2` is set for harsh braking/acceleration,
    `gap_s` (minimum following time-gap) for tailgating.
    """

    type: EventType
    start: str
    end: str
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    lat: float
    lon: float
    speed_kmh: Optional[float] = None
    limit_kmh: Optional[float] = None
    peak_mps2: Optional[float] = None
    gap_s: Optional[float] = None
    severity: Severity
    clip: Optional[str] = None


class TripSummary(BaseModel):
    distance_km: float
    duration_min: float
    max_speed_kmh: float
    avg_speed_kmh: float
    event_counts: dict[str, int] = Field(default_factory=dict)


class Score(BaseModel):
    """Explainable score: `value` is 0–100, `breakdown` maps each event
    type to the penalty points it cost (already normalized per 100 km)."""

    value: float
    breakdown: dict[str, float] = Field(default_factory=dict)


class TripResult(BaseModel):
    """Canonical output of `fleetsafety process` (result.json)."""

    trip_id: str
    driver_id: str
    vehicle_id: str
    summary: TripSummary
    events: list[Event] = Field(default_factory=list)
    score: Score
