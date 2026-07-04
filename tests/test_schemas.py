from fleetsafety.schemas import Meta, TripResult

CANONICAL_RESULT = {
    "trip_id": "trip_2026-07-04_veh07",
    "driver_id": "drv_113",
    "vehicle_id": "veh_07",
    "summary": {
        "distance_km": 12.7,
        "duration_min": 10.0,
        "max_speed_kmh": 118.8,
        "avg_speed_kmh": 76.3,
        "event_counts": {"speeding": 1, "harsh_braking": 0, "harsh_accel": 0},
    },
    "events": [
        {
            "type": "speeding",
            "start": "12:04:11",
            "end": "12:04:39",
            "start_s": 251.0,
            "end_s": 279.0,
            "lat": 35.71,
            "lon": -0.63,
            "speed_kmh": 118.0,
            "limit_kmh": 100.0,
            "peak_mps2": None,
            "severity": "high",
            "clip": None,
        }
    ],
    "score": {"value": 96.0, "breakdown": {"speeding": 4.0}},
}


def test_trip_result_round_trips_dict_to_model_to_dict():
    assert TripResult.model_validate(CANONICAL_RESULT).model_dump(mode="json") == CANONICAL_RESULT


def test_meta_parses_iso_start_time_with_zulu_suffix():
    meta = Meta.model_validate(
        {
            "trip_id": "t1",
            "vehicle_id": "v1",
            "driver_id": "d1",
            "start_time": "2026-07-04T12:00:00Z",
            "default_speed_limit_kmh": 100,
        }
    )
    assert meta.start_time.year == 2026
