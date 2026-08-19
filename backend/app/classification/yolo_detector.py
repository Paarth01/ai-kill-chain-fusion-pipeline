"""
Real object-detection backend using YOLOv8n (ultralytics).

Configurable via config.py / .env, with no code changes needed to point
this at real weights and a real camera feed instead of the bundled demo
images:

  YOLO_MODEL_PATH   - defaults to stock yolov8n.pt. Set to a path to your
                       own trained weights (e.g. from the Purplle Tech
                       Challenge project) to use them instead.
  YOLO_FRAME_SOURCE - "demo" (default, bundled ultralytics sample images),
                       "webcam" (local webcam via OpenCV), or a path to a
                       video file or image.

This is kept as an optional, lazily-imported dependency: `ultralytics`/
`torch` are large (multi-GB with CUDA deps), so requiring them for the
base scaffold would make `pip install -r requirements.txt` painfully slow
for anyone just running tests or the synthetic-data mode. Install
`requirements-detection.txt` and set ENABLE_REAL_DETECTION=true to turn
this on.
"""

from __future__ import annotations

import os
import random
import threading
from functools import lru_cache
from typing import Optional

from backend.app.config import settings

# COCO classes YOLOv8n actually detects that we treat as vehicle-adjacent
# "contacts" for this simulation — mapped to our own entity vocabulary
# rather than exposed as raw COCO labels.
VEHICLE_ADJACENT_CLASSES = {
    "car": "armored_signature",
    "truck": "armored_signature",
    "bus": "armored_signature",
    "motorcycle": "thermal_contact",
    "person": "unidentified_vehicle",  # kept generic on purpose — see README
}

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")


class DetectorUnavailable(Exception):
    """Raised when real-detection mode is requested but the optional deps
    aren't installed, or the configured frame source can't be opened.
    Callers should catch this and fall back to synthetic mode rather than
    crashing the feed."""


@lru_cache(maxsize=1)
def _load_model():
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise DetectorUnavailable(
            "ultralytics is not installed. Run `pip install -r requirements-detection.txt` "
            "or set ENABLE_REAL_DETECTION=false."
        ) from e

    return YOLO(settings.YOLO_MODEL_PATH)


@lru_cache(maxsize=1)
def _demo_frame_paths() -> list[str]:
    """Locate the sample images shipped inside the installed `ultralytics`
    package. Used only when YOLO_FRAME_SOURCE=demo (the default) — not
    bundled in this repo, they come for free with the pip install."""
    try:
        import ultralytics
    except ImportError as e:
        raise DetectorUnavailable("ultralytics is not installed.") from e

    assets_dir = os.path.join(os.path.dirname(ultralytics.__file__), "assets")
    paths = [os.path.join(assets_dir, f) for f in os.listdir(assets_dir) if f.lower().endswith((".jpg", ".png"))]
    if not paths:
        raise DetectorUnavailable("No demo frames found in the ultralytics assets directory.")
    return paths


class _VideoFrameSource:
    """Wraps a persistent cv2.VideoCapture for webcam or video-file frame
    sources. Video files loop back to the start on EOF rather than
    exhausting; a webcam read failure raises immediately."""

    def __init__(self, source: str):
        try:
            import cv2
        except ImportError as e:
            raise DetectorUnavailable(
                "opencv is not installed. Run `pip install -r requirements-detection.txt`."
            ) from e

        self._cv2 = cv2
        self._is_webcam = source == "webcam"
        self._cap = cv2.VideoCapture(0 if self._is_webcam else source)
        if not self._cap.isOpened():
            raise DetectorUnavailable(f"Could not open frame source: {source}")

    def next_frame(self):
        ok, frame = self._cap.read()
        if ok:
            return frame

        if self._is_webcam:
            raise DetectorUnavailable("Webcam frame read failed.")

        # Video file reached EOF — loop back to the start rather than
        # treating a finite demo clip as a one-shot source.
        self._cap.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self._cap.read()
        if not ok:
            raise DetectorUnavailable("Could not read a frame from the configured video file.")
        return frame


_video_source_lock = threading.Lock()
_video_source: Optional[_VideoFrameSource] = None
_video_source_key: Optional[str] = None


def _get_video_source(key: str) -> _VideoFrameSource:
    global _video_source, _video_source_key
    with _video_source_lock:
        if _video_source is None or _video_source_key != key:
            _video_source = _VideoFrameSource(key)
            _video_source_key = key
        return _video_source


def _get_frame():
    """Returns either a filepath (str, for demo/static-image sources) or a
    raw BGR frame (numpy array, for webcam/video sources) — both are
    valid inputs to `model.predict()`."""
    source = settings.YOLO_FRAME_SOURCE

    if source == "demo":
        return random.choice(_demo_frame_paths())

    if source == "webcam":
        return _get_video_source("webcam").next_frame()

    # Anything else: a path to a video file or a static image.
    if not os.path.exists(source):
        raise DetectorUnavailable(f"YOLO_FRAME_SOURCE path does not exist: {source}")
    if source.lower().endswith(IMAGE_EXTENSIONS):
        return source  # static image — pass the path straight to predict()
    return _get_video_source(source).next_frame()


def run_detection() -> Optional[tuple[str, float]]:
    """Runs a real YOLOv8n forward pass on the configured frame source and
    returns (entity_hint, confidence) for the highest-confidence
    vehicle-adjacent detection, or None if nothing relevant was detected
    in that frame.

    Raises DetectorUnavailable if the optional dependencies aren't
    installed or the configured frame source can't be read — callers are
    expected to catch this and fall back to synthetic mode.
    """
    model = _load_model()
    frame = _get_frame()

    results = model.predict(frame, verbose=False)
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None

    best_hint, best_conf = None, 0.0
    for box in boxes:
        class_name = model.names[int(box.cls[0])]
        if class_name not in VEHICLE_ADJACENT_CLASSES:
            continue
        conf = float(box.conf[0])
        if conf > best_conf:
            best_hint, best_conf = VEHICLE_ADJACENT_CLASSES[class_name], conf

    if best_hint is None:
        return None
    return best_hint, round(best_conf, 3)
