"""
API key auth for mutating endpoints.

Deliberately minimal — a single shared key via X-API-Key, not a full
user/session system. That's an intentional scope choice for a portfolio
project's operator-action endpoints, not a corner cut on something that
needed to be more sophisticated: there's only one "operator" role here,
so there's nothing a multi-user auth system would buy beyond complexity.

When API_KEY is unset, auth is disabled — this keeps `pip install -r
requirements.txt && uvicorn ...` and the test suite working with zero
setup. ALLOWED_ORIGINS has no bearing on this; only API_KEY does. Set
API_KEY before any real deployment.

Note the comparison below is a plain `!=`, not `hmac.compare_digest` — so
it isn't constant-time. Fine for a single shared local key; worth changing
if this ever guarded anything real.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from backend.app.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.API_KEY is None:
        return  # auth disabled — local/dev mode, no key configured
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")
