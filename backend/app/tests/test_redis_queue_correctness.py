"""
Correctness check for redis_queue_benchmark.py's core operations — not a
performance assertion (timing thresholds in CI are inherently flaky), just
confirming put()/get() actually round-trip real messages through a real
Redis instance without loss or corruption.

Skips cleanly if Redis isn't reachable, the same pattern
test_yolo_detector.py uses for its optional dependency (pytest.importorskip)
— this isn't part of the default CI backend-tests job (no Redis service
configured there); run it locally against `redis-server &`.
"""

import asyncio

import pytest
import pytest_asyncio

from backend.app.fusion.queue_backend import RedisQueueBackend
from backend.app.models.schemas import Coordinates, SensorReading, SourceType

REDIS_URL = "redis://localhost:6379/0"
TEST_KEY = "sentinel:test:benchmark_correctness"


def _redis_reachable() -> bool:
    try:
        import redis as redis_sync

        client = redis_sync.from_url(REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _redis_reachable(), reason="Redis not reachable at localhost:6379")


@pytest_asyncio.fixture
async def backend():
    import redis.asyncio as redis

    b = RedisQueueBackend(REDIS_URL, TEST_KEY)
    yield b
    # Clean up whatever this test left in the queue.
    client = redis.from_url(REDIS_URL, decode_responses=True)
    await client.delete(TEST_KEY)
    await client.aclose()


@pytest.mark.asyncio
async def test_put_then_get_round_trips_correctly(backend):
    reading = SensorReading(
        source_type=SourceType.VEHICLE_IR,
        entity_hint="correctness_check",
        coordinates=Coordinates(lat=28.6, lon=77.2),
        confidence=0.75,
    )

    await backend.put(reading)
    result = await backend.get()

    assert result.reading_id == reading.reading_id
    assert result.entity_hint == "correctness_check"
    assert result.coordinates.lat == 28.6


@pytest.mark.asyncio
async def test_many_messages_round_trip_without_loss_or_reordering_corruption(backend):
    """Not asserting FIFO order specifically (Redis LPUSH/BRPOP does
    preserve it, but that's tested in test_queue_backend.py's in-memory
    equivalent) — asserting the set of messages that come out is exactly
    the set that went in, at a volume large enough that silent drops
    would show up."""
    n = 200
    sent_ids = set()
    for i in range(n):
        reading = SensorReading(
            source_type=SourceType.ELINT,
            entity_hint=f"msg_{i}",
            coordinates=Coordinates(lat=28.6, lon=77.2),
            confidence=0.5,
        )
        sent_ids.add(reading.reading_id)
        await backend.put(reading)

    received_ids = set()
    for _ in range(n):
        result = await backend.get()
        received_ids.add(result.reading_id)

    assert received_ids == sent_ids


@pytest.mark.asyncio
async def test_concurrent_producer_and_consumer_do_not_lose_messages(backend):
    n = 100
    received = []

    async def producer():
        for i in range(n):
            reading = SensorReading(
                source_type=SourceType.UAV_UAS,
                entity_hint=f"concurrent_{i}",
                coordinates=Coordinates(lat=28.6, lon=77.2),
                confidence=0.6,
            )
            await backend.put(reading)

    async def consumer():
        for _ in range(n):
            result = await backend.get()
            received.append(result)

    await asyncio.gather(producer(), consumer())

    assert len(received) == n
