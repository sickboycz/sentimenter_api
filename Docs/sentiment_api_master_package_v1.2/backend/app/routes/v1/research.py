from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import ok_envelope

router = APIRouter(prefix="/v1", tags=["research"])

@router.get("/research/spy/event-study")
def event_study(
    request: Request,
    _api_key: str = Depends(require_api_key),
    market: str = Query("SPY", pattern="^(SPY|ES)$"),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    windows: list[str] = Query(...),
):
    # Placeholder: real implementation computes from DB.
    payload = {
        "market": market,
        "from": from_,
        "to": to,
        "filters": {"windows": windows},
        "sample_size": 0,
        "windows": [],
    }
    return ok_envelope(request.state.request_id, payload)
