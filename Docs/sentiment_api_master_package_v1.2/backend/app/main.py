from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from .utils.request_id import new_request_id
from .errors.models import err
from .http.response import ok_envelope
from .observability.metrics import REQUESTS_TOTAL, REQUEST_LATENCY
from .settings import settings

from .routes.compat import router as compat_router
from .routes.v1.health import router as health_router
from .routes.v1.mood import router as mood_router
from .routes.v1.index import router as index_router
from .routes.v1.news import router as news_router
from .routes.v1.sources import router as sources_router
from .routes.v1.research import router as research_router
from .routes.v1.impacts import router as impacts_router
from .routes.v1.universes import router as universes_router
from .routes.v1.sectors import router as sectors_router
from .routes.v1.topics import router as topics_router
from .routes.v1.stream import router as stream_router
from .routes.v1.metrics import router as metrics_router

app = FastAPI(
    title="sentiment_api",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.middleware("http")
async def request_context(request: Request, call_next: Callable):
    request_id = request.headers.get("X-Request-Id") or new_request_id()
    request.state.request_id = request_id

    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed = time.perf_counter() - start
        # best-effort metric labels
        path = request.url.path
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(elapsed)

    response.headers["X-Request-Id"] = request_id
    REQUESTS_TOTAL.labels(method=request.method, path=request.url.path, status=str(response.status_code)).inc()
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # exc.detail can be a dict from errors.http.http_error()
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "internal_error", "message": str(exc.detail)}
    e = err(detail.get("code","internal_error"), detail.get("message","error"), details=detail.get("details",{}), hint=detail.get("hint"), retryable=bool(detail.get("retryable",False)))
    body = ok_envelope(request.state.request_id, data={}, errors=[e])
    return JSONResponse(status_code=exc.status_code, content=body)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    e = err("internal_error", "Unhandled error", details={"type": type(exc).__name__}, retryable=True)
    body = ok_envelope(request.state.request_id, data={}, errors=[e])
    return JSONResponse(status_code=500, content=body)

# Routers
app.include_router(compat_router)
app.include_router(health_router)
app.include_router(mood_router)
app.include_router(index_router)
app.include_router(news_router)
app.include_router(sources_router)
app.include_router(research_router)
app.include_router(impacts_router)
app.include_router(universes_router)
app.include_router(sectors_router)
app.include_router(topics_router)
app.include_router(stream_router)

# metrics router should be root-level
app.include_router(metrics_router)

@app.get("/", include_in_schema=False)
def root():
    return {"name": "sentiment_api", "version": app.version, "environment": settings.environment}
