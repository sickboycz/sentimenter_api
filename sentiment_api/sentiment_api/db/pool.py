"""Async Postgres connection pool."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncio
import asyncpg


_pool: asyncpg.Pool | None = None
_init_lock = asyncio.Lock()


async def init_pool(database_url: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """Create connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )
    return _pool


async def ensure_pool(database_url: str | None = None) -> asyncpg.Pool:
    """Ensure pool exists; lazily initialize if missing."""
    global _pool
    if _pool is not None:
        return _pool
    async with _init_lock:
        if _pool is not None:
            return _pool
        if database_url is None:
            from sentiment_api.config import get_settings
            database_url = get_settings().database_url
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        return _pool


async def close_pool() -> None:
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    """Get current pool; returns None if not initialized."""
    return _pool


@asynccontextmanager
async def acquire() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool."""
    pool = get_pool()
    if pool is None:
        pool = await ensure_pool()
    async with pool.acquire() as conn:
        yield conn
