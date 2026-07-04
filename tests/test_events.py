import pytest

from fleetsafety.events.harsh_accel import detect_harsh_accel
from fleetsafety.events.harsh_braking import detect_harsh_braking
from fleetsafety.events.speeding import detect_speeding

# Injected by scripts/make_sample_trip.py (see its SPEED_PROFILE):
# speeding #1 ~t=186–219 peak 119 km/h (medium), brake t=331–332,
# accel t=391–392, speeding #2 ~t=428–467 peak 108 km/h (low).


@pytest.fixture(scope="module")
def speeding_events(processed_sample):
    meta, gps, _ = processed_sample
    return detect_speeding(gps, meta)


def test_detects_exactly_two_speeding_stretches(speeding_events):
    assert len(speeding_events) == 2


def test_speeding_severities_match_injected_overages(speeding_events):
    assert [event.severity for event in speeding_events] == ["medium", "low"]


def test_first_speeding_stretch_starts_where_injected(speeding_events):
    assert speeding_events[0].start_s == pytest.approx(186.5, abs=5.0)


def test_first_speeding_stretch_ends_where_injected(speeding_events):
    assert speeding_events[0].end_s == pytest.approx(218.5, abs=5.0)


def test_speeding_peak_speed_matches_injected(speeding_events):
    assert speeding_events[0].speed_kmh == pytest.approx(118.8, abs=1.0)


def test_detects_exactly_one_harsh_brake_from_imu(processed_sample, imu_accel):
    meta, gps, _ = processed_sample
    assert len(detect_harsh_braking(gps, meta, imu_accel)) == 1


def test_detects_exactly_one_harsh_accel_from_imu(processed_sample, imu_accel):
    meta, gps, _ = processed_sample
    assert len(detect_harsh_accel(gps, meta, imu_accel)) == 1


def test_harsh_brake_peak_matches_injected_decel(processed_sample, imu_accel):
    meta, gps, _ = processed_sample
    assert detect_harsh_braking(gps, meta, imu_accel)[0].peak_mps2 == pytest.approx(4.67, abs=0.3)


def test_detects_exactly_one_harsh_brake_gps_only(processed_sample, gps_only_accel):
    meta, gps, _ = processed_sample
    assert len(detect_harsh_braking(gps, meta, gps_only_accel)) == 1


def test_detects_exactly_one_harsh_accel_gps_only(processed_sample, gps_only_accel):
    meta, gps, _ = processed_sample
    assert len(detect_harsh_accel(gps, meta, gps_only_accel)) == 1
