"""2-tier retrieval: Tier A (hybrid) candidate retrieval + Tier B rerank with cache."""

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
    "ScoreBreakdown",
    "SearchResult",
    "SearchTrace",
    "EmbeddingProvider",
    "get_embedding_provider",
    "run_advanced_search",
]
