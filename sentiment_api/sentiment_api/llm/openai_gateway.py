"""
OpenAI API gateway — HARD LAW: Responses API primarily, no Chat requests. Chunking and batching only.

- Text generation: Responses API only (responses_structured, responses_text, responses_text_batched).
- Embeddings: openai client (batched). No Chat Completions; all text flows through Responses API.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("sentiment_api.llm.openai_gateway")

# Defaults when config not available
DEFAULT_CHAT_CHUNK_CHARS = 4000
DEFAULT_EMBED_BATCH_SIZE = 256
DEFAULT_EMBED_MAX_CHARS = 8000


def _get_client(api_key: str | None = None, base_url: str | None = None) -> Any:
    """Return OpenAI client. Only this module may construct it."""
    from sentiment_api.config import get_settings
    settings = get_settings()
    key = api_key or settings.openai_api_key
    if not key:
        return None
    try:
        from openai import OpenAI
        kwargs: dict[str, Any] = {"api_key": key}
        if base_url or getattr(settings, "openai_base_url", None):
            kwargs["base_url"] = base_url or settings.openai_base_url
        return OpenAI(**kwargs)
    except Exception as e:
        logger.warning("OpenAI client init failed: %s", e)
        return None


def _chunk_user_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most max_chars on paragraph/sentence/word boundaries."""
    text = (text or "").strip()
    if not text or len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_chars:
            chunks.append(rest.strip())
            break
        segment = rest[: max_chars + 1]
        for sep in ("\n\n", "\n", ". ", " "):
            idx = segment.rfind(sep)
            if idx > 0:
                idx = idx + len(sep) if sep in (" ", ". ") else idx + 1
                break
        else:
            idx = max_chars
        chunk = rest[:idx].strip()
        if chunk:
            chunks.append(chunk)
        rest = rest[idx:].lstrip()
    return chunks


# Schema for free-form text output (Responses API)
SCHEMA_TEXT = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}

# Schema for translation output (Responses API)
SCHEMA_TRANSLATION = {
    "type": "object",
    "properties": {"translation": {"type": "string"}},
    "required": ["translation"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Embeddings — batching only (chunk long texts)
# ---------------------------------------------------------------------------

def embeddings_batched(
    texts: list[str],
    model_id: str | None = None,
    dimensions: int | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    max_chars_per_text: int = DEFAULT_EMBED_MAX_CHARS,
) -> list[list[float]]:
    """
    Embeddings via gateway: long texts are truncated per item, then sent in batches.
    One API call per batch. Returns list of vectors in same order as input.
    """
    if not texts:
        return []
    from sentiment_api.config import get_settings
    import re as re_mod
    settings = get_settings()
    mid = model_id or settings.model_embedding_id or "openai:text-embedding-3-small:384"
    dim = dimensions
    if dim is None:
        m = re_mod.search(r":(384|768|1536|3072)$", mid or "")
        dim = int(m.group(1)) if m else 384
    key = api_key or settings.openai_api_key
    base = base_url or getattr(settings, "openai_base_url", None)
    client = _get_client(api_key=key, base_url=base)
    if not client:
        return []

    truncated = [t[:max_chars_per_text] for t in texts]
    out: list[list[float]] = []
    model_name = "text-embedding-3-large" if dim > 768 else "text-embedding-3-small"
    kwargs_dim = {}
    if model_name == "text-embedding-3-small" and dim in (384, 768):
        kwargs_dim["dimensions"] = dim
    elif model_name == "text-embedding-3-large" and dim in (256, 1024, 3072):
        kwargs_dim["dimensions"] = dim

    for i in range(0, len(truncated), batch_size):
        batch = truncated[i : i + batch_size]
        try:
            resp = client.embeddings.create(model=model_name, input=batch, **kwargs_dim)
            if resp.data:
                for d in sorted(resp.data, key=lambda x: x.index):
                    vec = getattr(d, "embedding", None) or []
                    if len(vec) >= dim:
                        out.append(vec[:dim])
                    else:
                        out.append(list(vec) + [0.0] * (dim - len(vec)))
            else:
                out.extend([[0.0] * dim] * len(batch))
        except Exception as e:
            logger.warning("OpenAI embeddings batch failed: %s", e)
            out.extend([[0.0] * dim] * len(batch))
    return out


def embed_one(text: str, model_id: str | None = None, dimensions: int | None = None) -> list[float]:
    """Single text embed via gateway (one-item batch)."""
    vecs = embeddings_batched([text], model_id=model_id, dimensions=dimensions)
    if not vecs:
        dim = dimensions or 384
        return [0.0] * dim
    return vecs[0]


# ---------------------------------------------------------------------------
# Responses API (structured outputs) — single call via gateway; batch at caller
# ---------------------------------------------------------------------------

def responses_structured(
    *,
    name: str,
    schema: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_output_tokens: int = 4096,
    temperature: float = 0.0,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: float = 30.0,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """
    OpenAI Responses API (structured JSON). Only form of communication with this endpoint.
    Returns (parsed_output, usage_info). usage_info has keys: input_tokens, output_tokens, latency_ms.
    """
    from sentiment_api.config import get_settings
    import httpx
    import time
    import json as _json

    settings = get_settings()
    key = api_key or settings.openai_api_key
    base = base_url or getattr(settings, "openai_base_url", None) or "https://api.openai.com/v1"
    model_id = model or getattr(settings, "model_escalation", None)
    if isinstance(model_id, list):
        model_id = model_id[0] if model_id else "gpt-4o-2024-08-06"
    model_id = model_id or "gpt-4o-2024-08-06"
    if not key:
        return None, {}

    payload: dict[str, Any] = {
        "model": model_id,
        "input": [
            {"role": "system", "content": (system_prompt or "")[:12000]},
            {"role": "user", "content": (user_prompt or "")[:12000]},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": name,
                "strict": True,
                "schema": schema,
            }
        },
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
        "store": False,
    }
    url = f"{base.rstrip('/')}/responses"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.post(url, headers=headers, json=payload)
    except Exception as e:
        logger.warning("OpenAI Responses API request failed: %s", e)
        return None, {"latency_ms": int((time.time() - t0) * 1000)}

    latency_ms = int((time.time() - t0) * 1000)
    usage_info: dict[str, Any] = {"latency_ms": latency_ms}
    if r.status_code < 200 or r.status_code >= 300:
        logger.warning("OpenAI Responses API error status=%s", r.status_code)
        return None, usage_info

    try:
        data = r.json()
    except Exception:
        return None, usage_info
    if isinstance(data.get("usage"), dict):
        usage_info["input_tokens"] = data["usage"].get("input_tokens")
        usage_info["output_tokens"] = data["usage"].get("output_tokens")

    parsed = None
    if isinstance(data.get("output_parsed"), dict):
        parsed = data["output_parsed"]
    elif isinstance(data.get("output_text"), str):
        try:
            parsed = _json.loads(data["output_text"])
        except Exception:
            pass
    if parsed is None and isinstance(data.get("output"), list):
        for item in data["output"]:
            if not isinstance(item, dict):
                continue
            for c in (item.get("content") or []):
                if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                    txt = c.get("text")
                    if isinstance(txt, str):
                        try:
                            parsed = _json.loads(txt)
                            break
                        except Exception:
                            pass
            if parsed is not None:
                break
    return parsed, usage_info


# ---------------------------------------------------------------------------
# Responses API — text generation (primary; no Chat requests)
# ---------------------------------------------------------------------------

def responses_text(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    *,
    temperature: float = 0.1,
    max_output_tokens: int = 8192,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_s: float = 60.0,
) -> str | None:
    """
    Single text response via Responses API (schema: { text: string }).
    Primary for all text generation; no Chat Completions.
    """
    parsed, _ = responses_structured(
        name="text_output",
        schema=SCHEMA_TEXT,
        system_prompt=(system_prompt or "").strip()[:12000],
        user_prompt=(user_prompt or "").strip()[:12000],
        model=model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        timeout_s=timeout_s,
    )
    if parsed and isinstance(parsed.get("text"), str):
        return parsed["text"].strip() or None
    return None


def responses_text_batched(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    *,
    temperature: float = 0.1,
    chunk_chars: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """
    Long user content: chunk and call Responses API per chunk; concatenate.
    Primary path for RAG/summaries; no Chat requests.
    """
    from sentiment_api.config import get_settings
    settings = get_settings()
    model_id = model or getattr(settings, "model_escalation", None)
    if isinstance(model_id, list):
        model_id = model_id[0] if model_id else "gpt-4o-2024-08-06"
    model_id = model_id or "gpt-4o-2024-08-06"
    max_chunk = chunk_chars or getattr(settings, "translation_chunk_chars", None) or DEFAULT_CHAT_CHUNK_CHARS

    user_str = (user_prompt or "").strip()
    if not user_str:
        return ""
    chunks = _chunk_user_text(user_str, max_chunk)
    if not chunks:
        return ""
    system = (system_prompt or "").strip()[:12000]
    key = api_key or settings.openai_api_key
    base = base_url or getattr(settings, "openai_base_url", None)
    parts: list[str] = []
    for chunk in chunks:
        out = responses_text(
            system,
            chunk,
            model=model_id,
            temperature=temperature,
            api_key=key,
            base_url=base,
        )
        if out:
            parts.append(out)
        else:
            parts.append(chunk)
    return "\n\n".join(parts)
