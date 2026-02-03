"""DB-backed cache interface for LLM calls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    cache_key: str
    status: str  # ok|failed|pending
    parsed_json: Optional[Dict[str, Any]] = None
    raw_json: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class LLMCacheStore:
    """
    Async DB-backed cache interface (aligns with sentiment_api.db.pool).

    Contract:
    - get() returns CacheEntry or None
    - upsert_pending() creates/updates row with status=pending
    - upsert_ok() stores parsed_json + raw_json and sets status=ok
    - upsert_failed() stores error and sets status=failed
    """
    async def get(self, cache_key: str) -> Optional[CacheEntry]:
        raise NotImplementedError

    async def upsert_pending(self, cache_key: str, meta: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def upsert_ok(self, cache_key: str, parsed_json: Dict[str, Any], raw_json: Dict[str, Any], usage: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def upsert_failed(self, cache_key: str, error_code: str, error_message: str, raw_json: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError
