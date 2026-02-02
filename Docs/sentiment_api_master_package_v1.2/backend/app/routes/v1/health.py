from __future__ import annotations

from fastapi import APIRouter
from ...utils.time import now_utc
from ...db.engine import db_ping

router = APIRouter(prefix="/v1", tags=["ops"])

@router.get("/health")
def health():
    ok, err = db_ping()
    checks = [
        {"name": "db", "status": "ok" if ok else "fail", "details": {"error": err} if err else {}},
    ]
    status = "ok" if ok else "degraded"
    return {"status": status, "as_of": now_utc().isoformat(), "checks": checks}
