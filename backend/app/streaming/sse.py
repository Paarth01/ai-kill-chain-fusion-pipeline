"""
SSE endpoint that periodically pushes the current fused-track snapshot to
any connected operator dashboard. Reuses the same "poll shared state, yield
JSON" pattern from the Purplle Tech Challenge / TripSync AI SSE endpoints.
"""

import asyncio
import json

from sse_starlette.sse import EventSourceResponse

from backend.app.ew.ew_simulator import ew_simulator
from backend.app.fusion.fusion_engine import fusion_engine

BROADCAST_INTERVAL_SECONDS = 1.0


async def track_event_generator():
    while True:
        fusion_engine.prune_stale()
        snapshot = [t.model_dump(mode="json") for t in fusion_engine.snapshot()]
        payload = {
            "tracks": snapshot,
            "ew_status": ew_simulator.status(),
        }
        yield {"event": "tracks_update", "data": json.dumps(payload)}
        await asyncio.sleep(BROADCAST_INTERVAL_SECONDS)


def get_track_stream() -> EventSourceResponse:
    return EventSourceResponse(track_event_generator())
