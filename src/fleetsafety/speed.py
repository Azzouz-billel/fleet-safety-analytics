"""Speed-limit lookup.

Phase 1: the whole trip uses meta.default_speed_limit_kmh. The signature
already takes (lat, lon) so a later phase can swap in a per-location
lookup (OSM `maxspeed` via a local extract or Overpass) without touching
any caller: detectors always ask per sample.
"""

import pandas as pd


def get_limit(lat: float, lon: float, default_kmh: float) -> float:
    """Speed limit in km/h at a location. Phase 1: always the default."""
    return default_kmh


def limit_series_kmh(gps: pd.DataFrame, default_kmh: float) -> pd.Series:
    """Per-sample speed limit for a processed GPS frame."""
    return pd.Series(
        [get_limit(lat, lon, default_kmh) for lat, lon in zip(gps["lat"], gps["lon"])],
        index=gps.index,
        name="limit_kmh",
    )
