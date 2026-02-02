"""Worker: process queue jobs (ingest -> normalize -> cluster -> summarize -> score -> index)."""

import asyncio
import hashlib
import base64
import logging
from datetime import datetime, timezone

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, close_pool, acquire
from sentiment_api.db.repo import (
    upsert_sources,
    insert_article,
    insert_article_body,
    insert_cluster,
    add_cluster_member,
    insert_embedding,
    insert_event,
    insert_summary,
    insert_expectation,
    insert_run,
    finish_run,
    get_clusters_for_embedding,
)
from sentiment_api.ingest.normalize import normalize_item
from sentiment_api.ingest.artifacts import save_l0
from sentiment_api.ingest.dedup import article_id, content_fingerprint
from sentiment_api.ingest.cluster import cluster_id, canonical_story_key, find_nearest_cluster
from sentiment_api.llm.embeddings import embed_text
from sentiment_api.llm.summaries import summarize_l1, summarize_l2, summarize_l3
from sentiment_api.llm.impact import score_impact
from sentiment_api.queue.client import get_queue, QUEUE_INGEST, QUEUE_NORMALIZE, QUEUE_SUMMARIZE, QUEUE_SCORE, QUEUE_INDEX
from sentiment_api.registry import load_registry
from sentiment_api.engines.index import compute_intraday_from_clusters, compute_daily_ohlc

logger = logging.getLogger("sentiment_api.worker")


def _event_id(cluster_id: str, event_type: str) -> str:
    h = hashlib.sha256(f"{cluster_id}|{event_type}|{datetime.utcnow().isoformat()[:10]}".encode()).digest()[:12]
    return f"evt_{base64.urlsafe_b64encode(h).decode().rstrip('=').lower()}"


async def process_ingest(payload: dict) -> None:
    """Receive raw item, normalize, dedupe, insert article, push to summarize."""
    import json
    settings = get_settings()
    run_id = None
    try:
        async with acquire() as conn:
            run_id = await insert_run(conn, "ingest", payload.get("source_id"), {"url": payload.get("url", "")[:100]})
    except Exception:
        pass
    reg = load_registry(settings.source_registry_path)
    norm = normalize_item(
        payload,
        reg.defaults,
        translate=True,
        translation_provider=None,
    )
    pub = norm.get("published_at") or datetime.now(timezone.utc)
    pub_str = pub.isoformat() if hasattr(pub, "isoformat") else str(pub)
    art_id = article_id(norm["source_id"], norm["canonical_url"], pub_str)
    norm["article_id"] = art_id
    norm["fetched_at"] = norm["fetched_at"]
    import json
    import hashlib
    queue = await get_queue(settings.redis_url)
    async with acquire() as conn:
        inserted = await insert_article(conn, norm)
        if inserted:
            html_path, txt_path = save_l0(art_id, norm["source_id"], payload.get("content_html", ""), norm.get("content_en", ""))
            await insert_article_body(
                conn, art_id,
                raw_html_path=html_path,
                extracted_text_path=txt_path,
                extracted_len=len(norm.get("content_en", "")),
                extraction_quality=0.9 if norm.get("content_en") else 0.0,
            )
    if run_id:
        async with acquire() as conn:
            await finish_run(conn, run_id, "ok" if inserted else "ok", {"article_id": art_id, "inserted": inserted})
    if inserted:
        await queue.rpush(QUEUE_SUMMARIZE, json.dumps({"article_id": art_id, "source_id": norm["source_id"], "norm": norm}))


def _dedupe_key(obj_id: str, text_hash: str, schema_ver: str, model: str) -> str:
    import hashlib
    return hashlib.sha256(f"{obj_id}|{text_hash}|{schema_ver}|{model}".encode()).hexdigest()[:32]


async def process_summarize(payload: dict) -> None:
    """Summarize article L1/L2, embed, cluster or create new cluster, push to score."""
    import hashlib
    settings = get_settings()
    art_id = payload.get("article_id")
    norm = payload.get("norm", {})
    if not art_id or not norm:
        return
    title = norm.get("title_en", "")
    content = norm.get("content_en", "")
    url = norm.get("url", "")
    pub = norm.get("published_at")
    pub_str = pub.isoformat() if hasattr(pub, "isoformat") else str(pub) if pub else ""
    run_id = None
    async with acquire() as conn:
        run_id = await insert_run(conn, "summarize", art_id, {"article_id": art_id})
    try:
        l1 = summarize_l1(art_id, title, content, url, pub_str)
        l2 = summarize_l2(art_id, title, content, url, l1)
        txt_hash = hashlib.sha256((title + content).encode()).hexdigest()[:16]
        async with acquire() as conn:
            await insert_summary(conn, "article", art_id, "L1", "sentiment_api.summary.article.L1", "1.0",
                settings.model_summarizer_id, "2026-02-01", _dedupe_key(art_id, txt_hash, "1.0", settings.model_summarizer_id), l1)
            await insert_summary(conn, "article", art_id, "L2", "sentiment_api.summary.article.L2", "1.0",
                settings.model_summarizer_id, "2026-02-01", _dedupe_key(art_id, txt_hash, "1.0", settings.model_summarizer_id), l2)
        text_for_embed = f"{title} {content}"[:4000]
        embedding = embed_text(text_for_embed, settings.model_embedding_id)
        async with acquire() as conn:
            await insert_embedding(conn, "article", art_id, settings.model_embedding_id, embedding)
            clusters_data = await get_clusters_for_embedding(conn, limit=500, model_id=settings.model_embedding_id)
        nearest = find_nearest_cluster(embedding, clusters_data, threshold=0.82)
        headline = l2.get("headline_en", title) or title[:200]
        topics = l2.get("topics", []) or ["general"]
        ckey = canonical_story_key(headline, topics)
        first_seen = datetime.now(timezone.utc)
        if nearest:
            cid = nearest
            source_count = 1
            source_urls = [url]
        else:
            cid = cluster_id(ckey, first_seen)
            source_count = 1
            source_urls = [url]
        l3 = summarize_l3(cid, [l2], [{"url": url, "quote_en": (title or content[:200])[:240], "relevance_score": 0.9}])
        ckey_hash = hashlib.sha256(str(l3).encode()).hexdigest()[:16]
        async with acquire() as conn:
            await insert_summary(conn, "cluster", cid, "L3", "sentiment_api.summary.cluster.L3", "1.0",
                settings.model_summarizer_id, "2026-02-01", _dedupe_key(cid, ckey_hash, "1.0", settings.model_summarizer_id), l3)
    except Exception as e:
        if run_id:
            async with acquire() as conn:
                await finish_run(conn, run_id, "fail", {"error": str(e)})
        raise
    imp = score_impact(cid, l3, source_count, "reputable_media")
    tone = l2.get("tone", {"polarity": 0, "subjectivity": 0.5})
    async with acquire() as conn:
        await insert_cluster(
            conn, cid, headline, ckey, topics, l2.get("regions", []),
            source_count, source_urls, tone, imp, imp.get("risk_vector", {})
        )
        await add_cluster_member(conn, cid, art_id)
        await insert_embedding(conn, "cluster", cid, settings.model_embedding_id, embedding)
    event_type = (topics + imp.get("reason_codes", []))[0] if (topics or imp.get("reason_codes")) else "OTHER"
    ev_id = _event_id(cid, event_type)
    async with acquire() as conn:
        await insert_event(
            conn, ev_id, cid, event_type, headline,
            imp.get("expected_direction", "Unknown"), imp.get("horizon", "unknown"),
            imp.get("confidence", 0.5), imp.get("reason_codes", []),
            imp.get("impact_score", 0), imp.get("impact_level", "L0"),
            l2.get("regions"), topics
        )
        await insert_expectation(
            conn, ev_id,
            imp.get("expected_direction", "Unknown"),
            imp.get("impact_score", 0) / 100.0,
            "SPY",
        )
    if run_id:
        async with acquire() as conn:
            await finish_run(conn, run_id, "ok", {"cluster_id": cid, "event_id": ev_id})
    import json
    queue = await get_queue(settings.redis_url)
    await queue.rpush(QUEUE_INDEX, json.dumps({"cluster_id": cid}))


async def process_index(payload: dict) -> None:
    """Update intraday and daily index, measure outcomes."""
    from sentiment_api.engines.outcomes import measure_outcomes
    await compute_intraday_from_clusters("5m")
    from datetime import date
    await compute_daily_ohlc(date.today())
    try:
        await measure_outcomes("SPY")
    except Exception as e:
        logger.debug("Outcomes measurement skipped: %s", e)


async def run_worker() -> None:
    """Main worker loop."""
    settings = get_settings()
    await init_pool(settings.database_url)
    queue_client = await get_queue(settings.redis_url)
    reg = load_registry(settings.source_registry_path)
    async with acquire() as conn:
        sources = [
            {
                "source_id": s.source_id,
                "name": s.name,
                "pack": s.pack,
                "type": s.type,
                "enabled": s.effective_enabled(reg.packs.get(s.pack, type("X", (), {"enabled": True})()).enabled, reg.defaults),
                "credibility": s.credibility_tier or reg.defaults.credibility_tier,
                "license": s.license_class or reg.defaults.license_class,
                "regions": s.regions or [],
                "topics": s.topics or [],
                "config": s.to_db_config(reg.defaults),
            }
            for s in reg.get_enabled_sources()
        ]
        await upsert_sources(conn, sources)
    logger.info("Worker started, synced %d sources", len(sources))
    import json
    while True:
        try:
            result = await queue_client.blpop([QUEUE_INGEST, QUEUE_NORMALIZE, QUEUE_SUMMARIZE, QUEUE_SCORE, QUEUE_INDEX], timeout=5)
            if not result:
                continue
            queue_name, data = result
            payload = json.loads(data) if isinstance(data, str) else data
            if queue_name == QUEUE_SUMMARIZE and "article_id" in payload and "norm" in payload:
                await process_summarize(payload)
            elif queue_name == QUEUE_INDEX and "cluster_id" in payload:
                await process_index(payload)
            elif queue_name == QUEUE_INGEST and "source_id" in payload and "url" in payload:
                await process_ingest(payload)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Worker error: %s", e)
    await close_pool()
