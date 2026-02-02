from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import ok_envelope
from ...utils.time import now_utc

router = APIRouter(prefix="/v1", tags=["impacts"])

def _empty_bundle(scope: str) -> dict:
    return {
        "as_of": now_utc().isoformat(),
        "scope": scope,
        "most_affected_market": {
            "market_id": "us_equities",
            "label_en": "US Equities",
            "expected_direction": "Neutral",
            "magnitude": 0.0,
            "confidence": 0.0,
            "horizon": "intraday",
            "channels": [],
            "rationale_en": "No processed clusters yet.",
        },
        "markets": [],
        "sectors": [],
        "winners": [],
        "losers": [],
        "notes_en": "Placeholder response. Implement impact allocation engine + DB-backed outputs."
    }

@router.get("/impacts/latest")
def impacts_latest(
    request: Request,
    _api_key: str = Depends(require_api_key),
    window: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    min_impact_level: str | None = Query(default=None),
    universes: list[str] | None = Query(default=None),
    limit_tickers: int | None = Query(default=None, ge=1, le=200),
    limit_sectors: int | None = Query(default=None, ge=0, le=30),
    include_evidence_urls: bool | None = Query(default=None),
    include_historical_edge: bool | None = Query(default=None),
):
    scope = window or "latest"
    return ok_envelope(request.state.request_id, _empty_bundle(scope))

@router.get("/impacts/clusters/{cluster_id}")
def impacts_by_cluster(
    cluster_id: str,
    request: Request,
    _api_key: str = Depends(require_api_key),
    universes: list[str] | None = Query(default=None),
    limit_tickers: int | None = Query(default=None, ge=1, le=200),
    limit_sectors: int | None = Query(default=None, ge=0, le=30),
    include_evidence_urls: bool | None = Query(default=None),
    include_historical_edge: bool | None = Query(default=None),
):
    return ok_envelope(request.state.request_id, _empty_bundle(f"cluster:{cluster_id}"))
