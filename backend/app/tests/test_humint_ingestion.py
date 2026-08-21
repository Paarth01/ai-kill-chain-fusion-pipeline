"""
Tests HUMINT ingestion: the POST /ingest/humint endpoint, the
build_contact_from_humint() adapter, and how a HUMINT-derived reading
behaves once it reaches the fusion engine.

The queue is stubbed out (see `_capture_queue`) rather than exercised for
real. Two reasons: the endpoint's job ends at "normalized and queued"
(fusion_loop consumes it separately), and main.py's module-level
reading_queue is a RedisQueueBackend whenever REDIS_URL is set — as it is
in CI — which would bind a real Redis connection to the TestClient's event
loop and then be read from another. Capturing the put keeps these tests
deterministic in both local and CI configurations, and the fused-output
assertions below run the captured reading through a real FusionEngine, so
the fusion path is genuinely tested rather than mocked.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.feeds.humint_ingest import build_contact_from_humint
from backend.app.fusion.fusion_engine import FusionEngine
from backend.app.models.schemas import (
    Coordinates,
    F2T2EAStage,
    HumintConfidence,
    HumintReport,
    SensorReading,
    SourceType,
    ThreatSeverity,
)
from backend.app.state_machine.f2t2ea import advance_stage

client = TestClient(app=main.app)


class _CaptureQueue:
    """Stands in for the real QueueBackend, recording what was put on it."""

    def __init__(self):
        self.puts: list[SensorReading] = []

    async def put(self, reading: SensorReading) -> None:
        self.puts.append(reading)


@pytest.fixture
def captured(monkeypatch) -> _CaptureQueue:
    queue = _CaptureQueue()
    monkeypatch.setattr(main, "reading_queue", queue)
    return queue


def _valid_payload(confidence: str = "high") -> dict:
    return {
        "source_id": "HUMINT-OBS-04",
        "report_text": "Two tracked vehicles moving north along the treeline.",
        "location": {"lat": 28.60, "lon": 77.20},
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
    }


def test_valid_humint_report_is_accepted_and_fuses_correctly(captured):
    """A well-formed report normalizes into a SensorReading, reaches the
    queue, and corroborates an existing sensor track — the whole point of
    adding the source, rather than just returning 202."""
    resp = client.post("/ingest/humint", json=_valid_payload("high"))

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["source_type"] == "humint"
    assert body["confidence"] == 0.8  # HIGH band -> 0.8

    # The endpoint queued exactly one normalized reading.
    assert len(captured.puts) == 1
    reading = captured.puts[0]
    assert reading.source_type == SourceType.HUMINT
    assert reading.coordinates == Coordinates(lat=28.60, lon=77.20)
    assert reading.reading_id == body["reading_id"]
    # Reporter's own words are preserved verbatim, attributed to the source.
    assert "Two tracked vehicles" in reading.raw_signature
    assert reading.raw_signature.startswith("HUMINT-OBS-04:")

    # Now the part that matters: it fuses like any other source. A UAV
    # contact already exists at nearly the same position; the HUMINT report
    # should merge into it and count as independent corroboration.
    engine = FusionEngine()
    uav_track = engine.ingest(
        SensorReading(
            source_type=SourceType.UAV_UAS,
            entity_hint="vehicle",
            coordinates=Coordinates(lat=28.6005, lon=77.2005),
            confidence=0.6,
            timestamp=reading.timestamp,
        )
    )
    merged = engine.ingest(reading)

    assert len(engine.tracks) == 1, "HUMINT should corroborate, not spawn a duplicate track"
    assert merged.track_id == uav_track.track_id
    assert set(merged.contributing_sources) == {SourceType.UAV_UAS, SourceType.HUMINT}
    assert merged.confidence > 0.6  # independent-source corroboration bump
    # Two independent sources agreeing advances FIND -> FIX.
    advance_stage(merged)
    assert merged.stage == F2T2EAStage.FIX


@pytest.mark.parametrize(
    "bad_payload, expected_field",
    [
        ({"location": None}, "location"),                              # explicitly null
        ({"location": {"lat": 28.60}}, "lon"),                         # incomplete pair
        ({"location": {"lat": "not-a-number", "lon": 77.20}}, "lat"),  # unparseable
    ],
)
def test_report_with_malformed_location_is_rejected(captured, bad_payload, expected_field):
    """A report that can't be placed on the map can't be fused, so it's
    rejected at the schema boundary with a 422 naming the offending field —
    never silently defaulted to coordinates nobody observed."""
    payload = _valid_payload()
    payload.update(bad_payload)

    resp = client.post("/ingest/humint", json=payload)

    assert resp.status_code == 422
    error_locations = [part for err in resp.json()["detail"] for part in err["loc"]]
    assert expected_field in error_locations
    # Critically: nothing reached the fusion queue.
    assert captured.puts == []


def test_missing_location_key_entirely_is_rejected(captured):
    """`location` has no default — omitting it is an error, not a shortcut."""
    payload = _valid_payload()
    del payload["location"]

    resp = client.post("/ingest/humint", json=payload)

    assert resp.status_code == 422
    assert any("location" in err["loc"] for err in resp.json()["detail"])
    assert captured.puts == []


def test_low_confidence_report_is_ingested_but_flagged_as_unknown_severity(captured):
    """A low-confidence report is NOT dropped — an uncertain human report is
    still intelligence. But it must not be able to drive the kill chain on
    its own: 0.25 falls below the classifier's 0.4 floor, so the resulting
    track carries UNKNOWN severity and stays at FIND, well short of TARGET.
    """
    resp = client.post("/ingest/humint", json=_valid_payload("low"))

    assert resp.status_code == 202
    assert resp.json()["confidence"] == 0.25  # LOW band -> 0.25
    assert len(captured.puts) == 1

    reading = captured.puts[0]
    engine = FusionEngine()
    track = engine.ingest(reading)
    advance_stage(track)

    # Ingested and visible in the fused output...
    assert track.contributing_sources == [SourceType.HUMINT]
    assert track.confidence == 0.25
    # ...but flagged as unreliable, and nowhere near an engageable stage.
    assert track.severity == ThreatSeverity.UNKNOWN
    assert track.stage == F2T2EAStage.FIND
    assert track.operator_ack is False

    # For contrast, the same report filed at HIGH confidence clears the
    # classifier's floor — confirming the flagging tracks the stated
    # confidence band rather than being a property of HUMINT as a source.
    high = build_contact_from_humint(
        HumintReport(
            source_id="HUMINT-OBS-04",
            report_text="Same sighting, reported with high certainty.",
            location=Coordinates(lat=28.70, lon=77.30),
            confidence=HumintConfidence.HIGH,
        )
    )
    high_track = advance_stage(FusionEngine().ingest(high))
    assert high_track.severity == ThreatSeverity.LOW  # 0.8 >= 0.4, single source
