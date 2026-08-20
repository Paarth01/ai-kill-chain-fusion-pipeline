"""
Prometheus-format metrics, served at /metrics.

Gauges are recomputed fresh from the live state on every scrape
(refresh_gauges()) rather than updated incrementally as state changes —
fusion_engine.tracks and ew_simulator's internal sets are already the
single source of truth, so recomputing from them on read avoids the
metrics ever silently drifting out of sync with the state they're
supposed to reflect.
"""

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest

from backend.app.ew.ew_simulator import ew_simulator
from backend.app.fusion.fusion_engine import fusion_engine
from backend.app.models.schemas import F2T2EAStage

registry = CollectorRegistry()

http_requests_total = Counter(
    "sentinel_http_requests_total",
    "Total HTTP requests handled",
    ["method", "path", "status_code"],
    registry=registry,
)

active_tracks_gauge = Gauge("sentinel_active_tracks", "Currently active fused tracks", registry=registry)

tracks_by_stage_gauge = Gauge(
    "sentinel_tracks_by_stage", "Active tracks by F2T2EA stage", ["stage"], registry=registry
)

ew_degraded_gauge = Gauge(
    "sentinel_ew_degraded_sources", "Number of source types currently EW-degraded", registry=registry
)

ew_spoofing_gauge = Gauge(
    "sentinel_ew_spoofing_sources", "Number of source types currently being spoofed", registry=registry
)


def refresh_gauges() -> None:
    tracks = fusion_engine.snapshot()
    active_tracks_gauge.set(len(tracks))

    counts = {stage.value: 0 for stage in F2T2EAStage}
    for t in tracks:
        counts[t.stage.value] += 1
    for stage, count in counts.items():
        tracks_by_stage_gauge.labels(stage=stage).set(count)

    ew_status = ew_simulator.status()
    ew_degraded_gauge.set(sum(1 for degraded in ew_status.values() if degraded))

    spoof_status = ew_simulator.spoof_status()
    ew_spoofing_gauge.set(sum(1 for spoofing in spoof_status.values() if spoofing))


def render_metrics() -> bytes:
    refresh_gauges()
    return generate_latest(registry)
