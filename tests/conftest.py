import importlib.util
from pathlib import Path

import pytest

from fleetsafety.cli import process_trip
from fleetsafety.gps import accel_source, process_gps
from fleetsafety.ingest import load_trip

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_TRIP_DIR = REPO_ROOT / "data" / "samples" / "sample_trip"
GENERATOR = REPO_ROOT / "scripts" / "make_sample_trip.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location("make_sample_trip", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def generator():
    return _generator_module()


@pytest.fixture(scope="session")
def sample_trip_dir(generator) -> Path:
    if not (SAMPLE_TRIP_DIR / "gps.csv").is_file():
        generator.write_trip(SAMPLE_TRIP_DIR)
    return SAMPLE_TRIP_DIR


@pytest.fixture(scope="session")
def sample_trip(sample_trip_dir):
    """(meta, raw gps frame, imu frame) for the committed sample trip."""
    return load_trip(sample_trip_dir)


@pytest.fixture(scope="session")
def processed_sample(sample_trip):
    """(meta, processed gps frame, imu frame)."""
    meta, gps, imu = sample_trip
    return meta, process_gps(gps), imu


@pytest.fixture(scope="session")
def imu_accel(processed_sample):
    _, gps, imu = processed_sample
    return accel_source(gps, imu)[0]


@pytest.fixture(scope="session")
def gps_only_accel(processed_sample):
    _, gps, _ = processed_sample
    return accel_source(gps, None)[0]


@pytest.fixture(scope="session")
def sample_result(sample_trip_dir, tmp_path_factory):
    """Full pipeline output; artifacts land in a session tmp dir."""
    out_dir = tmp_path_factory.mktemp("sample_out")
    return process_trip(sample_trip_dir, out_dir), out_dir
