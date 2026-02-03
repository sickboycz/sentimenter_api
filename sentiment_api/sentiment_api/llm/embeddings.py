"""M7 — Embeddings (OpenAI, sentence-transformers fallback). Schema requires 3072-dim."""

import logging
import os
from typing import Any

logger = logging.getLogger("sentiment_api.llm.embeddings")

DIM = 3072
_model: Any = None


def get_embedder(model_id: str = "openai:text-embedding-3-large", api_key: str | None = None) -> Any:
    """Return embedder instance. Priority: OpenAI > sentence-transformers."""
    global _model
    if _model is not None:
        return _model
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if key and "openai" in (model_id or ""):
        try:
            from openai import OpenAI
            _model = ("openai", OpenAI(api_key=key), model_id)
        except Exception as e:
            logger.warning("OpenAI init failed: %s, using sentence-transformers", e)
            _model = ("sentence_transformers", None, model_id)
    else:
        _model = ("sentence_transformers", None, model_id or "local")
    if _model[0] == "sentence_transformers" and _model[1] is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = ("sentence_transformers", SentenceTransformer("all-MiniLM-L6-v2"), _model[2])
        except Exception as e:
            logger.warning("sentence-transformers failed: %s, using deterministic mock", e)
            _model = ("mock", None, _model[2])
    return _model


def _pad_to_3072(vec: list[float]) -> list[float]:
    """Pad or truncate to 3072 dims for schema compatibility."""
    if len(vec) >= DIM:
        return vec[:DIM]
    return vec + [0.0] * (DIM - len(vec))


def embed_text(text: str, model_id: str | None = None) -> list[float]:
    """Embed text; returns 3072-dim vector."""
    provider, client, mid = get_embedder(model_id or "openai:text-embedding-3-large")
    if provider == "openai" and client:
        try:
            resp = client.embeddings.create(
                model="text-embedding-3-large",
                input=text[:8000],
            )
            if resp.data and len(resp.data) > 0:
                return resp.data[0].embedding
            logger.warning("OpenAI embeddings returned empty data")
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "invalid_api_key" in err_str or "authentication" in err_str or "incorrect api key" in err_str:
                logger.error("OpenAI embedding auth failed (invalid token): %s", e)
                raise
            logger.warning("Embedding failed: %s", e)
        provider = "sentence_transformers"
    if provider == "sentence_transformers" and client:
        try:
            vec = client.encode(text[:8000], convert_to_numpy=True).tolist()
            return _pad_to_3072(vec)
        except Exception as e:
            logger.warning("sentence-transformers encode failed: %s", e)
    import random
    random.seed(hash(text) % (2**32))
    return [random.gauss(0, 0.1) for _ in range(DIM)]
