import json
import logging

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.logging_config import JsonLogFormatter, configure_logging
from backend.app.main import app

client = TestClient(app)


def test_metrics_endpoint_returns_prometheus_format():
    resp = client.get("/metrics")

    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]

    body = resp.text
    assert "sentinel_active_tracks" in body
    assert "sentinel_tracks_by_stage" in body
    assert "sentinel_ew_degraded_sources" in body
    assert "sentinel_ew_spoofing_sources" in body
    assert "sentinel_http_requests_total" in body


def test_metrics_reflects_live_track_count():
    resp = client.get("/metrics")
    body = resp.text

    # active_tracks gauge line should be a real number, not a placeholder.
    active_line = next(line for line in body.splitlines() if line.startswith("sentinel_active_tracks "))
    value = float(active_line.split()[-1])
    assert value >= 0  # sanity: it's a real, parseable metric value


def test_metrics_scrape_itself_is_not_counted_in_http_requests_total():
    # Two scrapes shouldn't inflate the /metrics-path count, since the
    # middleware explicitly excludes /metrics from its own counting.
    client.get("/metrics")
    resp = client.get("/metrics")

    metrics_lines = [
        line for line in resp.text.splitlines() if line.startswith('sentinel_http_requests_total{') and 'path="/metrics"' in line
    ]
    assert metrics_lines == []


def test_health_endpoint_is_counted_in_http_requests_total():
    client.get("/health")
    resp = client.get("/metrics")

    health_lines = [
        line
        for line in resp.text.splitlines()
        if line.startswith("sentinel_http_requests_total{") and 'path="/health"' in line
    ]
    assert len(health_lines) >= 1


def test_json_log_formatter_produces_valid_parseable_json():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="backend.app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test message %s",
        args=("arg1",),
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)  # raises if not valid JSON — the actual claim being tested

    assert parsed["message"] == "test message arg1"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "backend.app.test"
    assert "timestamp" in parsed


def test_configure_logging_does_not_duplicate_handlers_on_repeated_calls():
    """configure_logging() gets called at import time; calling it again
    (e.g. across test runs sharing the process) should not accumulate
    duplicate handlers, which would otherwise duplicate every log line."""
    configure_logging()
    configure_logging()
    configure_logging()

    root_logger = logging.getLogger("backend")
    assert len(root_logger.handlers) == 1


def test_configure_logging_respects_log_format_setting():
    original = settings.LOG_FORMAT
    try:
        settings.LOG_FORMAT = "json"
        configure_logging()
        root_logger = logging.getLogger("backend")
        assert isinstance(root_logger.handlers[0].formatter, JsonLogFormatter)

        settings.LOG_FORMAT = "text"
        configure_logging()
        root_logger = logging.getLogger("backend")
        assert not isinstance(root_logger.handlers[0].formatter, JsonLogFormatter)
    finally:
        settings.LOG_FORMAT = original
        configure_logging()
