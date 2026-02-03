"""API key authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader, APIKeyQuery

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Annotated[str | None, Depends(_api_key_header)],
    query_key: Annotated[str | None, Depends(_api_key_query)],
) -> str | None:
    """Extract API key from header or query param if provided. None when no key (auth optional)."""
    key = (header_key or query_key or "").strip()
    return key if len(key) >= 16 else None
