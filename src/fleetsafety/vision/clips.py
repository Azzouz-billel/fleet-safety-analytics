"""Event clip export (Task 2.5): ±few seconds of video around an event."""

import logging
from pathlib import Path

import cv2

from .detect import FrameClock, video_fps

logger = logging.getLogger(__name__)

CLIP_PAD_S = 5.0


def export_clip(
    video_path: Path,
    start_s: float,
    end_s: float,
    out_path: Path,
    pad_s: float = CLIP_PAD_S,
) -> Path | None:
    """Write [start−pad, end+pad] of the trip video to out_path.

    Returns None (and logs) when the window lies outside the video —
    events can outlive a camera that stopped early.
    """
    fps = video_fps(video_path)
    clock = FrameClock(fps=fps)
    first = clock.frame_at(start_s - pad_s)
    last = clock.frame_at(end_s + pad_s)

    capture = cv2.VideoCapture(str(video_path))
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if first >= total:
            logger.warning("clip window %.1fs starts after video ends; skipping", start_s)
            return None
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        for _ in range(first, min(last + 1, total)):
            got, frame = capture.read()
            if not got:
                break
            writer.write(frame)
        writer.release()
    finally:
        capture.release()
    return out_path
