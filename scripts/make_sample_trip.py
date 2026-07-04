"""Generate a deterministic synthetic trip package for building and testing.

Writes gps.csv, imu.csv, meta.json to data/samples/sample_trip/ (or --out).

The 10-minute, 1 Hz route deliberately injects, in order:
  - speeding stretch #1: 119 km/h vs 100 limit (~19% over → medium)
  - one hard brake:      22 → 8 m/s in 3 s   (-4.67 m/s²)
  - one hard accel:      8 → 20 m/s in 3 s   (+4.0 m/s²)
  - speeding stretch #2: 108 km/h            (~8% over → low)
All other transitions stay well under the harsh thresholds.
"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

SEED = 42
START_TIME = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)
START_LAT, START_LON = 35.71, -0.63  # Oran
HEADING_DEG = 45.0
SPEED_LIMIT_KMH = 100.0
EARTH_M_PER_DEG_LAT = 111_320.0

# (time_s, speed_mps) breakpoints; speed is linear in between.
SPEED_PROFILE = [
    (0, 0.0),
    (60, 22.0),    # gentle pull-away (0.37 m/s²)
    (180, 22.0),   # cruise 79 km/h
    (190, 33.0),   # ramp up (1.1 m/s²)
    (215, 33.0),   # SPEEDING #1 — 119 km/h
    (225, 22.0),
    (330, 22.0),   # cruise
    (333, 8.0),    # HARD BRAKE — -4.67 m/s²
    (390, 8.0),    # crawl
    (393, 20.0),   # HARD ACCEL — +4.0 m/s²
    (420, 25.0),
    (430, 30.0),
    (465, 30.0),   # SPEEDING #2 — 108 km/h
    (475, 25.0),
    (560, 25.0),   # cruise 90 km/h
    (600, 18.0),   # gentle slow-down
]

# Ground truth the tests assert against.
EXPECTED_EVENT_COUNTS = {"speeding": 2, "harsh_braking": 1, "harsh_accel": 1}
EXPECTED_SPEEDING_SEVERITIES = ["medium", "low"]


def build_speed_series() -> tuple[np.ndarray, np.ndarray]:
    """Return (t, speed_mps) sampled at 1 Hz over the whole profile."""
    knots_t = np.array([p[0] for p in SPEED_PROFILE], dtype=float)
    knots_v = np.array([p[1] for p in SPEED_PROFILE], dtype=float)
    t = np.arange(0.0, knots_t[-1] + 1.0)
    return t, np.interp(t, knots_t, knots_v)


def integrate_positions(speed_mps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Dead-reckon lat/lon along a fixed heading from the start point."""
    heading = math.radians(HEADING_DEG)
    step_m = np.concatenate([[0.0], (speed_mps[:-1] + speed_mps[1:]) / 2.0])
    north_m = np.cumsum(step_m * math.cos(heading))
    east_m = np.cumsum(step_m * math.sin(heading))
    lat = START_LAT + north_m / EARTH_M_PER_DEG_LAT
    lon = START_LON + east_m / (EARTH_M_PER_DEG_LAT * np.cos(np.radians(lat)))
    return lat, lon


def write_trip(out_dir: Path) -> None:
    rng = np.random.default_rng(SEED)
    t, speed = build_speed_series()
    lat, lon = integrate_positions(speed)
    stamps = [(START_TIME + timedelta(seconds=float(s))).isoformat().replace("+00:00", "Z") for s in t]

    out_dir.mkdir(parents=True, exist_ok=True)

    gps_lines = ["timestamp,lat,lon,speed_mps,heading"]
    for i in range(len(t)):
        gps_lines.append(
            f"{stamps[i]},{lat[i]:.7f},{lon[i]:.7f},{speed[i]:.3f},{HEADING_DEG:.1f}"
        )
    (out_dir / "gps.csv").write_text("\n".join(gps_lines) + "\n")

    ax = np.gradient(speed, t) + rng.normal(0.0, 0.03, len(t))
    ay = rng.normal(0.0, 0.03, len(t))
    az = 9.81 + rng.normal(0.0, 0.03, len(t))
    gyro = rng.normal(0.0, 0.01, (3, len(t)))
    imu_lines = ["timestamp,ax,ay,az,gx,gy,gz"]
    for i in range(len(t)):
        imu_lines.append(
            f"{stamps[i]},{ax[i]:.4f},{ay[i]:.4f},{az[i]:.4f},"
            f"{gyro[0][i]:.4f},{gyro[1][i]:.4f},{gyro[2][i]:.4f}"
        )
    (out_dir / "imu.csv").write_text("\n".join(imu_lines) + "\n")

    meta = {
        "trip_id": "sample_trip",
        "vehicle_id": "veh_demo",
        "driver_id": "drv_demo",
        "start_time": stamps[0],
        "fps": 30,
        "resolution": [1920, 1080],
        "default_speed_limit_kmh": SPEED_LIMIT_KMH,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"Wrote {len(t)} samples to {out_dir}")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "data" / "samples" / "sample_trip",
        help="output trip directory",
    )
    args = parser.parse_args()
    write_trip(args.out)


if __name__ == "__main__":
    main()
