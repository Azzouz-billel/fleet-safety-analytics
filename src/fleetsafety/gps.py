"""GPS processing: speed, acceleration, distance, duration.

All computation is in SI units (m, m/s, m/s²). `process_gps` adds columns
to the ingested frame:

    speed_derived_mps  haversine hop distance / Δt (always computed)
    speed_raw_mps      device speed where present, else the derived speed
    speed_smooth_mps   moving average of speed_raw_mps (report + speeding)
    accel_mps2         d(speed_raw)/dt — unsmoothed, so brake spikes survive

The raw series is kept next to the smoothed one on purpose: validation
(`fleetsafety validate`) compares device speed against the derived series,
and harsh-event detection needs unsmoothed acceleration.
"""

from typing import Optional

import numpy as np
import pandas as pd

from . import config

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great-circle distance in meters; accepts scalars or arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def segment_distances_m(gps: pd.DataFrame) -> np.ndarray:
    """Distance of each hop between consecutive fixes; first element is 0."""
    lat, lon = gps["lat"].to_numpy(), gps["lon"].to_numpy()
    hops = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    return np.concatenate([[0.0], hops])


def derived_speed_mps(gps: pd.DataFrame) -> pd.Series:
    """Speed from position deltas: hop distance / hop Δt, per fix."""
    hops = segment_distances_m(gps)
    hop_dt = np.concatenate([[1.0], np.diff(gps["t"].to_numpy())])
    speed = np.divide(hops, hop_dt, out=np.zeros_like(hops), where=hop_dt != 0)
    if len(speed) > 1:
        speed[0] = speed[1]  # first fix has no inbound hop; reuse the second
    return pd.Series(speed, index=gps.index, name="speed_derived_mps")


def process_gps(
    gps: pd.DataFrame,
    smoothing_window_s: float = config.SPEED_SMOOTHING_WINDOW_S,
) -> pd.DataFrame:
    """Return a copy of the ingested GPS frame with speed/accel columns."""
    out = gps.copy()
    derived = derived_speed_mps(out)
    out["speed_derived_mps"] = derived
    if "speed_mps" in out.columns:
        provided = pd.to_numeric(out["speed_mps"], errors="coerce")
        out["speed_raw_mps"] = provided.fillna(derived)
    else:
        out["speed_raw_mps"] = derived

    dt = float(np.median(np.diff(out["t"]))) if len(out) > 1 else 1.0
    window = max(1, round(smoothing_window_s / dt))
    out["speed_smooth_mps"] = (
        out["speed_raw_mps"].rolling(window, center=True, min_periods=1).mean()
    )
    out["accel_mps2"] = np.gradient(out["speed_raw_mps"].to_numpy(), out["t"].to_numpy())
    return out


def trip_distance_km(gps: pd.DataFrame) -> float:
    return float(segment_distances_m(gps).sum() / 1000.0)


def trip_duration_min(gps: pd.DataFrame) -> float:
    return float((gps["t"].iloc[-1] - gps["t"].iloc[0]) / 60.0)


def accel_source(gps: pd.DataFrame, imu: Optional[pd.DataFrame]) -> tuple[pd.Series, str]:
    """Acceleration series aligned to the GPS clock, preferring IMU.

    IMU forward accel (ax) is the direct measurement; GPS-derived accel is
    the fallback. Returns (series indexed like gps, source name).
    """
    if imu is not None and "ax" in imu.columns:
        aligned = np.interp(gps["t"], imu["t"], imu["ax"])
        return pd.Series(aligned, index=gps.index, name="accel_mps2"), "imu"
    return gps["accel_mps2"], "gps"
