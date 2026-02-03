"""Chunk documents and ingest into Weaviate RetrievalChunk (Tier A vectors + text for BM25)."""

import asyncio
import json
import logging
import uuid as uuid_lib
from dataclasses import dataclass
from typing import Any

from sentiment_api.config import get_settings
from sentiment_api.retrieval.embedding_cache_sqlite import text_hash
from sentiment_api.retrieval.provider import EmbeddingProvider, get_embedding_provider
from sentiment_api.retrieval.tiera_retrieval import (
    _ensure_chunk_collection,
    _get_weaviate_client,
    _tier_a_dim_from_model,
)

logger = logging.getLogger("sentiment_api.retrieval.chunk_ingest")


@dataclass
class ChunkDoc:
    """One document to chunk and ingest. All fields optional except text and doc_id."""

    text: str
    doc_id: str
    source: str = ""
    url: str | None = None
    published_at: str | None = None
    tickers: list[str] | None = None
    sector: str | None = None
    language: str | None = None


def chunk_text(
    text: str,
    max_chars: int = 512,
    overlap_chars: int = 64,
) -> list[str]:
    """
    Split text into overlapping chunks. Deterministic: same text -> same chunks.
    """
    text = (text or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap_chars if end < len(text) else len(text)
    return chunks


def _chunk_id(doc_id: str, index: int) -> str:
    return f"{doc_id}_chunk_{index}"


def _uuid_chunk(doc_id: str, chunk_index: int) -> str:
    return str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, f"retrieval_chunk:{doc_id}:{chunk_index}"))


def _upsert_chunks_sync(
    client,
    class_name: str,
    chunk_objects: list[tuple[dict[str, Any], list[float]]],
) -> int:
    """Sync insert/replace chunk objects. Each item is (properties, vector)."""
    coll = client.collections.get(class_name)
    inserted = 0
    for idx, (props, vec) in enumerate(chunk_objects):
        uid = _uuid_chunk(props.get("doc_id", ""), idx)
        try:
            coll.data.insert(uuid=uid, properties=props, vector=vec)
            inserted += 1
        except Exception as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                coll.data.replace(uuid=uid, properties=props, vector=vec)
                inserted += 1
            else:
                logger.warning("Chunk insert failed doc_id=%s: %s", props.get("doc_id"), e)
    return inserted


async def ingest_chunks_to_weaviate(
    docs: list[ChunkDoc],
    max_chars: int = 512,
    overlap_chars: int = 64,
    provider: EmbeddingProvider | None = None,
) -> int:
    """
    Chunk each doc, embed with Tier A, upsert to Weaviate RetrievalChunk.
    Returns total number of chunks upserted.
    """
    settings = get_settings()
    provider = provider or get_embedding_provider()
    model_id = settings.retrieval_tiera_model_id
    class_name = settings.weaviate_chunk_class or "RetrievalChunk"
    dim = _tier_a_dim_from_model(model_id)

    client = _get_weaviate_client()
    _ensure_chunk_collection(client, class_name, dim)

    all_chunks_props: list[dict[str, Any]] = []
    all_chunks_texts: list[str] = []

    for doc in docs:
        chunks = chunk_text(doc.text, max_chars=max_chars, overlap_chars=overlap_chars)
        tickers_str = json.dumps(doc.tickers or [])
        for i, chunk_text_str in enumerate(chunks):
            cid = _chunk_id(doc.doc_id, i)
            th = text_hash(chunk_text_str)
            all_chunks_props.append({
                "text": chunk_text_str,
                "doc_id": doc.doc_id,
                "source": doc.source or "",
                "url": doc.url or "",
                "published_at": doc.published_at or "",
                "tickers": tickers_str,
                "sector": doc.sector or "",
                "language": doc.language or "",
                "text_hash": th,
                "chunk_id": cid,
            })
            all_chunks_texts.append(chunk_text_str)

    if not all_chunks_texts:
        return 0

    vectors = provider.embed_docs(model_id, all_chunks_texts)
    if len(vectors) != len(all_chunks_props):
        raise ValueError(
            f"embed_docs returned {len(vectors)} vectors for {len(all_chunks_props)} chunks"
        )

    chunk_objects = [(all_chunks_props[i], vectors[i]) for i in range(len(all_chunks_props))]
    inserted = await asyncio.to_thread(
        _upsert_chunks_sync, client, class_name, chunk_objects
    )
    logger.info(
        "chunk_ingest upserted chunks=%s docs=%s class=%s",
        inserted, len(docs), class_name,
        extra={"chunks_upserted": inserted, "docs_count": len(docs)},
    )
    return inserted
