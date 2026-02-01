"""API key authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from fastapi.security import APIKeyHeader, APIKeyQuery

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key(
    header_key: Annotated[str | None, Depends(_api_key_header)],
    query_key: Annotated[str | None, Depends(_api_key_query)],
) -> str:
    """Extract API key from header or query param (Moodix-compatible)."""
    key = header_key or query_key
    if not key or len(key) < 16:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return key
