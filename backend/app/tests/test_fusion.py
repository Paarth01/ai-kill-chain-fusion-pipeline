from datetime import datetime, timedelta

from backend.app.fusion.fusion_engine import FusionEngine
from backend.app.models.schemas import Coordinates, SensorReading, SourceType


def make_reading(lat, lon, source_type, confidence=0.6, ts=None):
    return SensorReading(
        source_type=source_type,
        entity_hint="test_entity",
        coordinates=Coordinates(lat=lat, lon=lon),
        confidence=confidence,
        timestamp=ts or datetime.utcnow(),
    )


def test_first_reading_creates_new_track():
    engine = FusionEngine()
    reading = make_reading(28.60, 77.20, SourceType.VEHICLE_IR)

    track = engine.ingest(reading)

    assert len(engine.tracks) == 1
    assert track.contributing_sources == [SourceType.VEHICLE_IR]
    assert track.reading_count == 1


def test_nearby_reading_from_new_source_merges_and_boosts_confidence():
    engine = FusionEngine()
    r1 = make_reading(28.60, 77.20, SourceType.VEHICLE_IR, confidence=0.6)
    track = engine.ingest(r1)
    initial_confidence = track.confidence

    # Close enough in space and time to be the same entity.
    r2 = make_reading(28.6005, 77.2005, SourceType.UAV_UAS, confidence=0.6)
    merged = engine.ingest(r2)

    assert len(engine.tracks) == 1
    assert merged.track_id == track.track_id
    assert set(merged.contributing_sources) == {SourceType.VEHICLE_IR, SourceType.UAV_UAS}
    assert merged.confidence > initial_confidence
    assert merged.reading_count == 2


def test_far_away_reading_creates_separate_track():
    engine = FusionEngine()
    r1 = make_reading(28.60, 77.20, SourceType.VEHICLE_IR)
    r2 = make_reading(29.50, 78.50, SourceType.UAV_UAS)  # far outside threshold

    engine.ingest(r1)
    engine.ingest(r2)

    assert len(engine.tracks) == 2


def test_stale_tracks_are_pruned():
    engine = FusionEngine()
    old_ts = datetime.utcnow() - timedelta(seconds=999)
    r1 = make_reading(28.60, 77.20, SourceType.VEHICLE_IR, ts=old_ts)
    engine.ingest(r1)
    # Force last_updated into the past for the prune check.
    for t in engine.tracks.values():
        t.last_updated = old_ts

    removed = engine.prune_stale()

    assert len(removed) == 1
    assert len(engine.tracks) == 0
