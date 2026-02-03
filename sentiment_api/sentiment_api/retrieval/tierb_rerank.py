"""Tier B: re-embed query + candidates with high-dim model, cache, cosine rerank; optional cross-encoder."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import numpy as np

from sentiment_api.config import get_settings
from sentiment_api.retrieval.embedding_cache_sqlite import EmbeddingCacheSqlite, text_hash
from sentiment_api.retrieval.models import Candidate, ScoreBreakdown, SearchResult
from sentiment_api.retrieval.provider import EmbeddingProvider, get_embedding_provider
from sentiment_api.retrieval.cross_encoder import CrossEncoder, NoOpCrossEncoder

logger = logging.getLogger("sentiment_api.retrieval.tierb")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Deterministic cosine similarity [0, 1] (assume non-negative or normalized)."""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def rerank_with_tierb(
    query_text: str,
    candidates: list[Candidate],
    top_n: int = 80,
    weights: dict[str, float] | None = None,
    provider: EmbeddingProvider | None = None,
    cache: EmbeddingCacheSqlite | None = None,
    cross_encoder: CrossEncoder | None = None,
    cross_top_m: int = 20,
    trace_id: str | None = None,
) -> tuple[list[SearchResult], float, int, int, float]:
    """
    Re-embed query with tierB; for each candidate get cached or embed tierB vector; cosine rerank.
    Optionally run cross-encoder on top M and fold into final score.
    Returns (results, latency_tierb_ms, cache_hits, cache_misses, latency_cross_ms).
    """
    settings = get_settings()
    tid = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    provider = provider or get_embedding_provider()
    cache = cache or EmbeddingCacheSqlite(settings.embedding_cache_path)
    model_id = settings.retrieval_tierb_model_id
    weights = weights or _parse_weights(settings.retrieval_weights)
    w_a = weights.get("tierA", 0.2)
    w_bm25 = weights.get("bm25", 0.2)
    w_b = weights.get("tierB", 0.6)
    w_cross = weights.get("cross", 0.0)

    hit_before, miss_before = cache.get_stats()
    t0 = time.perf_counter()

    # Query tierB embedding
    query_vec_b = provider.embed_query(model_id, query_text[:8000])

    # Candidate tierB vectors: resolve cache, then batch-embed misses to reduce API overhead
    need_embed: list[tuple[int, Candidate, str]] = []  # (candidate_index, candidate, text_hash)
    doc_vectors_b: list[list[float]] = [None] * len(candidates)  # type: ignore[list-item]
    for i, c in enumerate(candidates):
        th = c.text_hash or text_hash(c.text)
        cached = cache.get_cached_vector(model_id, th)
        if cached is not None:
            doc_vectors_b[i] = cached
        else:
            need_embed.append((i, c, th))

    if need_embed:
        texts_to_embed = [c.text for _, c, _ in need_embed]
        t_embed_start = time.perf_counter()
        vectors_batch = provider.embed_docs(model_id, texts_to_embed)
        embed_elapsed_ms = (time.perf_counter() - t_embed_start) * 1000
        logger.debug(
            "tierb_rerank trace_id=%s batch_embed count=%s latency_ms=%.2f",
            tid, len(vectors_batch), embed_elapsed_ms,
            extra={"trace_id": tid, "batch_embed_count": len(vectors_batch), "embed_latency_ms": embed_elapsed_ms},
        )
        for (idx, c, th), vec in zip(need_embed, vectors_batch):
            cache.put_cached_vector(model_id, th, vec)
            doc_vectors_b[idx] = vec

    # All slots filled (cache or batch). Tier B scores (cosine)
    assert all(doc_vectors_b[i] is not None for i in range(len(candidates)))
    doc_vecs: list[list[float]] = [doc_vectors_b[i] for i in range(len(candidates))]

    # Tier B scores (cosine)
    tier_b_scores = [cosine_similarity(query_vec_b, dv) for dv in doc_vecs]

    # Combined score: w_a * tier_a + w_bm25 * bm25 + w_b * tier_b (+ w_cross * cross)
    combined = []
    for i, c in enumerate(candidates):
        tb = tier_b_scores[i]
        ta = max(0.0, min(1.0, c.tier_a_score))
        bm = max(0.0, min(1.0, c.bm25_score))
        final = w_a * ta + w_bm25 * bm + w_b * tb + w_cross * 0.0
        combined.append((final, c, ScoreBreakdown(tier_a=ta, bm25=bm, tier_b=tb, cross=0.0, final=final)))
    combined.sort(key=lambda x: -x[0])
    top = combined[:top_n]

    # Q3 (optional): cross-encoder on top M
    cross_enc = cross_encoder if cross_encoder is not None else NoOpCrossEncoder()
    latency_cross_ms = 0.0
    if cross_top_m > 0 and w_cross > 0 and len(top) > 0:
        t_cross_start = time.perf_counter()
        m = min(cross_top_m, len(top))
        cross_scored: list[tuple[float, Candidate, ScoreBreakdown]] = []
        for final, c, breakdown in top[:m]:
            cross_s = cross_enc.score(query_text[:8000], (c.text or "")[:4000])
            new_final = breakdown.final + w_cross * max(0.0, min(1.0, cross_s))
            new_breakdown = ScoreBreakdown(
                tier_a=breakdown.tier_a,
                bm25=breakdown.bm25,
                tier_b=breakdown.tier_b,
                cross=cross_s,
                final=new_final,
            )
            cross_scored.append((new_final, c, new_breakdown))
        cross_scored.sort(key=lambda x: -x[0])
        top = cross_scored + list(top[m:])
        latency_cross_ms = (time.perf_counter() - t_cross_start) * 1000
        logger.debug(
            "tierb_rerank cross_encoder trace_id=%s top_m=%s latency_ms=%.2f",
            tid, m, latency_cross_ms,
            extra={"trace_id": tid, "cross_top_m": m, "latency_cross_ms": latency_cross_ms},
        )

    results = [
        SearchResult(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            snippet=(c.text or "")[:500],
            score_breakdown=breakdown,
            metadata=c.metadata,
        )
        for _, c, breakdown in top
    ]

    latency_ms = (time.perf_counter() - t0) * 1000
    hit_after, miss_after = cache.get_stats()
    cache_hits = hit_after - hit_before
    cache_misses = miss_after - miss_before

    logger.info(
        "tierb_rerank trace_id=%s rerank_count=%s cache_hits=%s cache_misses=%s latency_ms=%.2f",
        tid, len(results), cache_hits, cache_misses, latency_ms,
        extra={
            "trace_id": tid,
            "rerank_count": len(results),
            "cache_hit_count": cache_hits,
            "cache_miss_count": cache_misses,
            "latency_tierb_ms": latency_ms,
        },
    )
    return results, latency_ms, cache_hits, cache_misses, latency_cross_ms


def _parse_weights(raw: str) -> dict[str, float]:
    try:
        d = json.loads(raw)
        return {k: float(v) for k, v in d.items()}
    except (TypeError, json.JSONDecodeError, ValueError):
        return {"tierA": 0.2, "bm25": 0.2, "tierB": 0.6, "cross": 0.0}


async def rerank_with_tierb_async(
    query_text: str,
    candidates: list[Candidate],
    top_n: int = 80,
    weights: dict[str, float] | None = None,
    provider: EmbeddingProvider | None = None,
    cache: EmbeddingCacheSqlite | None = None,
    cross_encoder: CrossEncoder | None = None,
    cross_top_m: int = 20,
    trace_id: str | None = None,
) -> tuple[list[SearchResult], float, int, int, float]:
    """Async wrapper for rerank_with_tierb (run in thread)."""
    return await asyncio.to_thread(
        rerank_with_tierb,
        query_text,
        candidates,
        top_n,
        weights,
        provider,
        cache,
        cross_encoder,
        cross_top_m,
        trace_id,
    )
