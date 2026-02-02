"""FastAPI application — M9 API Service."""

import json
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        await init_pool(settings.database_url)
        from sentiment_api.db.pool import get_pool
        pool = get_pool()
        if pool:
            try:
                from sentiment_api.db.universe_repo import seed_sectors, upsert_universe
                async with pool.acquire() as conn:
                    await seed_sectors(conn)
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

# CORS: allow frontend origin(s) from config; also allow any origin on port 3000 (same-host UI by IP)
_cors_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://[^/]+:3000",  # e.g. http://80.211.210.49:3000 when UI opened by IP
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Set request_id for envelope correlation."""
    rid = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Return v1.2 envelope for HTTP errors on /v1/*."""
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
        return JSONResponse(status_code=exc.status_code, content=body)
    # Fallback for legacy string detail
    body = {
        "meta": {"request_id": rid, "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z")},
        "data": {},
        "errors": [{"code": "http_error", "message": str(detail)}],
    }
    return JSONResponse(status_code=exc.status_code, content=body)


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
    """Load registry; fail gracefully if path invalid."""
    settings = get_settings()
    try:
        return load_registry(settings.source_registry_path)
    except RegistryError as e:
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
    except Exception:
        pass
    return PlainTextResponse(collect_metrics(), media_type="text/plain; charset=utf-8")


# -----------------------------------------------------------------------------
# /ready — Readiness probe (DB ready)
# -----------------------------------------------------------------------------
@app.get("/ready")
async def ready():
    """Readiness: 200 when DB is ready to serve. No auth."""
    try:
        from sentiment_api.db.pool import get_pool
        pool = get_pool()
        if pool is None:
            return Response(status_code=503, content="Pool not initialized")
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return Response(status_code=200, content="ok")
    except Exception:
        return Response(status_code=503, content="DB not ready")


# -----------------------------------------------------------------------------
# /v1/health — No auth (AC-M10.4)
# -----------------------------------------------------------------------------
@app.get("/v1/health")
async def health():
    """Health and dependency checks."""
    checks = []
    settings = get_settings()

    # DB check
    try:
        from sentiment_api.db.pool import get_pool
        pool = get_pool()
        if pool is None:
            checks.append({"name": "postgres", "status": "fail", "details": {"error": "Pool not initialized"}})
        else:
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

    # OpenAI check (optional; fail = LLM disabled)
    try:
        import os
        key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if key:
            checks.append({"name": "openai", "status": "ok", "details": {}})
        else:
            checks.append({"name": "openai", "status": "fail", "details": {"message": "No API key; LLM features disabled"}})
    except Exception as e:
        checks.append({"name": "openai", "status": "fail", "details": {"error": str(e)}})

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
        imp = r["impact"] or {}
        tone = r["tone"] or {}
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
    """Cluster drilldown (articles + evidence + analogs)."""
    import asyncpg
    from sentiment_api.db.pool import acquire
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
    imp = row["impact"] or {}
    tone = row["tone"] or {}
    cluster_obj = {
        "cluster_id": row["cluster_id"],
        "first_seen": row["first_seen"].isoformat().replace("+00:00", "Z") if row["first_seen"] else None,
        "last_seen": row["last_seen"].isoformat().replace("+00:00", "Z") if row["last_seen"] else None,
        "headline_en": row["headline_en"] or "",
        "summary_bullets_en": [],
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
            except Exception:
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
    if include_asset_impacts:
        try:
            from sentiment_api.engines.asset_targeting import get_asset_impacts_for_cluster
            asset_impacts = await get_asset_impacts_for_cluster(cluster_id)
        except Exception:
            pass
    return {
        "meta": meta(),
        "data": {
            "cluster": cluster_obj,
            "articles": articles,
            "evidence": evidence,
            "asset_impacts": asset_impacts,
            "what_changed_en": None,
            "why_it_matters_en": None,
            "what_to_watch_en": None,
            "impact_explanation_en": None,
            "historical_analogs": [] if include_analogs else None,
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
        from sentiment_api.api.responses import error_detail
        return {"meta": meta(), "data": {}, "errors": [error_detail("IMPACTS_LATEST_ERROR", str(e))]}


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
async def stream_events(request: Request, _: Annotated[str, Depends(validate_api_key)]):
    """SSE stream: heartbeat, cluster_updated, mood_updated, impacts_updated, topics_updated. v1.2"""
    import asyncio
    from fastapi.responses import StreamingResponse
    rid = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:12]}")
    key = _client_key(request)

    async def gen():
        from sentiment_api.db.pool import get_pool, acquire
        try:
            tick = 0
            while True:
                ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                yield f"event: heartbeat\ndata: {json.dumps({'type':'heartbeat','ts':ts,'payload':{},'request_id':rid}, separators=(',', ':'))}\n\n"
                tick += 1
                if tick % 4 == 0:
                    payload: dict = {}
                    try:
                        pool = get_pool()
                        if pool:
                            async with acquire() as conn:
                                r = await conn.fetchrow("SELECT ts, index_value FROM sentiment_timeseries WHERE interval='5m' ORDER BY ts DESC LIMIT 1")
                                if r:
                                    payload = {"as_of": (r["ts"] or datetime.now(UTC)).isoformat().replace("+00:00", "Z"), "index_value": float(r["index_value"] or 0)}
                    except Exception:
                        pass
                    evt = {"type": "mood_updated", "ts": ts, "payload": payload, "request_id": rid}
                    yield f"event: mood_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    try:
                        from sentiment_api.engines.asset_targeting import get_latest_asset_impacts
                        imp = await get_latest_asset_impacts(window="6h", limit_tickers=5, limit_sectors=5)
                        evt = {"type": "impacts_updated", "ts": ts, "payload": imp, "request_id": rid}
                        yield f"event: impacts_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
                    except Exception:
                        evt = {"type": "impacts_updated", "ts": ts, "payload": {}, "request_id": rid}
                        yield f"event: impacts_updated\ndata: {json.dumps(evt, separators=(',', ':'))}\n\n"
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
                "data": [],
                "errors": [error_detail("REGISTRY_UNAVAILABLE", "Source registry could not be loaded")],
            },
        )
    sources = reg.get_enabled_sources() if enabled_only else reg.sources
    if types:
        sources = [s for s in sources if s.type in types]
    cred_map = {"official": "official", "reputable_media": "reputable_media", "local_media": "local_media", "dataset": "dataset", "user_added": "user_added"}
    lic_map = {"open": "open", "key_required": "key_required", "paid": "paid", "restricted": "restricted"}
    data = [
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
        "data": data,
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
    for src in sources:
        if src.type == "rss" and src.feed_url:
            for item in rss.collect(src, src.feed_url):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                total += 1
        elif src.type == "gdelt" and src.base_url:
            for item in gdelt.collect(src, src.base_url, getattr(src, "query_profiles", None)):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                total += 1
        elif src.type == "scrape" and src.page_url:
            for item in scrape.collect(src, src.page_url):
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
