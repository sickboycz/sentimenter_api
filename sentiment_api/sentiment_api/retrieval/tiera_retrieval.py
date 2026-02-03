"""Tier A: Weaviate hybrid (vector + BM25) candidate retrieval for 2-tier pipeline."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from sentiment_api.config import get_settings
from sentiment_api.retrieval.embedding_cache_sqlite import text_hash
from sentiment_api.retrieval.models import Candidate
from sentiment_api.retrieval.provider import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger("sentiment_api.retrieval.tiera")


def _tier_a_dim_from_model(model_id: str) -> int:
    """Infer Tier A vector dimension from model_id (384 or 768)."""
    return 384 if "384" in (model_id or "") else 768


def _get_weaviate_client():
    """Shared Weaviate client (same connection as vector_store)."""
    from sentiment_api.vector_store.weaviate_client import WeaviateVectorStore
    store = WeaviateVectorStore()
    return store._get_client()


def _ensure_chunk_collection(client, class_name: str, dim: int):
    """Create RetrievalChunk collection if not exists: self-provided vector + text for BM25."""
    from weaviate.classes.config import Configure, Property, DataType
    if client.collections.exists(class_name):
        return
    client.collections.create(
        name=class_name,
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),  # BM25 target
            Property(name="doc_id", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
            Property(name="url", data_type=DataType.TEXT),
            Property(name="published_at", data_type=DataType.TEXT),
            Property(name="tickers", data_type=DataType.TEXT),  # JSON array string
            Property(name="sector", data_type=DataType.TEXT),
            Property(name="language", data_type=DataType.TEXT),
            Property(name="text_hash", data_type=DataType.TEXT),
            Property(name="chunk_id", data_type=DataType.TEXT),
        ],
    )
    logger.info("Created Weaviate collection %s (dim=%s)", class_name, dim)


def retrieve_candidates(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_n: int = 200,
    alpha: float = 0.5,
    provider: EmbeddingProvider | None = None,
    trace_id: str | None = None,
) -> tuple[list[Candidate], float]:
    """
    Tier A hybrid retrieval: embed query with tierA, Weaviate hybrid (vector + BM25).
    Returns (candidates, latency_tiera_ms).
    """
    settings = get_settings()
    tid = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
    provider = provider or get_embedding_provider()
    model_id = settings.retrieval_tiera_model_id
    class_name = settings.weaviate_chunk_class or "RetrievalChunk"
    filters = filters or {}

    tier_a_dim = _tier_a_dim_from_model(model_id)
    t0 = time.perf_counter()
    try:
        client = _get_weaviate_client()
        _ensure_chunk_collection(client, class_name, tier_a_dim)
        coll = client.collections.get(class_name)

        # Embed query with Tier A
        query_vec = provider.embed_query(model_id, query_text[:8000])

        # Weaviate v4 hybrid: query (BM25) + vector (tierA), alpha
        from weaviate.classes.query import Filter, MetadataQuery

        wvc_filter = None
        if filters:
            conditions = []
            if "sources" in filters and filters["sources"]:
                src = filters["sources"][0] if isinstance(filters["sources"], list) else filters["sources"]
                conditions.append(Filter.by_property("source").equal(str(src)))
            if "language" in filters and filters["language"]:
                conditions.append(Filter.by_property("language").equal(str(filters["language"])))
            if "published_after" in filters and filters["published_after"]:
                conditions.append(Filter.by_property("published_at").greater_or_equal(str(filters["published_after"])))
            if "published_before" in filters and filters["published_before"]:
                conditions.append(Filter.by_property("published_at").less_or_equal(str(filters["published_before"])))
            if "tickers" in filters and filters["tickers"]:
                tickers = filters["tickers"]
                one = (tickers[0] if isinstance(tickers, list) else tickers).strip()
                if one:
                    conditions.append(Filter.by_property("tickers").like(f"%{one}%"))
            if conditions:
                wvc_filter = conditions[0]
                for c in conditions[1:]:
                    wvc_filter = wvc_filter & c

        response = coll.query.hybrid(
            query=query_text[:8000],
            vector=query_vec,
            alpha=alpha,
            limit=top_n,
            return_metadata=MetadataQuery(score=True, explain_score=True),
            filters=wvc_filter,
        )

        candidates = []
        for obj in response.objects:
            props = obj.properties or {}
            bm25_score = 0.0
            vector_score = 0.0
            if obj.metadata and hasattr(obj.metadata, "score"):
                vector_score = float(obj.metadata.score or 0.0)
            if obj.metadata and getattr(obj.metadata, "explain_score", None):
                try:
                    expl = obj.metadata.explain_score
                    if isinstance(expl, str):
                        import json as _json
                        expl = _json.loads(expl) if expl else {}
                    if isinstance(expl, dict):
                        bm25_score = float(expl.get("bm25", {}).get("score", 0) or 0)
                except Exception:
                    pass
            # Fused score from Weaviate as tier_a_score
            tier_a_score = float(getattr(obj.metadata, "score", 0) or 0.0)
            tickers = props.get("tickers") or "[]"
            if isinstance(tickers, str):
                try:
                    tickers = json.loads(tickers)
                except Exception:
                    tickers = []
            candidates.append(
                Candidate(
                    chunk_id=props.get("chunk_id", str(obj.uuid)),
                    text=props.get("text", ""),
                    doc_id=props.get("doc_id", ""),
                    source=props.get("source", ""),
                    url=props.get("url"),
                    published_at=props.get("published_at"),
                    tickers=tickers if isinstance(tickers, list) else [],
                    sector=props.get("sector"),
                    language=props.get("language"),
                    text_hash=props.get("text_hash", ""),
                    tier_a_score=tier_a_score,
                    bm25_score=bm25_score,
                    metadata={"weaviate_uuid": str(obj.uuid)},
                )
            )
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "tiera_retrieval trace_id=%s candidate_count=%s latency_ms=%.2f filter_summary=%s",
            tid, len(candidates), latency_ms, filters,
            extra={"trace_id": tid, "candidate_count": len(candidates), "latency_tiera_ms": latency_ms},
        )
        return candidates, latency_ms
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.exception(
            "tiera_retrieval failed trace_id=%s error=%s",
            tid, e,
            extra={"trace_id": tid, "error": str(e)},
        )
        raise


async def retrieve_candidates_async(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_n: int = 200,
    alpha: float = 0.5,
    provider: EmbeddingProvider | None = None,
    trace_id: str | None = None,
) -> tuple[list[Candidate], float]:
    """Async wrapper: run Tier A retrieval in thread (Weaviate client is sync)."""
    return await asyncio.to_thread(
        retrieve_candidates,
        query_text,
        filters,
        top_n,
        alpha,
        provider,
        trace_id,
    )
