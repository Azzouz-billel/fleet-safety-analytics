import pytest

from fleetsafety.importer import import_trip
from fleetsafety.ingest import TripPackageError, load_trip

# Header and units exactly as GPSLogger (Android) writes them.
GPSLOGGER_CSV = """\
time,lat,lon,elevation,accuracy,bearing,speed,satellites,provider,hdop,vdop,pdop,geoidheight,ageofdgpsdata,dgpsid,activity,battery,annotation,timestamp_ms,time_offset,distance,starttimestamp_ms,profile_name,battery_charging
2026-07-05T09:00:00.000Z,35.7100000,-0.6300000,45.0,4.0,45.0,12.5,9,gps,0.8,1.1,1.4,,,,"",88,,1783328400000,,0.0,1783328400000,Default,false
2026-07-05T09:00:01.000Z,35.7100800,-0.6299200,45.1,4.0,45.0,12.6,9,gps,0.8,1.1,1.4,,,,"",88,,1783328401000,,12.6,1783328400000,Default,false
2026-07-05T09:00:02.000Z,35.7101600,-0.6298400,45.2,4.0,45.0,12.4,9,gps,0.8,1.1,1.4,,,,"",88,,1783328402000,,25.1,1783328400000,Default,false
"""

GPX = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1" creator="Open GPX Tracker">
  <trk><trkseg>
    <trkpt lat="35.7100000" lon="-0.6300000"><ele>45.0</ele><time>2026-07-05T09:00:00Z</time></trkpt>
    <trkpt lat="35.7100800" lon="-0.6299200"><ele>45.1</ele><time>2026-07-05T09:00:01Z</time></trkpt>
    <trkpt lat="35.7101600" lon="-0.6298400"><ele>45.2</ele><time>2026-07-05T09:00:02Z</time></trkpt>
  </trkseg></trk>
</gpx>
"""


def _import(tmp_path, name, content):
    source = tmp_path / name
    source.write_text(content)
    return import_trip(source, tmp_path / "trip", "trip_test", "veh_01", "drv_01", 100.0)


def test_gpslogger_csv_import_yields_loadable_package(tmp_path):
    package = _import(tmp_path, "20260705.csv", GPSLOGGER_CSV)
    _, gps, _ = load_trip(package)
    assert len(gps) == 3


def test_gpslogger_csv_import_keeps_speed_in_mps(tmp_path):
    package = _import(tmp_path, "20260705.csv", GPSLOGGER_CSV)
    _, gps, _ = load_trip(package)
    assert gps["speed_mps"].iloc[0] == pytest.approx(12.5)


def test_gpslogger_csv_import_maps_bearing_to_heading(tmp_path):
    package = _import(tmp_path, "20260705.csv", GPSLOGGER_CSV)
    _, gps, _ = load_trip(package)
    assert gps["heading"].iloc[0] == pytest.approx(45.0)


def test_gpx_import_yields_loadable_package(tmp_path):
    package = _import(tmp_path, "track.gpx", GPX)
    _, gps, _ = load_trip(package)
    assert len(gps) == 3


def test_gpx_import_sets_meta_start_time_to_first_fix(tmp_path):
    package = _import(tmp_path, "track.gpx", GPX)
    meta, _, _ = load_trip(package)
    assert meta.start_time.isoformat() == "2026-07-05T09:00:00+00:00"


def test_unrecognized_csv_raises_clear_error(tmp_path):
    source = tmp_path / "random.csv"
    source.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(TripPackageError, match="does not look like a GPS logger export"):
        import_trip(source, tmp_path / "trip", "t", "v", "d", 100.0)
