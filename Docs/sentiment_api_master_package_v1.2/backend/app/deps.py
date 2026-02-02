from __future__ import annotations

from fastapi import Depends, Header, Query
from .settings import settings
from .errors.http import http_error

def _configured_keys() -> set[str]:
    raw = (settings.api_keys or "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}

def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None),
) -> str:
    key = (x_api_key or api_key or "").strip()
    if not key:
        raise http_error(401, "auth_missing_api_key", "Missing API key. Provide X-API-Key header or api_key query param.")
    configured = _configured_keys()
    if configured and key not in configured:
        raise http_error(403, "auth_invalid_api_key", "Invalid API key.")
    # In dev, if no keys configured, any non-empty key is accepted.
    return key
