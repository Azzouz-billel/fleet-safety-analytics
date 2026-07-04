import pytest

from fleetsafety.schemas import Event
from fleetsafety.scoring import score_trip

# With config defaults: weight(speeding)=2, weight(harsh_braking)=3,
# multiplier(low)=1, (medium)=2, (high)=3; floor distance 50 km.


def make_event(event_type: str, severity: str) -> Event:
    return Event(
        type=event_type,
        start="12:00:00",
        end="12:00:10",
        lat=35.71,
        lon=-0.63,
        severity=severity,
    )


def test_clean_trip_scores_100():
    assert score_trip([], distance_km=100.0).value == 100.0


def test_one_low_speeding_event_costs_its_documented_penalty():
    score = score_trip([make_event("speeding", "low")], distance_km=100.0)
    assert score.value == 98.0


def test_one_high_harsh_brake_costs_its_documented_penalty():
    score = score_trip([make_event("harsh_braking", "high")], distance_km=100.0)
    assert score.value == 91.0


def test_breakdown_sums_back_to_the_score():
    events = [
        make_event("speeding", "medium"),
        make_event("speeding", "low"),
        make_event("harsh_braking", "high"),
    ]
    score = score_trip(events, distance_km=100.0)
    assert score.value == pytest.approx(100.0 - sum(score.breakdown.values()))


def test_short_trips_normalize_with_the_floor_distance():
    score = score_trip([make_event("speeding", "low")], distance_km=5.0)
    assert score.value == 96.0


def test_score_clamps_at_zero():
    events = [make_event("harsh_braking", "high")] * 20
    assert score_trip(events, distance_km=10.0).value == 0.0
