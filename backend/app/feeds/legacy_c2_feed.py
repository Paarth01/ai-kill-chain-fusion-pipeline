"""
Simulates a legacy Command & Control system export.

Deliberately uses a different field-naming convention (short, uppercase,
flat keys — think an old fixed-format message standard) instead of the
clean `SensorReading` shape everything else uses. This forces an explicit
adapter step, which is the point: real "legacy C2 integration" work is
mostly about reconciling mismatched data contracts, not writing new sensor
code.
"""

import random
from datetime import datetime

from backend.app.models.schemas import Coordinates, SensorReading, SourceType

from .base import BaseFeed

LEGACY_ENTITY_CODES = ["CTC-1", "CTC-2", "CTC-9"]  # arbitrary legacy codes


def _generate_legacy_message() -> dict:
    """What the 'legacy system' actually emits — NOT a SensorReading."""
    return {
        "MSGTYPE": "CONTACT",
        "ECODE": random.choice(LEGACY_ENTITY_CODES),
        "LATDEG": round(random.uniform(28.40, 28.75), 5),
        "LONDEG": round(random.uniform(76.95, 77.35), 5),
        "CONF_PCT": random.randint(30, 80),  # note: percent, not 0-1 float
        "TS": datetime.utcnow().isoformat(),
    }


def adapt_legacy_message(msg: dict) -> SensorReading:
    """Translate the legacy flat/percent-based format into the normalized
    SensorReading contract the fusion engine expects."""
    return SensorReading(
        source_type=SourceType.LEGACY_C2,
        entity_hint=msg["ECODE"],
        coordinates=Coordinates(lat=msg["LATDEG"], lon=msg["LONDEG"]),
        confidence=round(msg["CONF_PCT"] / 100, 2),
        timestamp=datetime.fromisoformat(msg["TS"]),
    )


class LegacyC2Feed(BaseFeed):
    source_type = SourceType.LEGACY_C2

    def _generate_reading(self) -> SensorReading:
        legacy_msg = _generate_legacy_message()
        return adapt_legacy_message(legacy_msg)
