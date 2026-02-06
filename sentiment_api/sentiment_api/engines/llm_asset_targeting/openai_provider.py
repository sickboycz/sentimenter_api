"""OpenAI Responses API — all calls go through openai_gateway (chunking/batching only)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

DEFAULT_BASE_URL = "https://api.openai.com/v1"

@dataclass(frozen=True)
class LLMUsage:
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[int] = None

class OpenAIResponsesError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body

class OpenAIResponsesProvider:
    """Responses API wrapper; all HTTP goes through openai_gateway."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model: Optional[str] = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.base_url = os.environ.get("OPENAI_BASE_URL", base_url)
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-2024-08-06")
        self.timeout_s = timeout_s

    def call_structured(
        self,
        *,
        name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        temperature: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], LLMUsage]:
        from sentiment_api.llm.openai_gateway import responses_structured

        parsed, usage_info = responses_structured(
            name=name,
            schema=schema,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.model,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout_s=self.timeout_s,
        )
        if parsed is None:
            raise OpenAIResponsesError("Could not extract structured JSON from Responses API", body=None)
        usage = LLMUsage(
            tokens_in=usage_info.get("input_tokens"),
            tokens_out=usage_info.get("output_tokens"),
            latency_ms=usage_info.get("latency_ms"),
        )
        return parsed, usage
