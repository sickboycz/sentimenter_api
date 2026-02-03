"""Embedding provider abstraction for Tier A (cheap) and Tier B (expensive) models."""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Protocol, runtime_checkable

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.retrieval.provider")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for embedding: query and docs, deterministic error model."""

    def embed_query(self, model_id: str, text: str) -> list[float]:
        """Embed single query text. Raises on failure (no silent fallback)."""
        ...

    def embed_docs(self, model_id: str, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts (batch). Returns list of vectors in same order."""
        ...


def _normalize_text_for_hash(text: str) -> str:
    """Normalize text for hashing: strip, collapse whitespace."""
    return " ".join((text or "").strip().split())


def get_embedding_provider(use_fake: bool = False) -> EmbeddingProvider:
    """Return the embedding provider (real or fake for tests)."""
    if use_fake:
        return FakeEmbeddingProvider()
    return RealEmbeddingProvider()


class RealEmbeddingProvider:
    """Real provider: OpenAI or sentence-transformers, with timeout and retries."""

    def __init__(self) -> None:
        settings = get_settings()
        self._timeout_sec = getattr(settings, "retrieval_embedding_timeout_sec", 30.0) or 30.0
        self._retries = max(0, getattr(settings, "retrieval_embedding_retries", 2))

    def embed_query(self, model_id: str, text: str) -> list[float]:
        from sentiment_api.llm.embeddings import embed_text
        last_err: Exception | None = None
        for attempt in range(1 + self._retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(embed_text, (text or "")[:8000], model_id)
                    vec = fut.result(timeout=self._timeout_sec)
                if not vec:
                    raise ValueError(f"embed_query returned empty vector for model_id={model_id!r}")
                return vec
            except FuturesTimeoutError as e:
                last_err = e
                logger.warning(
                    "embed_query timeout model_id=%s attempt=%s timeout_sec=%s",
                    model_id, attempt + 1, self._timeout_sec,
                )
            except Exception as e:
                last_err = e
                if attempt < self._retries:
                    logger.warning("embed_query failed model_id=%s attempt=%s: %s", model_id, attempt + 1, e)
                else:
                    raise
        raise last_err or TimeoutError("embed_query timed out")

    def embed_docs(self, model_id: str, texts: list[str]) -> list[list[float]]:
        from sentiment_api.llm.embeddings import embed_texts
        if not texts:
            return []
        truncated = [(t or "")[:8000] for t in texts]
        last_err: Exception | None = None
        for attempt in range(1 + self._retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(embed_texts, truncated, model_id)
                    out = fut.result(timeout=max(self._timeout_sec, len(truncated) * 0.1))
                if len(out) != len(truncated):
                    raise ValueError(f"embed_docs returned {len(out)} vectors for {len(truncated)} texts")
                for vec in out:
                    if not vec:
                        raise ValueError(f"embed_docs returned empty vector for model_id={model_id!r}")
                return out
            except FuturesTimeoutError as e:
                last_err = e
                logger.warning(
                    "embed_docs timeout model_id=%s count=%s attempt=%s",
                    model_id, len(truncated), attempt + 1,
                )
            except Exception as e:
                last_err = e
                if attempt < self._retries:
                    logger.warning("embed_docs failed model_id=%s attempt=%s: %s", model_id, attempt + 1, e)
                else:
                    raise
        raise last_err or TimeoutError("embed_docs timed out")


class FakeEmbeddingProvider:
    """Deterministic fake for tests: hash-based pseudo-vectors."""

    def embed_query(self, model_id: str, text: str) -> list[float]:
        return self._vector(model_id, text)

    def embed_docs(self, model_id: str, texts: list[str]) -> list[list[float]]:
        return [self._vector(model_id, t) for t in texts]

    def _vector(self, model_id: str, text: str) -> list[float]:
        # Deterministic: dim from model_id. Tier A=384/768, Tier B=768 or 3072 (tierb_large).
        if "3072" in model_id or "tierb_large" in model_id.lower():
            dim = 3072
        elif "768" in model_id or "tierb" in model_id.lower():
            dim = 768
        elif "384" in model_id or "tiera" in model_id.lower():
            dim = 384
        else:
            dim = 768
        h = hash((model_id, _normalize_text_for_hash(text))) % (2**31)
        seed = h
        out = []
        for i in range(dim):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            out.append((seed / 0x7FFFFFFF - 0.5) * 0.2)
        return out
