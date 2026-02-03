"""2-tier retrieval pipeline: Tier A hybrid -> Tier B rerank -> optional cross-encoder, trace + score breakdown."""

import logging
import uuid
from typing import Any

from sentiment_api.config import get_settings
from sentiment_api.retrieval.cross_encoder import CrossEncoder, get_cross_encoder
from sentiment_api.retrieval.embedding_cache_sqlite import EmbeddingCacheSqlite
from sentiment_api.retrieval.models import SearchResult, SearchTrace
from sentiment_api.retrieval.provider import EmbeddingProvider, get_embedding_provider
from sentiment_api.retrieval.tiera_retrieval import retrieve_candidates_async
from sentiment_api.retrieval.tierb_rerank import _parse_weights, rerank_with_tierb_async

logger = logging.getLogger("sentiment_api.retrieval.pipeline")


async def run_advanced_search(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_n: int | None = None,
    rerank_n: int | None = None,
    alpha: float | None = None,
    weights: dict[str, float] | None = None,
    provider: EmbeddingProvider | None = None,
    cache: EmbeddingCacheSqlite | None = None,
    cross_encoder: CrossEncoder | None = None,
    trace_id: str | None = None,
) -> tuple[list[SearchResult], SearchTrace]:
    """
    Run 2-tier pipeline: Q1 Tier A hybrid -> Q2 Tier B rerank -> Q3 optional cross-encoder on top M.
    Returns (results, trace).
    """
    settings = get_settings()
    tid = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    filters = filters or {}
    top_n = top_n if top_n is not None else settings.retrieval_topn
    rerank_n = rerank_n if rerank_n is not None else settings.retrieval_rerankn
    alpha = alpha if alpha is not None else settings.retrieval_alpha
    weights = weights or _parse_weights(settings.retrieval_weights)
    provider = provider or get_embedding_provider()
    cache = cache or EmbeddingCacheSqlite(settings.embedding_cache_path)
    w_cross = weights.get("cross", 0) or 0
    use_real_cross = w_cross > 0 and bool(getattr(settings, "cross_encoder_model", None) or "").strip()
    cross_enc = cross_encoder if cross_encoder is not None else get_cross_encoder(use_noop=not use_real_cross)
    cross_top_m = getattr(settings, "retrieval_cross_top_m", 20) or 0

    trace = SearchTrace(
        trace_id=tid,
        filter_summary=filters,
        model_tiera=settings.retrieval_tiera_model_id,
        model_tierb=settings.retrieval_tierb_model_id,
    )

    # Q1: Tier A hybrid
    candidates, latency_tiera_ms = await retrieve_candidates_async(
        query_text=query_text,
        filters=filters,
        top_n=top_n,
        alpha=alpha,
        provider=provider,
        trace_id=tid,
    )
    trace.candidate_count = len(candidates)
    trace.latency_tiera_ms = latency_tiera_ms

    if not candidates:
        logger.info("advanced_search trace_id=%s candidate_count=0", tid, extra={"trace_id": tid})
        return [], trace

    # Q2: Tier B rerank; Q3: optional cross-encoder on top M
    results, latency_tierb_ms, cache_hits, cache_misses, latency_cross_ms = await rerank_with_tierb_async(
        query_text=query_text,
        candidates=candidates,
        top_n=rerank_n,
        weights=weights,
        provider=provider,
        cache=cache,
        cross_encoder=cross_enc,
        cross_top_m=cross_top_m,
        trace_id=tid,
    )
    trace.rerank_count = len(results)
    trace.latency_tierb_ms = latency_tierb_ms
    trace.latency_cross_ms = latency_cross_ms
    trace.cache_hit_count = cache_hits
    trace.cache_miss_count = cache_misses

    logger.info(
        "advanced_search trace_id=%s candidate_count=%s rerank_count=%s cache_hits=%s cache_misses=%s tiera_ms=%.2f tierb_ms=%.2f",
        tid, trace.candidate_count, trace.rerank_count, trace.cache_hit_count, trace.cache_miss_count,
        trace.latency_tiera_ms, trace.latency_tierb_ms,
        extra={
            "trace_id": tid,
            "candidate_count": trace.candidate_count,
            "rerank_count": trace.rerank_count,
            "cache_hit_count": trace.cache_hit_count,
            "cache_miss_count": trace.cache_miss_count,
            "latency_tiera_ms": trace.latency_tiera_ms,
            "latency_tierb_ms": trace.latency_tierb_ms,
        },
    )
    return results, trace
