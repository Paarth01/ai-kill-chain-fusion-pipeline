"""
Abstract base for a feed "producer". Each concrete feed generates synthetic
readings on an interval and pushes normalized `SensorReading` objects onto a
shared asyncio.Queue for the fusion engine to consume.

Real feeds (a real video stream, a real UAV telemetry socket, an actual
legacy C2 export) would replace `_generate_reading()` with real I/O — the
rest of the producer loop (interval timing, EW-degradation check, queue
push) stays the same.
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod

from backend.app.ew.ew_simulator import ew_simulator
from backend.app.fusion.queue_backend import QueueBackend
from backend.app.models.schemas import SensorReading, SourceType

# Rough bounding box used for synthetic coordinate generation.
# (Arbitrary — not tied to any real location; swap for a real AOI if desired.)
LAT_RANGE = (28.40, 28.75)
LON_RANGE = (76.95, 77.35)


class BaseFeed(ABC):
    source_type: SourceType

    def __init__(self, queue: QueueBackend, interval_seconds: float):
        self.queue = queue
        self.interval_seconds = interval_seconds
        self._running = False

    @abstractmethod
    def _generate_reading(self) -> SensorReading:
        """Produce one synthetic, normalized SensorReading."""

    @staticmethod
    def _random_coordinates():
        from backend.app.models.schemas import Coordinates

        return Coordinates(
            lat=round(random.uniform(*LAT_RANGE), 5),
            lon=round(random.uniform(*LON_RANGE), 5),
        )

    async def run(self):
        self._running = True
        while self._running:
            reading = self._generate_reading()

            # Apply EW degradation if this source is currently jammed.
            if ew_simulator.is_degraded(self.source_type):
                reading = ew_simulator.degrade_reading(reading)
                if reading is None:
                    # Reading dropped entirely — simulates total signal loss.
                    await asyncio.sleep(self.interval_seconds)
                    continue

            await self.queue.put(reading)

            # If this source is being spoofed, an extra phantom contact
            # may appear alongside the genuine reading this cycle — see
            # ew_simulator.maybe_spoof_reading's docstring for why it's
            # generated identically to a real reading rather than tagged.
            spoofed = ew_simulator.maybe_spoof_reading(self.source_type, self._generate_reading)
            if spoofed is not None:
                await self.queue.put(spoofed)

            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        self._running = False
