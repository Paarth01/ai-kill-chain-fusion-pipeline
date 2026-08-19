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
├── requirements.txt
├── requirements-detection.txt   # optional: real YOLOv8n mode
├── docker-compose.yml
├── Dockerfile                   # backend
├── render.yaml                  # backend deployment blueprint
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app, CORS, orchestration loop
│       ├── config.py                # settings (incl. ALLOWED_ORIGINS)
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
│       │   └── yolo_detector.py     # real YOLOv8n wrapper (optional dep)
│       ├── state_machine/
│       │   └── f2t2ea.py            # stage transition rules
│       ├── ew/
│       │   └── ew_simulator.py      # feed degradation toggle
│       ├── streaming/
│       │   └── sse.py               # SSE endpoint
│       └── tests/
│           ├── test_fusion.py
│           ├── test_state_machine.py
│           └── test_queue_backend.py
└── frontend/
    ├── Dockerfile                   # multi-stage: build + nginx serve
    ├── vercel.json                  # frontend deployment config
    ├── .env.example                 # VITE_API_BASE_URL
    └── src/
        ├── App.tsx
        ├── api.ts                   # REST + SSE client (env-configurable base URL)
        ├── types.ts                 # mirrors backend schemas
        └── components/
            ├── StatusBar.tsx        # connection indicator, EW toggles
            ├── TrackCard.tsx        # per-track card w/ operator actions
            └── StageLadder.tsx      # F2T2EA progress visualization
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
- Live fused track stream (SSE): `GET http://localhost:8000/stream/tracks`
- All active tracks (snapshot): `GET http://localhost:8000/tracks`
- Acknowledge a TARGET-stage track → ENGAGE: `POST http://localhost:8000/tracks/{id}/ack`
- Close out an ENGAGE-stage track → ASSESS: `POST http://localhost:8000/tracks/{id}/assess?summary=...`
- Toggle EW degradation on a feed: `POST http://localhost:8000/ew/toggle?source_type=uav_uas`
- Health check: `GET http://localhost:8000/health`

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

Type-check and build for production:
```bash
npx tsc -b
npx vite build
```

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
demo frames is a drop-in change to `classification/yolo_detector.py`.

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
3. After the first deploy, set `ALLOWED_ORIGINS` in the Render dashboard
   to your Vercel frontend's URL (step below) — `render.yaml` intentionally
   leaves this blank since it depends on the frontend URL you get.

**Frontend (Vercel):**
1. Import the repo in Vercel, set the project root to `frontend/`.
   `vercel.json` there defines the build (`npm run build`, `vite` preset).
2. Set an environment variable `VITE_API_BASE_URL` to your Render
   backend's URL (from the step above).
3. Redeploy so the build picks up the env var — `VITE_API_BASE_URL` is
   read at build time, not runtime (see `frontend/src/api.ts`).

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
| Fusion engine (spatial-temporal matching)              | Done   |
| F2T2EA state machine w/ explicit operator gate         | Done   |
| EW degradation simulator                               | Done   |
| SSE streaming API                                      | Done   |
| React operator dashboard (grid + map views)            | Done   |
| Backend test suite (13 tests)                          | Done   |
| CI (backend tests + frontend build)                    | Done   |
| Real YOLOv8n detection mode (optional, verified)        | Done   |
| Redis-backed distributed queue mode (optional, verified) | Done   |
| CORS + env-configurable frontend API base (verified)    | Done   |
| Live map view (Leaflet, dark tiles, severity-colored tracks) | Done |
| Load test suite (Locust) with measured results          | Done — see `loadtest/README.md` |
| Full-stack Docker Compose (backend + Redis + frontend)  | Done, not container-tested (no Docker in build environment — Dockerfiles follow standard patterns but weren't run) |
| Render + Vercel deployment configs                      | Written, not deployed (requires your own hosting accounts) |

## Load testing

`loadtest/` contains a Locust suite modeling realistic operator-dashboard
traffic (polling, EW toggles, acknowledge attempts) plus SSE stream
connections. Measured against a single local instance: **5,291 requests
at 300 concurrent users, 0 failures, ~176 req/s, p95 69ms, p99 130ms.**
Full results, methodology, and honest limits (single-process only, not
yet run against the Redis-backed distributed path) in
`loadtest/README.md`.

## Possible extensions (not required, not started)

- Swapping the demo frames in real-detection mode for your actual Purplle
  Tech Challenge model weights/video source instead of the bundled
  ultralytics sample images
- Running the load test against the Redis-backed distributed queue path,
  not just the default in-memory single-process mode

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
