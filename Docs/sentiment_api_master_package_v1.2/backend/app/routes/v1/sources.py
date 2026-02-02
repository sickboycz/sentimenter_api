from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import ok_envelope
from ...services.registry import list_sources

router = APIRouter(prefix="/v1", tags=["sources"])

@router.get("/sources")
def sources(
    request: Request,
    _api_key: str = Depends(require_api_key),
    enabled_only: bool = Query(default=False),
    types: list[str] | None = Query(default=None),
):
    data = list_sources(enabled_only=enabled_only, types=types)
    return ok_envelope(request.state.request_id, data)
