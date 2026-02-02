from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from ...deps import require_api_key
from ...http.response import ok_envelope
from ...utils.time import now_utc
from ...schemas.common import Direction

router = APIRouter(prefix="/v1", tags=["mood"])

@router.get("/mood/now")
def mood_now(request: Request, _api_key: str = Depends(require_api_key)):
    # Placeholder: real implementation reads from DB / index engine.
    snapshot = {
        "as_of": now_utc().isoformat(),
        "sentiment": Direction.Neutral.value,
        "trend": "Sideways",
        "index_intraday": 0.0,
        "news_volume_intraday": 0,
        "news_volatility_intraday": 0.0,
        "confidence": 0.0,
        "drivers": [],
        "risk_vector": {
            "risk_appetite": 0.0,
            "volatility_pressure": 0.0,
            "growth_outlook": 0.0,
            "inflation_pressure": 0.0,
            "rates_pressure": 0.0,
            "liquidity_stress": 0.0,
            "geopolitical_risk": 0.0,
            "energy_supply_risk": 0.0,
        },
    }
    return ok_envelope(request.state.request_id, snapshot)
