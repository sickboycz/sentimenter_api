"""Response helpers for consistent meta + pagination."""

import uuid
from datetime import UTC, datetime


def meta() -> dict:
    return {
        "request_id": f"req_{uuid.uuid4().hex[:12]}",
        "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def pagination(limit: int, returned: int, next_cursor: str | None = None) -> dict:
    return {
        "limit": limit,
        "next_cursor": next_cursor,
        "returned": returned,
    }


def error_detail(code: str, message: str, details: dict | None = None, hint: str | None = None) -> dict:
    d: dict = {"code": code, "message": message}
    if details:
        d["details"] = details
    if hint:
        d["hint"] = hint
    return d
