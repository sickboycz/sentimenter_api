from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from .deps import require_api_key

router = APIRouter(prefix="/api", tags=["compat"])

@router.get("/sp-sentiment")
def sp_sentiment(
    _api_key: str = Depends(require_api_key),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
):
    # Moodix-compatible endpoint returns a raw array.
    # Placeholder: return empty series when no data.
    return []
