"""M7 — Embeddings (OpenAI text-embedding-3-large or mock)."""

import logging
import os
from typing import Any

logger = logging.getLogger("sentiment_api.llm.embeddings")

DIM = 3072
_model: Any = None


def get_embedder(model_id: str = "openai:text-embedding-3-large", api_key: str | None = None) -> Any:
    """Return embedder instance."""
    global _model
    if _model is not None:
        return _model
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if key and "openai" in model_id:
        try:
            from openai import OpenAI
            _model = ("openai", OpenAI(api_key=key), model_id)
        except Exception as e:
            logger.warning("OpenAI init failed: %s, using mock", e)
            _model = ("mock", None, model_id)
    else:
        _model = ("mock", None, model_id)
    return _model


def embed_text(text: str, model_id: str | None = None) -> list[float]:
    """Embed text; returns 3072-dim vector."""
    provider, client, mid = get_embedder(model_id or "openai:text-embedding-3-large")
    if provider == "openai" and client:
        try:
            resp = client.embeddings.create(
                model="text-embedding-3-large",
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning("Embedding failed: %s", e)
    import random
    random.seed(hash(text) % (2**32))
    return [random.gauss(0, 0.1) for _ in range(DIM)]
