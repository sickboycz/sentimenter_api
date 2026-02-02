from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import list_envelope

router = APIRouter(prefix="/v1", tags=["index"])

@router.get("/index/intraday")
def index_intraday(
    request: Request,
    _api_key: str = Depends(require_api_key),
    interval: str = Query(..., pattern="^(1m|5m|15m|1h)$"),
    limit: int = Query(200, ge=1, le=500),
    cursor: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
):
    # Placeholder: real implementation queries sentiment_timeseries_intraday.
    data: list[dict] = []
    return list_envelope(request.state.request_id, data, limit=limit, next_cursor=None)
