from __future__ import annotations
import secrets

def new_request_id() -> str:
    return "req_" + secrets.token_hex(12)
