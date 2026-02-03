"""Repository layer for articles, clusters, events, embeddings."""

import json
from datetime import datetime, date
from typing import Any

import asyncpg

from sentiment_api.config import get_settings
from sentiment_api.db.pool import acquire


async def upsert_sources(conn: asyncpg.Connection, sources: list[dict]) -> None:
    """Upsert sources from registry."""
    for s in sources:
        await conn.execute(
            """
            INSERT INTO sources (source_id, name, pack, type, enabled, credibility, license, regions, topics, config, updated_at)
            VALUES ($1, $2, $3, $4::source_type, $5, $6::credibility_tier, $7::license_class, $8, $9, $10, now())
            ON CONFLICT (source_id) DO UPDATE SET
                name = EXCLUDED.name, pack = EXCLUDED.pack, type = EXCLUDED.type, enabled = EXCLUDED.enabled,
                credibility = EXCLUDED.credibility, license = EXCLUDED.license, regions = EXCLUDED.regions,
                topics = EXCLUDED.topics, config = EXCLUDED.config, updated_at = now()
            """,
            s["source_id"],
            s["name"],
            s["pack"],
            s["type"],
            s.get("enabled", True),
            s.get("credibility", "reputable_media"),
            s.get("license", "open"),
            s.get("regions", []),
            s.get("topics", []),
            json.dumps(s.get("config", {})),
        )


async def insert_article_body(
    conn: asyncpg.Connection,
    article_id: str,
    raw_html_path: str | None = None,
    extracted_text_path: str | None = None,
    extracted_len: int | None = None,
    extraction_quality: float | None = None,
    http_status: int | None = None,
) -> None:
    """Insert article_bodies (L0 artifact pointers)."""
    await conn.execute(
        """
        INSERT INTO article_bodies (article_id, raw_html_path, extracted_text_path, extracted_len, extraction_quality, http_status)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (article_id) DO UPDATE SET
            raw_html_path = COALESCE(EXCLUDED.raw_html_path, article_bodies.raw_html_path),
            extracted_text_path = COALESCE(EXCLUDED.extracted_text_path, article_bodies.extracted_text_path),
            extracted_len = COALESCE(EXCLUDED.extracted_len, article_bodies.extracted_len),
            extraction_quality = COALESCE(EXCLUDED.extraction_quality, article_bodies.extraction_quality),
            http_status = COALESCE(EXCLUDED.http_status, article_bodies.http_status)
        """,
        article_id,
        raw_html_path,
        extracted_text_path,
        extracted_len,
        extraction_quality,
        http_status,
    )


async def insert_article(conn: asyncpg.Connection, art: dict) -> str | None:
    """Insert article; return article_id or None if duplicate."""
    try:
        await conn.execute(
            """
            INSERT INTO articles (article_id, source_id, url, canonical_url, published_at, fetched_at,
                lang_original, title_raw, title_en, content_en, translation_status, translation_provider,
                translation_confidence, content_hash, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (article_id) DO NOTHING
            """,
            art["article_id"],
            art["source_id"],
            art["url"],
            art["canonical_url"],
            art.get("published_at"),
            art["fetched_at"],
            art.get("lang_original"),
            art.get("title_raw"),
            art["title_en"],
            art.get("content_en"),
            art.get("translation_status", "ok"),
            art.get("translation_provider"),
            art.get("translation_confidence"),
            art.get("content_hash"),
            json.dumps(art.get("metadata", {})),
        )
        return art["article_id"]
    except asyncpg.UniqueViolationError:
        return None


async def insert_cluster(
    conn: asyncpg.Connection,
    cluster_id: str,
    headline_en: str,
    canonical_story_key: str,
    topics: list[str],
    regions: list[str],
    source_count: int,
    source_urls: list[str],
    tone: dict,
    impact: dict,
    risk_vector: dict,
) -> None:
    """Insert or update cluster."""
    first_seen = datetime.utcnow()
    await conn.execute(
        """
        INSERT INTO clusters (cluster_id, first_seen, last_seen, headline_en, canonical_story_key,
            topics, regions, source_count, source_urls, tone, impact, risk_vector, updated_at)
        VALUES ($1, $2, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
        ON CONFLICT (cluster_id) DO UPDATE SET
            last_seen = now(), headline_en = COALESCE(EXCLUDED.headline_en, clusters.headline_en),
            source_count = clusters.source_count + 1,
            source_urls = clusters.source_urls || EXCLUDED.source_urls,
            tone = EXCLUDED.tone, impact = EXCLUDED.impact, risk_vector = EXCLUDED.risk_vector, updated_at = now()
        """,
        cluster_id,
        first_seen,
        headline_en,
        canonical_story_key,
        topics,
        regions,
        source_count,
        source_urls,
        json.dumps(tone),
        json.dumps(impact),
        json.dumps(risk_vector),
    )


async def add_cluster_member(conn: asyncpg.Connection, cluster_id: str, article_id: str) -> None:
    """Add article to cluster."""
    await conn.execute(
        """
        INSERT INTO cluster_members (cluster_id, article_id) VALUES ($1, $2)
        ON CONFLICT (cluster_id, article_id) DO NOTHING
        """,
        cluster_id,
        article_id,
    )


async def insert_embedding(
    conn: asyncpg.Connection,
    object_type: str,
    object_id: str,
    model: str,
    embedding: list[float],
) -> None:
    """Insert embedding. Uses pgvector or external vector store (Weaviate) per VECTOR_STORE_BACKEND."""
    settings = get_settings()
    backend = (settings.vector_store_backend or "pgvector").strip().lower()
    if backend == "pgvector":
        # pgvector expects string format: "[1.0, 2.0, ...]"
        import json
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        if isinstance(embedding, str):
            embedding_str = embedding
        else:
            embedding_str = json.dumps(list(embedding))
        await conn.execute(
            """
            INSERT INTO embeddings (object_type, object_id, model, dims, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5::vector, '{}')
            ON CONFLICT (object_type, object_id, model) DO UPDATE SET embedding = EXCLUDED.embedding
            """,
            object_type,
            object_id,
            model,
            len(embedding),
            embedding_str,
        )
    else:
        from sentiment_api.vector_store import get_vector_store
        store = get_vector_store(backend)
        await store.upsert(object_type, object_id, model, embedding)


async def insert_sentiment_tick(
    conn: asyncpg.Connection,
    ts: datetime,
    interval: str,
    index_value: float,
    news_volume: int,
    news_volatility: float,
    sentiment: str,
    confidence: float = 0.5,
    drivers: list | None = None,
) -> None:
    """Insert intraday sentiment tick."""
    await conn.execute(
        """
        INSERT INTO sentiment_timeseries (ts, interval, index_value, news_volume, news_volatility, sentiment, confidence, drivers)
        VALUES ($1, $2, $3, $4, $5, $6::direction, $7, $8)
        ON CONFLICT (ts, interval) DO UPDATE SET
            index_value = EXCLUDED.index_value, news_volume = EXCLUDED.news_volume,
            news_volatility = EXCLUDED.news_volatility, sentiment = EXCLUDED.sentiment,
            confidence = EXCLUDED.confidence, drivers = EXCLUDED.drivers
        """,
        ts,
        interval,
        index_value,
        news_volume,
        news_volatility,
        sentiment,
        confidence,
        json.dumps(drivers or []),
    )


async def upsert_sentiment_daily(
    conn: asyncpg.Connection,
    d: date,
    open_val: float,
    high: float,
    low: float,
    close: float,
    moodix_index: float,
    ma5: float | None,
    ma10: float | None,
    sentiment_wave: float | None,
    sentiment: str | None,
    news_volume: int = 0,
    news_volatility: float = 0.0,
) -> None:
    """Upsert daily sentiment row."""
    await conn.execute(
        """
        INSERT INTO sentiment_daily (date, update_time, open, high, low, close, moodix_index,
            ma5_moodix, ma10_moodix, sentiment_wave, sentiment, news_volume_intraday, news_volatility_intraday)
        VALUES ($1, now(), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (date) DO UPDATE SET
            update_time = now(), open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close,
            moodix_index = EXCLUDED.moodix_index, ma5_moodix = EXCLUDED.ma5_moodix, ma10_moodix = EXCLUDED.ma10_moodix,
            sentiment_wave = EXCLUDED.sentiment_wave, sentiment = EXCLUDED.sentiment,
            news_volume_intraday = EXCLUDED.news_volume_intraday, news_volatility_intraday = EXCLUDED.news_volatility_intraday
        """,
        d,
        open_val,
        high,
        low,
        close,
        moodix_index,
        ma5,
        ma10,
        sentiment_wave,
        sentiment,
        news_volume,
        news_volatility,
    )


async def insert_event_impacts(
    conn: asyncpg.Connection,
    event_id: str,
    impacts: list[dict],
) -> None:
    """Insert event_impacts rows (markets, sectors, tickers). Per-asset audit."""
    for imp in impacts:
        instrument = imp.get("instrument") or imp.get("market_id") or imp.get("symbol")
        if not instrument:
            continue
        direction = imp.get("direction", "Unknown")
        if direction not in ("Up", "Down", "Neutral", "Mixed", "Unknown"):
            direction = "Unknown"
        try:
            await conn.execute(
                """
                INSERT INTO event_impacts (event_id, instrument, instrument_type, direction, impact_score, horizon, confidence, details)
                VALUES ($1, $2, $3, $4::asset_direction, $5, $6, $7, $8)
                ON CONFLICT (event_id, instrument) DO UPDATE SET
                    direction = EXCLUDED.direction, impact_score = EXCLUDED.impact_score,
                    horizon = EXCLUDED.horizon, confidence = EXCLUDED.confidence, details = EXCLUDED.details
                """,
                event_id,
                instrument,
                imp.get("instrument_type", "ticker"),
                direction,
                float(imp.get("impact_score", 0) or 0),
                imp.get("horizon", "unknown") or "unknown",
                float(imp.get("confidence", 0) or 0),
                json.dumps(imp.get("details", {})),
            )
        except Exception:
            pass  # asset_direction enum may not exist in older DBs


async def insert_event(
    conn: asyncpg.Connection,
    event_id: str,
    cluster_id: str,
    event_type: str,
    headline_en: str,
    expected_direction: str,
    horizon: str,
    confidence: float,
    reason_codes: list[str],
    impact_score: float,
    impact_level: str,
    regions: list[str] | None = None,
    topics: list[str] | None = None,
) -> None:
    """Insert event."""
    await conn.execute(
        """
        INSERT INTO events (event_id, cluster_id, event_type, event_ts, headline_en,
            regions, topics, expected_direction, horizon, confidence, reason_codes, impact_score, impact_level)
        VALUES ($1, $2, $3, now(), $4, $5, $6, $7::direction, $8, $9, $10, $11, $12::impact_level)
        ON CONFLICT (event_id) DO NOTHING
        """,
        event_id,
        cluster_id,
        event_type,
        headline_en,
        regions or [],
        topics or [],
        expected_direction,
        horizon,
        confidence,
        reason_codes,
        impact_score,
        impact_level,
    )


async def insert_summary(
    conn: asyncpg.Connection,
    object_type: str,
    object_id: str,
    level: str,
    schema_id: str,
    schema_version: str,
    model_id: str,
    prompt_version: str,
    dedupe_key: str,
    content: dict,
) -> None:
    """Insert summary (L1-L4) with dedupe_key for caching."""
    await conn.execute(
        """
        INSERT INTO summaries (object_type, object_id, level, schema_id, schema_version, model_id, prompt_version, dedupe_key, content)
        VALUES ($1::object_type, $2, $3::summary_level, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (object_type, object_id, level, dedupe_key) DO NOTHING
        """,
        object_type,
        object_id,
        level,
        schema_id,
        schema_version,
        model_id,
        prompt_version,
        dedupe_key,
        json.dumps(content),
    )


async def insert_expectation(
    conn: asyncpg.Connection,
    event_id: str,
    expected_direction: str,
    expected_magnitude: float | None = None,
    market: str = "SPY",
) -> str:
    """Insert expectation for forward eval. Returns expectation_id."""
    row = await conn.fetchrow(
        """
        INSERT INTO expectations (event_id, expected_direction, expected_magnitude, market)
        VALUES ($1, $2::direction, $3, $4)
        RETURNING expectation_id
        """,
        event_id,
        expected_direction,
        expected_magnitude,
        market,
    )
    return str(row["expectation_id"])


async def insert_run(conn: asyncpg.Connection, run_type: str, source_id: str | None = None, stats: dict | None = None) -> str:
    """Insert run record. Returns run_id."""
    row = await conn.fetchrow(
        """
        INSERT INTO runs (run_type, source_id, stats) VALUES ($1, $2, $3)
        RETURNING run_id
        """,
        run_type,
        source_id,
        json.dumps(stats or {}),
    )
    return str(row["run_id"])


async def finish_run(conn: asyncpg.Connection, run_id: str, status: str = "ok", error: dict | None = None) -> None:
    """Mark run as finished."""
    await conn.execute(
        "UPDATE runs SET ended_at = now(), status = $1, error = $2 WHERE run_id = $3",
        status,
        json.dumps(error) if error else None,
        run_id,
    )


async def get_clusters_by_ids(
    conn: asyncpg.Connection,
    cluster_ids: list[str],
) -> list[dict]:
    """Fetch cluster headline_en, topics, impact by cluster_ids (for RAG when using external vector store)."""
    if not cluster_ids:
        return []
    rows = await conn.fetch(
        """
        SELECT cluster_id, headline_en, topics, impact
        FROM clusters
        WHERE cluster_id = ANY($1::text[])
        """,
        cluster_ids,
    )
    return [
        {
            "cluster_id": r["cluster_id"],
            "headline_en": r["headline_en"],
            "topics": list(r["topics"] or []),
            "impact": r["impact"] or {},
        }
        for r in rows
    ]


async def get_clusters_for_embedding(conn: asyncpg.Connection, limit: int = 500, model_id: str | None = None) -> list[tuple[str, list[float], datetime]]:
    """Get cluster_ids and embeddings for similarity search. Uses pgvector or external store per VECTOR_STORE_BACKEND."""
    model_id = model_id or "openai:text-embedding-3-large"
    settings = get_settings()
    backend = (settings.vector_store_backend or "pgvector").strip().lower()
    if backend == "pgvector":
        rows = await conn.fetch(
            """
            SELECT e.object_id, e.embedding, c.last_seen
            FROM embeddings e
            JOIN clusters c ON c.cluster_id = e.object_id
            WHERE e.object_type = 'cluster' AND e.model = $1
            ORDER BY c.last_seen DESC
            LIMIT $2
            """,
            model_id,
            limit,
        )
        result = []
        for r in rows:
            emb = r["embedding"]
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            elif not isinstance(emb, list):
                emb = list(emb) if emb else []
            result.append((r["object_id"], emb, r["last_seen"]))
        return result
    from sentiment_api.vector_store import get_vector_store
    store = get_vector_store(backend)
    pairs = await store.get_cluster_vectors(model_id=model_id, limit=limit)
    # External store has no last_seen; use min datetime so ordering is unchanged
    return [(cid, emb, datetime.min) for cid, emb in pairs]
