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
├── RESUME_BULLETS.md            # portfolio bullets (short + long version)
├── LICENSE                      # MIT (project's own code)
├── requirements.txt
├── requirements-detection.txt   # optional: real YOLOv8n mode
├── docker-compose.yml           # full stack: backend + redis + frontend
├── Dockerfile                   # backend
├── render.yaml                  # backend deployment blueprint
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml     # 3 jobs: backend-tests, frontend-build, e2e
├── loadtest/
│   ├── locustfile.py            # operator-traffic + SSE load profile
│   ├── redis_queue_benchmark.py # direct queue throughput bench (no HTTP)
│   ├── requirements.txt
│   ├── README.md                # measured results, in-memory + Redis
│   └── results/                 # raw Locust CSVs from actual runs
├── backend/
│   └── app/                     # every package below also has an __init__.py
│       ├── main.py              # FastAPI app, all routes, CORS, fusion loop
│       ├── config.py            # pydantic-settings — every env var lives here
│       ├── auth.py              # X-API-Key dependency (mutating endpoints only)
│       ├── logging_config.py    # structured logging, LOG_FORMAT=text|json
│       ├── models/
│       │   └── schemas.py       # Pydantic models & enums
│       ├── feeds/
│       │   ├── base.py             # abstract async feed producer
│       │   ├── vehicle_ir_feed.py  # synthetic OR real YOLOv8n mode
│       │   ├── uav_feed.py
│       │   ├── elint_feed.py
│       │   └── legacy_c2_feed.py   # deliberately mismatched schema + adapter
│       ├── fusion/
│       │   ├── fusion_engine.py    # spatial-temporal + predictive matching
│       │   └── queue_backend.py    # in-memory OR Redis-backed queue
│       ├── classification/
│       │   ├── detector.py         # severity classifier
│       │   └── yolo_detector.py    # real YOLOv8n wrapper — configurable
│       │                             model path + demo/webcam/video source
│       ├── state_machine/
│       │   └── f2t2ea.py           # stage transitions + operator gate
│       ├── ew/
│       │   └── ew_simulator.py     # feed degradation + spoofing toggles
│       ├── streaming/
│       │   └── sse.py              # SSE endpoint (not auth-gated — see below)
│       ├── persistence/
│       │   └── db.py               # HistoryStore — SQLite/Postgres via
│       │                             async SQLAlchemy; stage_events table
│       ├── observability/
│       │   └── metrics.py          # Prometheus collectors + render_metrics()
│       └── tests/                  # 55 tests
│           ├── test_fusion.py
│           ├── test_predictive_matching.py
│           ├── test_state_machine.py
│           ├── test_queue_backend.py
│           ├── test_redis_queue_correctness.py  # skipped w/o a live Redis
│           ├── test_persistence.py
│           ├── test_persistence_postgres.py     # skipped w/o a live Postgres
│           ├── test_observability.py
│           ├── test_ew_spoofing.py
│           ├── test_auth.py
│           └── test_yolo_detector.py
└── frontend/
    ├── package.json / package-lock.json
    ├── index.html
    ├── vite.config.ts              # dev proxy to :8000 + Vitest config
    ├── tsconfig.json
    ├── tailwind.config.js          # "console" dark palette
    ├── postcss.config.js
    ├── playwright.config.ts        # E2E config (real browser, live stack)
    ├── vercel.json                 # frontend deployment config
    ├── Dockerfile                  # multi-stage: build + nginx serve
    ├── .env.example                # VITE_API_BASE_URL, VITE_API_KEY
    ├── e2e/
    │   └── dashboard.spec.ts       # real-browser test, wired into CI
    └── src/
        ├── main.tsx                # React entrypoint
        ├── App.tsx                 # view tabs, SSE wiring, track state
        ├── App.test.tsx
        ├── api.ts                  # REST + SSE client (base URL + API key)
        ├── api.test.ts
        ├── types.ts                # mirrors backend schemas
        ├── index.css               # Tailwind entry + focus-ring utility
        ├── vite-env.d.ts
        ├── test/
        │   ├── setup.ts            # Testing Library cleanup + jest-dom
        │   └── fixtures.ts         # shared FusedTrack test factory
        └── components/
            ├── StatusBar.tsx       # connection state, EW jam/spoof toggles
            ├── StatusBar.test.tsx
            ├── TrackCard.tsx       # per-track card w/ operator actions
            ├── TrackCard.test.tsx
            ├── StageLadder.tsx     # F2T2EA progress visualization
            ├── StageLadder.test.tsx
            ├── TrackMap.tsx        # live Leaflet map, severity-colored
            ├── HistoryPanel.tsx    # stage-event log + 5s auto-refresh toggle
            └── HistoryPanel.test.tsx
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

**Python 3.12 is the supported version** (what CI pins). On 3.13 the pinned
`asyncpg==0.29.0` has no prebuilt Windows wheel and will try to compile
from source, which needs the MSVC build tools — verified the hard way, so
use 3.12 unless you want to install those.

Then:
- Live fused track stream (SSE, unauthenticated — see note below): `GET http://localhost:8000/stream/tracks`
- All active tracks (snapshot, unauthenticated): `GET http://localhost:8000/tracks`
- Acknowledge a TARGET-stage track → ENGAGE (requires `X-API-Key` if `API_KEY` is set): `POST http://localhost:8000/tracks/{id}/ack`
- Close out a track → ASSESS (requires `X-API-Key` if set): `POST http://localhost:8000/tracks/{id}/assess?summary=...`
- Toggle EW degradation on a feed (requires `X-API-Key` if set): `POST http://localhost:8000/ew/toggle?source_type=uav_uas`
- EW degradation status (all sources): `GET http://localhost:8000/ew/status`
- Toggle EW spoofing on a feed (requires `X-API-Key` if set): `POST http://localhost:8000/ew/spoof/toggle?source_type=elint`
- EW spoofing status: `GET http://localhost:8000/ew/spoof/status`
- One track's full stage-transition history: `GET http://localhost:8000/tracks/{id}/history`
- Global recent activity feed (`limit` 1–1000, default 100): `GET http://localhost:8000/history?limit=100`
- Health check: `GET http://localhost:8000/health`
- Prometheus metrics: `GET http://localhost:8000/metrics`

That's all 12 application routes. FastAPI additionally serves its
auto-generated `/docs`, `/redoc`, and `/openapi.json` — left enabled
because they're genuinely useful for poking at this, but worth disabling
before any real deployment since they're not auth-gated either.

**Two honest gaps in the operator actions above,** since the README used to
imply otherwise:
- `/ack` *is* properly gated — it raises 400 unless the track is at TARGET,
  so ENGAGE is only ever reachable by explicit operator action.
- `/assess` is **not** gated: `assess_track()` performs no stage check, so a
  FIND-stage track can be forced straight to ASSESS (verified by doing it).
- The `?summary=` note is **accepted and then discarded** — `assess_track()`
  takes the parameter and never uses it, and there's no summary column in
  the `stage_events` table. The dashboard's close-out box therefore sends
  text nowhere. Called out rather than left as a surprise.

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
55 tests. Without a live Redis and Postgres you'll see **43 passed, 9
skipped** (3 Redis + 5 Postgres integration tests skip themselves; the
YOLO tests skip if `requirements-detection.txt` isn't installed) — the
skips are by design, not failures. CI runs the Redis ones for real against
a `redis:7-alpine` service container.

### Frontend (operator dashboard)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — it proxies `/tracks`, `/history`, `/stream`,
`/ew`, and `/health` to the backend on port 8000 (see `vite.config.ts`), so
run the backend first.

The dashboard shows each fused track as a card with a live F2T2EA stage
ladder, confidence bar, contributing-source chips, and a degraded-feed
indicator. When a track reaches TARGET it surfaces an **Acknowledge**
control — the only way any track advances to ENGAGE, and always an
explicit operator action, never automatic. ENGAGE-stage tracks get a
close-out control that advances them to ASSESS (the note it collects is
currently discarded server-side — see the gaps listed above).

Toggle between the card grid and a live map view (top-left buttons) —
the map plots each track's coordinates on a dark basemap, color-coded by
severity, with the same live SSE updates driving both views.

Type-check, run tests, and build for production:
```bash
npx tsc -b
npx vitest run
npx vite build
```
Equivalent npm scripts are defined in `package.json`: `npm run dev`,
`npm test` (Vitest, 32 tests), `npm run build` (`tsc -b && vite build`),
`npm run preview`, `npm run test:e2e` (Playwright). Vitest is configured to
exclude `e2e/` so it doesn't try to collect the Playwright specs — that
test-discovery conflict was a real bug, fixed in `vite.config.ts`.

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

### Configuration

Everything is read from `.env` via `backend/app/config.py` — a plain
`Settings` class over `os.getenv` with `load_dotenv()`, evaluated once at
import. All of it has a working default; the app runs with an empty `.env`.
Note there's no validation layer: a malformed numeric value raises at
import rather than being coerced.

| Variable | Default | What it does |
|----------|---------|--------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowlist (not wide open) |
| `API_KEY` | unset | Shared `X-API-Key` on mutating endpoints; no-op when unset |
| `DATABASE_URL` | unset → SQLite `./sentinel.db` | Postgres URL; normalized to `+asyncpg`/`+aiosqlite` automatically |
| `LOG_FORMAT` | `text` | `text` or `json` structured logging |
| `REDIS_URL` | unset → in-memory queue | Switches to `RedisQueueBackend` |
| `REDIS_QUEUE_KEY` | `sentinel:readings` | Redis list key |
| `FUSION_DISTANCE_THRESHOLD_KM` | `1.5` | Max haversine distance to merge a reading into a track |
| `FUSION_TIME_WINDOW_SECONDS` | `30` | Max age of a track to still be a match candidate |
| `TRACK_STALE_AFTER_SECONDS` | `120` | Age at which a track is pruned — see caveat below |
| `VEHICLE_IR_INTERVAL` | `2` | Seconds between synthetic readings (per feed) |
| `UAV_UAS_INTERVAL` | `3` | ″ |
| `ELINT_INTERVAL` | `4` | ″ |
| `LEGACY_C2_INTERVAL` | `5` | ″ |
| `ENABLE_REAL_DETECTION` | `false` | Real YOLOv8n inference on the vehicle/IR feed |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | Weights to load in real-detection mode |
| `YOLO_FRAME_SOURCE` | `demo` | `demo`, `webcam`, or a video/image path |

`HOST` and `PORT` are also defined in `config.py` but nothing reads them —
the bind address comes from the `uvicorn` CLI flags. Left in place rather
than quietly deleted, but they're dead config, not knobs.

The SSE broadcast interval (1.0s) is a module constant in
`streaming/sse.py`, not an env var.

**Stale-track caveat, stated plainly:** `prune_stale()` is only called from
the SSE broadcast loop, so `TRACK_STALE_AFTER_SECONDS` only takes effect
while at least one client is connected to `/stream/tracks`. With no
dashboard open, `/tracks` and `/metrics` will keep reporting tracks past
their expiry. A real system would prune on a timer independent of who's
watching; this one doesn't.

Frontend build-time vars (`frontend/.env.example`): `VITE_API_BASE_URL`
and `VITE_API_KEY`. Both are read at **build** time, not runtime.

### CI

`.github/workflows/ci.yml` runs three jobs on every push/PR to `main`:

1. **`backend-tests`** — Python 3.12, `pytest backend/app/tests`, with a
   live `redis:7-alpine` service container and `REDIS_URL` set, so the
   Redis queue correctness tests actually execute rather than skipping.
2. **`frontend-build`** — Node 20, `npm ci` → `tsc -b` → `vitest run` →
   `vite build`. Type errors, failing component tests, and build breakage
   all fail the job.
3. **`e2e`** — needs both jobs above. Boots a real uvicorn backend (feed
   intervals dropped to `0.5s` so tracks reach TARGET quickly), installs
   Chromium via `playwright install --with-deps`, and runs the browser
   test. Uploads the `playwright-report` artifact on failure.

CI deliberately uses `requirements.txt` only (not
`requirements-detection.txt`) to keep it fast — the real-detection path is
exercised locally/manually, not on every push. Postgres isn't wired into
CI either, so the 5 Postgres tests skip there; they were verified against
a real local PostgreSQL 16 instance instead.

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
| Backend test suite (55 tests — all pass w/ Redis+Postgres+YOLO live) | Done |
| Frontend test suite (32 tests, Vitest + Testing Library) | Done |
| CI (3 jobs: backend + live Redis, frontend typecheck/tests/build, e2e) | Done |
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
| E2E browser test (Playwright, 4 specs) of the live dashboard | Written, wired into CI, not run in this sandbox — see note below |
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
- **Metrics** (`GET /metrics`, Prometheus text format) — five collectors on
  a private registry (so no default process/GC metrics):
  `sentinel_active_tracks`, `sentinel_tracks_by_stage{stage}`,
  `sentinel_ew_degraded_sources`, `sentinel_ew_spoofing_sources`, and
  `sentinel_http_requests_total{method,path,status_code}`. Gauges are
  recomputed fresh from live state on every scrape rather than updated
  incrementally, so they can't drift out of sync with the state they
  reflect. `/metrics` excludes itself from the request counter.

  One caveat worth knowing: the `path` label is the raw request path, so
  per-track routes like `/tracks/TRK-1A2B3C4D/ack` create a new counter
  series per track ID. Unbounded label cardinality — fine at this scale,
  wrong for a long-running deployment, where the fix is to label with the
  route template instead of the resolved path.

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
