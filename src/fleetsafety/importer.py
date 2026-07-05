"""Convert a phone GPS-logger export into a trip package.

Supported sources:
  - GPSLogger CSV (Android) — columns like time,lat,lon,…,bearing,speed
  - GPX 1.0/1.1 track files (Open GPX Tracker, most logger apps)

Output: <out_dir>/gps.csv + meta.json in the trip-package contract, ready
for `fleetsafety process`. Speed stays in m/s (GPSLogger logs m/s; GPX
rarely has speed at all — the pipeline derives it from positions then).
"""

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from .ingest import TripPackageError

logger = logging.getLogger(__name__)

# Accepted source-column spellings, in priority order, per target column.
COLUMN_ALIASES = {
    "timestamp": ("time", "timestamp", "date time", "datetime"),
    "lat": ("lat", "latitude"),
    "lon": ("lon", "longitude", "lng"),
    "speed_mps": ("speed", "speed_mps"),
    "heading": ("bearing", "heading", "course", "direction"),
}
REQUIRED = ("timestamp", "lat", "lon")


def import_trip(
    source: Path,
    out_dir: Path,
    trip_id: str,
    vehicle_id: str,
    driver_id: str,
    default_speed_limit_kmh: float,
) -> Path:
    """Build a trip package from a logger export; returns the package dir."""
    if not source.is_file():
        raise TripPackageError(f"source file not found: {source}")
    gps = _read_gpx(source) if source.suffix.lower() == ".gpx" else _read_logger_csv(source)
    if gps.empty:
        raise TripPackageError(f"no GPS fixes found in {source}")

    out_dir.mkdir(parents=True, exist_ok=True)
    gps.to_csv(out_dir / "gps.csv", index=False)
    meta = {
        "trip_id": trip_id,
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "start_time": str(gps["timestamp"].iloc[0]),
        "default_speed_limit_kmh": default_speed_limit_kmh,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    logger.info("imported %d fixes from %s into %s", len(gps), source.name, out_dir)
    return out_dir


def _read_logger_csv(source: Path) -> pd.DataFrame:
    raw = pd.read_csv(source)
    raw.columns = [str(c).strip().lower() for c in raw.columns]

    resolved = {}
    for target, aliases in COLUMN_ALIASES.items():
        found = next((a for a in aliases if a in raw.columns), None)
        if found is not None:
            resolved[target] = raw[found]
    missing = [c for c in REQUIRED if c not in resolved]
    if missing:
        raise TripPackageError(
            f"{source} does not look like a GPS logger export; "
            f"could not find column(s) for: {', '.join(missing)} "
            f"(accepted names: {COLUMN_ALIASES})"
        )

    gps = pd.DataFrame(resolved)
    for optional in ("speed_mps", "heading"):
        if optional not in gps.columns:
            gps[optional] = None
    return gps[["timestamp", "lat", "lon", "speed_mps", "heading"]]


def _read_gpx(source: Path) -> pd.DataFrame:
    """Parse trackpoints namespace-agnostically (GPX 1.0 vs 1.1 vs app quirks)."""
    rows = []
    for _, element in ET.iterparse(source):
        if element.tag.rpartition("}")[2] != "trkpt":
            continue
        fields = {child.tag.rpartition("}")[2]: (child.text or "").strip() for child in element.iter()}
        rows.append(
            {
                "timestamp": fields.get("time"),
                "lat": float(element.get("lat")),
                "lon": float(element.get("lon")),
                "speed_mps": fields.get("speed") or None,
                "heading": fields.get("course") or None,
            }
        )
        element.clear()
    gps = pd.DataFrame(rows)
    if not gps.empty and gps["timestamp"].isna().any():
        raise TripPackageError(f"{source} has trackpoints without <time>; cannot build a clock")
    return gps
