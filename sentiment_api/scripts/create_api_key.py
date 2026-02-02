#!/usr/bin/env python3
"""Create an API key and insert into api_keys table."""

import asyncio
import os
import secrets
import sys

async def main():
    from sentiment_api.db.pool import init_pool, acquire
    from sentiment_api.config import get_settings
    settings = get_settings()
    await init_pool(settings.database_url)
    key = secrets.token_urlsafe(32)
    try:
        from argon2 import PasswordHasher
        key_hash = PasswordHasher().hash(key)
    except ImportError:
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO api_keys (name, key_hash, enabled, rate_limit_per_min, notes)
            VALUES ($1, $2, true, 120, $3)
            """,
            "default",
            key_hash,
            "Bootstrap key",
        )
    print("API key created. Store securely:")
    print(key)
    print("\nUse as: X-API-Key:", key[:16] + "...")

if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
