import cv2
import numpy as np
import pytest

from fleetsafety.vision.detect import FrameClock, iter_frames, video_fps

# Task 2.1 acceptance: given a timestamp, retrieve the correct frame;
# frame times align with the GPS/IMU trip clock.


def test_frame_index_maps_to_trip_time():
    clock = FrameClock(fps=30.0)
    assert clock.time_of(90) == pytest.approx(3.0)


def test_video_offset_shifts_frame_times():
    clock = FrameClock(fps=30.0, video_offset_s=12.5)
    assert clock.time_of(0) == pytest.approx(12.5)


def test_timestamp_maps_back_to_frame_index():
    clock = FrameClock(fps=25.0, video_offset_s=10.0)
    assert clock.frame_at(14.0) == 100


def test_times_before_video_start_clamp_to_frame_zero():
    clock = FrameClock(fps=30.0, video_offset_s=60.0)
    assert clock.frame_at(2.0) == 0


def test_round_trip_frame_to_time_to_frame():
    clock = FrameClock(fps=29.97)
    assert clock.frame_at(clock.time_of(1234)) == 1234


@pytest.fixture(scope="module")
def tiny_video(tmp_path_factory):
    """20-frame 10 fps video; frame index encoded in pixel brightness."""
    path = tmp_path_factory.mktemp("video") / "tiny.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for i in range(20):
        writer.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
    writer.release()
    return path


def test_video_fps_read_from_file(tiny_video):
    assert video_fps(tiny_video) == pytest.approx(10.0)


def test_iter_frames_respects_sampling_stride(tiny_video):
    indices = [i for i, _ in iter_frames(tiny_video, every_n=5)]
    assert indices == [0, 5, 10, 15]


def test_retrieved_frame_content_matches_its_index(tiny_video):
    frames = dict(iter_frames(tiny_video, every_n=5))
    # frames are 10 brightness units apart; ±4.9 tolerates codec loss while
    # still uniquely identifying frame 10 (brightness 100)
    assert frames[10].mean() == pytest.approx(100, abs=4.9)
