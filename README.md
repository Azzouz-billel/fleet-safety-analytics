# Fleet Safety Analytics

From one real car trip (GPS + optional video), produce a validated, **explainable driver-safety report**: speed chart, event map, event table, and a 0–100 safety score with a transparent breakdown.

Phase 1 (this repo today) is **GPS-only** — no computer vision. It analyzes a company's own vehicles; framing is coaching, not surveillance.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Quick start (synthetic sample trip)

```bash
python scripts/make_sample_trip.py        # writes data/samples/sample_trip/
fleetsafety process data/samples/sample_trip
# → data/samples/sample_trip/out/result.json + report.html
fleetsafety validate data/samples/sample_trip
# → prints device-speed vs GPS-derived speed accuracy
```

Open `data/samples/sample_trip/out/report.html` in a browser for the one-page report.

## Input: a trip package

```
data/raw/<trip_id>/
├── video.mp4        # optional (unused in Phase 1)
├── gps.csv          # REQUIRED — timestamp,lat,lon,speed_mps,heading
├── imu.csv          # optional  — timestamp,ax,ay,az,gx,gy,gz
└── meta.json        # REQUIRED — trip/vehicle/driver ids, start_time, default_speed_limit_kmh
```

- `timestamp` may be ISO 8601 (`2026-07-04T12:00:00Z`) or epoch seconds; both are parsed.
- `speed_mps` may be empty — speed is then derived from lat/lon deltas (haversine).
- All units are metric internally (m/s, m/s²); reports display km/h.

### Recording a real trip with a phone

1. Mount the phone in the vehicle. Log GPS at 1 Hz with **GPSLogger** (Android,
   CSV export) or **Open GPX Tracker** (iPhone, GPX export).
2. Copy the exported file to this machine and build a trip package from it:

   ```bash
   fleetsafety import ~/Downloads/20260705.csv --trip-id trip_2026-07-05_veh01 --limit 80
   ```

   Both GPSLogger CSV and GPX are auto-detected; `--limit` is the default
   speed limit (km/h) of the roads driven. The package lands in
   `data/raw/<trip_id>/` (override with `--out`).
3. `fleetsafety process data/raw/<trip_id>` → report + score.
4. `fleetsafety validate data/raw/<trip_id>` to check device speed vs GPS-derived speed.

## Tests

```bash
pytest tests/
```

## Project layout

```
src/fleetsafety/
├── schemas.py        # pydantic data contracts (Meta, Event, TripResult, …)
├── config.py         # ALL thresholds & score weights live here
├── ingest.py         # load + validate a trip package, normalize clocks
├── gps.py            # speed/accel/distance from GPS
├── speed.py          # speed-limit lookup (default-only in Phase 1)
├── events/           # speeding, harsh_braking, harsh_accel detectors
├── scoring.py        # explainable 0–100 score
├── report.py         # one-page HTML report
├── vision/           # Phase 2 stubs (detection, tracking, tailgating)
└── cli.py            # `fleetsafety process|validate <trip_dir>`
```

## Status

- ✅ Phase 1 — GPS-only single-trip report (this repo)
- ⏳ Phase 2 — vision events (requires a real recorded trip first)
- ⏳ Phase 3 — multi-vehicle backend + dashboard
