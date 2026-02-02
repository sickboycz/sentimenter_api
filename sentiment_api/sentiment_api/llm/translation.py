"""M2 — Translation to English (OpenAI, required for non-English content)."""

import logging
import os

logger = logging.getLogger("sentiment_api.llm.translation")


def translate_openai(text: str, from_lang: str, to_lang: str = "en") -> str | None:
    """Translate via OpenAI API (GPT-5.2 escalation). Returns translated text or None on failure."""
    from sentiment_api.llm.client import call_chat
    out = call_chat(
        f"Translate the following text from {from_lang} to {to_lang}. Output ONLY the translation, no preamble.",
        text[:8000],
        temperature=0.1,
    )
    return out if out else None
