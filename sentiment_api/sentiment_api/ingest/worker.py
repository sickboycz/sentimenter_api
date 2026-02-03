"""Worker: process queue jobs (ingest -> normalize -> cluster -> summarize -> score -> index)."""

import asyncio
import hashlib
import base64
import json
import logging
from datetime import datetime, timezone, date

from sentiment_api.config import get_settings


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime/date objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)
from sentiment_api.db.pool import init_pool, close_pool, acquire
from sentiment_api.db.repo import (
    upsert_sources,
    insert_article,
    insert_article_body,
    insert_cluster,
    add_cluster_member,
    insert_embedding,
    insert_event,
    insert_event_impacts,
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

try:
    from sentiment_api.logging_file import add_file_handler
    add_file_handler("worker")
except Exception as ex:
    logger.debug("Worker file handler setup skipped: %s", ex)

_HEARTBEAT_KEY = "sentiment_api:ops:worker_heartbeat"
_LAST_JOB_KEY = "sentiment_api:ops:worker_last_job"
_COUNTS_KEY = "sentiment_api:ops:worker_counts"
_HEARTBEAT_INTERVAL_SEC = 5
_HEARTBEAT_TTL_SEC = 30


async def _heartbeat_loop(queue_client) -> None:
    """Keep a short-lived heartbeat in Redis so ops UI can detect liveness."""
    while True:
        try:
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            await queue_client.set(_HEARTBEAT_KEY, now, ex=_HEARTBEAT_TTL_SEC)
        except Exception as ex:
            logger.debug("Worker heartbeat update failed: %s", ex)
        await asyncio.sleep(_HEARTBEAT_INTERVAL_SEC)


async def _record_job(queue_client, queue_name: str) -> None:
    """Record last job metadata + per-queue counters for ops UI."""
    try:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        await queue_client.hset(_LAST_JOB_KEY, mapping={"queue": queue_name, "at": now})
        await queue_client.hincrby(_COUNTS_KEY, queue_name, 1)
    except Exception as ex:
        logger.debug("Worker job record failed: %s", ex)


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
    except Exception as ex:
        logger.warning("Ingest insert_run failed (continuing): %s", ex)
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
        await queue.rpush(QUEUE_SUMMARIZE, json.dumps({"article_id": art_id, "source_id": norm["source_id"], "norm": norm}, cls=_DateTimeEncoder))
        logger.info("Ingest: article %s inserted, pushed to summarize", art_id)
    else:
        logger.debug("Ingest: article %s duplicate, skipped summarize", art_id)


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
        logger.warning("Summarize: skipping job (missing article_id or norm): art_id=%s has_norm=%s", art_id, bool(norm))
        return
    title = norm.get("title_en", "")
    content = norm.get("content_en", "")
    url = norm.get("url", "")
    pub = norm.get("published_at")
    pub_str = pub.isoformat() if hasattr(pub, "isoformat") else str(pub) if pub else ""
    run_id = None
    async with acquire() as conn:
        run_id = await insert_run(conn, "summarize", art_id, {"article_id": art_id})
    logger.info("Summarize: starting article %s (title_len=%d content_len=%d)", art_id, len(title), len(content))
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
        logger.info("Summarize: article %s embed done, clusters=%d nearest=%s", art_id, len(clusters_data), nearest or "new")
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
    try:
        async with acquire() as conn:
            await insert_cluster(
                conn, cid, headline, ckey, topics, l2.get("regions", []),
                source_count, source_urls, tone, imp, imp.get("risk_vector", {})
            )
            await add_cluster_member(conn, cid, art_id)
            await insert_embedding(conn, "cluster", cid, settings.model_embedding_id, embedding)
    except Exception as e:
        logger.exception("Clustering DB error (insert_cluster/add_cluster_member/insert_embedding): %s", e)
        raise
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
        # M5.5: Asset targeting + event_impacts for L2+
        level = imp.get("impact_level", "L0")
        if level not in ("L0", "L1"):
            try:
                from sentiment_api.engines.asset_targeting import get_asset_impacts_for_cluster, _bundle_to_event_impacts, persist_asset_targeting_audit
                bundle = await get_asset_impacts_for_cluster(cid, limit_tickers=30, limit_sectors=11)
                await persist_asset_targeting_audit(cid, bundle)
                impacts = _bundle_to_event_impacts(bundle, cid)
                await insert_event_impacts(conn, ev_id, impacts)
            except Exception as ex:
                logger.debug("Asset targeting skipped: %s", ex)
    if run_id:
        async with acquire() as conn:
            await finish_run(conn, run_id, "ok", {"cluster_id": cid, "event_id": ev_id})
    import json
    queue = await get_queue(settings.redis_url)
    await queue.rpush(QUEUE_INDEX, json.dumps({"cluster_id": cid}))
    logger.info("Summarize: cluster %s created for article %s, pushed to index", cid, art_id)


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


async def _verify_db_connection() -> None:
    """Verify DB is reachable and clustering tables exist. Raises on failure."""
    async with acquire() as conn:
        await conn.fetchval("SELECT 1")
        has_clusters = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'clusters')"
        )
        has_embeddings = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'embeddings')"
        )
        if not has_clusters or not has_embeddings:
            raise RuntimeError(
                "Clustering tables missing: clusters=%s embeddings=%s. Run DB migrations."
                % (has_clusters, has_embeddings)
            )
    logger.info("DB connection OK (clusters and embeddings tables present)")


async def run_worker() -> None:
    """Main worker loop."""
    settings = get_settings()
    await init_pool(settings.database_url)
    await _verify_db_connection()
    queue_client = await get_queue(settings.redis_url)
    heartbeat_task = asyncio.create_task(_heartbeat_loop(queue_client))
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
    try:
        while True:
            try:
                # Prefer downstream queues so summarize/cluster/embed run; otherwise ingest starves them
                result = await queue_client.blpop([QUEUE_SUMMARIZE, QUEUE_INDEX, QUEUE_SCORE, QUEUE_INGEST, QUEUE_NORMALIZE], timeout=5)
                if not result:
                    continue
                queue_name, data = result
                await _record_job(queue_client, queue_name)
                try:
                    if isinstance(data, bytes):
                        payload = json.loads(data.decode("utf-8"))
                    elif isinstance(data, str):
                        payload = json.loads(data)
                    else:
                        payload = data
                except json.JSONDecodeError as e:
                    logger.warning("Malformed queue payload (JSON decode failed): %s", e)
                    continue
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
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except Exception as ex:
            logger.debug("Worker heartbeat task cancel: %s", ex)
        await close_pool()
