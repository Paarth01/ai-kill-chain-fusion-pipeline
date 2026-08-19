"""
Tests the X-API-Key auth boundary using FastAPI's TestClient directly
against `app`, toggling `settings.API_KEY` between tests to cover both
the default (disabled) and configured (enforced) states.
"""

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


def test_ew_toggle_open_by_default():
    """With API_KEY unset (the default), no header is required."""
    assert settings.API_KEY is None
    resp = client.post("/ew/toggle?source_type=uav_uas")
    assert resp.status_code == 200
    client.post("/ew/toggle?source_type=uav_uas")  # reset toggle state


def test_ew_toggle_requires_key_when_configured():
    settings.API_KEY = "test-secret-key"
    try:
        resp = client.post("/ew/toggle?source_type=elint")
        assert resp.status_code == 401
    finally:
        settings.API_KEY = None  # don't leak state into other tests


def test_ew_toggle_succeeds_with_correct_key():
    settings.API_KEY = "test-secret-key"
    try:
        resp = client.post("/ew/toggle?source_type=elint", headers={"X-API-Key": "test-secret-key"})
        assert resp.status_code == 200
        client.post("/ew/toggle?source_type=elint", headers={"X-API-Key": "test-secret-key"})  # reset
    finally:
        settings.API_KEY = None


def test_ew_toggle_rejects_wrong_key():
    settings.API_KEY = "test-secret-key"
    try:
        resp = client.post("/ew/toggle?source_type=legacy_c2", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401
    finally:
        settings.API_KEY = None


def test_read_endpoints_never_require_a_key():
    """Read endpoints (health, tracks) are intentionally never gated —
    only mutating endpoints are. This should hold whether or not API_KEY
    is configured."""
    settings.API_KEY = "test-secret-key"
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/tracks").status_code == 200
    finally:
        settings.API_KEY = None
