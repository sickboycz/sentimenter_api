from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import ok_envelope, build_meta, build_pagination
from ...utils.time import now_utc

router = APIRouter(prefix="/v1", tags=["universes"])

_UNIVERSES = [
    {"universe_id": "sp500", "name_en": "S&P 500", "description_en": "S&P 500 constituents", "source": "seed", "as_of": now_utc().isoformat(), "constituent_count": 500},
    {"universe_id": "nasdaq_composite", "name_en": "Nasdaq Composite", "description_en": "Nasdaq Composite constituents", "source": "seed", "as_of": now_utc().isoformat(), "constituent_count": 0},
]

@router.get("/universes")
def list_universes(request: Request, _api_key: str = Depends(require_api_key)):
    return ok_envelope(request.state.request_id, _UNIVERSES)

@router.get("/universes/{universe_id}/constituents")
def universe_constituents(
    universe_id: str,
    request: Request,
    _api_key: str = Depends(require_api_key),
    limit: int = Query(200, ge=1, le=500),
    cursor: str | None = Query(default=None),
):
    # Placeholder: real implementation reads ticker_universe filtered by universe.
    data: list[dict] = []
    meta = build_meta(request.state.request_id).model_dump(mode="json")
    page = build_pagination(limit=limit, returned=len(data), next_cursor=None).model_dump(mode="json")
    return {"meta": meta, "page": page, "data": data, "errors": []}
