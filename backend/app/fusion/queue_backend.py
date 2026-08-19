"""
Queue abstraction between feed producers and the fusion consumer.

Default: an in-process asyncio.Queue — the whole app runs as one process,
which is what the test suite and `uvicorn backend.app.main:app` use.

Distributed mode: when REDIS_URL is set, feeds and fusion instead
communicate over a Redis list (LPUSH/BRPOP), so you can run feed
producers and the fusion worker as separate processes or containers —
the scaling path referenced in docker-compose.yml's `redis` service.
Same interface either way, so `main.py` doesn't need to know which
backend is active.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from backend.app.config import settings
from backend.app.models.schemas import SensorReading


class QueueBackend(Protocol):
    async def put(self, reading: SensorReading) -> None: ...
    async def get(self) -> SensorReading: ...


class InMemoryQueueBackend:
    def __init__(self):
        self._queue: asyncio.Queue[SensorReading] = asyncio.Queue()

    async def put(self, reading: SensorReading) -> None:
        await self._queue.put(reading)

    async def get(self) -> SensorReading:
        return await self._queue.get()


class RedisQueueBackend:
    """Backed by a Redis list. Producers LPUSH a JSON-serialized reading;
    the fusion worker BRPOPs (blocking pop) so it never busy-polls."""

    def __init__(self, redis_url: str, key: str):
        import redis.asyncio as redis  # imported lazily — optional dep

        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._key = key

    async def put(self, reading: SensorReading) -> None:
        await self._redis.lpush(self._key, reading.model_dump_json())

    async def get(self) -> SensorReading:
        # BRPOP blocks server-side until an item is available; timeout=0 = wait forever.
        _, raw = await self._redis.brpop(self._key)
        return SensorReading.model_validate_json(raw)


def get_queue_backend() -> QueueBackend:
    if settings.REDIS_URL:
        return RedisQueueBackend(settings.REDIS_URL, settings.REDIS_QUEUE_KEY)
    return InMemoryQueueBackend()
