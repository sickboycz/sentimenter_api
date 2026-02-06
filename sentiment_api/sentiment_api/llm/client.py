"""OpenAI LLM client — all calls go through openai_gateway (chunking and batching only)."""

import logging
import os

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
    """
    Text via Responses API only (no Chat requests). Uses responses_text_batched.
    """
    from sentiment_api.llm.openai_gateway import responses_text_batched

    key = get_settings().openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return ""
    model_list = models or getattr(get_settings(), "model_escalation", None) or DEFAULT_ESCALATION
    last_err: Exception | None = None
    for model in model_list:
        try:
            out = responses_text_batched(
                system,
                user,
                model=model,
                temperature=temperature,
            )
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
