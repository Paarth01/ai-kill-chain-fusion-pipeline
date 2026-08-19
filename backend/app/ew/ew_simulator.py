"""
Simulates Electronic Warfare interference: a source type can be toggled
into a "degraded" state, causing its feed to either drop readings entirely
or emit them with reduced confidence — modeling jamming/contested-spectrum
conditions. The fusion engine should still produce a usable (if lower-
confidence) picture from whatever sources remain clean.
"""

import random

from backend.app.models.schemas import SensorReading, SourceType


class EWSimulator:
    def __init__(self):
        self._degraded_sources: set[SourceType] = set()

    def toggle(self, source_type: SourceType) -> bool:
        """Flip degradation on/off for a source. Returns new state."""
        if source_type in self._degraded_sources:
            self._degraded_sources.remove(source_type)
            return False
        self._degraded_sources.add(source_type)
        return True

    def is_degraded(self, source_type: SourceType) -> bool:
        return source_type in self._degraded_sources

    def status(self) -> dict:
        return {s.value: (s in self._degraded_sources) for s in SourceType}

    def degrade_reading(self, reading: SensorReading) -> SensorReading | None:
        """Either drop the reading (simulating jamming blackout) or return
        it with a confidence penalty and a `degraded` flag set."""
        if random.random() < 0.4:
            return None  # signal lost entirely this cycle

        reading.confidence = round(reading.confidence * random.uniform(0.3, 0.6), 2)
        reading.degraded = True
        return reading


# Module-level singleton — simple for a single-process scaffold.
# Swap for a Redis-backed shared state if you move to multi-worker (see
# docker-compose.yml's redis service).
ew_simulator = EWSimulator()
