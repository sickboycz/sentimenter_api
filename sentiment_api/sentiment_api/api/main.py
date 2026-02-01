"""FastAPI application — M9 API Service."""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from sentiment_api.api.auth import get_api_key
from sentiment_api.api.responses import error_detail, meta, pagination
from sentiment_api.config import get_settings
from sentiment_api.db.pool import close_pool, init_pool
from sentiment_api.registry import load_registry, RegistryError


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        await init_pool(settings.database_url)
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
    version="1.0.0",
    summary="Global macro + political news impact intelligence (Sentimeter)",
    lifespan=lifespan,
)


def _get_registry():
    """Load registry; fail gracefully if path invalid."""
    settings = get_settings()
    try:
        return load_registry(settings.source_registry_path)
    except RegistryError as e:
        return None


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

    status = "ok" if all(c["status"] == "ok" for c in checks) else "degraded"
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
    _: Annotated[str, Depends(get_api_key)],
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
async def get_mood_now(_: Annotated[str, Depends(get_api_key)]):
    """Latest mood snapshot (drivers + risk vector)."""
    import asyncpg
    from sentiment_api.db.pool import acquire
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
    _: Annotated[str, Depends(get_api_key)],
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
    _: Annotated[str, Depends(get_api_key)],
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
    _: Annotated[str, Depends(get_api_key)],
    cluster_id: str,
    include_articles: bool = Query(True),
    include_evidence: bool = Query(True),
    include_analogs: bool = Query(False),
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
    return {
        "meta": meta(),
        "data": {
            "cluster": cluster_obj,
            "articles": articles,
            "evidence": evidence,
            "what_changed_en": None,
            "why_it_matters_en": None,
            "what_to_watch_en": None,
            "impact_explanation_en": None,
            "historical_analogs": [] if include_analogs else None,
        },
        "errors": [],
    }


# -----------------------------------------------------------------------------
# /v1/research/spy/event-study
# -----------------------------------------------------------------------------
@app.get("/v1/research/spy/event-study")
async def get_spy_event_study(
    _: Annotated[str, Depends(get_api_key)],
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
        td = date_type.fromisoformat(to_date)
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
# /v1/ask — RAG query (optional)
# -----------------------------------------------------------------------------
@app.post("/v1/ask")
async def ask_rag(
    _: Annotated[str, Depends(get_api_key)],
    body: dict = Body(default={"query": ""}),
):
    """RAG query over memory (retrieve + answer with citations)."""
    query = (body or {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query required in body")
    from sentiment_api.db.pool import get_pool
    pool = get_pool()
    if pool is None:
        return {"meta": meta(), "data": {"answer": "Service unavailable.", "citations": []}, "errors": [error_detail("UNAVAILABLE", "DB not initialized")]}
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                "SELECT cluster_id, headline_en FROM clusters ORDER BY last_seen DESC LIMIT 5"
            )
        citations = [{"cluster_id": r["cluster_id"], "headline_en": r["headline_en"]} for r in rows]
        return {"meta": meta(), "data": {"answer": "RAG not fully implemented; returning recent clusters.", "citations": citations}, "errors": []}
    except Exception:
        return {"meta": meta(), "data": {"answer": "", "citations": []}, "errors": [error_detail("RAG_ERROR", "Query failed")]}


# -----------------------------------------------------------------------------
# /v1/sources
# -----------------------------------------------------------------------------
@app.get("/v1/sources")
async def list_sources(
    _: Annotated[str, Depends(get_api_key)],
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
