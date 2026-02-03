"""Worker: process queue jobs (ingest -> normalize -> cluster -> summarize -> score -> index)."""

import asyncio
import hashlib
import base64
import json
import logging
import os
import socket
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
    get_article_needing_summarize,
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
from sentiment_api.queue.client import get_queue, get_queue_lengths, QUEUE_INGEST, QUEUE_NORMALIZE, QUEUE_SUMMARIZE, QUEUE_SCORE, QUEUE_INDEX
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
_WORKER_KEY_PREFIX = "sentiment_api:ops:worker:"
_HEARTBEAT_INTERVAL_SEC = 5
_HEARTBEAT_TTL_SEC = 30
_WORKER_KEY_TTL_SEC = 45

# Per-worker state for ops UI (worker list + work assignment). Set in run_worker().
_worker_id: str | None = None
_worker_state: dict = {}

# Order used when queue_work_division is False; when True, worker polls by descending queue length
WORKER_QUEUES = [QUEUE_SUMMARIZE, QUEUE_INDEX, QUEUE_SCORE, QUEUE_INGEST, QUEUE_NORMALIZE]


def _get_worker_id() -> str:
    """Stable worker id for this process (env WORKER_ID or hostname-pid)."""
    raw = os.environ.get("WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
    return raw.replace(" ", "_").replace(":", "_")


async def _heartbeat_loop(queue_client) -> None:
    """Keep a short-lived heartbeat in Redis so ops UI can detect liveness; also write per-worker key for worker list."""
    global _worker_id, _worker_state
    while True:
        try:
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            await queue_client.set(_HEARTBEAT_KEY, now, ex=_HEARTBEAT_TTL_SEC)
            if _worker_id:
                _worker_state["last_seen"] = now
                key = f"{_WORKER_KEY_PREFIX}{_worker_id}"
                await queue_client.set(key, json.dumps(_worker_state), ex=_WORKER_KEY_TTL_SEC)
        except Exception as ex:
            logger.debug("Worker heartbeat update failed: %s", ex)
        await asyncio.sleep(_HEARTBEAT_INTERVAL_SEC)


def _queue_short_name(queue_name: str) -> str:
    """Redis queue name to stage key for weights (e.g. sentiment_api:ingest -> ingest)."""
    if ":" in queue_name:
        return queue_name.split(":", 1)[1]
    return queue_name


_WORKERS_ON_QUEUE_AGE_SEC = 90  # treat worker as "on queue" if last_job was within this age


async def _get_workers_per_queue(queue_client) -> tuple[dict[str, int], int]:
    """Return (per-queue count of workers on that queue, total worker count). Workers counted if last_seen within _WORKERS_ON_QUEUE_AGE_SEC."""
    now = datetime.now(timezone.utc)
    keys = await queue_client.keys(f"{_WORKER_KEY_PREFIX}*") or []
    counts: dict[str, int] = {}
    for key in keys:
        try:
            raw = await queue_client.get(key)
            if not raw:
                continue
            payload = json.loads(raw)
            last_seen_str = payload.get("last_seen")
            if not last_seen_str:
                continue
            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            if (now - last_seen).total_seconds() > _WORKERS_ON_QUEUE_AGE_SEC:
                continue
            q = payload.get("last_job", {}).get("queue")
            if q:
                counts[q] = counts.get(q, 0) + 1
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return counts


def _resolve_caps_for_worker_count(settings, current_workers: int) -> dict[str, int]:
    """Caps to use: from queue_stage_caps_by_workers for current_workers (nearest <= count), else queue_stage_caps."""
    by_workers = getattr(settings, "queue_stage_caps_by_workers", None) or {}
    if not by_workers:
        return getattr(settings, "queue_stage_caps", None) or {}
    # Use largest N such that N <= current_workers (e.g. 7 workers -> profile 7; 6 -> 6)
    best_n = max((n for n in by_workers if n <= current_workers), default=None)
    if best_n is not None:
        return by_workers[best_n]
    # Fewer workers than smallest profile (e.g. 4 workers, profiles start at 6): use smallest profile
    return by_workers[min(by_workers)]


async def _poll_order_by_depth(queue_client, settings) -> list[str]:
    """Return queue names ordered by weighted depth, respecting stage caps so we get flow.
    When there's no work at a level (depth 0), priority is low so workers take other work; when work appears they go back.
    Only consider queues where current workers on queue < cap; then sort by (depth * stage_weight) descending."""
    lengths = await get_queue_lengths(queue_client, WORKER_QUEUES)
    workers_on, current_workers = await _get_workers_per_queue(queue_client)
    caps = _resolve_caps_for_worker_count(settings, current_workers)
    weights = getattr(settings, "queue_stage_weights", None) or {}

    def priority(q: str) -> tuple:
        depth = lengths.get(q, 0)
        w = weights.get(_queue_short_name(q), 1)
        return (-(depth * w), WORKER_QUEUES.index(q))

    # Only queues where we're under cap (or no cap set for that stage). Empty queues stay in list so workers can take other work.
    candidates = [
        q for q in WORKER_QUEUES
        if workers_on.get(q, 0) < caps.get(_queue_short_name(q), 999)
    ]
    return sorted(candidates, key=priority)


async def _record_job(queue_client, queue_name: str) -> None:
    """Record last job metadata + per-queue counters for ops UI (legacy keys + per-worker key)."""
    global _worker_id, _worker_state
    try:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        await queue_client.hset(_LAST_JOB_KEY, mapping={"queue": queue_name, "at": now})
        await queue_client.hincrby(_COUNTS_KEY, queue_name, 1)
        if _worker_id:
            _worker_state["last_job"] = {"queue": queue_name, "at": now}
            _worker_state["counts"] = _worker_state.get("counts") or {}
            _worker_state["counts"][queue_name] = _worker_state["counts"].get(queue_name, 0) + 1
            key = f"{_WORKER_KEY_PREFIX}{_worker_id}"
            await queue_client.set(key, json.dumps(_worker_state), ex=_WORKER_KEY_TTL_SEC)
    except Exception as ex:
        logger.debug("Worker job record failed: %s", ex)


def _event_id(cluster_id: str, event_type: str) -> str:
    h = hashlib.sha256(f"{cluster_id}|{event_type}|{datetime.now(timezone.utc).isoformat()[:10]}".encode()).digest()[:12]
    return f"evt_{base64.urlsafe_b64encode(h).decode().rstrip('=').lower()}"


async def process_ingest(payload: dict) -> None:
    """Receive raw item, normalize, dedupe, insert article, push to summarize."""
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
        # Duplicate: auto-push to summarize if article exists but has no L2 (fixes backlog)
        async with acquire() as conn:
            payload = await get_article_needing_summarize(conn, art_id, norm["canonical_url"])
        if payload:
            await queue.rpush(QUEUE_SUMMARIZE, json.dumps(payload, cls=_DateTimeEncoder))
            logger.info("Ingest: article %s duplicate but missing L2, pushed to summarize", payload["article_id"])
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
    async with acquire() as conn:
        has_l2 = await conn.fetchval(
            "SELECT 1 FROM summaries WHERE object_type = 'article' AND object_id = $1 AND level = 'L2' LIMIT 1",
            art_id,
        )
    if has_l2:
        logger.debug("Summarize: article %s already has L2, skipping", art_id)
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
            clusters_data = await get_clusters_for_embedding(conn, limit=200, model_id=settings.model_embedding_id)
        nearest, best_sim = find_nearest_cluster(embedding, clusters_data, threshold=settings.cluster_similarity_threshold)
        if nearest:
            logger.info("Summarize: article %s embed done, clusters=%d merged into %s (sim=%.3f)", art_id, len(clusters_data), nearest, best_sim)
        else:
            logger.info("Summarize: article %s embed done, clusters=%d new cluster (best_sim=%.3f)", art_id, len(clusters_data), best_sim)
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
    global _worker_id, _worker_state
    _worker_id = _get_worker_id()
    _worker_state = {"last_seen": None, "last_job": {}, "counts": {}}
    from sentiment_api.debug_bootstrap import run as _debug_bootstrap_run
    _debug_bootstrap_run()
    settings = get_settings()
    await init_pool(settings.database_url)
    await _verify_db_connection()
    queue_client = await get_queue(settings.redis_url)
    # Register worker in Redis immediately so ops UI shows worker list before first heartbeat
    if _worker_id:
        _worker_state["last_seen"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        await queue_client.set(f"{_WORKER_KEY_PREFIX}{_worker_id}", json.dumps(_worker_state), ex=_WORKER_KEY_TTL_SEC)
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
    try:
        while True:
            try:
                # Work division: when enabled, poll by weighted depth (more workers at earlier stages); else use fixed order
                if settings.queue_work_division:
                    poll_order = await _poll_order_by_depth(queue_client, settings)
                else:
                    poll_order = WORKER_QUEUES
                result = await queue_client.blpop(poll_order, timeout=5)
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
