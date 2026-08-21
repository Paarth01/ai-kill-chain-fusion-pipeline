# Load Testing

`locustfile.py` models two distinct usage patterns rather than treating
every endpoint as equivalent load:

- **SentinelOperatorUser** (weight 3) — what an operator dashboard
  actually does: polls `/tracks`, checks `/health`, occasionally toggles
  EW degradation, and occasionally attempts to acknowledge a TARGET-stage
  track (best-effort — under concurrent load, which tracks are in TARGET
  at any given moment is a race, and a `400` from another simulated
  operator winning that race is treated as expected, not a failure).
- **SentinelDashboardStreamUser** (weight 1) — opens the SSE stream and
  reads a handful of live events before disconnecting, modeling the cost
  of held-open streaming connections separately from request/response
  polling.

## Setup

```bash
pip install -r loadtest/requirements.txt
```

## Run

Interactive (web UI at `http://localhost:8089`):
```bash
locust -f loadtest/locustfile.py --host http://localhost:8000
```

Headless (what produced the numbers below):
```bash
locust -f loadtest/locustfile.py --host http://localhost:8000 \
    --headless -u 300 -r 50 -t 30s --csv loadtest/results/run
```

## Results (measured, not estimated)

Run against a single local backend instance (in-memory queue mode, no
Redis, no real-detection mode — the default synthetic-data configuration)
with feed intervals sped up to 0.5s so tracks populate fast enough to
give the acknowledge-flow test something to act on.

**300 concurrent users, 30 seconds:**

| Metric | Value |
|---|---|
| Total requests | 5,291 |
| Failures | 0 (0.00%) |
| Aggregate throughput | ~176 req/s |
| Median (p50) response time | 10 ms |
| p95 | 69 ms |
| p99 | 130 ms |
| Max | 186 ms |

Backend `/health` stayed `ok` throughout and immediately after the run.
Raw CSVs are in `results/` (`run_stats.csv`, `run_stats_history.csv`,
`run_failures.csv`, `run_exceptions.csv`) if you want to inspect further
or regenerate a report.

## Honest limits of this test

- **Single process, in-memory queue** for the results above. See the
  Redis-backed run below for the distributed-mode comparison.
- **Not testing the fusion/detection pipeline under load** — the feed
  producers run at their own fixed interval regardless of HTTP traffic;
  this test measures the API layer's concurrency handling, not fusion
  throughput under a flood of sensor readings.
- **Local network, not a real deployment.** Numbers will differ once
  backend and frontend are on separate hosted origins (Render/Vercel) —
  expect higher latency from real network hops, not from the app itself.

## Redis-backed distributed mode: same test, `REDIS_URL` set

Ran the identical 300-user/30s profile against an instance configured
with `REDIS_URL` pointed at a local Redis server, to confirm the API
layer holds up the same way when the fusion pipeline is running in
distributed mode rather than the default in-process queue.

| Metric | In-memory (above) | Redis-backed |
|---|---|---|
| Total requests | 5,291 | 5,359 |
| Failures | 0 | 0 |
| Aggregate throughput | ~176 req/s | ~178 req/s |
| p50 | 10 ms | 9 ms |
| p95 | 69 ms | 81 ms |
| p99 | 130 ms | 150 ms |

Essentially comparable — a slightly wider tail latency under Redis mode
(p99 150ms vs 130ms), plausibly from Redis competing for resources on the
same single test machine, not from anything architecturally worse.
`/health` stayed `ok` throughout and after the run in both modes.

**Important caveat, stated plainly:** none of the HTTP endpoints this
test hits (`/tracks`, `/health`, `/ew/toggle`, `/tracks/{id}/ack`) touch
the queue backend directly — `RedisQueueBackend` only sits between the
feed producers and the fusion consumer loop, internal to the process, not
in the HTTP request path. So this run confirms **the API layer stays
healthy and comparably fast while the fusion pipeline is Redis-backed
underneath it** — it is not a direct benchmark of Redis queue throughput
itself. See below for that.

Raw CSVs for this run are in `results/` with the `run_redis_` prefix.

## Direct Redis queue throughput

`redis_queue_benchmark.py` is the benchmark the caveat above says is
missing — it hits `RedisQueueBackend.put()`/`.get()` directly, no FastAPI,
no CORS, no auth, no HTTP at all.

```bash
redis-server &
PYTHONPATH=. python loadtest/redis_queue_benchmark.py
```

**Results (measured, 5,000 messages, local Redis):**

| Operation | Throughput |
|---|---|
| `put()` sequential | 8,356 ops/sec |
| `get()` sequential | 8,688 ops/sec |
| Concurrent producer + consumer (end-to-end) | 4,552 ops/sec |

The concurrent number is the more realistic one — it mirrors the real
`fusion_loop()`/feed-producer relationship (both running at once against
the same queue) rather than the sequential put-then-get numbers above it,
and roughly halves from the sequential figures as expected once producer
and consumer are genuinely contending for the same connection/event loop
rather than running one after the other.

For scale: this exceeds every feed's configured interval by several
orders of magnitude (the fastest default feed interval is 2 seconds, i.e.
0.5 readings/sec) — the queue backend is nowhere close to being the
bottleneck in this system's normal operation, even in distributed mode.

Correctness (not just throughput) is verified separately in
`backend/app/tests/test_redis_queue_correctness.py` — 3 tests confirming
put/get round-trips preserve message identity at volume (200 messages)
and that concurrent producer/consumer access doesn't drop messages.
Skipped automatically if Redis isn't reachable, so a plain local `pytest`
run stays green without one — but CI's `backend-tests` job does provision
a `redis:7-alpine` service container and sets `REDIS_URL`, so these three
run for real on every push. Locally, start `redis-server &` first.
