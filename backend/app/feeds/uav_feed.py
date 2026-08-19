"""Simulates UAV/UAS overhead ISR contacts."""

import random

from backend.app.models.schemas import SensorReading, SourceType

from .base import BaseFeed

ENTITY_HINTS = ["aerial_contact", "moving_group", "static_object"]


class UAVFeed(BaseFeed):
    source_type = SourceType.UAV_UAS

    def _generate_reading(self) -> SensorReading:
        return SensorReading(
            source_type=self.source_type,
            entity_hint=random.choice(ENTITY_HINTS),
            coordinates=self._random_coordinates(),
            confidence=round(random.uniform(0.5, 0.85), 2),
        )
