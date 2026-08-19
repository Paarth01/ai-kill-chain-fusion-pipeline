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

- **Single process, in-memory queue.** This measures one backend
  instance's request-handling capacity, not the Redis-backed distributed
  path (`fusion/queue_backend.py`'s `RedisQueueBackend`) or a
  multi-instance deployment. Those would need a separate test against
  that configuration.
- **Not testing the fusion/detection pipeline under load** — the feed
  producers run at their own fixed interval regardless of HTTP traffic;
  this test measures the API layer's concurrency handling, not fusion
  throughput under a flood of sensor readings.
- **Local network, not a real deployment.** Numbers will differ once
  backend and frontend are on separate hosted origins (Render/Vercel) —
  expect higher latency from real network hops, not from the app itself.
