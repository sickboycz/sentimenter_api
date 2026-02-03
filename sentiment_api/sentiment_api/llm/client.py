"""OpenAI LLM client with GPT-5.2 escalation chain."""

import logging
import os
from typing import Any

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.llm.client")

# GPT-5.2 family: mini (fast) -> 5.2 (balanced) -> 5.2-pro (best)
DEFAULT_ESCALATION = ["gpt-5-mini", "gpt-5.2", "gpt-5.2-pro"]


def call_chat(
    system: str,
    user: str,
    models: list[str] | None = None,
    temperature: float = 0.1,
) -> str:
    """Call OpenAI Chat Completions with escalation: try models in order until success."""
    key = get_settings().openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return ""
    models = models or getattr(get_settings(), "model_escalation", None) or DEFAULT_ESCALATION
    last_err: Exception | None = None
    for model in models:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }
            try:
                resp = client.chat.completions.create(**kwargs)
            except Exception as temp_err:
                err_str = str(temp_err).lower()
                if "temperature" in err_str and "unsupported" in err_str:
                    kwargs["temperature"] = 1.0
                    resp = client.chat.completions.create(**kwargs)
                else:
                    raise
            choices = getattr(resp, "choices", None) or []
            out = (choices[0].message.content or "").strip() if choices else ""
            if out:
                return out
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "401" in err_str or "invalid_api_key" in err_str or "authentication" in err_str or "incorrect api key" in err_str:
                logger.error("OpenAI auth failed (invalid token): %s", e)
                raise
            logger.warning("LLM %s failed: %s, escalating", model, e)
    if last_err:
        logger.error("All models failed; last: %s", last_err)
    return ""
