import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST

from backend.app.auth import require_api_key
from backend.app.config import settings
from backend.app.ew.ew_simulator import ew_simulator
from backend.app.feeds.elint_feed import ELINTFeed
from backend.app.feeds.legacy_c2_feed import LegacyC2Feed
from backend.app.feeds.uav_feed import UAVFeed
from backend.app.feeds.vehicle_ir_feed import VehicleIRFeed
from backend.app.fusion.fusion_engine import fusion_engine
from backend.app.fusion.queue_backend import get_queue_backend
from backend.app.logging_config import configure_logging
from backend.app.models.schemas import SourceType
from backend.app.observability.metrics import http_requests_total, render_metrics
from backend.app.persistence.db import history_store
from backend.app.state_machine.f2t2ea import acknowledge_track, advance_stage, assess_track
from backend.app.streaming.sse import get_track_stream

configure_logging()
logger = logging.getLogger("backend.app.main")

background_tasks: list[asyncio.Task] = []
reading_queue = get_queue_backend()


async def _log_track_event(track) -> None:
    await history_store.log_stage_event(
        track_id=track.track_id,
        stage=track.stage.value,
        severity=track.severity.value,
        confidence=track.confidence,
        contributing_sources=[s.value for s in track.contributing_sources],
        timestamp=track.last_updated,
    )


async def fusion_loop():
    """Consumes normalized readings off the shared queue, fuses them, and
    advances each affected track's F2T2EA stage. Logs a history event on
    a new track's creation and on every subsequent stage change — not on
    every merge, which would flood the history table with same-stage
    reading-count bumps that don't represent anything happening."""
    while True:
        reading = await reading_queue.get()
        track = fusion_engine.ingest(reading)
        is_new_track = track.reading_count == 1
        prev_stage = track.stage
        advance_stage(track)
        if is_new_track or track.stage != prev_stage:
            await _log_track_event(track)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sentinel-FFT2EA starting up (log_format=%s)", settings.LOG_FORMAT)
    await history_store.init_db()

    feeds = [
        VehicleIRFeed(reading_queue, settings.VEHICLE_IR_INTERVAL),
        UAVFeed(reading_queue, settings.UAV_UAS_INTERVAL),
        ELINTFeed(reading_queue, settings.ELINT_INTERVAL),
        LegacyC2Feed(reading_queue, settings.LEGACY_C2_INTERVAL),
    ]

    for feed in feeds:
        background_tasks.append(asyncio.create_task(feed.run()))
    background_tasks.append(asyncio.create_task(fusion_loop()))

    yield

    logger.info("Sentinel-FFT2EA shutting down")
    for feed in feeds:
        feed.stop()
    for task in background_tasks:
        task.cancel()
    await history_store.dispose()


app = FastAPI(title="Sentinel-FFT2EA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def count_requests(request: Request, call_next):
    """Counts every request for /metrics. Deliberately excludes /metrics
    itself from the count — a metrics endpoint counting scrapes of itself
    is noise, not signal, for anyone actually reading the dashboard."""
    response = await call_next(request)
    if request.url.path != "/metrics":
        http_requests_total.labels(
            method=request.method, path=request.url.path, status_code=response.status_code
        ).inc()
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "active_tracks": len(fusion_engine.tracks)}


@app.get("/metrics")
async def metrics():
    return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stream/tracks")
async def stream_tracks():
    return get_track_stream()


@app.get("/tracks")
async def list_tracks():
    return [t.model_dump(mode="json") for t in fusion_engine.snapshot()]


@app.post("/tracks/{track_id}/ack", dependencies=[Depends(require_api_key)])
async def ack_track(track_id: str):
    """Operator acknowledges a TARGET-stage track, advancing it to ENGAGE.
    This is the only way a track can reach ENGAGE — never automatic.
    Requires X-API-Key if API_KEY is configured (see backend/app/auth.py)."""
    track = fusion_engine.tracks.get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    try:
        acknowledge_track(track)
    except ValueError as e:
        raise HTTPException(400, str(e))
    await _log_track_event(track)
    return track.model_dump(mode="json")


@app.post("/tracks/{track_id}/assess", dependencies=[Depends(require_api_key)])
async def close_track(track_id: str, summary: str = ""):
    track = fusion_engine.tracks.get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    assess_track(track, summary)
    await _log_track_event(track)
    return track.model_dump(mode="json")


@app.get("/tracks/{track_id}/history")
async def track_history(track_id: str):
    """Full stage-transition history for one track, from persistent
    storage — survives a server restart, unlike the in-memory
    FusionEngine's live track state."""
    return await history_store.get_track_history(track_id)


@app.get("/history")
async def recent_history(limit: int = Query(default=100, ge=1, le=1000)):
    """Most recent stage-transition events across all tracks — a global
    activity log usable for a simple session replay."""
    return await history_store.get_recent_history(limit=limit)


@app.post("/ew/toggle", dependencies=[Depends(require_api_key)])
async def toggle_ew(source_type: SourceType):
    """Flip EW degradation on/off for a given source type.
    Requires X-API-Key if API_KEY is configured (see backend/app/auth.py)."""
    new_state = ew_simulator.toggle(source_type)
    return {"source_type": source_type.value, "degraded": new_state}


@app.get("/ew/status")
async def ew_status():
    return ew_simulator.status()


@app.post("/ew/spoof/toggle", dependencies=[Depends(require_api_key)])
async def toggle_ew_spoof(source_type: SourceType):
    """Flip spoofing on/off for a given source type — a fabricated
    contact may appear alongside genuine readings, indistinguishable
    from a real one by design (see ew/ew_simulator.py). Requires
    X-API-Key if API_KEY is configured."""
    new_state = ew_simulator.toggle_spoof(source_type)
    return {"source_type": source_type.value, "spoofing": new_state}


@app.get("/ew/spoof/status")
async def ew_spoof_status():
    return ew_simulator.spoof_status()
