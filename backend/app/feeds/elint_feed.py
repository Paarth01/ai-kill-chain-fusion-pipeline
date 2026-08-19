"""
Simulates ELINT-style electronic-signature contacts: no visual detection,
just an RF signature and a rough geolocation estimate (electronic
intelligence typically has wider position uncertainty than optical/IR).
"""

import random

from backend.app.models.schemas import SensorReading, SourceType

from .base import BaseFeed

SIGNATURE_PREFIXES = ["RF-EM", "RF-COMMS", "RF-RADAR"]


class ELINTFeed(BaseFeed):
    source_type = SourceType.ELINT

    def _generate_reading(self) -> SensorReading:
        signature = f"{random.choice(SIGNATURE_PREFIXES)}-{random.randint(1000, 9999)}"
        return SensorReading(
            source_type=self.source_type,
            entity_hint="rf_emitter",
            coordinates=self._random_coordinates(),
            # ELINT geolocation is inherently fuzzier — lower confidence band.
            confidence=round(random.uniform(0.35, 0.65), 2),
            raw_signature=signature,
        )
