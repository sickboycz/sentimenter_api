from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from ...deps import require_api_key
from ...http.response import ok_envelope

router = APIRouter(prefix="/v1", tags=["sectors"])

# Minimal set; expand to full GICS-like taxonomy as needed.
_SECTORS = [
    {"sector_id": "technology", "name_en": "Information Technology", "taxonomy": "gics_like"},
    {"sector_id": "healthcare", "name_en": "Health Care", "taxonomy": "gics_like"},
    {"sector_id": "financials", "name_en": "Financials", "taxonomy": "gics_like"},
    {"sector_id": "energy", "name_en": "Energy", "taxonomy": "gics_like"},
    {"sector_id": "industrials", "name_en": "Industrials", "taxonomy": "gics_like"},
    {"sector_id": "consumer_discretionary", "name_en": "Consumer Discretionary", "taxonomy": "gics_like"},
    {"sector_id": "consumer_staples", "name_en": "Consumer Staples", "taxonomy": "gics_like"},
    {"sector_id": "communication_services", "name_en": "Communication Services", "taxonomy": "gics_like"},
    {"sector_id": "utilities", "name_en": "Utilities", "taxonomy": "gics_like"},
    {"sector_id": "real_estate", "name_en": "Real Estate", "taxonomy": "gics_like"},
    {"sector_id": "materials", "name_en": "Materials", "taxonomy": "gics_like"},
]

@router.get("/sectors")
def sectors(request: Request, _api_key: str = Depends(require_api_key)):
    return ok_envelope(request.state.request_id, _SECTORS)
