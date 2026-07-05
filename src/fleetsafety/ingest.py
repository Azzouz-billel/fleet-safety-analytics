"""Load a trip package from disk and normalize all clocks.

A trip package is a directory containing gps.csv (required), meta.json
(required), and optionally imu.csv and video.mp4. Every time series gets
a `t` column in seconds from `meta.start_time`, so GPS, IMU, and (later)
video frames share one clock.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .schemas import Meta

logger = logging.getLogger(__name__)

GPS_COLUMNS = {"timestamp", "lat", "lon", "speed_mps", "heading"}
IMU_COLUMNS = {"timestamp", "ax", "ay", "az", "gx", "gy", "gz"}

# Numeric timestamps below this are relative seconds, not epoch seconds
# (epoch seconds for any date after 1970-04-26 exceed it).
RELATIVE_TIMESTAMP_MAX = 1e7


class TripPackageError(ValueError):
    """A trip package is missing files or malformed."""


def load_trip(trip_dir: str | Path) -> tuple[Meta, pd.DataFrame, Optional[pd.DataFrame]]:
    """Load a trip package. Returns (meta, gps, imu-or-None).

    Both dataframes gain a `t` column: seconds from meta.start_time.
    Raises TripPackageError with a precise message on anything invalid.
    """
    trip_dir = Path(trip_dir)
    if not trip_dir.is_dir():
        raise TripPackageError(f"trip directory not found: {trip_dir}")

    missing = [name for name in ("gps.csv", "meta.json") if not (trip_dir / name).is_file()]
    if missing:
        raise TripPackageError(
            f"trip package {trip_dir} is missing required file(s): {', '.join(missing)}"
        )

    try:
        meta = Meta.model_validate(json.loads((trip_dir / "meta.json").read_text()))
    except Exception as exc:
        raise TripPackageError(f"invalid meta.json in {trip_dir}: {exc}") from exc

    gps = _read_series(trip_dir / "gps.csv", GPS_COLUMNS, meta)
    if len(gps) < 2:
        raise TripPackageError(
            f"gps.csv in {trip_dir} has {len(gps)} fix(es); at least 2 are "
            "needed to compute speed and duration"
        )

    imu_path = trip_dir / "imu.csv"
    imu = _read_series(imu_path, IMU_COLUMNS, meta) if imu_path.is_file() else None

    logger.info(
        "loaded trip %s: %d gps rows, %s imu rows",
        meta.trip_id, len(gps), len(imu) if imu is not None else "no",
    )
    return meta, gps, imu


def _read_series(path: Path, required_columns: set[str], meta: Meta) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = required_columns - set(df.columns)
    if missing:
        raise TripPackageError(f"{path} is missing column(s): {', '.join(sorted(missing))}")
    df["t"] = _to_relative_seconds(df["timestamp"], meta)
    return df.sort_values("t", ignore_index=True)


def _to_relative_seconds(timestamps: pd.Series, meta: Meta) -> pd.Series:
    """Normalize ISO 8601, epoch, or already-relative timestamps to
    seconds from meta.start_time (the shared trip clock)."""
    numeric = pd.to_numeric(timestamps, errors="coerce")
    if numeric.notna().all():
        if numeric.max() < RELATIVE_TIMESTAMP_MAX:
            return numeric - numeric.iloc[0]
        return numeric - meta.start_time.timestamp()
    parsed = pd.to_datetime(timestamps, utc=True, format="ISO8601")
    return (parsed - pd.Timestamp(meta.start_time)).dt.total_seconds()
