"""Command-line entry point.

    fleetsafety process <trip_dir>   → <trip_dir>/out/result.json + report.html
    fleetsafety validate <trip_dir>  → device speed vs GPS-derived speed accuracy

`process` wires the full Phase 1 pipeline:
ingest → gps → limits → events → scoring → report.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from . import gps as gps_mod
from .events.harsh_accel import detect_harsh_accel
from .events.harsh_braking import detect_harsh_braking
from .events.speeding import detect_speeding
from .ingest import TripPackageError, load_trip
from .report import generate_report
from .schemas import Meta, TripResult, TripSummary
from .scoring import score_trip

logger = logging.getLogger("fleetsafety")

MPS_TO_KMH = 3.6


def process_trip(trip_dir: Path, out_dir: Path | None = None) -> TripResult:
    """Run the full pipeline on one trip package; writes result.json + report.html."""
    meta, gps_raw, imu = load_trip(trip_dir)
    gps = gps_mod.process_gps(gps_raw)

    accel, accel_from = gps_mod.accel_source(gps, imu)
    logger.info("harsh-event acceleration source: %s", accel_from)

    events = [
        *detect_speeding(gps, meta),
        *detect_harsh_braking(gps, meta, accel),
        *detect_harsh_accel(gps, meta, accel),
    ]
    events.sort(key=lambda e: e.start_s or 0.0)

    distance_km = gps_mod.trip_distance_km(gps)
    counts = {"speeding": 0, "harsh_braking": 0, "harsh_accel": 0}
    for event in events:
        counts[event.type] = counts.get(event.type, 0) + 1

    result = TripResult(
        trip_id=meta.trip_id,
        driver_id=meta.driver_id,
        vehicle_id=meta.vehicle_id,
        summary=TripSummary(
            distance_km=round(distance_km, 2),
            duration_min=round(gps_mod.trip_duration_min(gps), 1),
            max_speed_kmh=round(float(gps["speed_smooth_mps"].max()) * MPS_TO_KMH, 1),
            avg_speed_kmh=round(float(gps["speed_raw_mps"].mean()) * MPS_TO_KMH, 1),
            event_counts=counts,
        ),
        events=events,
        score=score_trip(events, distance_km),
    )

    out_dir = out_dir or trip_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(result.model_dump_json(indent=2) + "\n")
    generate_report(result, meta, gps, out_dir / "report.html")
    logger.info("wrote %s and report.html (score %.1f)", out_dir / "result.json", result.score.value)
    return result


def validate_trip(trip_dir: Path) -> bool:
    """Compare device-reported speed against GPS-position-derived speed.

    This is the Phase 1 ground-truth check: if the two disagree wildly the
    GPS track is unusable. Returns True when at least 90% of samples agree
    within max(5%, 1 m/s).
    """
    _, gps_raw, _ = load_trip(trip_dir)
    gps = gps_mod.process_gps(gps_raw)

    provided = gps["speed_mps"].astype(float)
    if provided.isna().all():
        print("gps.csv has no device speed column values; nothing to validate against.")
        return True

    derived = gps["speed_derived_mps"]
    error = (derived - provided).abs()
    tolerance = np.maximum(provided.abs() * 0.05, 1.0)
    agree_pct = float((error <= tolerance).mean() * 100.0)

    print(f"samples:              {len(gps)}")
    print(f"mean |error|:         {error.mean():.3f} m/s")
    print(f"max  |error|:         {error.max():.3f} m/s")
    print(f"within max(5%, 1m/s): {agree_pct:.1f}%")
    passed = agree_pct >= 90.0
    print("PASS" if passed else "FAIL — check GPS quality or timestamps")
    return passed


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="fleetsafety", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="produce result.json + report.html for a trip")
    p_process.add_argument("trip_dir", type=Path)
    p_process.add_argument("--out", type=Path, default=None, help="output dir (default <trip_dir>/out)")

    p_validate = sub.add_parser("validate", help="check device speed vs GPS-derived speed")
    p_validate.add_argument("trip_dir", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "process":
            result = process_trip(args.trip_dir, args.out)
            print(json.dumps(result.summary.model_dump(), indent=2))
            print(f"score: {result.score.value} breakdown: {result.score.breakdown}")
            return 0
        return 0 if validate_trip(args.trip_dir) else 1
    except TripPackageError as exc:
        logger.error("bad trip package: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
