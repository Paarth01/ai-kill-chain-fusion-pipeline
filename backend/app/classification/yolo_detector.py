"""
Real object-detection backend using YOLOv8n (ultralytics).

This is the concrete implementation of the "swap in the real model" step
described in the README/roadmap. It's kept as an optional, lazily-imported
dependency: `ultralytics`/`torch` are large (multi-GB with CUDA deps), so
requiring them for the base scaffold would make `pip install -r
requirements.txt` painfully slow for anyone just running tests or the
synthetic-data mode. Install `requirements-detection.txt` and set
ENABLE_REAL_DETECTION=true to turn this on.

Runs inference against a small rotating set of demo frames (the sample
images bundled with the `ultralytics` package itself, used here purely as
stand-ins for real camera frames) rather than fabricating a confidence
number, so when this mode is enabled the reading really is the output of a
YOLOv8n forward pass.
"""

from __future__ import annotations

import os
import random
from functools import lru_cache
from typing import Optional

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


class DetectorUnavailable(Exception):
    """Raised when real-detection mode is requested but ultralytics/torch
    aren't installed. Callers should catch this and fall back to synthetic
    mode rather than crashing the feed."""


@lru_cache(maxsize=1)
def _load_model():
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise DetectorUnavailable(
            "ultralytics is not installed. Run `pip install -r requirements-detection.txt` "
            "or set ENABLE_REAL_DETECTION=false."
        ) from e

    return YOLO("yolov8n.pt")


@lru_cache(maxsize=1)
def _demo_frame_paths() -> list[str]:
    """Locate the sample images shipped inside the installed `ultralytics`
    package. We deliberately don't bundle these in this repo — they come
    for free with the pip install and are used only as stand-ins for real
    camera frames."""
    try:
        import ultralytics
    except ImportError as e:
        raise DetectorUnavailable("ultralytics is not installed.") from e

    assets_dir = os.path.join(os.path.dirname(ultralytics.__file__), "assets")
    paths = [os.path.join(assets_dir, f) for f in os.listdir(assets_dir) if f.lower().endswith((".jpg", ".png"))]
    if not paths:
        raise DetectorUnavailable("No demo frames found in the ultralytics assets directory.")
    return paths


def run_detection() -> Optional[tuple[str, float]]:
    """Runs a real YOLOv8n forward pass on a random demo frame and returns
    (entity_hint, confidence) for the highest-confidence vehicle-adjacent
    detection, or None if nothing relevant was detected in that frame.

    Raises DetectorUnavailable if the optional dependencies aren't
    installed — callers are expected to catch this and fall back to
    synthetic mode.
    """
    model = _load_model()
    frame_path = random.choice(_demo_frame_paths())

    results = model.predict(frame_path, verbose=False)
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
