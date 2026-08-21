# Resume Bullets — Sentinel-FFT2EA

Drafted to match the metric-driven "X as measured by Y by doing Z" style
used elsewhere in this portfolio. Pick the set that fits the space you
have — short list first, then a slightly longer alternate set with more
technical specificity if the target role wants depth over brevity.

## Standard (3 bullets)

**Sentinel-FFT2EA — Multi-Source ISR Fusion Pipeline for the F2T2EA Decision Cycle**
*Solo project, built for the Indian Army Internship Program (IAIP) AI/ML application*

- Shortened the Find-Fix-Track-Target-Engage-Assess cycle for 5 heterogeneous
  data sources (vehicle/IR, UAV/UAS, ELINT, legacy C2, and push-ingested
  HUMINT text reports) as measured by 49 passing automated backend tests
  across fusion, state-machine, and persistence layers (plus 32 frontend
  tests) by architecting a spatial-temporal fusion engine with
  constant-velocity predictive matching and an explicit operator-gated
  F2T2EA state machine.
- Sustained system reliability under adversarial and high-load conditions
  as measured by 0 failures across 5,291 requests at 300 concurrent users
  (Locust) and 8,688 ops/sec on direct Redis queue throughput benchmarks
  by building EW degradation/spoofing simulation, a Redis-backed
  distributed queue mode verified against real PostgreSQL and Redis
  instances, and Prometheus-instrumented observability.
- Delivered a full-stack, deployment-ready system as measured by CI-verified
  backend, frontend, and end-to-end browser test suites (GitHub Actions,
  incl. a live Redis service container) by building a FastAPI backend
  with dual SQLite/Postgres persistence and API-key auth, paired with a
  React/TypeScript operator dashboard (live map, stage-transition
  history, real-time SSE).

## Alternate (more technical depth, for a role that wants it)

- Engineered a spatial-temporal sensor fusion engine with constant-velocity
  predictive matching (extrapolating track position from a smoothed
  velocity estimate) to correctly associate readings a static
  nearest-neighbor matcher would reject — verified with concrete distance
  measurements, not just unit test pass/fail.
- Built a Redis-backed distributed queue architecture as an alternative to
  the default in-process mode, with correctness (not just throughput)
  verified via concurrent producer/consumer tests against a real Redis
  instance and measured at 8,356–8,688 ops/sec direct queue throughput.
- Designed a dual-backend persistence layer (SQLite by default, PostgreSQL
  via a single config change) using SQLAlchemy's async engine, verified
  against both a local SQLite file and a real installed PostgreSQL 16
  instance — including cross-instance durability checks proving data
  survives a process restart.
- Simulated Electronic Warfare conditions at two distinct threat levels:
  degradation (dropped/weakened readings, modeling jamming) and spoofing
  (fabricated-but-plausible contacts indistinguishable from genuine
  sensor data by design) — both independently toggleable per source and
  surfaced live on the operator dashboard.
- Instrumented the system for production observability: structured
  JSON/text logging and a Prometheus `/metrics` endpoint exposing live
  gauges (active tracks, tracks-by-stage, EW status) recomputed fresh on
  every scrape to avoid metric drift.
- Achieved 0 failures across 5,291 requests at 300 concurrent users
  (Locust load test, both in-memory and Redis-backed queue modes) against
  a FastAPI backend with API-key-gated mutating endpoints and
  origin-allowlisted CORS.
- Built a CI pipeline (GitHub Actions) running the backend suite against a
  live Redis service container, 32 frontend tests (Vitest + Testing
  Library), and an end-to-end Playwright browser test against the live
  full stack — not just unit-level coverage.

## One-liner (for a skills/projects summary line)

Built Sentinel-FFT2EA, a 5-source ISR fusion pipeline (FastAPI + React)
modeling the F2T2EA decision cycle with predictive tracking, EW
degradation/spoofing simulation, HUMINT report ingestion, and dual
SQLite/Postgres persistence — 93 tests across backend, frontend, and
browser E2E, load-tested to 300 concurrent users with zero failures.

---

*A note on honesty, since it mattered throughout building this: every
number above was actually measured, not estimated — real Locust runs,
real Redis/Postgres instances, real test executions. If asked to walk
through any of these in an interview, the full methodology and raw
results are in `loadtest/README.md` and the git commit history, which
documents not just what was built but what broke along the way and how
it got fixed.*
