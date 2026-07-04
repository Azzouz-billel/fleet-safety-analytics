"""Explainable safety score.

    score = 100 − Σ (weight[event_type] × severity_multiplier × count)
            normalized per 100 km, clamped to [0, 100]

The breakdown maps each event type to the exact penalty it cost, so
`100 − sum(breakdown.values())` reproduces the (pre-clamp) score. Weights
and multipliers live in config.py.
"""

from . import config
from .schemas import Event, Score


def score_trip(events: list[Event], distance_km: float) -> Score:
    """Score a trip from its detected events and driven distance.

    Distances below SCORE_NORMALIZATION_FLOOR_KM normalize as if the trip
    were that long — otherwise one event on a short hop craters the score.
    """
    per_100km = 100.0 / max(distance_km, config.SCORE_NORMALIZATION_FLOOR_KM)

    breakdown: dict[str, float] = {}
    for event in events:
        penalty = (
            config.SCORE_WEIGHTS[event.type]
            * config.SEVERITY_MULTIPLIER[event.severity]
            * per_100km
        )
        breakdown[event.type] = breakdown.get(event.type, 0.0) + penalty

    breakdown = {kind: round(points, 2) for kind, points in breakdown.items()}
    value = max(0.0, min(100.0, 100.0 - sum(breakdown.values())))
    return Score(value=round(value, 1), breakdown=breakdown)
