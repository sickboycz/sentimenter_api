"""Async Postgres-backed LLM call cache (uses sentiment_api.db.pool)."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sentiment_api.db.pool import acquire
from .cache_store import CacheEntry, LLMCacheStore


class AsyncPostgresLLMCacheStore(LLMCacheStore):
    """
    Async Postgres implementation for llm_call_cache.
    Uses sentiment_api.db.pool (asyncpg).
    """

    async def get(self, cache_key: str) -> Optional[CacheEntry]:
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT status, parsed_json, raw_json, error_code, error_message
                FROM llm_call_cache
                WHERE cache_key = $1
                """,
                cache_key,
            )
        if not row:
            return None
        parsed = row["parsed_json"]
        raw = row["raw_json"]
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed) if parsed else None
            except json.JSONDecodeError:
                parsed = None
        if isinstance(raw, str):
            try:
                raw = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                raw = None
        return CacheEntry(
            cache_key=cache_key,
            status=row["status"],
            parsed_json=parsed,
            raw_json=raw,
            error_code=row["error_code"],
            error_message=row["error_message"],
        )

    async def upsert_pending(self, cache_key: str, meta: Dict[str, Any]) -> None:
        async with acquire() as conn:
            await conn.execute(
                """
                INSERT INTO llm_call_cache
                  (cache_key, cluster_id, cluster_version, step, model, prompt_hash, packet_hash, schema_hash, status, raw_json)
                VALUES
                  ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9::jsonb)
                ON CONFLICT (cache_key) DO UPDATE SET
                  status='pending', updated_at=now(), raw_json=EXCLUDED.raw_json
                """,
                cache_key,
                meta.get("cluster_id"),
                meta.get("cluster_version"),
                meta.get("step"),
                meta.get("model"),
                meta.get("prompt_hash"),
                meta.get("packet_hash"),
                meta.get("schema_hash"),
                json.dumps(meta),
            )

    async def upsert_ok(self, cache_key: str, parsed_json: Dict[str, Any], raw_json: Dict[str, Any], usage: Dict[str, Any]) -> None:
        async with acquire() as conn:
            await conn.execute(
                """
                UPDATE llm_call_cache
                SET status='ok',
                    parsed_json=$2::jsonb,
                    raw_json=$3::jsonb,
                    latency_ms=$4,
                    tokens_in=$5,
                    tokens_out=$6,
                    error_code=NULL,
                    error_message=NULL,
                    updated_at=now()
                WHERE cache_key=$1
                """,
                cache_key,
                json.dumps(parsed_json),
                json.dumps(raw_json),
                usage.get("latency_ms"),
                usage.get("tokens_in"),
                usage.get("tokens_out"),
            )

    async def upsert_failed(self, cache_key: str, error_code: str, error_message: str, raw_json: Optional[Dict[str, Any]] = None) -> None:
        async with acquire() as conn:
            await conn.execute(
                """
                UPDATE llm_call_cache
                SET status='failed',
                    raw_json=$2::jsonb,
                    error_code=$3,
                    error_message=$4,
                    updated_at=now()
                WHERE cache_key=$1
                """,
                cache_key,
                json.dumps(raw_json or {}),
                error_code,
                error_message,
            )
