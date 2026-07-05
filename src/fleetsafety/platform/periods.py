"""Per-driver period scores (Task 3.3).

A period score applies the same explainable formula as a single trip —
100 − Σ(weight × severity × count) per 100 km — but over every trip a
driver made in a calendar week or month, so long clean trips offset
isolated events instead of one bad hop defining the driver.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..scoring import score_trip
from .models import PeriodScore, Trip

logger = logging.getLogger(__name__)


def period_start_of(day: date, period: str) -> date:
    """Monday of the week, or first of the month."""
    if period == "week":
        return day - timedelta(days=day.weekday())
    if period == "month":
        return day.replace(day=1)
    raise ValueError(f"unknown period {period!r}; use 'week' or 'month'")


def recompute_period_scores(session: Session, period: str = "week") -> int:
    """Rebuild all PeriodScore rows for the given period length; commits.

    Undated trips (no start_time) can't belong to a period and are skipped.
    Returns the number of (driver, period) rows written.
    """
    buckets: dict[tuple[str, date], list[Trip]] = defaultdict(list)
    for trip in session.query(Trip).all():
        if trip.start_time is None:
            continue
        buckets[(trip.driver_id, period_start_of(trip.start_time.date(), period))].append(trip)

    session.query(PeriodScore).filter_by(period=period).delete()
    for (driver_id, start), trips in buckets.items():
        events = [event for trip in trips for event in trip.events]
        distance = sum(trip.distance_km for trip in trips)
        session.add(
            PeriodScore(
                driver_id=driver_id,
                period=period,
                period_start=start,
                score=score_trip(events, distance).value,
                distance_km=round(distance, 2),
                trip_count=len(trips),
                event_count=len(events),
            )
        )
    session.commit()
    logger.info("recomputed %d %s-scores", len(buckets), period)
    return len(buckets)
