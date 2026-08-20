"""
Direct throughput benchmark of RedisQueueBackend.put()/.get() — the piece
loadtest/locustfile.py explicitly does NOT measure, since none of the
HTTP endpoints it load-tests touch the queue backend directly (see
loadtest/README.md's caveat on the Redis-mode results).

This measures exactly what those results couldn't: raw put/get throughput
against the actual Redis-backed queue implementation, isolated from
FastAPI, CORS, auth, or any other HTTP-layer cost.

Run:
    redis-server &
    python loadtest/redis_queue_benchmark.py

Requires REDIS_URL to point at a real Redis instance (defaults to
redis://localhost:6379/0).
"""

import asyncio
import os
import time
from datetime import datetime, timezone

from backend.app.fusion.queue_backend import RedisQueueBackend
from backend.app.models.schemas import Coordinates, SensorReading, SourceType

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BENCHMARK_KEY = "sentinel:benchmark:readings"
N_MESSAGES = 5000


def make_reading(i: int) -> SensorReading:
    return SensorReading(
        source_type=SourceType.VEHICLE_IR,
        entity_hint=f"benchmark_{i}",
        coordinates=Coordinates(lat=28.6, lon=77.2),
        confidence=0.7,
        timestamp=datetime.now(timezone.utc),
    )


async def benchmark_put(backend: RedisQueueBackend, n: int) -> float:
    readings = [make_reading(i) for i in range(n)]
    start = time.perf_counter()
    for reading in readings:
        await backend.put(reading)
    elapsed = time.perf_counter() - start
    return elapsed


async def benchmark_get(backend: RedisQueueBackend, n: int) -> float:
    start = time.perf_counter()
    for _ in range(n):
        await backend.get()
    elapsed = time.perf_counter() - start
    return elapsed


async def benchmark_concurrent(backend_put: RedisQueueBackend, backend_get: RedisQueueBackend, n: int) -> float:
    """Producer and consumer running concurrently against the same queue,
    closer to the real fusion_loop()/feed producer relationship than the
    sequential put-then-get benchmarks above."""

    async def producer():
        for i in range(n):
            await backend_put.put(make_reading(i))

    async def consumer():
        for _ in range(n):
            await backend_get.get()

    start = time.perf_counter()
    await asyncio.gather(producer(), consumer())
    return time.perf_counter() - start


async def main():
    print(f"Redis Queue Backend Benchmark — {N_MESSAGES} messages, REDIS_URL={REDIS_URL}\n")

    put_backend = RedisQueueBackend(REDIS_URL, BENCHMARK_KEY)
    put_elapsed = await benchmark_put(put_backend, N_MESSAGES)
    put_throughput = N_MESSAGES / put_elapsed
    print(f"put():  {N_MESSAGES} messages in {put_elapsed:.3f}s  ->  {put_throughput:,.0f} ops/sec")
    await put_backend.close()

    get_backend = RedisQueueBackend(REDIS_URL, BENCHMARK_KEY)
    get_elapsed = await benchmark_get(get_backend, N_MESSAGES)
    get_throughput = N_MESSAGES / get_elapsed
    print(f"get():  {N_MESSAGES} messages in {get_elapsed:.3f}s  ->  {get_throughput:,.0f} ops/sec")
    await get_backend.close()

    concurrent_backend_put = RedisQueueBackend(REDIS_URL, BENCHMARK_KEY + ":concurrent")
    concurrent_backend_get = RedisQueueBackend(REDIS_URL, BENCHMARK_KEY + ":concurrent")
    concurrent_elapsed = await benchmark_concurrent(concurrent_backend_put, concurrent_backend_get, N_MESSAGES)
    concurrent_throughput = N_MESSAGES / concurrent_elapsed
    print(
        f"concurrent put+get: {N_MESSAGES} messages in {concurrent_elapsed:.3f}s  "
        f"->  {concurrent_throughput:,.0f} ops/sec (end-to-end)"
    )
    await concurrent_backend_put.close()
    await concurrent_backend_get.close()


if __name__ == "__main__":
    asyncio.run(main())