"""Idempotency-Key support for POST endpoints (v1.2 spec)."""

import json
import logging
from typing import Any

from starlette.requests import Request

logger = logging.getLogger("sentiment_api.idempotency")

IDEMPOTENCY_PREFIX = "idempotency:"
IDEMPOTENCY_TTL = 86400  # 24h


async def get_cached(request: Request) -> dict | None:
    """Return {status, body} if Idempotency-Key hit, else None."""
    key = (request.headers.get("Idempotency-Key") or "").strip()
    if not key or len(key) < 16 or len(key) > 128:
        return None
    key = f"{IDEMPOTENCY_PREFIX}{key[:64]}"
    try:
        import redis.asyncio as redis
        from sentiment_api.config import get_settings
        r = redis.from_url(get_settings().redis_url)
        raw = await r.get(key)
        await r.aclose()
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug("Idempotency cache read failed: %s", e)
    return None


async def set_cached(request: Request, status: int, body: dict[str, Any]) -> None:
    """Store response under Idempotency-Key."""
    key = (request.headers.get("Idempotency-Key") or "").strip()
    if not key or len(key) < 16 or len(key) > 128:
        return
    key = f"{IDEMPOTENCY_PREFIX}{key[:64]}"
    try:
        import redis.asyncio as redis
        from sentiment_api.config import get_settings
        r = redis.from_url(get_settings().redis_url)
        await r.setex(key, IDEMPOTENCY_TTL, json.dumps({"status": status, "body": body}))
        await r.aclose()
    except Exception as e:
        logger.debug("Idempotency cache write failed: %s", e)
