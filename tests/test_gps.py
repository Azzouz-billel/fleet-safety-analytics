import numpy as np
import pandas as pd
import pytest

from fleetsafety.cli import validate_trip
from fleetsafety.gps import process_gps, trip_distance_km, trip_duration_min

INJECTED_SPEED_MPS = 20.0
SAMPLES = 100
METERS_PER_DEG_LAT = 111_320.0


def straight_line_trip() -> pd.DataFrame:
    """1 Hz constant-speed run due north with no device speed column."""
    t = np.arange(SAMPLES, dtype=float)
    return pd.DataFrame(
        {
            "t": t,
            "lat": 35.71 + t * INJECTED_SPEED_MPS / METERS_PER_DEG_LAT,
            "lon": np.full(SAMPLES, -0.63),
        }
    )


def test_derived_speed_matches_injected_within_5pct():
    gps = process_gps(straight_line_trip())
    assert gps["speed_raw_mps"].mean() == pytest.approx(INJECTED_SPEED_MPS, rel=0.05)


def test_distance_matches_injected_within_5pct():
    gps = process_gps(straight_line_trip())
    expected_km = INJECTED_SPEED_MPS * (SAMPLES - 1) / 1000.0
    assert trip_distance_km(gps) == pytest.approx(expected_km, rel=0.05)


def test_duration_is_time_span_of_fixes():
    gps = process_gps(straight_line_trip())
    assert trip_duration_min(gps) == pytest.approx((SAMPLES - 1) / 60.0)


def test_constant_speed_has_no_spurious_acceleration():
    gps = process_gps(straight_line_trip())
    assert gps["accel_mps2"].abs().max() < 0.1


def test_empty_device_speed_falls_back_to_derived():
    trip = straight_line_trip().assign(speed_mps=np.nan)
    gps = process_gps(trip)
    assert gps["speed_raw_mps"].equals(gps["speed_derived_mps"])


def test_sample_trip_device_speed_validates_against_positions(sample_trip_dir):
    assert validate_trip(sample_trip_dir) is True
