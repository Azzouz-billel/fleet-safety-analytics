"""ByteTrack vehicle tracking with stable IDs (Task 2.3).

Wraps supervision's ByteTrack around per-frame YOLO detections so every
vehicle keeps one track_id across frames — the prerequisite for lead-
vehicle selection and time-gap estimation in tailgating.py.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from .detect import VEHICLE_CLASSES, Box, FrameClock, FrameDetections, iter_frames, video_fps

logger = logging.getLogger(__name__)


def track_vehicles(
    video_path: Path,
    clock: Optional[FrameClock] = None,
    every_n: int = 2,
    model_name: str = "yolov8n.pt",
    conf: float = 0.35,
    max_frames: Optional[int] = None,
) -> list[FrameDetections]:
    """Detect + track: like detect_vehicles but each Box gets a track_id.

    ByteTrack needs a steady frame cadence, so this runs its own loop
    instead of reusing detect_vehicles' output.
    """
    # NOTE: supervision deprecates ByteTrack in v0.30 (trackers move to the
    # separate `trackers` package); requirements pin <0.30 until we migrate.
    import supervision as sv
    from ultralytics import YOLO

    clock = clock or FrameClock(fps=video_fps(video_path))
    model = YOLO(model_name)
    tracker = sv.ByteTrack(frame_rate=clock.fps / every_n)

    tracked: list[FrameDetections] = []
    for frame_index, frame in iter_frames(video_path, every_n):
        if max_frames is not None and len(tracked) >= max_frames:
            break
        result = model.predict(frame, conf=conf, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(result)
        detections = detections[np.isin(detections.class_id, list(VEHICLE_CLASSES))]
        detections = tracker.update_with_detections(detections)

        frame_det = FrameDetections(frame_index=frame_index, t_s=clock.time_of(frame_index))
        for xyxy, box_conf, cls_id, track_id in zip(
            detections.xyxy, detections.confidence, detections.class_id, detections.tracker_id
        ):
            x1, y1, x2, y2 = (float(v) for v in xyxy)
            frame_det.boxes.append(
                Box(
                    cls=VEHICLE_CLASSES[int(cls_id)],
                    conf=float(box_conf),
                    xywh=((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1),
                    track_id=int(track_id),
                )
            )
        tracked.append(frame_det)
    logger.info("tracked vehicles on %d frames of %s", len(tracked), Path(video_path).name)
    return tracked
