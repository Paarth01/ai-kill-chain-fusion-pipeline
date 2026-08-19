import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.ew.ew_simulator import ew_simulator
from backend.app.feeds.elint_feed import ELINTFeed
from backend.app.feeds.legacy_c2_feed import LegacyC2Feed
from backend.app.feeds.uav_feed import UAVFeed
from backend.app.feeds.vehicle_ir_feed import VehicleIRFeed
from backend.app.fusion.fusion_engine import fusion_engine
from backend.app.fusion.queue_backend import get_queue_backend
from backend.app.models.schemas import SourceType
from backend.app.state_machine.f2t2ea import acknowledge_track, advance_stage, assess_track
from backend.app.streaming.sse import get_track_stream

background_tasks: list[asyncio.Task] = []
reading_queue = get_queue_backend()


async def fusion_loop():
    """Consumes normalized readings off the shared queue, fuses them, and
    advances each affected track's F2T2EA stage."""
    while True:
        reading = await reading_queue.get()
        track = fusion_engine.ingest(reading)
        advance_stage(track)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    for feed in feeds:
        feed.stop()
    for task in background_tasks:
        task.cancel()


app = FastAPI(title="Sentinel-FFT2EA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "active_tracks": len(fusion_engine.tracks)}


@app.get("/stream/tracks")
async def stream_tracks():
    return get_track_stream()


@app.get("/tracks")
async def list_tracks():
    return [t.model_dump(mode="json") for t in fusion_engine.snapshot()]


@app.post("/tracks/{track_id}/ack")
async def ack_track(track_id: str):
    """Operator acknowledges a TARGET-stage track, advancing it to ENGAGE.
    This is the only way a track can reach ENGAGE — never automatic."""
    track = fusion_engine.tracks.get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    try:
        acknowledge_track(track)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return track.model_dump(mode="json")


@app.post("/tracks/{track_id}/assess")
async def close_track(track_id: str, summary: str = ""):
    track = fusion_engine.tracks.get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    assess_track(track, summary)
    return track.model_dump(mode="json")


@app.post("/ew/toggle")
async def toggle_ew(source_type: SourceType):
    """Flip EW degradation on/off for a given source type."""
    new_state = ew_simulator.toggle(source_type)
    return {"source_type": source_type.value, "degraded": new_state}


@app.get("/ew/status")
async def ew_status():
    return ew_simulator.status()
