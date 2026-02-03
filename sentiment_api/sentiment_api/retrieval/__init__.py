"""2-tier retrieval: Tier A (hybrid) candidate retrieval + Tier B rerank + optional cross-encoder; chunk ingest."""

from sentiment_api.retrieval.chunk_ingest import ChunkDoc, chunk_text, ingest_chunks_to_weaviate
from sentiment_api.retrieval.cross_encoder import CrossEncoder, NoOpCrossEncoder, get_cross_encoder
from sentiment_api.retrieval.models import (
    Candidate,
    ScoreBreakdown,
    SearchResult,
    SearchTrace,
)
from sentiment_api.retrieval.provider import EmbeddingProvider, get_embedding_provider
from sentiment_api.retrieval.pipeline import run_advanced_search

__all__ = [
    "Candidate",
    "ChunkDoc",
    "ScoreBreakdown",
    "SearchResult",
    "SearchTrace",
    "CrossEncoder",
    "NoOpCrossEncoder",
    "get_cross_encoder",
    "EmbeddingProvider",
    "get_embedding_provider",
    "run_advanced_search",
    "chunk_text",
    "ingest_chunks_to_weaviate",
]
