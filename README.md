# Sentinel-FFT2EA

> Built in response to the Indian Army Internship Program's AI/ML "Kill
> Chain for Armoured Formation" brief — a self-directed exercise in the
> program's named F2T2EA cycle, ISR fusion, and legacy C2 integration,
> using synthetic data only.

A simulated multi-source threat fusion and decision-support pipeline. Ingests
synthetic sensor feeds from multiple source types, fuses them into unified
tracks, classifies them, and advances each track through the
**Find → Fix → Track → Target → Engage → Assess (F2T2EA)** decision cycle —
with a simulated Electronic Warfare (EW) degraded mode to show the system
still producing a usable fused picture when a feed is jammed or dropped.

> **This is a portfolio/learning project.** All sensor data is synthetically
> generated. There is no real targeting, weapons, or classified logic here —
> it's an architecture exercise in multi-source data fusion, state machines,
> and real-time streaming, framed around a publicly documented military
> decision-cycle concept (F2T2EA is a widely taught doctrine term, not
> sensitive information).

## Why this project exists

Built to demonstrate hands-on fluency with:
- **ISR** — multi-sensor ingest (vehicle/IR, UAV/UAS, ELINT-style signals)
- **Legacy C2 integration** — adapting an older/mismatched data format into
  the fusion pipeline
- **Electronic Warfare resilience** — degraded/contested feed handling
- **F2T2EA** — explicit state-machine modeling of the decision cycle
- Real-time operator dashboards (SSE streaming, reused from prior projects)

## Architecture

```
 ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
 │ Vehicle/IR │   │  UAV/UAS   │   │   ELINT    │   │ Legacy C2  │
 │   Feed     │   │   Feed     │   │   Feed     │   │   Feed     │
 └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
       │                │                │                │
       └────────────────┴───────┬────────┴────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │   EW Simulator   │  (randomly degrades a feed)
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │  Fusion Engine   │  (spatial-temporal matching)
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │  Classifier      │  (severity / confidence)
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │ F2T2EA State     │  (per-track stage advancement)
                        │ Machine          │
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │  SSE Broadcast   │  (live operator dashboard feed)
                        └─────────────────┘
```

## Project layout

```
sentinel-fft2ea/
├── README.md
├── LICENSE                      # MIT (project's own code)
├── requirements.txt
├── requirements-detection.txt   # optional: real YOLOv8n mode
├── docker-compose.yml
├── Dockerfile                   # backend
├── render.yaml                  # backend deployment blueprint
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── loadtest/
│   ├── locustfile.py            # operator-traffic + SSE load profile
│   ├── requirements.txt
│   ├── README.md                # measured results, in-memory + Redis
│   └── results/                 # raw Locust CSVs from actual runs
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app, CORS, auth, orchestration loop
│       ├── config.py                # settings (CORS, API_KEY, YOLO_*, Redis)
│       ├── auth.py                  # X-API-Key dependency (mutating endpoints only)
│       ├── models/
│       │   └── schemas.py           # Pydantic models & enums
│       ├── feeds/
│       │   ├── base.py              # abstract async feed producer
│       │   ├── vehicle_ir_feed.py   # synthetic OR real YOLOv8n mode
│       │   ├── uav_feed.py
│       │   ├── elint_feed.py
│       │   └── legacy_c2_feed.py    # deliberately mismatched schema + adapter
│       ├── fusion/
│       │   ├── fusion_engine.py     # spatial-temporal track matching/merging
│       │   └── queue_backend.py     # in-memory OR Redis-backed queue
│       ├── classification/
│       │   ├── detector.py          # severity classifier
│       │   └── yolo_detector.py     # real YOLOv8n wrapper — configurable
│       │                              model path + demo/webcam/video source
│       ├── state_machine/
│       │   └── f2t2ea.py            # stage transition rules
│       ├── ew/
│       │   └── ew_simulator.py      # feed degradation toggle
│       ├── streaming/
│       │   └── sse.py               # SSE endpoint (not auth-gated — see below)
│       └── tests/
│           ├── test_fusion.py
│           ├── test_state_machine.py
│           ├── test_queue_backend.py
│           ├── test_auth.py
│           └── test_yolo_detector.py
└── frontend/
    ├── Dockerfile                   # multi-stage: build + nginx serve
    ├── vercel.json                  # frontend deployment config
    ├── playwright.config.ts         # E2E config (real browser, live stack)
    ├── .env.example                 # VITE_API_BASE_URL, VITE_API_KEY
    ├── e2e/
    │   └── dashboard.spec.ts        # real-browser test, wired into CI
    └── src/
        ├── App.tsx
        ├── api.ts                   # REST + SSE client (base URL + API key)
        ├── api.test.ts
        ├── types.ts                 # mirrors backend schemas
        ├── test/
        │   ├── setup.ts             # Testing Library cleanup + jest-dom
        │   └── fixtures.ts          # shared FusedTrack test factory
        └── components/
            ├── StatusBar.tsx        # connection indicator, EW toggles
            ├── StatusBar.test.tsx
            ├── TrackCard.tsx        # per-track card w/ operator actions
            ├── TrackCard.test.tsx
            ├── TrackMap.tsx         # live Leaflet map, severity-colored
            ├── StageLadder.tsx      # F2T2EA progress visualization
            └── StageLadder.test.tsx
```

## Setup

### Backend

```bash
cd sentinel-fft2ea
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload --port 8000
```

Then:
- Live fused track stream (SSE, unauthenticated — see note below): `GET http://localhost:8000/stream/tracks`
- All active tracks (snapshot, unauthenticated): `GET http://localhost:8000/tracks`
- Acknowledge a TARGET-stage track → ENGAGE (requires `X-API-Key` if `API_KEY` is set): `POST http://localhost:8000/tracks/{id}/ack`
- Close out an ENGAGE-stage track → ASSESS (requires `X-API-Key` if set): `POST http://localhost:8000/tracks/{id}/assess?summary=...`
- Toggle EW degradation on a feed (requires `X-API-Key` if set): `POST http://localhost:8000/ew/toggle?source_type=uav_uas`
- Health check: `GET http://localhost:8000/health`
- Toggle EW spoofing on a feed (requires `X-API-Key` if set): `POST http://localhost:8000/ew/spoof/toggle?source_type=elint`
- EW spoofing status: `GET http://localhost:8000/ew/spoof/status`
- One track's full stage-transition history: `GET http://localhost:8000/tracks/{id}/history`
- Global recent activity feed: `GET http://localhost:8000/history?limit=100`
- Prometheus metrics: `GET http://localhost:8000/metrics`

**Auth note:** by default `API_KEY` is unset and none of this is
enforced — fine for local dev, not fine for a real deployment. Set
`API_KEY` in `.env` before deploying, and set `VITE_API_KEY` to match on
the frontend. Read endpoints (`/tracks`, `/health`) and the SSE stream
stay unauthenticated even with `API_KEY` set — the browser's
`EventSource` API can't send custom headers, so protecting the stream
would need a different scheme (e.g. a short-lived signed query param),
which isn't implemented here. Stated as a real, known gap rather than
glossed over.

Run tests:
```bash
pytest backend/app/tests -v
```

### Frontend (operator dashboard)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — it proxies `/tracks`, `/stream`, `/ew`, and
`/health` to the backend on port 8000 (see `vite.config.ts`), so run the
backend first.

The dashboard shows each fused track as a card with a live F2T2EA stage
ladder, confidence bar, contributing-source chips, and a degraded-feed
indicator. When a track reaches TARGET it surfaces an **Acknowledge**
control — the only way any track advances to ENGAGE, and always an
explicit operator action, never automatic. ENGAGE-stage tracks get a
close-out control that advances them to ASSESS with a summary note.

Toggle between the card grid and a live map view (top-left buttons) —
the map plots each track's coordinates on a dark basemap, color-coded by
severity, with the same live SSE updates driving both views.

Type-check, run tests, and build for production:
```bash
npx tsc -b
npx vitest run
npx vite build
```

**End-to-end test (real browser, live SSE stream):** unlike the component
tests above, `frontend/e2e/dashboard.spec.ts` runs against the actual
running stack — real backend, real dev server, real Chromium. Needs both
servers up first:
```bash
# terminal 1
uvicorn backend.app.main:app --port 8000
# terminal 2
cd frontend && npm run dev
# terminal 3
cd frontend
npx playwright install --with-deps chromium   # first time only
npx playwright test
```
This is also wired into CI as its own job and runs automatically on
every push — see the Status table below for why it couldn't be verified
in the sandbox this project was built in.

### Real YOLOv8n detection mode (optional)

By default the vehicle/IR feed fabricates a plausible reading. To make it
run actual YOLOv8n inference instead:

```bash
pip install -r requirements-detection.txt
```

Then in `.env`:
```
ENABLE_REAL_DETECTION=true
```

This runs a genuine YOLOv8n forward pass (via `ultralytics`) against demo
frames — the sample images bundled with the `ultralytics` package itself,
used as stand-ins for real camera input — and uses the model's actual
class and confidence output instead of a random number. If the optional
dependencies aren't installed, the feed logs a warning once and falls back
to synthetic mode automatically rather than crashing.

This is intentionally kept optional and separate from `requirements.txt`:
`ultralytics`/`torch` are large, and requiring them just to run the test
suite would slow down everyone who isn't specifically exercising this
path. Swapping in your actual Purplle Tech Challenge model instead of the
demo frames is a config change, not a code change — see below.

**Pointing this at your real model and a real video/webcam:**
```
YOLO_MODEL_PATH=/path/to/your/purplle-weights.pt
YOLO_FRAME_SOURCE=/path/to/a/video.mp4    # or: webcam
```
`YOLO_FRAME_SOURCE=webcam` reads from a local webcam via OpenCV; a path to
a video file loops back to the start on EOF rather than exhausting after
one pass; a path to a static image works too. Verified directly (not just
written): generated a real test video, confirmed frames read correctly
and looping works past the clip's end, confirmed a missing path raises a
clear error instead of crashing the feed silently (`test_yolo_detector.py`).

**Licensing note, stated plainly:** this project's own code is MIT
licensed (see `LICENSE`), but `ultralytics` itself is AGPL-3.0 — which
has real copyleft implications if you deploy a service using it publicly
(the AGPL's network-use clause), separate from Ultralytics' own
commercial licensing option. Worth knowing before enabling
`ENABLE_REAL_DETECTION` on anything beyond a local/personal demo — this
isn't legal advice, just a heads-up to look into before a real deployment.

### Distributed mode via Redis (optional)

By default, feed producers and the fusion consumer share an in-process
`asyncio.Queue` — the whole app is one process. To run them as separate
processes/containers instead, set `REDIS_URL` in `.env`
(e.g. `redis://localhost:6379/0`) and the app automatically switches to
`RedisQueueBackend` (`fusion/queue_backend.py`), which uses `LPUSH`/`BRPOP`
on a Redis list instead of the in-memory queue — no other code changes
needed. `docker-compose.yml` wires this up automatically between the
`backend` and `redis` services.

### Docker (full stack: backend + Redis + frontend)

```bash
docker compose up --build
```

Runs all three services: backend (port 8000, wired to Redis via
`REDIS_URL`), Redis, and the frontend (port 5173, served via nginx from a
production build). Open `http://localhost:5173` — no separate `npm run
dev` needed.

### CI

`.github/workflows/ci.yml` runs the backend pytest suite and a frontend
type-check + build on every push/PR to `main`. It deliberately uses
`requirements.txt` only (not `requirements-detection.txt`) to keep CI fast
— the real-detection path is exercised locally/manually, not on every push.

## Deployment

Configs are included for the same split-hosting pattern used elsewhere in
this portfolio (backend on Render, frontend on Vercel) — **not yet
deployed**, since that requires your own Render/Vercel accounts:

**Backend (Render):**
1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint" → point at the repo. `render.yaml` at
   the root defines the service (Python env, `pip install -r
   requirements.txt`, `uvicorn` start command). Real-detection mode is set
   to `false` by default here — Render's free tier build won't fit
   torch/ultralytics; leave `requirements-detection.txt` for local/self-hosted use.
3. Set `API_KEY` in the Render dashboard to a real secret — `render.yaml`
   leaves it blank intentionally rather than shipping a default key.
4. After the first deploy, set `ALLOWED_ORIGINS` in the Render dashboard
   to your Vercel frontend's URL (step below) — `render.yaml` intentionally
   leaves this blank since it depends on the frontend URL you get.

**Frontend (Vercel):**
1. Import the repo in Vercel, set the project root to `frontend/`.
   `vercel.json` there defines the build (`npm run build`, `vite` preset).
2. Set environment variables `VITE_API_BASE_URL` (your Render backend's
   URL) and `VITE_API_KEY` (matching the `API_KEY` you set on Render).
3. Redeploy so the build picks up both env vars — they're read at build
   time, not runtime (see `frontend/src/api.ts`).

Update the Render backend's `ALLOWED_ORIGINS` once you have the final
Vercel URL, and redeploy the backend — CORS is origin-allowlisted, not
wide open (see `backend/app/config.py` / `main.py`).

## Status

Everything below is implemented and was verified working end-to-end
(automated tests + live manual runs) before this was packaged — including
real YOLOv8n inference and a real Redis-backed queue, not just stubs.

| Piece                                                | Status |
|-------------------------------------------------------|--------|
| Synthetic multi-source feeds (IR, UAV, ELINT, C2)      | Done   |
| Fusion engine w/ predictive (constant-velocity) matching | Done — see note below |
| F2T2EA state machine w/ explicit operator gate         | Done   |
| EW degradation + spoofing simulator (incl. dashboard controls) | Done |
| SSE streaming API                                      | Done   |
| React operator dashboard (grid + map + history views, auto-refresh) | Done |
| Stage-event history persistence (SQLite + real-Postgres-verified) | Done |
| Structured logging (text/JSON) + Prometheus `/metrics` | Done   |
| Backend test suite (54 tests — all pass w/ Redis+Postgres+YOLO live) | Done |
| Frontend test suite (32 tests, Vitest + Testing Library) | Done |
| CI (backend tests incl. live Redis service, frontend typecheck/tests/build) | Done |
| Real YOLOv8n detection mode (optional, verified)        | Done   |
| Configurable model weights + video/webcam source (optional, verified) | Done |
| Redis-backed distributed queue mode (optional, verified) | Done   |
| CORS + env-configurable frontend API base (verified)    | Done   |
| API key auth on mutating endpoints (verified)           | Done   |
| Live map view (Leaflet, dark tiles, severity-colored tracks) | Done |
| Load test suite (Locust), in-memory + Redis-backed, measured | Done — see `loadtest/README.md` |
| Direct Redis queue-throughput benchmark, measured        | Done — see `loadtest/README.md` |
| LICENSE (MIT)                                            | Done   |
| Full-stack Docker Compose (backend + Redis + frontend)  | Written, not build-tested — see note below |
| E2E browser test (Playwright) of the live dashboard      | Written, wired into CI, not run in this sandbox — see note below |
| Render + Vercel deployment configs                      | Written, not deployed (requires your own hosting accounts) |

**On "predictive (constant-velocity) matching":** named deliberately, not
oversold — this is a single predicted position per track extrapolated
from a smoothed velocity estimate, not full multi-hypothesis tracking
(JPDA/Kalman with maintained competing hypotheses). It's a real,
measured improvement to the same underlying "matching a moving target"
problem (see `backend/app/fusion/fusion_engine.py`'s module docstring and
`test_predictive_matching.py`), described as exactly that and no more.

**On the two "written, not verified here" rows above:** this sandbox's
network only allows a specific domain allowlist (npm, PyPI, GitHub,
Ubuntu's package archive, etc.). Docker itself runs fine here — I
installed it and confirmed the daemon starts — but pulling the
`python:3.12-slim` base image from Docker Hub returns a 403, since that
registry isn't on the allowlist. Same story for a real browser: Playwright's
own CDN is blocked, and Ubuntu's `chromium-browser` package is a dead
stub pointing at a snap that doesn't work in this environment either.
Both are genuine sandbox limits, not skipped effort — confirmed by
actually trying each one, not assumed.

The E2E test (`frontend/e2e/dashboard.spec.ts`) is wired into
`.github/workflows/ci.yml` as its own job, and GitHub Actions runners
don't have this sandbox's restriction — it will actually execute in a
real headless Chromium there. **After pushing, check the Actions tab
rather than taking "it's written" as "it's verified."** If it fails,
that's useful signal, not a formality — send me the failure and I'll fix
it from the error, the same way the StageLadder bug and the
Vitest/Playwright test-discovery conflict got caught and fixed during
this build, not glossed over.

## Load testing

`loadtest/` contains a Locust suite modeling realistic operator-dashboard
traffic (polling, EW toggles, acknowledge attempts) plus SSE stream
connections. Measured against a single local instance: **5,291 requests
at 300 concurrent users, 0 failures, ~176 req/s, p95 69ms, p99 130ms** in
the default in-memory mode, and a comparable **5,359 requests, 0
failures, ~178 req/s** with the Redis-backed distributed queue path
active. A separate direct benchmark (`redis_queue_benchmark.py`, bypassing
HTTP entirely) measured the queue backend itself: **8,356 put/sec, 8,688
get/sec, 4,552 ops/sec concurrent producer+consumer** — several orders of
magnitude above what any feed's configured interval actually demands.
Full results, methodology, and correctness tests (not just throughput)
in `loadtest/README.md`.

## Observability

- **Structured logging** (`backend/app/logging_config.py`): `LOG_FORMAT=text`
  (default, human-readable) or `LOG_FORMAT=json` (one object per line,
  for a real log aggregator).
- **Metrics** (`GET /metrics`, Prometheus text format): active track
  count, tracks-by-F2T2EA-stage, EW-degraded and EW-spoofing source
  counts, HTTP request counts by method/path/status. Gauges are recomputed
  fresh from live state on every scrape rather than updated incrementally,
  so they can't drift out of sync with the state they reflect.

## EW spoofing (in addition to degradation)

Beyond dropping/weakening readings (degradation), `POST
/ew/spoof/toggle?source_type=...` injects a fabricated-but-plausible
contact into a source's feed — generated by the exact same function a
real feed uses, deliberately indistinguishable from genuine data. A
spoofed reading can flow all the way through fusion and reach
TARGET/ENGAGE like any real one; left that way on purpose, since a
trivially-filterable spoofed reading wouldn't demonstrate the actual
vulnerability. Live dashboard controls in the StatusBar (a second "EW
SPOOF" row, amber-styled, independent of the "EW JAM" degradation row)
— a source can be jammed, spoofed, both, or neither.

## Persistent history & replay

Every track's F2T2EA stage transitions are logged to persistent storage
(SQLite by default, Postgres via `DATABASE_URL` — verified against a real
local PostgreSQL 16 instance, not just assumed compatible) — survives a
server restart, unlike the in-memory `FusionEngine`. `GET
/tracks/{id}/history` for one track's timeline, `GET /history?limit=N`
for a global recent-activity feed. The dashboard's third view tab
("history") shows this as a scrollable log with an optional 5s
auto-refresh toggle — not an animated replay, a real design choice given
the scope of everything else here, not a shortcut hidden as a feature.

## Resume bullets

`RESUME_BULLETS.md` — drafted to match this portfolio's existing
metric-driven style, with a short 3-bullet version and a longer
technical-depth alternate.

## Notes on scope & framing

- Every "sensor reading" is generated by a `random`-seeded synthetic
  producer — see `feeds/`. No real sensor, satellite, or intelligence data
  is used or required.
- The Legacy C2 feed deliberately uses a different field-naming convention
  and requires an adapter function (`feeds/legacy_c2_feed.py`) — this is
  intentional, to demonstrate handling a heterogeneous/legacy data contract
  rather than assuming every source is clean and pre-normalized.
- "Engage" and "Assess" stages are just state labels in a data pipeline —
  there is no actuation, targeting, or weapons logic anywhere in this
  codebase.
