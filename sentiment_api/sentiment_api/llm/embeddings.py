"""M7 — Embeddings (OpenAI, sentence-transformers fallback). Schema uses 768-dim (Tier B). Tier A = 384."""

import logging
import os
import re
from typing import Any

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.llm.embeddings")

# Default dimension for clustering and DB (Tier B)
DIM = 768
_model: Any = None


def _dim_from_model_id(model_id: str | None) -> int:
    """Parse dimensions from model_id (e.g. ...:384 or ...:768). Default DIM (768)."""
    if not model_id:
        return DIM
    m = re.search(r":(384|768|1536|3072)$", model_id)
    if m:
        return int(m.group(1))
    if "384" in model_id or "tiera" in model_id.lower():
        return 384
    if "768" in model_id or "tierb" in model_id.lower():
        return 768
    return DIM


def get_embedder(model_id: str = "openai:text-embedding-3-small", api_key: str | None = None) -> Any:
    """Return embedder instance. Priority: OpenAI > sentence-transformers."""
    global _model
    if _model is not None:
        return _model
    key = api_key or get_settings().openai_api_key or os.environ.get("OPENAI_API_KEY")
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


def _pad_to_dim(vec: list[float], dim: int) -> list[float]:
    """Pad or truncate to dim for schema compatibility."""
    if len(vec) >= dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))


def embed_text(text: str, model_id: str | None = None, dimensions: int | None = None) -> list[float]:
    """Embed text; returns 768-dim vector by default (Tier B). Use model_id suffix :384 for Tier A."""
    target_dim = dimensions if dimensions is not None else _dim_from_model_id(model_id)
    mid = model_id or get_settings().model_embedding_id or "openai:text-embedding-3-small:384"
    provider, client, _ = get_embedder(mid)
    if provider == "openai" and client:
        try:
            # text-embedding-3-small supports dimensions=384 or 768
            model_name = "text-embedding-3-large" if target_dim > 768 else "text-embedding-3-small"
            kwargs = {"model": model_name, "input": text[:8000]}
            if model_name == "text-embedding-3-small" and target_dim in (384, 768):
                kwargs["dimensions"] = target_dim
            elif model_name == "text-embedding-3-large" and target_dim in (256, 1024, 3072):
                kwargs["dimensions"] = target_dim
            resp = client.embeddings.create(**kwargs)
            if resp.data and len(resp.data) > 0:
                return _pad_to_dim(resp.data[0].embedding, target_dim)
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
            return _pad_to_dim(vec, target_dim)
        except Exception as e:
            logger.warning("sentence-transformers encode failed: %s", e)
    import random
    random.seed(hash(text) % (2**32))
    return [random.gauss(0, 0.1) for _ in range(target_dim)]


# Max texts per OpenAI batch (API supports up to 2048; larger = fewer round trips, lower cost)
_OPENAI_BATCH_SIZE = 256


def embed_texts(
    texts: list[str],
    model_id: str | None = None,
    dimensions: int | None = None,
) -> list[list[float]]:
    """Embed multiple texts in batch (single API call per chunk). Returns list of vectors in same order."""
    if not texts:
        return []
    target_dim = dimensions if dimensions is not None else _dim_from_model_id(model_id)
    mid = model_id or get_settings().model_embedding_id or "openai:text-embedding-3-small:384"
    provider, client, _ = get_embedder(mid)
    if provider == "openai" and client:
        out: list[list[float]] = []
        for i in range(0, len(texts), _OPENAI_BATCH_SIZE):
            chunk = [t[:8000] for t in texts[i : i + _OPENAI_BATCH_SIZE]]
            try:
                model_name = "text-embedding-3-large" if target_dim > 768 else "text-embedding-3-small"
                kwargs: dict = {"model": model_name, "input": chunk}
                if model_name == "text-embedding-3-small" and target_dim in (384, 768):
                    kwargs["dimensions"] = target_dim
                elif model_name == "text-embedding-3-large" and target_dim in (256, 1024, 3072):
                    kwargs["dimensions"] = target_dim
                resp = client.embeddings.create(**kwargs)
                if resp.data:
                    for d in sorted(resp.data, key=lambda x: x.index):
                        out.append(_pad_to_dim(d.embedding, target_dim))
                else:
                    for _ in chunk:
                        out.append([0.0] * target_dim)
            except Exception as e:
                err_str = str(e).lower()
                if "401" in err_str or "invalid_api_key" in err_str or "authentication" in err_str:
                    logger.error("OpenAI embedding auth failed: %s", e)
                    raise
                logger.warning("Batch embed failed, falling back to single calls: %s", e)
                for t in chunk:
                    out.append(embed_text(t, model_id, target_dim))
        return out
    if provider == "sentence_transformers" and client:
        try:
            truncated = [t[:8000] for t in texts]
            mat = client.encode(truncated, convert_to_numpy=True)
            return [_pad_to_dim(mat[j].tolist(), target_dim) for j in range(len(truncated))]
        except Exception as e:
            logger.warning("sentence_transformers batch encode failed: %s", e)
    import random
    return [embed_text(t, model_id, target_dim) for t in texts]
