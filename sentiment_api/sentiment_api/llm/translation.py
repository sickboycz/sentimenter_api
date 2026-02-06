"""
M2 — Translation step using Responses API only (no Chat requests).

Chunking: long text is split into segments; each chunk is sent via Responses API
with schema { translation: string }. Results are concatenated.
"""

import logging

logger = logging.getLogger("sentiment_api.llm.translation")

DEFAULT_CHUNK_CHARS = 1500


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most max_chars on paragraph/sentence/word boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_chars:
            chunks.append(rest.strip())
            break
        segment = rest[: max_chars + 1]
        idx = segment.rfind("\n\n")
        if idx <= 0:
            idx = segment.rfind("\n")
        if idx <= 0:
            idx = max(segment.rfind(". "), segment.rfind("。"), segment.rfind("."))
        if idx <= 0:
            idx = segment.rfind(" ")
        if idx <= 0:
            idx = max_chars
        else:
            idx = idx + 1 if segment[idx] in (" ", "\n") else idx + 2 if segment[idx : idx + 2] == ". " else idx + 1
        chunk = rest[:idx].strip()
        if chunk:
            chunks.append(chunk)
        rest = rest[idx:].lstrip()
    return chunks


def translate_step_openai(
    text: str,
    from_lang: str,
    to_lang: str = "en",
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    chunk_chars: int | None = None,
) -> str | None:
    """
    Translate via Responses API only (schema: { translation: string }).
    Chunk text, one Responses API call per chunk, concatenate results.
    """
    if not text or not text.strip():
        return ""
    from sentiment_api.config import get_settings
    from sentiment_api.llm.openai_gateway import responses_structured, SCHEMA_TRANSLATION

    settings = get_settings()
    key = api_key or settings.openai_api_key
    if not key:
        logger.debug("Translation skipped: no OPENAI_API_KEY")
        return None
    model_id = model or getattr(settings, "model_translation", None) or "gpt-4o-mini"
    base = base_url or getattr(settings, "openai_base_url", None)
    max_chunk = chunk_chars if chunk_chars is not None else getattr(settings, "translation_chunk_chars", DEFAULT_CHUNK_CHARS)

    chunks = _chunk_text(text, max_chunk)
    if not chunks:
        return ""

    system = (
        f"You are a professional translator. Translate the following text from {from_lang} to {to_lang}. "
        "Output ONLY the translation, no preamble, no explanations."
    )
    parts: list[str] = []
    for chunk in chunks:
        parsed, _ = responses_structured(
            name="translation",
            schema=SCHEMA_TRANSLATION,
            system_prompt=system,
            user_prompt=chunk,
            model=model_id,
            temperature=0.1,
            api_key=key,
            base_url=base,
        )
        if parsed and isinstance(parsed.get("translation"), str):
            parts.append(parsed["translation"].strip())
        else:
            parts.append(chunk)
    if not parts:
        return None
    return "\n\n".join(parts)


def translate_openai(text: str, from_lang: str, to_lang: str = "en") -> str | None:
    """
    Translate to English via Responses API only (no Chat requests).
    Uses TRANSLATION_CHUNK_CHARS, MODEL_TRANSLATION, OPENAI_BASE_URL.
    """
    return translate_step_openai(text, from_lang, to_lang)
