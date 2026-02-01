"""Async Postgres connection pool."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg


_pool: asyncpg.Pool | None = None


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
        raise RuntimeError("DB pool not initialized; Postgres may be unavailable")
    async with pool.acquire() as conn:
        yield conn
