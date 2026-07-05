"""Frame extraction, time sync, and YOLO vehicle detection (Tasks 2.1–2.2).

FrameClock is the video half of the shared-clock rule: a frame index maps
to seconds-from-trip-start exactly like GPS/IMU `t`, so detections can be
joined against speed and events. Detection is lazy about ultralytics —
the pipeline must keep working GPS-only when the model isn't installed.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# COCO class ids for vehicles (YOLO default weights).
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass(frozen=True)
class FrameClock:
    """Maps frame index ↔ trip time (seconds from trip start).

    `video_offset_s` is when the video started on the trip clock —
    0.0 when recording began exactly at meta.start_time.
    """

    fps: float
    video_offset_s: float = 0.0

    def time_of(self, frame_index: int) -> float:
        return self.video_offset_s + frame_index / self.fps

    def frame_at(self, t_s: float) -> int:
        return max(0, round((t_s - self.video_offset_s) * self.fps))


@dataclass
class Box:
    cls: str
    conf: float
    xywh: tuple[float, float, float, float]  # center x, center y, width, height
    track_id: Optional[int] = None


@dataclass
class FrameDetections:
    frame_index: int
    t_s: float
    boxes: list[Box] = field(default_factory=list)


def video_fps(video_path: Path) -> float:
    capture = cv2.VideoCapture(str(video_path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
    finally:
        capture.release()
    if not fps or fps <= 0:
        raise ValueError(f"cannot read fps from {video_path}")
    return float(fps)


def iter_frames(video_path: Path, every_n: int = 1) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR frame) for every n-th frame."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video {video_path}")
    try:
        index = 0
        while True:
            got, frame = capture.read()
            if not got:
                return
            if index % every_n == 0:
                yield index, frame
            index += 1
    finally:
        capture.release()


def detect_vehicles(
    video_path: Path,
    clock: Optional[FrameClock] = None,
    every_n: int = 5,
    model_name: str = "yolov8n.pt",
    conf: float = 0.35,
    max_frames: Optional[int] = None,
) -> list[FrameDetections]:
    """Run YOLO on every n-th frame; keep only vehicle boxes."""
    from ultralytics import YOLO  # heavy import: only when vision is used

    clock = clock or FrameClock(fps=video_fps(video_path))
    model = YOLO(model_name)

    detections: list[FrameDetections] = []
    for frame_index, frame in iter_frames(video_path, every_n):
        if max_frames is not None and len(detections) >= max_frames:
            break
        result = model.predict(frame, conf=conf, verbose=False)[0]
        frame_det = FrameDetections(frame_index=frame_index, t_s=clock.time_of(frame_index))
        for cls_id, box_conf, xywh in zip(
            result.boxes.cls.tolist(), result.boxes.conf.tolist(), result.boxes.xywh.tolist()
        ):
            if int(cls_id) in VEHICLE_CLASSES:
                frame_det.boxes.append(
                    Box(cls=VEHICLE_CLASSES[int(cls_id)], conf=float(box_conf), xywh=tuple(xywh))
                )
        detections.append(frame_det)
    logger.info(
        "detected vehicles on %d frames of %s (every %d frames)",
        len(detections), Path(video_path).name, every_n,
    )
    return detections
