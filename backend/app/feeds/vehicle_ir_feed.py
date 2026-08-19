"""
Simulates onboard vehicle/IR sensor detections (tanks, ICVs).

Two modes, controlled by ENABLE_REAL_DETECTION in .env:

- Synthetic mode (default): fabricates a plausible reading, same as before.
  Fast, zero heavy dependencies — good for CI and everyday development.

- Real detection mode: runs an actual YOLOv8n forward pass via
  `classification/yolo_detector.py` and uses the model's genuine output
  (class → entity_hint mapping, real confidence score) instead of a random
  number. Requires `pip install -r requirements-detection.txt`. Falls back
  to synthetic mode automatically (with a one-time log line) if the
  optional dependencies aren't installed, so flipping the env var never
  crashes the app.
"""

import logging
import random

from backend.app.config import settings
from backend.app.models.schemas import SensorReading, SourceType

from .base import BaseFeed

logger = logging.getLogger(__name__)

ENTITY_HINTS = ["unidentified_vehicle", "armored_signature", "thermal_contact"]

_real_detection_warned = False


class VehicleIRFeed(BaseFeed):
    source_type = SourceType.VEHICLE_IR

    def _generate_reading(self) -> SensorReading:
        if settings.ENABLE_REAL_DETECTION:
            reading = self._try_real_detection()
            if reading is not None:
                return reading
            # Either the model found nothing in that frame, or the optional
            # deps aren't installed — fall through to synthetic this cycle.

        return SensorReading(
            source_type=self.source_type,
            entity_hint=random.choice(ENTITY_HINTS),
            coordinates=self._random_coordinates(),
            confidence=round(random.uniform(0.55, 0.9), 2),
        )

    def _try_real_detection(self) -> SensorReading | None:
        global _real_detection_warned
        from backend.app.classification.yolo_detector import DetectorUnavailable, run_detection

        try:
            result = run_detection()
        except DetectorUnavailable as e:
            if not _real_detection_warned:
                logger.warning(
                    "ENABLE_REAL_DETECTION is set but unavailable (%s). "
                    "Falling back to synthetic vehicle/IR readings.",
                    e,
                )
                _real_detection_warned = True
            return None

        if result is None:
            return None  # model ran, but found nothing vehicle-adjacent this frame

        entity_hint, confidence = result
        return SensorReading(
            source_type=self.source_type,
            entity_hint=entity_hint,
            coordinates=self._random_coordinates(),
            confidence=confidence,
        )
