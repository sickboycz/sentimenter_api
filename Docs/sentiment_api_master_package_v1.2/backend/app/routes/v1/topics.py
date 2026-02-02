from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import list_envelope

router = APIRouter(prefix="/v1", tags=["topics"])

@router.get("/topics/index")
def topics_index(
    request: Request,
    _api_key: str = Depends(require_api_key),
    interval: str | None = Query(default="5m", pattern="^(1m|5m|15m|1h|1d)$"),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    topics: list[str] | None = Query(default=None),
    limit: int = Query(500, ge=1, le=500),
    cursor: str | None = Query(default=None),
):
    # Placeholder: real implementation queries topic_index_intraday.
    data: list[dict] = []
    return list_envelope(request.state.request_id, data, limit=limit, next_cursor=None)
