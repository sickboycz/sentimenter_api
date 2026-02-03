"""Optional cross-encoder rerank: score(query, doc_text) -> float. No-op by default."""

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("sentiment_api.retrieval.cross_encoder")


@runtime_checkable
class CrossEncoder(Protocol):
    """Interface for cross-encoder / reranker: score (query, doc_text) -> float."""

    def score(self, query: str, doc_text: str) -> float:
        """Return relevance score in [0, 1]. Raises on failure (no silent fallback)."""
        ...


class NoOpCrossEncoder:
    """No-op cross-encoder: always returns 0.0. Use when no reranker model is configured."""

    def score(self, query: str, doc_text: str) -> float:
        return 0.0


class SentenceTransformerCrossEncoder:
    """Sentence-transformers CrossEncoder: score(query, doc_text) -> [0, 1] via sigmoid."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import CrossEncoder as STCrossEncoder
        self._model = STCrossEncoder(model_name)

    def score(self, query: str, doc_text: str) -> float:
        pair = [query[:8000], (doc_text or "")[:4000]]
        scores = self._model.predict([pair])
        raw = float(scores[0])
        return max(0.0, min(1.0, 1.0 / (1.0 + (2.71828 ** -raw))))


_cross_encoder_instance: CrossEncoder | None = None


def get_cross_encoder(use_noop: bool = False) -> CrossEncoder:
    """Return cross-encoder implementation. Uses CROSS_ENCODER_MODEL when set and use_noop=False."""
    global _cross_encoder_instance
    if use_noop:
        return NoOpCrossEncoder()
    from sentiment_api.config import get_settings
    model = get_settings().cross_encoder_model
    if not model or not model.strip():
        return NoOpCrossEncoder()
    if _cross_encoder_instance is None:
        try:
            _cross_encoder_instance = SentenceTransformerCrossEncoder(model.strip())
            logger.info("Cross-encoder loaded: %s", model)
        except Exception as e:
            logger.warning("Cross-encoder init failed (%s), falling back to NoOp: %s", model, e)
            return NoOpCrossEncoder()
    return _cross_encoder_instance
