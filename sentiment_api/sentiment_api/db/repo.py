"""Repository layer for articles, clusters, events, embeddings."""

import json
import logging
from datetime import datetime, date, timezone
from typing import Any

import asyncpg

from sentiment_api.config import get_settings
from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.db.repo")


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
    """Insert article; return article_id if inserted, None if duplicate (article_id or canonical_url)."""
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO articles (article_id, source_id, url, canonical_url, published_at, fetched_at,
                lang_original, title_raw, title_en, content_en, translation_status, translation_provider,
                translation_confidence, content_hash, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (article_id) DO NOTHING
            RETURNING article_id
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
        return row["article_id"] if row else None
    except asyncpg.UniqueViolationError as e:
        logger.debug("Article duplicate (article_id or canonical_url): %s", e)
        return None


async def get_article_needing_summarize(
    conn: asyncpg.Connection,
    article_id_hint: str,
    canonical_url: str,
) -> dict | None:
    """Return article row as {article_id, source_id, norm} if it exists and has no L2 summary, else None."""
    row = await conn.fetchrow(
        """
        SELECT a.article_id, a.source_id, a.url, a.canonical_url, a.published_at, a.fetched_at,
               a.title_en, a.content_en, a.metadata
        FROM articles a
        WHERE (a.article_id = $1 OR a.canonical_url = $2)
          AND NOT EXISTS (
              SELECT 1 FROM summaries s
              WHERE s.object_type = 'article' AND s.object_id = a.article_id AND s.level = 'L2'
          )
        LIMIT 1
        """,
        article_id_hint,
        canonical_url,
    )
    if not row:
        return None
    norm = {
        "source_id": row["source_id"],
        "url": row["url"],
        "canonical_url": row["canonical_url"],
        "title_en": row["title_en"] or "",
        "content_en": row["content_en"] or "",
        "published_at": row["published_at"].isoformat() if row["published_at"] else "",
        "fetched_at": row["fetched_at"].isoformat() if row["fetched_at"] else "",
        "metadata": row["metadata"] or {},
    }
    return {"article_id": row["article_id"], "source_id": row["source_id"], "norm": norm}


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
    first_seen = datetime.now(timezone.utc)
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
        except Exception as ex:
            logger.debug("insert_event_impacts skipped (asset_direction enum may be missing): %s", ex)


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


async def get_cluster_l3_summary(conn: asyncpg.Connection, cluster_id: str) -> dict | None:
    """Fetch latest L3 summary for a cluster (what_changed_en, why_it_matters_en, what_to_watch_en, etc.)."""
    row = await conn.fetchrow(
        """
        SELECT content FROM summaries
        WHERE object_type = 'cluster' AND object_id = $1 AND level = 'L3'
        ORDER BY created_at DESC LIMIT 1
        """,
        cluster_id,
    )
    if not row or not row.get("content"):
        return None
    raw = row["content"]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
    return raw if isinstance(raw, dict) else None


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
    settings = get_settings()
    model_id = model_id or settings.model_embedding_id or "openai:text-embedding-3-small:384"
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
            elif isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except (json.JSONDecodeError, TypeError):
                    emb = []
            elif not isinstance(emb, list):
                emb = list(emb) if emb else []
            if isinstance(emb, list) and emb:
                try:
                    emb = [float(x) for x in emb]
                except (TypeError, ValueError):
                    emb = []
            result.append((r["object_id"], emb, r["last_seen"]))
        return result
    from sentiment_api.vector_store import get_vector_store
    store = get_vector_store(backend)
    pairs = await store.get_cluster_vectors(model_id=model_id, limit=limit)
    # External store has no last_seen; use min datetime so ordering is unchanged
    return [(cid, emb, datetime.min) for cid, emb in pairs]


async def get_similar_clusters(
    conn: asyncpg.Connection,
    cluster_id: str,
    limit: int = 20,
    min_similarity: float = 0.5,
    model_id: str | None = None,
) -> list[dict]:
    """Return historically similar clusters by embedding cosine similarity.
    Excludes the current cluster. Each item: cluster_id, similarity, label_en, date."""
    import math

    settings = get_settings()
    model_id = model_id or settings.model_embedding_id or "openai:text-embedding-3-small:384"
    backend = (settings.vector_store_backend or "pgvector").strip().lower()

    if backend != "pgvector":
        return []

    # Get current cluster embedding
    row = await conn.fetchrow(
        """
        SELECT e.embedding, c.headline_en, c.last_seen
        FROM embeddings e
        JOIN clusters c ON c.cluster_id = e.object_id
        WHERE e.object_type = 'cluster' AND e.object_id = $1 AND e.model = $2
        """,
        cluster_id,
        model_id,
    )
    if not row or not row["embedding"]:
        return []

    vec0 = row["embedding"]
    if hasattr(vec0, "tolist"):
        vec0 = vec0.tolist()
    elif isinstance(vec0, str):
        try:
            vec0 = json.loads(vec0)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(vec0, list) or not vec0:
        return []

    try:
        vec0 = [float(x) for x in vec0]
    except (TypeError, ValueError):
        return []

    norm0 = math.sqrt(sum(x * x for x in vec0))
    if norm0 == 0:
        return []

    # Get other clusters with embeddings (exclude self)
    rows = await conn.fetch(
        """
        SELECT e.object_id as cluster_id, e.embedding, c.headline_en, c.last_seen
        FROM embeddings e
        JOIN clusters c ON c.cluster_id = e.object_id
        WHERE e.object_type = 'cluster' AND e.object_id != $1 AND e.model = $2
        ORDER BY c.last_seen DESC
        LIMIT $3
        """,
        cluster_id,
        model_id,
        limit * 3,
    )

    scored: list[tuple[str, float, str, datetime]] = []
    for r in rows:
        emb = r["embedding"]
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        elif isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(emb, list) or len(emb) != len(vec0):
            continue
        try:
            emb = [float(x) for x in emb]
        except (TypeError, ValueError):
            continue
        dot = sum(a * b for a, b in zip(vec0, emb))
        norm = math.sqrt(sum(x * x for x in emb))
        if norm == 0:
            continue
        sim = dot / (norm0 * norm)
        sim = max(0.0, min(1.0, sim))
        if sim >= min_similarity:
            scored.append((r["cluster_id"], sim, r["headline_en"] or r["cluster_id"], r["last_seen"]))

    scored.sort(key=lambda x: -x[1])
    result = []
    for cid, sim, label, dt in scored[:limit]:
        date_str = dt.date().isoformat() if dt and hasattr(dt, "date") else ""
        result.append({
            "cluster_id": cid,
            "similarity": round(sim, 4),
            "label_en": (label or "")[:200],
            "date": date_str,
        })
    return result
