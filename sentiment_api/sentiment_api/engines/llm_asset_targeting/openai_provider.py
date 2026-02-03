"""OpenAI Responses API wrapper for strict structured outputs (temperature=0, store=false)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx

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
    """Minimal Responses API wrapper for strict structured outputs."""

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

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

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
        payload: Dict[str, Any] = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
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
        if metadata:
            payload["metadata"] = metadata

        url = f"{self.base_url}/responses"

        t0 = time.time()
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, headers=self._headers(), json=payload)
        latency_ms = int((time.time() - t0) * 1000)

        if r.status_code < 200 or r.status_code >= 300:
            raise OpenAIResponsesError(
                f"OpenAI error status={r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )

        data = r.json()
        parsed_obj: Optional[Dict[str, Any]] = None

        if isinstance(data, dict) and isinstance(data.get("output_parsed"), dict):
            parsed_obj = data["output_parsed"]

        if parsed_obj is None and isinstance(data, dict) and isinstance(data.get("output_text"), str):
            import json
            try:
                parsed_obj = json.loads(data["output_text"])
            except Exception:
                parsed_obj = None

        if parsed_obj is None and isinstance(data, dict) and isinstance(data.get("output"), list):
            import json
            for item in data["output"]:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for c in content:
                    if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                        txt = c.get("text")
                        if isinstance(txt, str):
                            try:
                                parsed_obj = json.loads(txt)
                                break
                            except Exception:
                                pass
                if parsed_obj is not None:
                    break

        if parsed_obj is None:
            raise OpenAIResponsesError("Could not extract structured JSON from Responses API", body=data)

        usage = data.get("usage") if isinstance(data, dict) else None
        tokens_in = usage.get("input_tokens") if isinstance(usage, dict) else None
        tokens_out = usage.get("output_tokens") if isinstance(usage, dict) else None

        return parsed_obj, LLMUsage(tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms)
