"""Persist canonical TripResults into the platform DB.

Idempotent by trip_id: re-posting a trip replaces its previous rows, so
re-processing a trip package and re-uploading is always safe.
"""

import logging

from sqlalchemy.orm import Session

from ..schemas import TripResult
from .models import Company, Driver, Trip, TripEvent, Vehicle

logger = logging.getLogger(__name__)

DEFAULT_COMPANY = "default"


def store_trip_result(session: Session, result: TripResult) -> Trip:
    """Insert (or replace) one trip with its events; commits."""
    company = session.query(Company).filter_by(name=DEFAULT_COMPANY).one_or_none()
    if company is None:
        company = Company(name=DEFAULT_COMPANY)
        session.add(company)
        session.flush()

    if session.get(Driver, result.driver_id) is None:
        session.add(Driver(id=result.driver_id, company_id=company.id))
    if session.get(Vehicle, result.vehicle_id) is None:
        session.add(Vehicle(id=result.vehicle_id, company_id=company.id))

    existing = session.get(Trip, result.trip_id)
    if existing is not None:
        session.delete(existing)
        session.flush()

    trip = Trip(
        id=result.trip_id,
        driver_id=result.driver_id,
        vehicle_id=result.vehicle_id,
        start_time=result.start_time.replace(tzinfo=None) if result.start_time else None,
        distance_km=result.summary.distance_km,
        duration_min=result.summary.duration_min,
        max_speed_kmh=result.summary.max_speed_kmh,
        avg_speed_kmh=result.summary.avg_speed_kmh,
        score=result.score.value,
        result_json=result.model_dump_json(),
        events=[
            TripEvent(
                type=event.type,
                severity=event.severity,
                start=event.start,
                end=event.end,
                start_s=event.start_s,
                end_s=event.end_s,
                lat=event.lat,
                lon=event.lon,
                speed_kmh=event.speed_kmh,
                limit_kmh=event.limit_kmh,
                peak_mps2=event.peak_mps2,
                gap_s=event.gap_s,
                clip=event.clip,
            )
            for event in result.events
        ],
    )
    session.add(trip)
    session.commit()
    logger.info("stored trip %s (%d events)", trip.id, len(trip.events))
    return trip
