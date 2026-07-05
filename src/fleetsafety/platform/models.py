"""SQLAlchemy ORM models (Task 3.1). Mirrors schemas.py: a stored Trip is
one TripResult; TripEvent rows mirror Event; PeriodScore holds the
per-driver week/month aggregates from periods.py."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class Driver(Base):
    __tablename__ = "driver"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("company.id"), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")


class Vehicle(Base):
    __tablename__ = "vehicle"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("company.id"), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Trip(Base):
    __tablename__ = "trip"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("driver.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicle.id"), index=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    distance_km: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[float] = mapped_column(Float)
    max_speed_kmh: Mapped[float] = mapped_column(Float)
    avg_speed_kmh: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    result_json: Mapped[str] = mapped_column(Text)  # full canonical result for replay

    driver: Mapped[Driver] = relationship(back_populates="trips")
    events: Mapped[list["TripEvent"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )


class TripEvent(Base):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trip.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)
    start: Mapped[str] = mapped_column(String)
    end: Mapped[str] = mapped_column(String)
    start_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    limit_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    peak_mps2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gap_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clip: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    trip: Mapped[Trip] = relationship(back_populates="events")


class PeriodScore(Base):
    __tablename__ = "score"
    __table_args__ = (UniqueConstraint("driver_id", "period", "period_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("driver.id"), index=True)
    period: Mapped[str] = mapped_column(String)  # "week" | "month"
    period_start: Mapped[date] = mapped_column(Date)
    score: Mapped[float] = mapped_column(Float)
    distance_km: Mapped[float] = mapped_column(Float)
    trip_count: Mapped[int] = mapped_column(Integer)
    event_count: Mapped[int] = mapped_column(Integer)
