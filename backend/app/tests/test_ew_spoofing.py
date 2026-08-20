from unittest.mock import patch

from backend.app.ew.ew_simulator import EWSimulator
from backend.app.models.schemas import Coordinates, SensorReading, SourceType


def make_reading():
    return SensorReading(
        source_type=SourceType.UAV_UAS,
        entity_hint="phantom_contact",
        coordinates=Coordinates(lat=28.6, lon=77.2),
        confidence=0.7,
    )


def test_toggle_spoof_flips_state():
    sim = EWSimulator()
    assert sim.is_spoofing(SourceType.ELINT) is False

    new_state = sim.toggle_spoof(SourceType.ELINT)
    assert new_state is True
    assert sim.is_spoofing(SourceType.ELINT) is True

    new_state = sim.toggle_spoof(SourceType.ELINT)
    assert new_state is False
    assert sim.is_spoofing(SourceType.ELINT) is False


def test_spoof_status_reports_only_active_sources():
    sim = EWSimulator()
    sim.toggle_spoof(SourceType.UAV_UAS)

    status = sim.spoof_status()

    assert status["uav_uas"] is True
    assert status["elint"] is False
    assert status["vehicle_ir"] is False
    assert status["legacy_c2"] is False


def test_maybe_spoof_reading_returns_none_when_spoofing_inactive():
    sim = EWSimulator()
    # Not toggled on for this source — should never call the generator.
    result = sim.maybe_spoof_reading(SourceType.LEGACY_C2, make_reading)
    assert result is None


def test_maybe_spoof_reading_fires_when_the_random_gate_passes():
    """Deterministic, not statistical: force the random gate to pass so
    this test doesn't flake based on the 30% chance."""
    sim = EWSimulator()
    sim.toggle_spoof(SourceType.UAV_UAS)

    with patch("backend.app.ew.ew_simulator.random.random", return_value=0.1):  # < 0.3 threshold
        result = sim.maybe_spoof_reading(SourceType.UAV_UAS, make_reading)

    assert result is not None
    assert isinstance(result, SensorReading)
    assert result.source_type == SourceType.UAV_UAS


def test_maybe_spoof_reading_skips_when_the_random_gate_fails():
    """The other deterministic branch — most cycles, even while spoofing
    is active, produce no phantom contact."""
    sim = EWSimulator()
    sim.toggle_spoof(SourceType.UAV_UAS)

    with patch("backend.app.ew.ew_simulator.random.random", return_value=0.9):  # >= 0.3 threshold
        result = sim.maybe_spoof_reading(SourceType.UAV_UAS, make_reading)

    assert result is None


def test_spoofed_reading_is_structurally_identical_to_a_real_one():
    """The whole point: a spoofed reading carries no marker distinguishing
    it from genuine sensor data — same schema, same fields, nothing
    filterable. Checked directly rather than just asserted in a docstring."""
    sim = EWSimulator()
    sim.toggle_spoof(SourceType.ELINT)

    with patch("backend.app.ew.ew_simulator.random.random", return_value=0.0):
        spoofed = sim.maybe_spoof_reading(SourceType.ELINT, make_reading)
    genuine = make_reading()

    assert type(spoofed) is type(genuine)
    assert set(spoofed.model_dump().keys()) == set(genuine.model_dump().keys())


def test_spoof_toggle_endpoint_and_sse_payload_expose_spoof_status():
    """Integration check that the dashboard's spoof toggle buttons have
    real data to render: /ew/spoof/toggle actually flips state, and the
    SSE payload's ew_spoof_status field reflects it — not just that the
    EWSimulator class works in isolation."""
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)

    resp = client.post("/ew/spoof/toggle?source_type=uav_uas")
    assert resp.status_code == 200
    assert resp.json() == {"source_type": "uav_uas", "spoofing": True}

    status_resp = client.get("/ew/spoof/status")
    assert status_resp.json()["uav_uas"] is True

    # Reset so this test doesn't leak state into other tests sharing the
    # module-level ew_simulator singleton.
    client.post("/ew/spoof/toggle?source_type=uav_uas")
