from __future__ import annotations
from fastapi import HTTPException

def http_error(status_code: int, code: str, message: str, *, details: dict | None = None, hint: str | None = None, retryable: bool = False) -> HTTPException:
    # We raise HTTPException and catch it in a global handler to format the envelope.
    payload = {"code": code, "message": message, "details": details or {}, "hint": hint, "retryable": retryable}
    return HTTPException(status_code=status_code, detail=payload)
