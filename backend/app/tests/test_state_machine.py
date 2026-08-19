import pytest

from backend.app.models.schemas import Coordinates, F2T2EAStage, FusedTrack, SourceType
from backend.app.state_machine.f2t2ea import acknowledge_track, advance_stage, assess_track


def make_track(**overrides) -> FusedTrack:
    defaults = dict(
        coordinates=Coordinates(lat=28.6, lon=77.2),
        contributing_sources=[SourceType.VEHICLE_IR],
        confidence=0.5,
        reading_count=1,
    )
    defaults.update(overrides)
    return FusedTrack(**defaults)


def test_starts_at_find():
    track = make_track()
    assert track.stage == F2T2EAStage.FIND


def test_advances_to_fix_with_second_source():
    track = make_track(contributing_sources=[SourceType.VEHICLE_IR, SourceType.UAV_UAS])
    advance_stage(track)
    assert track.stage == F2T2EAStage.FIX


def test_advances_to_track_with_enough_readings():
    track = make_track(
        contributing_sources=[SourceType.VEHICLE_IR, SourceType.UAV_UAS],
        reading_count=3,
    )
    track.stage = F2T2EAStage.FIX
    advance_stage(track)
    assert track.stage == F2T2EAStage.TRACK


def test_advances_to_target_when_severity_crosses_threshold():
    track = make_track(
        contributing_sources=[SourceType.VEHICLE_IR, SourceType.UAV_UAS, SourceType.ELINT],
        reading_count=5,
        confidence=0.85,
    )
    track.stage = F2T2EAStage.TRACK
    advance_stage(track)
    assert track.stage == F2T2EAStage.TARGET


def test_engage_requires_explicit_acknowledgement_from_target():
    track = make_track()
    track.stage = F2T2EAStage.TARGET
    acknowledge_track(track)
    assert track.stage == F2T2EAStage.ENGAGE
    assert track.operator_ack is True


def test_cannot_acknowledge_track_not_in_target_stage():
    track = make_track()  # stage == FIND
    with pytest.raises(ValueError):
        acknowledge_track(track)


def test_assess_closes_out_track():
    track = make_track()
    track.stage = F2T2EAStage.ENGAGE
    assess_track(track, summary="resolved in simulation")
    assert track.stage == F2T2EAStage.ASSESS
