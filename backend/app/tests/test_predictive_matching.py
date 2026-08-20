from datetime import datetime, timedelta

from backend.app.config import settings
from backend.app.fusion.fusion_engine import FusionEngine, predict_position
from backend.app.models.schemas import Coordinates, SensorReading, SourceType


def make_reading(lat, lon, source_type, confidence=0.6, ts=None):
    return SensorReading(
        source_type=source_type,
        entity_hint="test_entity",
        coordinates=Coordinates(lat=lat, lon=lon),
        confidence=confidence,
        timestamp=ts or datetime.utcnow(),
    )


def test_predict_position_is_a_noop_for_a_stationary_track():
    engine = FusionEngine()
    t0 = datetime.utcnow()
    track = engine.ingest(make_reading(28.60, 77.20, SourceType.VEHICLE_IR, ts=t0))

    predicted = predict_position(track, t0 + timedelta(seconds=10))

    assert predicted.lat == track.coordinates.lat
    assert predicted.lon == track.coordinates.lon


def test_velocity_estimate_updates_after_two_consistent_readings():
    engine = FusionEngine()
    t0 = datetime.utcnow()

    # Two readings for the same track, moving steadily north.
    engine.ingest(make_reading(28.600, 77.200, SourceType.VEHICLE_IR, ts=t0))
    track = engine.ingest(make_reading(28.610, 77.200, SourceType.VEHICLE_IR, ts=t0 + timedelta(seconds=10)))

    assert track.velocity_lat > 0  # moving toward increasing latitude
    assert abs(track.velocity_lon) < 1e-6  # no east/west drift


def test_predictive_matching_catches_a_reading_static_matching_would_miss():
    """The core claim this feature makes: a track's next reading can land
    outside the raw distance threshold from its *last-known* position,
    but still match correctly once velocity is accounted for. Numbers
    below were verified empirically (not hand-derived) against the real
    _merge() confidence-weighted-averaging behavior, which lags position
    updates behind the raw readings — so the margins here are real, not
    idealized."""
    engine = FusionEngine()
    t0 = datetime.utcnow()

    # Establish a track moving steadily north — two readings 10s apart.
    engine.ingest(make_reading(28.600, 77.200, SourceType.VEHICLE_IR, ts=t0))
    track = engine.ingest(make_reading(28.610, 77.200, SourceType.UAV_UAS, ts=t0 + timedelta(seconds=10)))
    track_id = track.track_id

    # A third reading, another 10s later, continuing that heading.
    third_reading = make_reading(28.620, 77.200, SourceType.ELINT, ts=t0 + timedelta(seconds=20))

    from backend.app.fusion.fusion_engine import _haversine_km

    raw_distance = _haversine_km(third_reading.coordinates, track.coordinates)
    predicted = predict_position(track, third_reading.timestamp)
    predicted_distance = _haversine_km(third_reading.coordinates, predicted)

    # Verified concretely: raw distance from the track's last-known
    # position exceeds the 1.5km default threshold (a static matcher
    # would reject this and spawn a duplicate track), while the
    # velocity-predicted distance falls comfortably under it.
    assert raw_distance > settings.FUSION_DISTANCE_THRESHOLD_KM
    assert predicted_distance < settings.FUSION_DISTANCE_THRESHOLD_KM
    assert predicted_distance < raw_distance  # prediction is a real improvement, not incidental

    merged = engine.ingest(third_reading)
    assert merged.track_id == track_id  # matched the same track, not a new one
    assert len(engine.tracks) == 1


def test_no_prior_velocity_falls_back_to_static_matching():
    """A track with only one reading so far (no velocity estimate yet)
    should behave exactly like the original static nearest-neighbor
    matching — this is the 'gracefully degrades' claim in predict_position's
    docstring, checked directly rather than just asserted in a comment."""
    engine = FusionEngine()
    t0 = datetime.utcnow()

    track = engine.ingest(make_reading(28.600, 77.200, SourceType.VEHICLE_IR, ts=t0))
    assert track.velocity_lat == 0.0 and track.velocity_lon == 0.0

    nearby_reading = make_reading(28.6005, 77.2005, SourceType.UAV_UAS, ts=t0 + timedelta(seconds=5))
    merged = engine.ingest(nearby_reading)

    assert merged.track_id == track.track_id
    assert len(engine.tracks) == 1
