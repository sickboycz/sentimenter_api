"""FastAPI application — M9 API Service."""

import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from sentiment_api.api.auth import get_api_key
from sentiment_api.api.keys import validate_api_key
from sentiment_api.api.rate_limit import RateLimitMiddleware, _client_key, _dec_sse
from sentiment_api.api.responses import error_detail, meta, pagination
from sentiment_api.config import get_settings
from sentiment_api.db.pool import close_pool, init_pool
from sentiment_api.registry import load_registry, RegistryError


def _ensure_dict(val: dict | str | None) -> dict:
    """Normalize DB JSON/JSONB (can be dict or string) to dict."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val) if val.strip() else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sentiment_api.debug_bootstrap import run as debug_bootstrap_run
    debug_bootstrap_run()
    from sentiment_api.logging_file import add_file_handler
    add_file_handler("api")
    settings = get_settings()
    try:
        await init_pool(settings.database_url)
        from sentiment_api.db.pool import get_pool
        pool = get_pool()
        if pool:
            try:
                from sentiment_api.db.universe_repo import seed_sectors, seed_industries, upsert_universe
                async with pool.acquire() as conn:
                    registry_dir = Path(settings.source_registry_path).parent
                    await seed_sectors(conn, registry_dir)
                    await seed_industries(conn, registry_dir)
                    try:
                        from sentiment_api.universe import load_universe_registry
                        ureg = load_universe_registry(settings.universe_registry_path)
                        for u in ureg.get_enabled():
                            await upsert_universe(conn, u.universe_id, u.name_en, "registry", u.description_en)
                    except Exception:
                        await upsert_universe(conn, "sp500", "S&P 500", "seed", "S&P 500 constituents")
                        await upsert_universe(conn, "nasdaq100", "Nasdaq-100", "seed", "Nasdaq-100 constituents")
            except Exception as ex:
                import logging
                logging.getLogger("sentiment_api").debug("Universe seed skipped (tables may not exist): %s", ex)
    except Exception as e:
        import logging
        logging.getLogger("sentiment_api").warning(
            "DB pool init failed (Postgres may be down): %s. API will start but DB endpoints may fail.",
            e,
        )
    yield
    await close_pool()


app = FastAPI(
    title="sentiment_api",
    version="1.2.0",
    summary="Global macro + political news impact intelligence (Sentimeter)",
    lifespan=lifespan,
)

# CORS: allow frontend origin(s) from config; regex allows any host:3000 (same-host UI by IP)
# Ensure localhost:3000 is always allowed so UI works when CORS_ORIGINS is unset or empty (e.g. in Docker)
_cors_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["http://localhost:3000"]
elif "http://localhost:3000" not in _cors_origins:
    _cors_origins = list(_cors_origins) + ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://[^:/]+:3000",  # e.g. http://80.211.210.49:3000 when UI opened by IP
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

# Enable request logging (method/path/status/duration) when debugging
_DEBUG_LOG = os.environ.get("DEBUG_ATTACH") == "1" or os.environ.get("DEBUG_LOG") == "1"

@app.middleware("http")
async def cors_fix_middleware(request: Request, call_next):
    """Ensure every response has CORS headers when Origin is allowed (fixes 401/429/etc from middleware or deps)."""
    response = await call_next(request)
    if "access-control-allow-origin" not in (h.lower() for h in response.headers.keys()):
        cors = _cors_headers_for_request(request)
        for k, v in cors.items():
            response.headers[k] = v
    return response


@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Set request_id for envelope correlation."""
    rid = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.middleware("http")
async def debug_request_log_middleware(request, call_next):
    """Log method/path/status/duration at INFO when DEBUG_ATTACH or DEBUG_LOG is set."""
    import time
    import logging
    start = time.perf_counter()
    response = await call_next(request)
    if _DEBUG_LOG:
        ms = (time.perf_counter() - start) * 1000
        logging.getLogger("sentiment_api").info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path or "/",
            response.status_code,
            ms,
        )
    return response


def _cors_headers_for_request(request: Request) -> dict:
    """Add CORS headers so exception/error responses allow the requesting origin (avoids CORS block on 401/404/500)."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if origin in _cors_origins:
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
    if re.match(r"^https?://[^:/]+:3000$", origin):
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Return v1.2 envelope for HTTP errors on /v1/*. Include CORS headers so 401/404/500 don't block the UI."""
    rid = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:12]}")
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        err_obj = {"code": detail["code"], "message": detail["message"]}
        if detail.get("details"):
            err_obj["details"] = detail["details"]
        if detail.get("hint"):
            err_obj["hint"] = detail["hint"]
        body = {
            "meta": {"request_id": rid, "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z")},
            "data": {},
            "errors": [err_obj],
        }
        return JSONResponse(status_code=exc.status_code, content=body, headers=_cors_headers_for_request(request))
    # Fallback for legacy string detail
    body = {
        "meta": {"request_id": rid, "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z")},
        "data": {},
        "errors": [{"code": "http_error", "message": str(detail)}],
    }
    return JSONResponse(status_code=exc.status_code, content=body, headers=_cors_headers_for_request(request))


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Record API latency and errors for Prometheus (AC-M10.3)."""
    import time
    from sentiment_api.metrics import api_latency_ms, api_errors_total, api_requests_total
    start = time.perf_counter()
    try:
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        route = request.url.path or "unknown"
        status = str(response.status_code)
        api_latency_ms(route, ms)
        api_requests_total(route, status)
        if response.status_code >= 400:
            api_errors_total(route, status)
        return response
    except Exception:
        ms = (time.perf_counter() - start) * 1000
        route = request.url.path or "unknown"
        api_latency_ms(route, ms)
        api_requests_total(route, "500")
        api_errors_total(route, "500")
        raise


def _get_registry():
    """Load registry; fail gracefully if path invalid or parse error."""
    import logging
    import yaml
    settings = get_settings()
    try:
        return load_registry(settings.source_registry_path)
    except (RegistryError, json.JSONDecodeError, yaml.YAMLError, OSError) as e:
        logging.getLogger("sentiment_api").debug("Registry load failed: %s", e)
        return None


# -----------------------------------------------------------------------------
# /metrics — Prometheus (no auth, AC-M10.1, M10.2, M10.3)
# -----------------------------------------------------------------------------
@app.get("/metrics")
async def metrics():
    """Prometheus metrics: ingestion, translation, queue, API."""
    from sentiment_api.metrics import collect_metrics
    from sentiment_api.config import get_settings
    try:
        import redis.asyncio as redis
        r = redis.from_url(get_settings().redis_url)
        from sentiment_api.queue.client import QUEUE_INGEST, QUEUE_SUMMARIZE, QUEUE_INDEX
        for q in [QUEUE_INGEST, QUEUE_SUMMARIZE, QUEUE_INDEX]:
            d = await r.llen(q)
            from sentiment_api.metrics import queue_depth
            queue_depth(q, d)
        await r.aclose()
    except Exception as ex:
        import logging as _log
        _log.getLogger("sentiment_api").debug("Metrics queue depth update skipped: %s", ex)
    return PlainTextResponse(collect_metrics(), media_type="text/plain; charset=utf-8")


# -----------------------------------------------------------------------------
# /ready — Readiness probe (DB ready)
# -----------------------------------------------------------------------------
@app.get("/ready")
async def ready():
    """Readiness: 200 when DB is ready to serve. No auth."""
    try:
        from sentiment_api.db.pool import get_pool, ensure_pool
        pool = get_pool()
        if pool is None:
            try:
                pool = await ensure_pool(get_settings().database_url)
            except Exception as e:
                return Response(status_code=503, content=f"DB not ready: {e!s}")
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return Response(status_code=200, content="ok")
    except Exception as e:
        return Response(status_code=503, content=f"DB not ready: {e!s}")


# -----------------------------------------------------------------------------
# /v1/health — No auth (AC-M10.4)
# -----------------------------------------------------------------------------
@app.get("/v1/health")
async def health():
    """Health and dependency checks."""
    checks = []
    settings = get_settings()

    # DB check (lazy-init pool if lifespan init failed, e.g. Postgres not ready at startup)
    try:
        from sentiment_api.db.pool import ensure_pool
        pool = await ensure_pool(settings.database_url)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks.append({"name": "postgres", "status": "ok", "details": {}})
    except Exception as e:
        checks.append({"name": "postgres", "status": "fail", "details": {"error": str(e)}})

    # Redis check (optional)
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks.append({"name": "redis", "status": "ok", "details": {}})
    except Exception as e:
        checks.append({"name": "redis", "status": "fail", "details": {"error": str(e)}})

    # Registry check
    try:
        reg = _get_registry()
        if reg:
            checks.append({"name": "registry", "status": "ok", "details": {"sources": len(reg.sources)}})
        else:
            checks.append({"name": "registry", "status": "fail", "details": {"error": "Registry load failed"}})
    except Exception as e:
        checks.append({"name": "registry", "status": "fail", "details": {"error": str(e)}})

    # Artifact store check (write test)
    try:
        import tempfile
        root = Path(settings.artifact_root)
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=root, prefix=".health_", delete=True) as tf:
            tf.write(b"ok")
        checks.append({"name": "artifacts", "status": "ok", "details": {"path": str(root)}})
    except Exception as e:
        checks.append({"name": "artifacts", "status": "fail", "details": {"error": str(e)}})

    # OpenAI check: validate key by calling API; fail clearly if invalid
    try:
        import os
        key = (
            settings.openai_api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("SENTIMENT_API_OPENAI_API_KEY")
            or ""
        )
        if not key:
            checks.append({"name": "openai", "status": "fail", "details": {"message": "No API key; set OPENAI_API_KEY"}})
        else:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            # Validate key: list() has no limit in current client; consume one item
            next(iter(client.models.list()), None)
            checks.append({"name": "openai", "status": "ok", "details": {}})
    except Exception as e:
        err_str = str(e)
        is_auth = "401" in err_str or "invalid_api_key" in err_str.lower() or "authentication" in err_str.lower() or "incorrect api key" in err_str.lower()
        msg = "Invalid or expired API key" if is_auth else err_str
        checks.append({"name": "openai", "status": "fail", "details": {"error": msg}})

    core_names = {"postgres", "redis", "registry", "artifacts"}
    core_checks = [c for c in checks if c["name"] in core_names]
    status = "ok" if all(c["status"] == "ok" for c in core_checks) else "degraded"
    if any(c["name"] == "postgres" and c["status"] == "fail" for c in checks):
        status = "down"

    return {
        "status": status,
        "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }


# -----------------------------------------------------------------------------
# /v1/status — Dashboard status pills (API, Ingestion, Allocation, Research)
# -----------------------------------------------------------------------------
@app.get("/v1/status")
async def get_status():
    """Dashboard at-a-glance: api, ingestion, allocation, research. No auth."""
    h = await health()
    api_status = h["status"]
    as_of = h["as_of"]

    ingestion_status = "unknown"
    allocation_status = "unknown"
    research_status = "unknown"

    try:
        from sentiment_api.db.pool import get_pool, acquire
        pool = get_pool()
        if pool:
            async with acquire() as conn:
                # Ingestion: recent ingest run in last 15 min
                row = await conn.fetchrow(
                    """SELECT status FROM runs WHERE run_type = 'ingest' AND started_at > now() - interval '15 minutes'
                       ORDER BY started_at DESC LIMIT 1"""
                )
                if row:
                    ingestion_status = "ok" if row["status"] == "ok" else "degraded"
                # Allocation: any successful summarize in last 30 min = ok; else if any failed = degraded
                ok_row = await conn.fetchrow(
                    """SELECT 1 FROM runs WHERE run_type = 'summarize' AND status = 'ok'
                       AND started_at > now() - interval '30 minutes' LIMIT 1"""
                )
                any_row = await conn.fetchrow(
                    """SELECT status FROM runs WHERE run_type = 'summarize' AND started_at > now() - interval '30 minutes'
                       ORDER BY started_at DESC LIMIT 1"""
                )
                if ok_row:
                    allocation_status = "ok"
                elif any_row:
                    allocation_status = "degraded"
    except Exception as ex:
        import logging as _log
        _log.getLogger("sentiment_api").debug("Status runs query failed: %s", ex)

    return {
        "api": api_status,
        "ingestion": ingestion_status,
        "allocation": allocation_status,
        "research": research_status,
        "as_of": as_of,
    }


# -----------------------------------------------------------------------------
# /api/sp-sentiment — Moodix-compatible (AC-M9.1)
# -----------------------------------------------------------------------------
@app.get("/api/sp-sentiment")
async def get_sp_sentiment(
    _: Annotated[str, Depends(validate_api_key)],
    from_date: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    """Moodix-compatible daily series export."""
    import asyncpg
    from sentiment_api.db.pool import acquire
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, update_time, open, high, low, close, moodix_index,
                       ma5_moodix, ma10_moodix, sentiment_wave, sentiment, trend,
                       moodix_index_intraday, news_volume_intraday, news_volatility_intraday,
                       moodix_index_week, news_volume_week, moodix_index_month, news_volume_month,
                       moodix_index_year, news_volume_year
                FROM sentiment_daily
                WHERE ($1::date IS NULL OR date >= $1) AND ($2::date IS NULL OR date <= $2)
                ORDER BY date DESC
                LIMIT 500
                """,
                from_date,
                to,
            )
    except asyncpg.UndefinedTableError:
        rows = []
    result = []
    for r in rows:
        result.append({
            "date": r["date"].isoformat() if r["date"] else None,
            "update_time": r["update_time"].isoformat().replace("+00:00", "Z") if r["update_time"] else None,
            "open": float(r["open"]) if r["open"] is not None else None,
            "high": float(r["high"]) if r["high"] is not None else None,
            "low": float(r["low"]) if r["low"] is not None else None,
            "close": float(r["close"]) if r["close"] is not None else None,
            "moodix_index": float(r["moodix_index"]) if r["moodix_index"] is not None else None,
            "ma5_moodix": float(r["ma5_moodix"]) if r["ma5_moodix"] is not None else None,
            "ma10_moodix": float(r["ma10_moodix"]) if r["ma10_moodix"] is not None else None,
            "sentiment_wave": float(r["sentiment_wave"]) if r["sentiment_wave"] is not None else None,
            "sentiment": r["sentiment"],
            "trend": r["trend"],
            "moodix_index_intraday": float(r["moodix_index_intraday"]) if r["moodix_index_intraday"] is not None else None,
            "news_volume_intraday": r["news_volume_intraday"] or 0,
            "news_volatility_intraday": float(r["news_volatility_intraday"]) if r["news_volatility_intraday"] is not None else 0.0,
            "moodix_index_week": float(r["moodix_index_week"]) if r["moodix_index_week"] is not None else None,
            "news_volume_week": r["news_volume_week"],
            "moodix_index_month": float(r["moodix_index_month"]) if r["moodix_index_month"] is not None else None,
            "news_volume_month": r["news_volume_month"],
            "moodix_index_year": float(r["moodix_index_year"]) if r["moodix_index_year"] is not None else None,
            "news_volume_year": r["news_volume_year"],
        })
    return result


# -----------------------------------------------------------------------------
# /v1/mood/now
# -----------------------------------------------------------------------------
@app.get("/v1/mood/now")
async def get_mood_now(_: Annotated[str, Depends(validate_api_key)]):
    """Latest mood snapshot (drivers + risk vector)."""
    import asyncpg
    from sentiment_api.db.pool import acquire, get_pool
    if get_pool() is None:
        return {
            "meta": meta(),
            "data": {
                "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "sentiment": "Neutral",
                "trend": "Flat",
                "index_intraday": 0.0,
                "news_volume_intraday": 0,
                "news_volatility_intraday": 0.0,
                "confidence": 0.0,
                "drivers": [],
                "risk_vector": {
                    "risk_appetite": 0.0,
                    "volatility_pressure": 0.0,
                    "growth_outlook": 0.0,
                    "inflation_pressure": 0.0,
                    "rates_pressure": 0.0,
                    "liquidity_stress": 0.0,
                    "geopolitical_risk": 0.0,
                    "energy_supply_risk": 0.0,
                },
            },
            "errors": [],
        }
    try:
        async with acquire() as conn:
            row = await conn.fetchrow(
            """
            SELECT ts, interval, index_value, news_volume, news_volatility, sentiment
            FROM sentiment_timeseries
            WHERE interval = '5m'
            ORDER BY ts DESC
            LIMIT 1
            """
        )
    except asyncpg.UndefinedTableError:
        row = None
    if not row:
        # Return synthetic default when no data (spec: explainable)
        return {
            "meta": meta(),
            "data": {
                "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "sentiment": "Neutral",
                "trend": "Flat",
                "index_intraday": 0.0,
                "news_volume_intraday": 0,
                "news_volatility_intraday": 0.0,
                "confidence": 0.0,
                "drivers": [],
                "risk_vector": {
                    "risk_appetite": 0.0,
                    "volatility_pressure": 0.0,
                    "growth_outlook": 0.0,
                    "inflation_pressure": 0.0,
                    "rates_pressure": 0.0,
                    "liquidity_stress": 0.0,
                    "geopolitical_risk": 0.0,
                    "energy_supply_risk": 0.0,
                },
            },
            "errors": [],
        }

    # Build drivers from recent clusters
    drivers = []
    try:
        async with acquire() as conn:
            cluster_rows = await conn.fetch(
                """
            SELECT cluster_id, headline_en, impact->>'impact_score' as impact_score,
                   impact->>'expected_direction' as direction
            FROM clusters
            WHERE (impact->>'impact_level') NOT IN ('L0')
            ORDER BY last_seen DESC
            LIMIT 10
                """
            )
    except asyncpg.UndefinedTableError:
        cluster_rows = []
    for cr in cluster_rows:
        score = float(cr["impact_score"] or 0)
        direction = cr["direction"] or "Unknown"
        contrib = (score / 100.0) * (-0.5 if direction == "RiskOff" else 0.5 if direction == "RiskOn" else 0)
        drivers.append({
            "cluster_id": cr["cluster_id"],
            "headline_en": cr["headline_en"] or "",
            "impact_score": score,
            "direction": direction,
            "contribution": round(contrib, 3),
        })

    return {
        "meta": meta(),
        "data": {
            "as_of": row["ts"].isoformat().replace("+00:00", "Z") if row["ts"] else datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "sentiment": row["sentiment"] or "Neutral",
            "trend": "Growing" if (row["news_volatility"] or 0) > 0.5 else "Flat",
            "index_intraday": float(row["index_value"]) if row["index_value"] is not None else 0.0,
            "news_volume_intraday": row["news_volume"] or 0,
            "news_volatility_intraday": float(row["news_volatility"]) if row["news_volatility"] is not None else 0.0,
            "confidence": 0.5,
            "drivers": drivers[:10],
            "risk_vector": {
                "risk_appetite": max(-1, min(1, float(row["index_value"] or 0))),
                "volatility_pressure": float(row["news_volatility"] or 0),
                "growth_outlook": 0.0,
                "inflation_pressure": 0.0,
                "rates_pressure": 0.0,
                "liquidity_stress": 0.0,
                "geopolitical_risk": 0.0,
                "energy_supply_risk": 0.0,
            },
        },
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/index/intraday
# -----------------------------------------------------------------------------
@app.get("/v1/index/intraday")
async def get_intraday_index(
    _: Annotated[str, Depends(validate_api_key)],
    interval: str = Query(..., pattern="^(1m|5m|15m|1h)$"),
    since: str | None = Query(None),
    until: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
):
    """Intraday index series (paged)."""
    import asyncpg
    from sentiment_api.db.pool import acquire
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
            """
            SELECT ts, index_value, news_volume, news_volatility, sentiment
            FROM sentiment_timeseries
            WHERE interval = $1
              AND ($2::timestamptz IS NULL OR ts >= $2)
              AND ($3::timestamptz IS NULL OR ts <= $3)
            ORDER BY ts DESC
            LIMIT $4 + 1
            """,
            interval,
            since,
            until,
            limit + 1,
        )
    except asyncpg.UndefinedTableError:
        rows = []
    has_more = len(rows) > limit
    rows = rows[:limit]
    data = [
        {
            "ts": r["ts"].isoformat().replace("+00:00", "Z"),
            "index_value": float(r["index_value"]),
            "news_volume": r["news_volume"] or 0,
            "news_volatility": float(r["news_volatility"] or 0),
            "sentiment": r["sentiment"] or "Neutral",
        }
        for r in rows
    ]
    next_cursor = rows[-1]["ts"].isoformat() if has_more and rows else None
    return {
        "meta": meta(),
        "pagination": pagination(limit=limit, returned=len(data), next_cursor=next_cursor),
        "data": data,
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/news/clusters
# -----------------------------------------------------------------------------
@app.get("/v1/news/clusters")
async def list_clusters(
    _: Annotated[str, Depends(validate_api_key)],
    since: str | None = Query(None),
    until: str | None = Query(None),
    min_impact_level: str | None = Query(None, pattern="^(L0|L1|L2|L3|L4|L5)$"),
    direction: str | None = Query(None, pattern="^(RiskOn|RiskOff|Neutral|Mixed|Unknown)$"),
    topics: list[str] = Query(default=[]),
    regions: list[str] = Query(default=[]),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
    include_source_urls: bool = Query(True),
):
    """List story clusters (filterable)."""
    import asyncpg
    from sentiment_api.db.pool import acquire
    level_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    min_level = level_order.get(min_impact_level, 0) if min_impact_level else 0

    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT cluster_id, first_seen, last_seen, headline_en, topics, regions,
                       tone, impact, source_count, source_urls
                FROM clusters
                WHERE ($1::timestamptz IS NULL OR last_seen >= $1)
                  AND ($2::timestamptz IS NULL OR last_seen <= $2)
                  AND ($3::int IS NULL OR
                       CASE (impact->>'impact_level')
                         WHEN 'L0' THEN 0 WHEN 'L1' THEN 1 WHEN 'L2' THEN 2
                         WHEN 'L3' THEN 3 WHEN 'L4' THEN 4 WHEN 'L5' THEN 5 ELSE 0 END >= $3)
                  AND ($4::text IS NULL OR (impact->>'expected_direction') = $4)
                ORDER BY last_seen DESC
                LIMIT $5
                """,
                since,
                until,
                min_level if min_impact_level else None,
                direction,
                limit,
            )
    except asyncpg.UndefinedTableError:
        rows = []
    data = []
    for r in rows:
        imp = _ensure_dict(r.get("impact"))
        tone = _ensure_dict(r.get("tone"))
        data.append({
            "cluster_id": r["cluster_id"],
            "first_seen": r["first_seen"].isoformat().replace("+00:00", "Z") if r["first_seen"] else None,
            "last_seen": r["last_seen"].isoformat().replace("+00:00", "Z") if r["last_seen"] else None,
            "headline_en": r["headline_en"] or "",
            "summary_bullets_en": [],
            "topics": list(r["topics"] or []),
            "regions": list(r["regions"] or []),
            "tone": {"polarity": tone.get("polarity", 0), "subjectivity": tone.get("subjectivity", 0)},
            "impact": {
                "impact_score": imp.get("impact_score", 0),
                "impact_level": imp.get("impact_level", "L0"),
                "expected_direction": imp.get("expected_direction", "Unknown"),
                "horizon": imp.get("horizon", "unknown"),
                "confidence": imp.get("confidence", 0),
                "reason_codes": imp.get("reason_codes", []),
            },
            "source_count": r["source_count"] or 1,
            "source_urls": list(r["source_urls"] or []) if include_source_urls else [],
        })
    return {
        "meta": meta(),
        "pagination": pagination(limit=limit, returned=len(data), next_cursor=None),
        "data": data,
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/news/clusters/{cluster_id}
# -----------------------------------------------------------------------------
@app.get("/v1/news/clusters/{cluster_id}")
async def get_cluster_by_id(
    _: Annotated[str, Depends(validate_api_key)],
    cluster_id: str,
    include_articles: bool = Query(True),
    include_evidence: bool = Query(True),
    include_analogs: bool = Query(False),
    include_asset_impacts: bool = Query(False),
):
    """Cluster drilldown (articles + evidence + narrative from L3 summary)."""
    import asyncpg
    import logging as _log
    from sentiment_api.db.pool import acquire
    from sentiment_api.db.repo import get_cluster_l3_summary
    _api_log = _log.getLogger("sentiment_api.api")
    if not cluster_id.startswith("clu_") or len(cluster_id) < 14:
        raise HTTPException(status_code=400, detail="Invalid cluster_id format")
    try:
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM clusters WHERE cluster_id = $1",
                cluster_id,
            )
    except asyncpg.UndefinedTableError:
        row = None
    if not row:
        raise HTTPException(status_code=404, detail="Cluster not found")
    imp = _ensure_dict(row.get("impact"))
    tone = _ensure_dict(row.get("tone"))
    what_changed_en: str | None = None
    why_it_matters_en: str | None = None
    what_to_watch_en: str | None = None
    impact_explanation_en: str | None = None
    summary_bullets: list[str] = []
    try:
        async with acquire() as conn:
            l3 = await get_cluster_l3_summary(conn, cluster_id)
        if l3:
            def _l3_str(key: str) -> str | None:
                v = l3.get(key)
                if v is None:
                    return None
                if isinstance(v, list):
                    s = " ".join(str(x) for x in v) if v else ""
                else:
                    s = str(v) if v else ""
                return s.strip() or None
            what_changed_en = _l3_str("what_changed_en")
            why_it_matters_en = _l3_str("why_it_matters_en")
            what_to_watch_en = _l3_str("what_to_watch_en")
            impact_explanation_en = (_l3_str("why_it_matters_en") or "")[:500] or None
            summary_bullets = l3.get("summary_bullets_en") if isinstance(l3.get("summary_bullets_en"), list) else []
    except Exception as e:
        _api_log.debug("Cluster L3 summary fetch failed for %s: %s", cluster_id, e)
    cluster_obj = {
        "cluster_id": row["cluster_id"],
        "first_seen": row["first_seen"].isoformat().replace("+00:00", "Z") if row["first_seen"] else None,
        "last_seen": row["last_seen"].isoformat().replace("+00:00", "Z") if row["last_seen"] else None,
        "headline_en": row["headline_en"] or "",
        "summary_bullets_en": summary_bullets,
        "topics": list(row["topics"] or []),
        "regions": list(row["regions"] or []),
        "tone": {"polarity": tone.get("polarity", 0), "subjectivity": tone.get("subjectivity", 0)},
        "impact": {
            "impact_score": imp.get("impact_score", 0),
            "impact_level": imp.get("impact_level", "L0"),
            "expected_direction": imp.get("expected_direction", "Unknown"),
            "horizon": imp.get("horizon", "unknown"),
            "confidence": imp.get("confidence", 0),
            "reason_codes": imp.get("reason_codes", []),
        },
        "source_count": row["source_count"] or 1,
        "source_urls": list(row["source_urls"] or []),
    }
    articles = []
    evidence = []
    if include_articles:
        async with acquire() as conn:
            try:
                art_rows = await conn.fetch(
                    """
                    SELECT a.article_id, a.source_id, a.url, a.published_at, a.title_en, a.lang_original
                    FROM articles a
                    JOIN cluster_members cm ON a.article_id = cm.article_id
                    WHERE cm.cluster_id = $1 AND (a.deleted_at IS NULL)
                    """,
                    cluster_id,
                )
            except Exception as e:
                _api_log.debug("Cluster articles (with deleted_at) failed: %s", e)
                art_rows = await conn.fetch(
                    """
                    SELECT a.article_id, a.source_id, a.url, a.published_at, a.title_en, a.lang_original
                    FROM articles a
                    JOIN cluster_members cm ON a.article_id = cm.article_id
                    WHERE cm.cluster_id = $1
                    """,
                    cluster_id,
                )
            for ar in art_rows:
                articles.append({
                    "article_id": ar["article_id"],
                    "source_id": ar["source_id"],
                    "url": ar["url"],
                    "published_at": ar["published_at"].isoformat().replace("+00:00", "Z") if ar["published_at"] else None,
                    "title_en": ar["title_en"] or "",
                    "lang_original": ar["lang_original"] or "en",
                })
            if include_evidence and articles:
                for ar in art_rows[:5]:
                    evidence.append({
                        "url": ar["url"],
                        "text_en": (ar.get("title_en") or "")[:500],
                        "relevance_score": 0.9,
                    })
    asset_impacts = None
    market_impacts: list = []
    sector_impacts: list = []
    ticker_impacts: list = []
    if include_asset_impacts:
        try:
            from sentiment_api.engines.asset_targeting import get_asset_impacts_for_cluster
            asset_impacts = await get_asset_impacts_for_cluster(cluster_id)
            if asset_impacts:
                market_impacts = asset_impacts.get("markets") or []
                sector_impacts = asset_impacts.get("sectors") or []
                ticker_impacts = list(asset_impacts.get("winners") or []) + list(asset_impacts.get("losers") or [])
        except Exception as e:
            _api_log.warning("Asset impacts for cluster %s failed: %s", cluster_id, e)

    historical_analogs_list: list[dict] = []
    if include_analogs:
        try:
            from sentiment_api.db.repo import get_similar_clusters
            async with acquire() as conn:
                historical_analogs_list = await get_similar_clusters(conn, cluster_id, limit=20, min_similarity=0.5)
        except Exception as e:
            _api_log.debug("Historical analogs for cluster %s failed: %s", cluster_id, e)

    return {
        "meta": meta(),
        "data": {
            "cluster": cluster_obj,
            "articles": articles,
            "evidence": evidence,
            "asset_impacts": asset_impacts,
            "market_impacts": market_impacts,
            "sector_impacts": sector_impacts,
            "ticker_impacts": ticker_impacts,
            "what_changed_en": what_changed_en,
            "why_it_matters_en": why_it_matters_en,
            "what_to_watch_en": what_to_watch_en,
            "impact_explanation_en": impact_explanation_en,
            "historical_analogs": historical_analogs_list if include_analogs else None,
        },
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/impacts/clusters/{cluster_id} — Asset targeting for single cluster
# -----------------------------------------------------------------------------
@app.get("/v1/impacts/clusters/{cluster_id}")
async def get_asset_impacts_by_cluster(
    _: Annotated[str, Depends(validate_api_key)],
    cluster_id: str,
    universes: list[str] = Query(default=[]),
    limit_tickers: int = Query(50, ge=0, le=200),
    limit_sectors: int = Query(11, ge=0, le=30),
    include_evidence_urls: bool = Query(True),
    include_historical_edge: bool = Query(False),
):
    """Markets/sectors/tickers impact targeting for a single cluster."""
    if not cluster_id.startswith("clu_") or len(cluster_id) < 14:
        raise HTTPException(status_code=400, detail="Invalid cluster_id format")
    try:
        from sentiment_api.engines.asset_targeting import get_asset_impacts_for_cluster, persist_asset_targeting_audit
        data = await get_asset_impacts_for_cluster(
            cluster_id,
            universes=universes or ["sp500", "nasdaq100"],
            limit_tickers=limit_tickers,
            limit_sectors=limit_sectors,
        )
        await persist_asset_targeting_audit(cluster_id, data)
        return {"meta": meta(), "data": data, "errors": []}
    except Exception as e:
        from sentiment_api.api.responses import error_detail
        return {"meta": meta(), "data": {}, "errors": [error_detail("ASSET_IMPACTS_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/impacts/latest — Latest news → predicted winners/losers
# -----------------------------------------------------------------------------
@app.get("/v1/impacts/latest")
async def get_latest_asset_impacts(
    _: Annotated[str, Depends(validate_api_key)],
    window: str = Query("6h", pattern="^(1h|2h|6h|12h|24h|3d|7d)$"),
    since: str | None = Query(None),
    until: str | None = Query(None),
    min_impact_level: str = Query("L2", pattern="^(L0|L1|L2|L3|L4|L5)$"),
    universes: list[str] = Query(default=[]),
    limit_tickers: int = Query(50, ge=0, le=200),
    limit_sectors: int = Query(11, ge=0, le=30),
    include_evidence_urls: bool = Query(True),
    include_historical_edge: bool = Query(False),
):
    """Latest news → predicted winners/losers (markets/sectors/tickers)."""
    from sentiment_api.db.pool import get_pool
    if get_pool() is None:
        from datetime import datetime as dt, timezone
        from sentiment_api.engines.asset_targeting import _empty_bundle
        now = dt.now(timezone.utc)
        iso = now.isoformat().replace("+00:00", "Z")
        scope = {"since": iso, "until": iso, "min_impact_level": min_impact_level, "universes": universes or ["sp500", "nasdaq100"]}
        return {"meta": meta(), "data": _empty_bundle(now, scope), "errors": []}
    try:
        from datetime import datetime as dt, timezone
        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts as _get
        since_dt = dt.fromisoformat(since.replace("Z", "+00:00")) if since else None
        until_dt = dt.fromisoformat(until.replace("Z", "+00:00")) if until else None
        data = await _get(
            window=window,
            since=since_dt,
            until=until_dt,
            min_impact_level=min_impact_level,
            universes=universes or ["sp500", "nasdaq100"],
            limit_tickers=limit_tickers,
            limit_sectors=limit_sectors,
        )
        return {"meta": meta(), "data": data, "errors": []}
    except Exception as e:
        from datetime import datetime as dt, timezone
        from sentiment_api.api.responses import error_detail
        from sentiment_api.engines.asset_targeting import _empty_bundle
        now = dt.now(timezone.utc)
        iso = now.isoformat().replace("+00:00", "Z")
        scope = {"since": iso, "until": iso, "min_impact_level": min_impact_level, "universes": universes or ["sp500", "nasdaq100"]}
        return {"meta": meta(), "data": _empty_bundle(now, scope), "errors": [error_detail("IMPACTS_LATEST_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/impact/markets — Dashboard: top market impacts (v2.0 UI compatibility)
# -----------------------------------------------------------------------------
@app.get("/v1/impact/markets")
async def get_impact_markets(_: Annotated[str, Depends(validate_api_key)]):
    """Top market impacts for dashboard (derived from /v1/impacts/latest)."""
    try:
        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts
        from datetime import datetime as dt, timezone
        bundle = await get_latest_asset_impacts(window="6h", limit_tickers=0, limit_sectors=0)
    except Exception:
        from sentiment_api.engines.asset_targeting import _empty_bundle
        from datetime import datetime as dt, timezone
        bundle = _empty_bundle(dt.now(timezone.utc), {"window": "6h"})
    _dir_map = {"Up": "RiskOn", "Down": "RiskOff", "Neutral": "Neutral", "Mixed": "Mixed", "Unknown": "Unknown"}
    top_markets = []
    for m in bundle.get("markets", [])[:20]:
        direction = m.get("direction", "Unknown")
        top_markets.append({
            "market_id": m.get("market_id", "unknown"),
            "label_en": m.get("market_id", "unknown").replace("_", " ").title(),
            "expected_direction": _dir_map.get(direction, direction),
            "magnitude": min(1.0, max(0, float(m.get("impact_score", 0) or 0) / 100)),
            "confidence": float(m.get("confidence", 0) or 0),
            "horizon": m.get("horizon", "unknown"),
            "channels": list(m.get("channels", [])),
            "rationale_en": (m.get("rationale_bullets_en") or ["—"])[0] if m.get("rationale_bullets_en") else "—",
        })
    return {
        "meta": meta(),
        "data": {"as_of": bundle.get("as_of", ""), "top_markets": top_markets, "methodology_version": "v1.2"},
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/impact/sectors — Dashboard: sector impacts (v2.0 UI compatibility)
# -----------------------------------------------------------------------------
@app.get("/v1/impact/sectors")
async def get_impact_sectors(_: Annotated[str, Depends(validate_api_key)]):
    """Sector impacts for dashboard (derived from /v1/impacts/latest)."""
    try:
        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts
        from datetime import datetime as dt, timezone
        bundle = await get_latest_asset_impacts(window="6h", limit_tickers=0, limit_sectors=20)
    except Exception:
        from sentiment_api.engines.asset_targeting import _empty_bundle
        from datetime import datetime as dt, timezone
        bundle = _empty_bundle(dt.now(timezone.utc), {"window": "6h"})
    _dir_map = {"Up": "RiskOn", "Down": "RiskOff", "Neutral": "Neutral", "Mixed": "Mixed", "Unknown": "Unknown"}
    sectors = []
    for s in bundle.get("sectors", [])[:20]:
        direction = s.get("direction", "Unknown")
        sectors.append({
            "sector_id": s.get("sector_id", "unknown"),
            "sector_name_en": s.get("name_en", s.get("sector_id", "unknown")),
            "expected_direction": _dir_map.get(direction, direction),
            "impact_score": min(100, max(0, float(s.get("impact_score", 0) or 0))),
            "confidence": float(s.get("confidence", 0) or 0),
            "horizon": s.get("horizon", "unknown"),
            "channels": list(s.get("channels", [])),
            "rationale_en": (s.get("rationale_bullets_en") or ["—"])[0] if s.get("rationale_bullets_en") else "—",
        })
    return {
        "meta": meta(),
        "data": {"as_of": bundle.get("as_of", ""), "sectors": sectors, "methodology_version": "v1.2"},
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/impact/tickers — Dashboard: winners/losers (v2.0 UI compatibility)
# -----------------------------------------------------------------------------
@app.get("/v1/impact/tickers")
async def get_impact_tickers(_: Annotated[str, Depends(validate_api_key)]):
    """Winners/losers for dashboard (derived from /v1/impacts/latest)."""
    try:
        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts
        from datetime import datetime as dt, timezone
        bundle = await get_latest_asset_impacts(window="6h", limit_tickers=50, limit_sectors=0)
    except Exception:
        from sentiment_api.engines.asset_targeting import _empty_bundle
        from datetime import datetime as dt, timezone
        bundle = _empty_bundle(dt.now(timezone.utc), {"window": "6h"})
    _dir_map = {"Up": "RiskOn", "Down": "RiskOff", "Neutral": "Neutral", "Mixed": "Mixed", "Unknown": "Unknown"}

    def map_ticker(t, universe_default="sp500"):
        direction = t.get("direction", "Unknown")
        score = float(t.get("impact_score", 0) or 0)
        return {
            "symbol": (t.get("symbol") or "—")[:16],
            "company_name_en": t.get("name"),
            "universe": universe_default,
            "sector_id": t.get("sector_id"),
            "expected_direction": _dir_map.get(direction, direction),
            "expected_return_bps": int(t.get("expected_return_bps", score * 5)),
            "expected_volatility_delta": float(t.get("expected_volatility_delta", 0) or 0),
            "confidence": float(t.get("confidence", 0) or 0),
            "horizon": t.get("horizon", "unknown"),
            "drivers": list(t.get("drivers", [])),
            "rationale_en": (t.get("rationale_bullets_en") or ["—"])[0] if t.get("rationale_bullets_en") else "—",
        }
    winners = [map_ticker(w) for w in bundle.get("winners", [])[:25]]
    losers = [map_ticker(l) for l in bundle.get("losers", [])[:25]]
    return {
        "meta": meta(),
        "data": {"as_of": bundle.get("as_of", ""), "winners": winners, "losers": losers, "methodology_version": "v1.2"},
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/universes — List configured universes
# -----------------------------------------------------------------------------
@app.get("/v1/universes")
async def list_universes(_: Annotated[str, Depends(validate_api_key)]):
    """List configured universes (S&P 500, Nasdaq Composite, ...)."""
    try:
        from sentiment_api.db.pool import acquire
        from sentiment_api.db.universe_repo import list_universes as _list
        async with acquire() as conn:
            data = await _list(conn)
        return {"meta": meta(), "data": data, "errors": []}
    except Exception as e:
        from sentiment_api.api.responses import error_detail
        return {"meta": meta(), "data": [], "errors": [error_detail("UNIVERSES_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/universes/{universe_id}/constituents — List tickers in universe
# -----------------------------------------------------------------------------
@app.get("/v1/universes/{universe_id}/constituents")
async def list_universe_constituents(
    _: Annotated[str, Depends(validate_api_key)],
    universe_id: str,
    as_of: str | None = Query(None),
    sector_id: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
):
    """List tickers in a universe (paged)."""
    try:
        from datetime import date
        from sentiment_api.db.pool import acquire
        from sentiment_api.db.universe_repo import list_universe_constituents as _list
        as_of_date = date.fromisoformat(as_of) if as_of else None
        async with acquire() as conn:
            rows, next_cursor = await _list(conn, universe_id, as_of_date, sector_id, q, limit, cursor)
        return {
            "meta": meta(),
            "pagination": {"limit": limit, "next_cursor": next_cursor, "returned": len(rows)},
            "data": rows,
            "errors": [],
        }
    except Exception as e:
        from sentiment_api.api.responses import error_detail
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# /v1/tickers/{symbol}/detail — Company detail from Yahoo Finance (no storage)
# -----------------------------------------------------------------------------
@app.get("/v1/tickers/{symbol}/detail")
async def get_ticker_detail(
    _: Annotated[str, Depends(validate_api_key)],
    symbol: str,
):
    """Company detail from Yahoo Finance: summary, current price, earnings, key statistics. Fetched on demand, not stored."""
    try:
        from sentiment_api.services.yahoo_finance import get_company_detail
        data = await get_company_detail(symbol)
        if data.get("error"):
            raise HTTPException(status_code=404, detail=data["error"])
        return {"meta": meta(), "data": data, "errors": []}
    except HTTPException:
        raise
    except Exception as e:
        from sentiment_api.api.responses import error_detail
        return {"meta": meta(), "data": {}, "errors": [error_detail("TICKER_DETAIL_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/sectors — List sector taxonomy
# -----------------------------------------------------------------------------
@app.get("/v1/sectors")
async def list_sectors(_: Annotated[str, Depends(validate_api_key)]):
    """List sector taxonomy (GICS-like 11 sectors)."""
    try:
        from sentiment_api.db.pool import acquire
        from sentiment_api.db.universe_repo import list_sectors as _list
        async with acquire() as conn:
            data = await _list(conn)
        return {"meta": meta(), "data": data, "errors": []}
    except Exception as e:
        from sentiment_api.api.responses import error_detail
        return {"meta": meta(), "data": [], "errors": [error_detail("SECTORS_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/topics/index — Topic indices (v1.2)
# -----------------------------------------------------------------------------
@app.get("/v1/topics/index")
async def get_topics_index(
    _: Annotated[str, Depends(validate_api_key)],
    request: Request,
    interval: str = Query("5m", pattern="^(1m|5m|15m|1h|1d)$"),
    since: str | None = Query(None),
    until: str | None = Query(None),
    topics_filter: list[str] | None = Query(None, alias="topics"),
    limit: int = Query(500, ge=1, le=500),
    cursor: str | None = Query(None),
):
    """Topic contribution timeline (mood/topic index). v1.2"""
    from sentiment_api.db.pool import get_pool, acquire
    data: list[dict] = []
    pool = get_pool()
    if pool:
        try:
            async with acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT t.topic_id, t.ts, t.news_volume,
                           initcap(replace(t.topic_id, '_', ' ')) AS topic_name_en
                    FROM (
                      SELECT unnest(c.topics) AS topic_id,
                             date_trunc('hour', c.last_seen) AS ts,
                             count(*)::int AS news_volume
                      FROM clusters c
                      WHERE array_length(c.topics, 1) > 0
                        AND c.last_seen >= now() - interval '7 days'
                        AND ($1::text[] IS NULL OR c.topics && $1)
                      GROUP BY 1, 2
                      ORDER BY ts DESC, news_volume DESC
                      LIMIT $2
                    ) t
                    """,
                    topics_filter or None,
                    limit,
                )
                for r in rows:
                    data.append({
                        "ts": (r["ts"] or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
                        "topic_id": r["topic_id"] or "unknown",
                        "topic_name_en": r["topic_name_en"] or r["topic_id"] or "Unknown",
                        "index_value": float(r["news_volume"] or 0) * 0.1,
                        "sentiment": "Neutral",
                        "news_volume": int(r["news_volume"] or 0),
                    })
        except Exception as e:
            import logging
            logging.getLogger("sentiment_api").debug("Topics index query failed: %s", e)
    rid = getattr(request.state, "request_id", meta()["request_id"])
    return {
        "meta": {"request_id": rid, "as_of": meta()["as_of"]},
        "pagination": pagination(limit=limit, returned=len(data), next_cursor=None),
        "data": data,
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/stream/events — SSE (v1.2)
# -----------------------------------------------------------------------------
@app.get("/v1/stream/events")
async def stream_events(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    max_events: int | None = Query(None, description="Optional: stop after N events (for tests)"),
):
    """SSE stream: heartbeat, cluster_updated, mood_updated, impacts_updated, topics_updated. v1.2"""
    import asyncio
    from fastapi.responses import StreamingResponse
    rid = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:12]}")
    key = _client_key(request)

    async def gen():
        import logging
        from sentiment_api.db.pool import get_pool, acquire
        _sse_log = logging.getLogger("sentiment_api.api")
        events_yielded = 0
        try:
            tick = 0
            while max_events is None or events_yielded < max_events:
                ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                yield f"event: heartbeat\ndata: {json.dumps({'type':'heartbeat','ts':ts,'payload':{},'request_id':rid}, separators=(',', ':'))}\n\n"
                events_yielded += 1
                tick += 1
                if max_events is not None and events_yielded >= max_events:
                    break
                if tick % 4 == 0:
                    payload: dict = {}
                    try:
                        pool = get_pool()
                        if pool:
                            async with acquire() as conn:
                                r = await conn.fetchrow("SELECT ts, index_value FROM sentiment_timeseries WHERE interval='5m' ORDER BY ts DESC LIMIT 1")
                                if r:
                                    payload = {"as_of": (r["ts"] or datetime.now(UTC)).isoformat().replace("+00:00", "Z"), "index_value": float(r["index_value"] or 0)}
                    except Exception as e:
                        _sse_log.debug("SSE mood_updated fetch failed: %s", e)
                    evt = {"type": "mood_updated", "ts": ts, "payload": payload, "request_id": rid}
                    yield f"event: mood_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    events_yielded += 1
                    if max_events is not None and events_yielded >= max_events:
                        break
                    try:
                        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts
                        imp = await get_latest_asset_impacts(window="6h", limit_tickers=5, limit_sectors=5)
                        evt = {"type": "impacts_updated", "ts": ts, "payload": imp, "request_id": rid}
                        yield f"event: impacts_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                        events_yielded += 1
                    except Exception as e:
                        _sse_log.debug("SSE impacts_updated failed: %s", e)
                        evt = {"type": "impacts_updated", "ts": ts, "payload": {}, "request_id": rid}
                        yield f"event: impacts_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    events_yielded += 1
                    if max_events is not None and events_yielded >= max_events:
                        break
                    try:
                        pool = get_pool()
                        if pool:
                            async with acquire() as conn:
                                rows = await conn.fetch("SELECT unnest(topics) AS topic_id FROM clusters WHERE array_length(topics,1)>0 AND last_seen>=now()-interval '1 day' LIMIT 20")
                                topics = list({r["topic_id"] for r in rows if r.get("topic_id")})
                                evt = {"type": "topics_updated", "ts": ts, "payload": {"topics": topics}, "request_id": rid}
                                yield f"event: topics_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                        else:
                            evt = {"type": "topics_updated", "ts": ts, "payload": {}, "request_id": rid}
                            yield f"event: topics_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    except Exception:
                        evt = {"type": "topics_updated", "ts": ts, "payload": {}, "request_id": rid}
                        yield f"event: topics_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    events_yielded += 1
                    if max_events is not None and events_yielded >= max_events:
                        break
                await asyncio.sleep(15)
        finally:
            _dec_sse(key)

    return StreamingResponse(gen(), media_type="text/event-stream")


# -----------------------------------------------------------------------------
# /v1/research/spy/event-study
# -----------------------------------------------------------------------------
@app.get("/v1/research/spy/event-study")
async def get_spy_event_study(
    _: Annotated[str, Depends(validate_api_key)],
    from_date: str = Query(..., alias="from"),
    to: str = Query(...),
    windows: list[str] = Query(..., pattern="^(30m|2h|1d|3d|1w)$"),
    market: str = Query(..., pattern="^(SPY|ES)$"),
    min_impact_level: str | None = Query(None),
    direction: str | None = Query(None),
    topics: list[str] = Query(default=[]),
    regions: list[str] = Query(default=[]),
):
    """Event-study and correlation summaries for SPY/ES."""
    import asyncpg
    from datetime import date as date_type
    try:
        from sentiment_api.engines.research import run_event_study
        from sentiment_api.db.pool import get_pool
        fd = date_type.fromisoformat(from_date)
        td = date_type.fromisoformat(to)
        result = await run_event_study(
            fd, td, market=market, windows=windows,
            min_impact_level=min_impact_level, direction=direction,
        )
        return {"meta": meta(), "data": result, "errors": []}
    except asyncpg.UndefinedTableError:
        data = [{"window": w, "mean_return": 0.0, "median_return": 0.0, "mean_abs_return": 0.0, "hit_rate": 0.0, "sample_size": 0} for w in windows]
        return {"meta": meta(), "data": {"windows": data, "market": market, "from": from_date, "to": to}, "errors": []}
    except Exception as e:
        return {"meta": meta(), "data": {"windows": [], "market": market, "from": from_date, "to": to}, "errors": [error_detail("EVENT_STUDY_ERROR", str(e))]}


# -----------------------------------------------------------------------------
# /v1/ask — RAG query (retrieve + answer with citations)
# -----------------------------------------------------------------------------
@app.post("/v1/ask")
async def ask_rag(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    body: dict = Body(default={"query": ""}),
):
    """RAG query over memory: vector retrieval + LLM answer with citations."""
    from sentiment_api.api.idempotency import get_cached, set_cached
    cached = await get_cached(request)
    if cached:
        return JSONResponse(status_code=cached["status"], content=cached["body"])
    query = (body or {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query required in body")
    from sentiment_api.db.pool import get_pool, acquire
    from sentiment_api.llm.rag import retrieve_similar, generate_answer
    from sentiment_api.llm.embeddings import embed_text
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Service unavailable")
    settings = get_settings()
    try:
        query_embedding = embed_text(query[:4000], settings.model_embedding_id)
        async with acquire() as conn:
            contexts = await retrieve_similar(conn, query_embedding, settings.model_embedding_id, top_k=10)
        answer, citations = generate_answer(query, contexts)
        out = {"meta": meta(), "data": {"answer": answer, "citations": citations}, "errors": []}
        await set_cached(request, 200, out)
        return out
    except Exception as e:
        import logging
        logging.getLogger("sentiment_api").exception("RAG failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# POST /v1/retrieval/ingest — chunk documents and ingest into Weaviate (Tier A)
# -----------------------------------------------------------------------------
@app.post("/v1/retrieval/ingest")
async def retrieval_ingest(
    _: Annotated[str, Depends(validate_api_key)],
    body: dict = Body(default=None),
):
    """
    Chunk documents and ingest into Weaviate RetrievalChunk (Tier A vectors + text for BM25).
    Body: { "documents": [ { "text", "doc_id", "source?", "url?", "published_at?", "tickers?", "sector?", "language?" } ], "max_chars?", "overlap_chars?" }.
    """
    from sentiment_api.retrieval.chunk_ingest import ChunkDoc, ingest_chunks_to_weaviate

    payload = body or {}
    docs_raw = payload.get("documents") or []
    if not docs_raw:
        raise HTTPException(status_code=400, detail="documents required (non-empty array)")
    max_chars = payload.get("max_chars", 512)
    overlap_chars = payload.get("overlap_chars", 64)
    docs = []
    for d in docs_raw:
        if not isinstance(d, dict) or not d.get("text") or not d.get("doc_id"):
            raise HTTPException(status_code=400, detail="Each document must have text and doc_id")
        docs.append(
            ChunkDoc(
                text=str(d["text"]),
                doc_id=str(d["doc_id"]),
                source=str(d.get("source") or ""),
                url=str(d["url"]) if d.get("url") is not None else None,
                published_at=str(d["published_at"]) if d.get("published_at") is not None else None,
                tickers=list(d["tickers"]) if isinstance(d.get("tickers"), list) else None,
                sector=str(d["sector"]) if d.get("sector") is not None else None,
                language=str(d["language"]) if d.get("language") is not None else None,
            )
        )
    try:
        count = await ingest_chunks_to_weaviate(
            docs=docs,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
        return {
            "meta": meta(),
            "data": {"chunks_upserted": count, "documents_count": len(docs)},
            "errors": [],
        }
    except Exception as e:
        import logging
        logging.getLogger("sentiment_api").exception("Retrieval ingest failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# POST /v1/search/advanced — 2-tier retrieval (Tier A hybrid + Tier B rerank)
# -----------------------------------------------------------------------------
@app.post("/v1/search/advanced")
async def search_advanced(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    body: dict = Body(default=None),
):
    """
    2-tier retrieval: Tier A hybrid (vector + BM25) candidate retrieval,
    Tier B rerank with high-dim embeddings (cached). Returns score breakdown + trace.
    """
    from sentiment_api.retrieval.pipeline import run_advanced_search

    payload = body or {}
    query_text = (payload.get("query") or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="query required in body")
    filters = payload.get("filters") or {}
    top_n = payload.get("topN")
    rerank_n = payload.get("rerankN")
    alpha = payload.get("alpha")
    weights_raw = payload.get("weights")
    weights = None
    if isinstance(weights_raw, dict):
        weights = weights_raw
    elif isinstance(weights_raw, str):
        try:
            import json as _json
            weights = _json.loads(weights_raw)
        except _json.JSONDecodeError:
            pass
    trace_id = getattr(request.state, "request_id", None)

    try:
        results, trace = await run_advanced_search(
            query_text=query_text,
            filters=filters,
            top_n=top_n,
            rerank_n=rerank_n,
            alpha=alpha,
            weights=weights,
            trace_id=trace_id,
        )
        data = {
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "doc_id": r.doc_id,
                    "snippet": r.snippet,
                    "score_breakdown": r.score_breakdown.to_dict(),
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "trace": trace.to_dict(),
        }
        return {
            "meta": meta(),
            "data": data,
            "errors": [],
        }
    except Exception as e:
        import logging
        logging.getLogger("sentiment_api").exception("Advanced search failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# /v1/sources
# -----------------------------------------------------------------------------
@app.get("/v1/sources")
async def list_sources(
    _: Annotated[str, Depends(validate_api_key)],
    enabled_only: bool = Query(True),
    types: list[str] | None = Query(None),
):
    """List configured sources (registry view)."""
    reg = _get_registry()
    if not reg:
        return JSONResponse(
            status_code=503,
            content={
                "meta": meta(),
                "data": {"sources": []},
                "errors": [error_detail("REGISTRY_UNAVAILABLE", "Source registry could not be loaded")],
            },
        )
    sources = reg.get_enabled_sources() if enabled_only else reg.sources
    if types:
        sources = [s for s in sources if s.type in types]
    cred_map = {"official": "official", "reputable_media": "reputable_media", "local_media": "local_media", "dataset": "dataset", "user_added": "user_added"}
    lic_map = {"open": "open", "key_required": "key_required", "paid": "paid", "restricted": "restricted"}
    items = [
        {
            "source_id": s.source_id,
            "name": s.name,
            "type": s.type,
            "credibility_tier": cred_map.get(s.credibility_tier or reg.defaults.credibility_tier, "reputable_media"),
            "license_class": lic_map.get(s.license_class or reg.defaults.license_class, "open"),
        }
        for s in sources
    ]
    return {
        "meta": meta(),
        "data": {"sources": items},
        "errors": [],
    }


# -----------------------------------------------------------------------------
# POST /v1/admin/ingest/run — Trigger ingest (operator)
# -----------------------------------------------------------------------------
@app.post("/v1/admin/ingest/run")
async def admin_ingest_run(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    source_id: str | None = Query(None),
):
    """Trigger ingest run: push one poll cycle to queue. If source_id given, poll only that source."""
    from sentiment_api.api.idempotency import get_cached, set_cached
    cached = await get_cached(request)
    if cached:
        return JSONResponse(status_code=cached["status"], content=cached["body"])
    from sentiment_api.queue.client import get_queue, QUEUE_INGEST
    from sentiment_api.registry import load_registry
    settings = get_settings()
    reg = _get_registry()
    if not reg:
        raise HTTPException(status_code=503, detail="Registry unavailable")
    queue = await get_queue(settings.redis_url)
    sources = reg.get_enabled_sources()
    if source_id:
        sources = [s for s in sources if s.source_id == source_id]
        if not sources:
            raise HTTPException(status_code=404, detail="Source not found")
    from sentiment_api.collectors.rss import RSSCollector
    from sentiment_api.collectors.gdelt import GDELTCollector
    from sentiment_api.collectors.scrape import ScrapeCollector
    from sentiment_api.ingest.daemon import _serialize_item
    rss, gdelt, scrape = RSSCollector(), GDELTCollector(), ScrapeCollector()
    total = 0
    defaults = reg.defaults
    for src in sources:
        respect_robots = src.effective_respect_robots_txt(defaults)
        if src.type == "rss" and src.feed_url:
            for item in rss.collect(src, src.feed_url, respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                total += 1
        elif src.type == "gdelt" and src.base_url:
            for item in gdelt.collect(src, src.base_url, getattr(src, "query_profiles", None), respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                total += 1
        elif src.type == "scrape" and src.page_url:
            for item in scrape.collect(src, src.page_url, respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                total += 1
    out = {"meta": meta(), "data": {"pushed": total, "sources_polled": len(sources)}, "errors": []}
    await set_cached(request, 200, out)
    return out


# -----------------------------------------------------------------------------
# POST /v1/admin/backfill — Backfill by date range (AC-M1.4)
# -----------------------------------------------------------------------------
@app.post("/v1/admin/backfill")
async def admin_backfill(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    body: dict = Body(default={}),
):
    """Backfill sources by date range. Body: {from: YYYY-MM-DD, to: YYYY-MM-DD, source_id?: str}."""
    from sentiment_api.api.idempotency import get_cached, set_cached
    cached = await get_cached(request)
    if cached:
        return JSONResponse(status_code=cached["status"], content=cached["body"])
    from datetime import date as date_type
    from sentiment_api.ingest.backfill import run_backfill
    fd = body.get("from") or body.get("from_date")
    td = body.get("to") or body.get("to_date")
    source_id = body.get("source_id")
    if not fd or not td:
        raise HTTPException(status_code=400, detail="from and to dates required (YYYY-MM-DD)")
    try:
        from_d = date_type.fromisoformat(fd)
        to_d = date_type.fromisoformat(td)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    if from_d > to_d:
        raise HTTPException(status_code=400, detail="from must be <= to")
    result = await run_backfill(from_d, to_d, source_id)
    out = {"meta": meta(), "data": result, "errors": []}
    await set_cached(request, 200, out)
    return out


# -----------------------------------------------------------------------------
# POST /v1/admin/summarize/run — Force summarize (queue articles without L2)
# -----------------------------------------------------------------------------
@app.post("/v1/admin/summarize/run")
async def admin_summarize_run(
    request: Request,
    _: Annotated[str, Depends(validate_api_key)],
    limit: int | None = Query(None, ge=1, le=10000),
    dry_run: bool = Query(False),
):
    """Push articles without L2 summary to summarize queue. Worker will process them."""
    from sentiment_api.api.idempotency import get_cached, set_cached
    cached = await get_cached(request)
    if cached:
        return JSONResponse(status_code=cached["status"], content=cached["body"])
    from sentiment_api.db.pool import acquire
    from sentiment_api.queue.client import get_queue, QUEUE_SUMMARIZE
    settings = get_settings()
    queue = await get_queue(settings.redis_url)
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT a.article_id, a.source_id, a.url, a.canonical_url, a.published_at, a.fetched_at,
                   a.title_en, a.content_en, a.metadata
            FROM articles a
            WHERE NOT EXISTS (
                SELECT 1 FROM summaries s
                WHERE s.object_type = 'article' AND s.object_id = a.article_id AND s.level = 'L2'
            )
            ORDER BY a.fetched_at DESC NULLS LAST
            LIMIT $1
            """,
            limit or 10000,
        )
    queued = 0
    for r in rows:
        norm = {
            "source_id": r["source_id"],
            "url": r["url"],
            "canonical_url": r["canonical_url"],
            "title_en": r["title_en"] or "",
            "content_en": r["content_en"] or "",
            "published_at": r["published_at"].isoformat() if r["published_at"] else "",
            "fetched_at": r["fetched_at"].isoformat() if r["fetched_at"] else "",
            "metadata": r["metadata"] or {},
        }
        payload = {"article_id": r["article_id"], "source_id": r["source_id"], "norm": norm}
        if not dry_run:
            await queue.rpush(QUEUE_SUMMARIZE, json.dumps(payload, default=str))
        queued += 1
    out = {"meta": meta(), "data": {"queued": queued, "dry_run": dry_run}, "errors": []}
    await set_cached(request, 200, out)
    return out


# -----------------------------------------------------------------------------
# GET /v1/admin/logs — Tail log files (api, worker, daemon) for ops UI
# -----------------------------------------------------------------------------
_LOG_DIR = Path("/data/logs")
_ALLOWED_LOG_SOURCES = frozenset({"api", "worker", "daemon"})


# -----------------------------------------------------------------------------
# GET /v1/debug/asset_targeting/{cluster_id} — Debug chunked LLM asset targeting
# -----------------------------------------------------------------------------
@app.get("/v1/debug/asset_targeting/{cluster_id}")
async def debug_asset_targeting(
    _: Annotated[str, Depends(validate_api_key)],
    cluster_id: str,
):
    """
    Debug endpoint for chunked LLM asset targeting.
    Returns: packet + hashes, cache status for A/B/C, allocations, diagnostics.
    """
    from sentiment_api.db.pool import acquire
    from sentiment_api.db.repo import get_cluster_l3_summary

    if not cluster_id.startswith("clu_") or len(cluster_id) < 14:
        raise HTTPException(status_code=400, detail="Invalid cluster_id format")

    async with acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM clusters WHERE cluster_id = $1", cluster_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cluster not found")

    imp = _ensure_dict(row.get("impact"))
    l3 = None
    try:
        async with acquire() as conn:
            l3 = await get_cluster_l3_summary(conn, cluster_id)
    except Exception:
        pass

    summary_bullets = []
    if l3 and isinstance(l3.get("summary_bullets_en"), list):
        summary_bullets = l3["summary_bullets_en"]
    evidence_rows = [{"url": u, "text_en": "", "relevance_score": 0.9} for u in (row.get("source_urls") or [])[:6]]

    try:
        from sentiment_api.engines.llm_asset_targeting.packet_builder import build_cluster_packet, sha256_str, canonical_json
        packet, packet_hash = build_cluster_packet(
            cluster_id=cluster_id,
            cluster_version=1,
            headline_en=row["headline_en"] or "",
            summary_bullets_en=summary_bullets,
            topics=list(row.get("topics") or []),
            regions=list(row.get("regions") or []),
            impact_score=float(imp.get("impact_score", 0) or 0),
            impact_level=str(imp.get("impact_level", "L0")),
            expected_direction=str(imp.get("expected_direction", "Unknown")),
            confidence=float(imp.get("confidence", 0.5) or 0.5),
            evidence_rows=evidence_rows,
        )
        packet_dump = packet.model_dump()
    except Exception as e:
        packet_dump = {}
        packet_hash = ""
        import logging
        logging.getLogger("sentiment_api").debug("Packet build failed: %s", e)

    cache_status: dict = {}
    cache_keys: dict = {}
    prompt_hashes: dict = {}
    schema_hashes: dict = {}
    call_a: dict = {}
    call_b: dict = {}
    call_c: dict = {}
    channels: dict = {}
    candidate_diagnostics: dict = {}
    allocations: dict = {"markets": [], "sectors": [], "winners": [], "losers": []}
    try:
        async with acquire() as conn:
            cache_rows = await conn.fetch(
                """SELECT step, status, error_code, error_message, cache_key, prompt_hash, schema_hash, parsed_json
                   FROM llm_call_cache WHERE cluster_id = $1""",
                cluster_id,
            )
            for r in cache_rows:
                step = r["step"]
                cache_status[step] = {"status": r["status"], "error_code": r["error_code"], "error_message": r["error_message"]}
                cache_keys[step] = r["cache_key"]
                if r.get("prompt_hash"):
                    prompt_hashes[step] = r["prompt_hash"]
                if r.get("schema_hash"):
                    schema_hashes[step] = r["schema_hash"]
                parsed = r.get("parsed_json")
                if parsed and r["status"] == "ok":
                    if isinstance(parsed, str):
                        import json as _json
                        try:
                            parsed = _json.loads(parsed)
                        except Exception:
                            parsed = None
                    if parsed:
                        if step == "channel_infer":
                            call_a = parsed
                            channels = {c.get("name"): float(c.get("sign", 0)) * float(c.get("strength", 0)) for c in parsed.get("channels", [])}
                        elif step == "sector_map":
                            call_b = parsed
                        elif step == "ticker_select":
                            call_c = parsed

            # Populate candidate_diagnostics when call_a/call_b and packet available
            if call_a and call_b and packet_dump and packet_dump.get("cluster_id"):
                try:
                    from pathlib import Path
                    from sentiment_api.engines.llm_asset_targeting.candidate_generator import build_allowed_symbols
                    from sentiment_api.engines.llm_asset_targeting.schemas import ChannelInferResult, SectorMapResult, ClusterPacket
                    from sentiment_api.engines.llm_asset_targeting.security_master import DBSecurityMaster
                    reg_dir = Path(__file__).resolve().parent.parent.parent / "registry" / "llm_asset_targeting"
                    if (reg_dir / "channel_rulesets.yaml").exists():
                        ca = ChannelInferResult(**call_a)
                        sb = SectorMapResult(**call_b)
                        pkt = ClusterPacket(**packet_dump)
                        sec = DBSecurityMaster()
                        _, cand_diag = await build_allowed_symbols(
                            packet=pkt, call_a=ca, call_b=sb,
                            security_master=sec, rulesets_path=str(reg_dir / "channel_rulesets.yaml"),
                        )
                        candidate_diagnostics = cand_diag.__dict__
                except Exception as _cd_ex:
                    import logging
                    logging.getLogger("sentiment_api").debug("Candidate diagnostics build failed: %s", _cd_ex)

            market_rows = await conn.fetch(
                "SELECT * FROM cluster_market_allocations WHERE cluster_id = $1",
                cluster_id,
            )
            sector_rows = await conn.fetch(
                "SELECT * FROM cluster_sector_allocations WHERE cluster_id = $1",
                cluster_id,
            )
            ticker_rows = await conn.fetch(
                "SELECT * FROM cluster_ticker_allocations WHERE cluster_id = $1",
                cluster_id,
            )
        for r in market_rows:
            allocations["markets"].append(dict(r))
        for r in sector_rows:
            allocations["sectors"].append(dict(r))
        for r in ticker_rows:
            d = dict(r)
            if d.get("signed_score", 0) >= 0:
                allocations["winners"].append(d)
            else:
                allocations["losers"].append(d)
    except Exception as e:
        import logging
        logging.getLogger("sentiment_api.api").debug("Debug asset_targeting cache/allocations fetch failed for %s: %s", cluster_id, e)

    return {
        "meta": meta(),
        "data": {
            "cluster_id": cluster_id,
            "packet": packet_dump,
            "packet_hash": packet_hash,
            "prompt_hashes": prompt_hashes,
            "schema_hashes": schema_hashes,
            "cache_status": cache_status,
            "cache_keys": cache_keys,
            "channels": channels,
            "call_a": call_a,
            "call_b": call_b,
            "call_c": call_c,
            "candidate_diagnostics": candidate_diagnostics,
            "allocations": allocations,
            "invariant_violations": [],
        },
        "errors": [],
    }


@app.get("/v1/admin/logs")
async def admin_logs(
    _: Annotated[str, Depends(validate_api_key)],
    sources: list[str] = Query(default=["api", "worker", "daemon"], description="api, worker, daemon"),
    tail: int = Query(50, ge=1, le=500),
):
    """Return last N lines from each selected service log file (/data/logs/<source>.log)."""
    data: dict[str, list[str]] = {}
    for src in sources:
        if src not in _ALLOWED_LOG_SOURCES:
            continue
        path = _LOG_DIR / f"{src}.log"
        try:
            if path.is_file():
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                data[src] = [line.rstrip("\n") for line in lines[-tail:]]
            else:
                data[src] = []
        except OSError:
            data[src] = []
    return {"meta": meta(), "data": data, "errors": []}


# -----------------------------------------------------------------------------
# GET /v1/admin/ops — Ops summary (queues, counts, heartbeats)
# -----------------------------------------------------------------------------
@app.get("/v1/admin/ops")
async def admin_ops(
    _: Annotated[str, Depends(validate_api_key)],
):
    """Return ops summary: queue depth, counts, recent runs, worker/daemon heartbeat."""
    from sentiment_api.queue.client import (
        QUEUE_INGEST,
        QUEUE_NORMALIZE,
        QUEUE_SUMMARIZE,
        QUEUE_SCORE,
        QUEUE_INDEX,
    )
    from sentiment_api.db.pool import get_pool, acquire

    now = datetime.now(UTC)
    data: dict = {
        "queues": {},
        "counts": {},
        "latest": {},
        "runs": {},
        "heartbeats": {},
        "redis": {"status": "unknown"},
        "db": {"status": "unknown"},
        "system": None,
        "desired_workers": None,
    }

    def _parse_ts(ts: str | None) -> datetime | None:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    def _to_iso(ts: datetime | None) -> str | None:
        if not ts:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.isoformat().replace("+00:00", "Z")

    def _age_sec(ts: datetime | None) -> float | None:
        if not ts:
            return None
        return round((now - ts).total_seconds(), 1)

    # Redis: queue depths + heartbeats
    try:
        import redis.asyncio as redis
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        queue_map = {
            "ingest": QUEUE_INGEST,
            "normalize": QUEUE_NORMALIZE,
            "summarize": QUEUE_SUMMARIZE,
            "score": QUEUE_SCORE,
            "index": QUEUE_INDEX,
        }
        for name, q in queue_map.items():
            try:
                data["queues"][name] = int(await r.llen(q))
            except Exception:
                data["queues"][name] = 0
        data["queues_total"] = sum(int(v or 0) for v in data["queues"].values())

        daemon_hb = _parse_ts(await r.get("sentiment_api:ops:daemon_heartbeat"))
        daemon_last_cycle_raw = await r.get("sentiment_api:ops:daemon_last_cycle")

        # Per-worker keys (sentiment_api:ops:worker:{id}) for worker list + work assignment
        worker_keys = await r.keys("sentiment_api:ops:worker:*") or []
        workers_list: list[dict] = []
        for key in worker_keys:
            try:
                raw = await r.get(key)
                if not raw:
                    continue
                payload = json.loads(raw)
                wid = key.replace("sentiment_api:ops:worker:", "")
                last_seen = _parse_ts(payload.get("last_seen"))
                workers_list.append({
                    "id": wid,
                    "last_seen": _to_iso(last_seen),
                    "age_sec": _age_sec(last_seen),
                    "last_job": payload.get("last_job") or {},
                    "counts": {k: int(v) for k, v in (payload.get("counts") or {}).items()},
                })
            except (json.JSONDecodeError, TypeError):
                continue
        data["workers"] = workers_list
        # Aggregate heartbeat for backward compatibility (from workers or legacy single key)
        worker_hb = None
        worker_last_job = {}
        worker_counts = {}
        if workers_list:
            worker_hb = max(
                (_parse_ts(w.get("last_seen")) for w in workers_list if w.get("last_seen")),
                default=None,
            )
            # Most recent last_job by "at"
            by_at = [(w.get("last_job") or {}, w.get("last_job", {}).get("at") or "") for w in workers_list]
            worker_last_job = max(by_at, key=lambda x: x[1])[0] if by_at else {}
            for w in workers_list:
                for k, v in (w.get("counts") or {}).items():
                    worker_counts[k] = worker_counts.get(k, 0) + v
        else:
            worker_hb = _parse_ts(await r.get("sentiment_api:ops:worker_heartbeat"))
            worker_last_job = await r.hgetall("sentiment_api:ops:worker_last_job") or {}
            worker_counts_raw = await r.hgetall("sentiment_api:ops:worker_counts") or {}
            worker_counts = {k: int(v) for k, v in worker_counts_raw.items() if v is not None}

        data["heartbeats"]["worker"] = {
            "last_seen": _to_iso(worker_hb),
            "age_sec": _age_sec(worker_hb),
            "last_job": worker_last_job,
            "counts": worker_counts,
        }

        daemon_last_cycle = None
        if daemon_last_cycle_raw:
            try:
                daemon_last_cycle = json.loads(daemon_last_cycle_raw)
            except json.JSONDecodeError:
                daemon_last_cycle = None
        data["heartbeats"]["daemon"] = {
            "last_seen": _to_iso(daemon_hb),
            "age_sec": _age_sec(daemon_hb),
            "last_cycle": daemon_last_cycle or {},
        }
        data["redis"] = {"status": "ok"}
        # Desired worker count (set by scale API; applied by host or script)
        try:
            raw = await r.get("sentiment_api:ops:desired_workers")
            data["desired_workers"] = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            data["desired_workers"] = None
        await r.aclose()
    except Exception as e:
        data["redis"] = {"status": "fail", "error": str(e)}

    # System stats (CPU, memory, disk) from this process/container
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        data["system"] = {
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(mem.percent, 1),
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }
    except Exception as e:
        data["system"] = {"error": str(e)}

    # DB: counts + recent runs
    try:
        import logging
        from sentiment_api.db.pool import ensure_pool
        await ensure_pool()
        async with acquire() as conn:
            counts = data["counts"]
            latest = data["latest"]
            _ops_log = logging.getLogger("sentiment_api.api.ops")
            try:
                counts["articles"] = int(await conn.fetchval("SELECT count(*) FROM articles"))
                latest["article_at"] = _to_iso(await conn.fetchval("SELECT max(published_at) FROM articles"))
            except Exception as e:
                _ops_log.debug("Ops articles count failed: %s", e)
            try:
                counts["clusters"] = int(await conn.fetchval("SELECT count(*) FROM clusters"))
                latest["cluster_at"] = _to_iso(await conn.fetchval("SELECT max(last_seen) FROM clusters"))
            except Exception as e:
                _ops_log.debug("Ops clusters count failed: %s", e)
            try:
                counts["events"] = int(await conn.fetchval("SELECT count(*) FROM events"))
                latest["event_at"] = _to_iso(await conn.fetchval("SELECT max(created_at) FROM events"))
            except Exception as e:
                _ops_log.debug("Ops events count failed: %s", e)
            try:
                counts["summaries"] = int(await conn.fetchval("SELECT count(*) FROM summaries"))
            except Exception as e:
                _ops_log.debug("Ops summaries count failed: %s", e)
            try:
                counts["runs"] = int(await conn.fetchval("SELECT count(*) FROM runs"))
            except Exception as e:
                _ops_log.debug("Ops runs count failed: %s", e)

            try:
                run_rows = await conn.fetch(
                    """
                    SELECT run_type, status, started_at, ended_at, stats, error
                    FROM runs
                    ORDER BY started_at DESC
                    LIMIT 50
                    """
                )
                runs: dict[str, dict] = {}
                for r in run_rows:
                    if r["run_type"] in runs:
                        continue
                    runs[r["run_type"]] = {
                        "run_type": r["run_type"],
                        "status": r["status"],
                        "started_at": _to_iso(r["started_at"]),
                        "ended_at": _to_iso(r["ended_at"]) if r["ended_at"] else None,
                        "stats": r["stats"] or {},
                        "error": r["error"],
                    }
                data["runs"] = runs
            except Exception as e:
                _ops_log.debug("Ops runs fetch failed: %s", e)
        data["db"] = {"status": "ok"}
    except Exception as e:
        data["db"] = {"status": "fail", "error": str(e)}

    return {"meta": meta(), "data": data, "errors": []}


# -----------------------------------------------------------------------------
# POST /v1/admin/scale/workers — Set desired worker count (store in Redis; optionally run docker compose scale)
# -----------------------------------------------------------------------------
@app.post("/v1/admin/scale/workers")
async def admin_scale_workers(
    _: Annotated[str, Depends(validate_api_key)],
    body: dict,
):
    """Set desired worker count. Writes to Redis; if COMPOSE_PROJECT_DIR is set, runs docker compose up -d --scale worker=N."""
    count = body.get("count")
    if count is None:
        raise HTTPException(status_code=400, detail="Missing 'count' in body")
    try:
        n = int(count)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'count' must be an integer")
    if n < 0 or n > 64:
        raise HTTPException(status_code=400, detail="'count' must be between 0 and 64")

    settings = get_settings()
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.set("sentiment_api:ops:desired_workers", str(n))
        await r.aclose()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")

    applied = False
    msg = f"Desired workers set to {n}."
    if settings.compose_project_dir:
        import subprocess
        import shutil
        compose_dir = settings.compose_project_dir
        compose_file = Path(compose_dir) / "docker-compose.yml"
        # Prefer docker CLI (docker compose); fallback to /usr/bin/docker when API runs in container
        compose_cmd = shutil.which("docker") or ("/usr/bin/docker" if Path("/usr/bin/docker").exists() else None)
        if compose_cmd:
            try:
                proc = subprocess.run(
                    [compose_cmd, "compose", "-f", str(compose_file), "up", "-d", "--scale", f"worker={n}"],
                    cwd=str(compose_dir),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={**os.environ, "DOCKER_HOST": os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")},
                )
                if proc.returncode == 0:
                    applied = True
                    msg = f"Workers scaled to {n}."
                else:
                    msg = f"Desired workers set to {n}; docker scale failed: {proc.stderr or proc.stdout or 'unknown'}"
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                msg = f"Desired workers set to {n}; scale failed: {e}. Run: docker compose up -d --scale worker={n}"
        else:
            msg = f"Desired workers set to {n}. Rebuild API with docker CLI and set COMPOSE_PROJECT_DIR, or run: docker compose up -d --scale worker={n}"
    else:
        msg = f"Desired workers set to {n}. To apply, run: docker compose up -d --scale worker={n}"

    return {"meta": meta(), "data": {"count": n, "applied": applied, "message": msg}, "errors": []}


def run():
    """Run uvicorn server."""
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "sentiment_api.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=(settings.env == "dev"),
    )


if __name__ == "__main__":
    run()
