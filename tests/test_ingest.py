import json

import pytest

from fleetsafety.ingest import TripPackageError, load_trip


def test_sample_trip_gps_has_all_rows(sample_trip):
    _, gps, _ = sample_trip
    assert len(gps) == 601


def test_sample_trip_imu_has_all_rows(sample_trip):
    _, _, imu = sample_trip
    assert len(imu) == 601


def test_shared_clock_starts_at_zero(sample_trip):
    _, gps, _ = sample_trip
    assert gps["t"].iloc[0] == 0.0


def test_missing_required_files_raise_clear_error(tmp_path):
    with pytest.raises(TripPackageError, match="gps.csv, meta.json"):
        load_trip(tmp_path)


def test_single_fix_trip_is_rejected_not_crashed(tmp_path):
    meta = {
        "trip_id": "t1",
        "vehicle_id": "v1",
        "driver_id": "d1",
        "start_time": "2026-07-05T09:00:00Z",
        "default_speed_limit_kmh": 100,
    }
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    (tmp_path / "gps.csv").write_text(
        "timestamp,lat,lon,speed_mps,heading\n2026-07-05T09:00:00Z,35.71,-0.63,10,45\n"
    )
    with pytest.raises(TripPackageError, match="at least 2"):
        load_trip(tmp_path)


def test_epoch_timestamps_normalize_to_seconds_from_start(tmp_path):
    start_epoch = 1_780_000_000
    meta = {
        "trip_id": "t1",
        "vehicle_id": "v1",
        "driver_id": "d1",
        "start_time": start_epoch,
        "default_speed_limit_kmh": 100,
    }
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    (tmp_path / "gps.csv").write_text(
        "timestamp,lat,lon,speed_mps,heading\n"
        f"{start_epoch},35.71,-0.63,10,45\n"
        f"{start_epoch + 5},35.7105,-0.63,10,45\n"
    )
    _, gps, _ = load_trip(tmp_path)
    assert gps["t"].tolist() == [0.0, 5.0]
