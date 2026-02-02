"""API key validation against api_keys table or SENTIMENT_API_API_KEYS (AC-M9.1)."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException

from sentiment_api.api.auth import get_api_key
from sentiment_api.config import get_settings
from sentiment_api.db.pool import get_pool, acquire

logger = logging.getLogger("sentiment_api.api.keys")


def _env_keys() -> set[str]:
    raw = (get_settings().api_keys or "").strip()
    return {k.strip() for k in raw.split(",") if k.strip()} if raw else set()


def _verify_key(stored_hash: str, key: str) -> bool:
    if not stored_hash or not key:
        return False
    try:
        from argon2 import PasswordHasher
        PasswordHasher().verify(stored_hash, key)
        return True
    except Exception:
        pass
    import hashlib
    return hashlib.sha256(key.encode()).hexdigest() == stored_hash


async def validate_api_key(key: Annotated[str, Depends(get_api_key)]) -> str:
    """Validate API key against api_keys table or SENTIMENT_API_API_KEYS. Returns key on success."""
    env_whitelist = _env_keys()
    if env_whitelist and key in env_whitelist:
        return key
    pool = get_pool()
    if pool is None:
        if env_whitelist:
            raise HTTPException(
                status_code=401,
                detail={"code": "auth_invalid_api_key", "message": "Invalid API key."},
            )
        raise HTTPException(
            status_code=503,
            detail={"code": "service_unavailable", "message": "Service unavailable"},
        )
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                "SELECT api_key_id, key_hash, enabled FROM api_keys WHERE enabled = true"
            )
    except Exception as e:
        logger.warning("api_keys lookup failed: %s", e)
        raise HTTPException(status_code=503, detail="Service unavailable")
    for row in rows:
        if not row["enabled"]:
            continue
        if _verify_key(row["key_hash"], key):
            try:
                async with acquire() as conn2:
                    await conn2.execute(
                        "UPDATE api_keys SET last_used_at = now() WHERE api_key_id = $1",
                        row["api_key_id"],
                    )
            except Exception:
                pass
            return key
    raise HTTPException(
        status_code=401,
        detail={"code": "auth_invalid_api_key", "message": "Invalid API key."},
    )
