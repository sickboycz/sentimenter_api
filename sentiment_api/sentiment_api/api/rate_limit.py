"""Rate limiting middleware — v1.2 spec: 60 req/min default, 10 req/min research, 10 SSE streams."""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sentiment_api.rate_limit")

# Limits per api_key
DEFAULT_LIMIT = 60  # req/min
RESEARCH_LIMIT = 10  # req/min for /v1/research/*
SSE_CONCURRENT_LIMIT = 10  # concurrent SSE streams per api_key

# Sliding window: (timestamps,)
_windows: dict[str, list[float]] = defaultdict(list)
_sse_count: dict[str, int] = defaultdict(int)
_lock = asyncio.Lock()


def _client_key(request: Request) -> str:
    """Identify client: api_key if present, else IP."""
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key:
        return f"key:{key[:32]}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _is_research_path(path: str) -> bool:
    return path.startswith("/v1/research/")


def _is_sse_path(path: str) -> bool:
    return path == "/v1/stream/events"


async def _check_limit(key: str, limit: int) -> bool:
    """Return True if under limit (sliding window, 1 min)."""
    now = time.monotonic()
    async with _lock:
        w = _windows[key]
        cutoff = now - 60
        w[:] = [t for t in w if t > cutoff]
        if len(w) >= limit:
            return False
        w.append(now)
        return True


async def _inc_sse(key: str) -> bool:
    """Increment SSE count; return False if over limit."""
    async with _lock:
        c = _sse_count[key]
        if c >= SSE_CONCURRENT_LIMIT:
            return False
        _sse_count[key] = c + 1
        return True


def _dec_sse(key: str) -> None:
    async def _do():
        async with _lock:
            _sse_count[key] = max(0, _sse_count[key] - 1)
    asyncio.create_task(_do())


class RateLimitMiddleware(BaseHTTPMiddleware):
    """v1.2: 60 req/min default, 10 req/min research, 10 SSE streams per api_key."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limit for /metrics, /ready, /v1/health (readiness probes)
        path = request.url.path or ""
        if path in ("/metrics", "/ready", "/v1/health", "/v1/status", "/"):
            return await call_next(request)

        key = _client_key(request)
        limit = RESEARCH_LIMIT if _is_research_path(path) else DEFAULT_LIMIT

        if _is_sse_path(path):
            if not await _inc_sse(key):
                from fastapi.responses import JSONResponse
                from datetime import datetime, timezone
                return JSONResponse(
                    status_code=429,
                    content={
                        "meta": {"request_id": getattr(request.state, "request_id", "req_unknown"), "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
                        "data": {},
                        "errors": [{"code": "rate_limit_exceeded", "message": "Max concurrent SSE streams exceeded (10 per key)."}],
                    },
                )
            return await call_next(request)

        if not await _check_limit(key, limit):
            from datetime import datetime, timezone
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "meta": {"request_id": getattr(request.state, "request_id", "req_unknown"), "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
                    "data": {},
                    "errors": [{"code": "rate_limit_exceeded", "message": f"Rate limit exceeded ({limit} req/min)."}],
                },
            )

        return await call_next(request)
