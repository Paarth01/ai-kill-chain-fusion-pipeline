"""
Structured logging setup. Two formats, controlled by LOG_FORMAT:

- "text" (default): human-readable, good for local development
- "json": one JSON object per line — what you actually want once this is
  running somewhere with a log aggregator (Render, Datadog, CloudWatch,
  etc.) rather than a terminal someone's watching directly

Applied once at app startup (main.py's lifespan). Doesn't touch
uvicorn's own access-log formatting — this configures the app's own
logger namespace (backend.app.*), which is what the app's own log
statements (e.g. the real-detection fallback warning in
vehicle_ir_feed.py) go through.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from backend.app.config import settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    root_logger = logging.getLogger("backend")
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if configure_logging() is called more than
    # once (e.g. across test runs sharing the process).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)
    root_logger.propagate = False
