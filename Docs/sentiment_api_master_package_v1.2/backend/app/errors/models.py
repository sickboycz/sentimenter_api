from __future__ import annotations
from typing import Any, Dict, Optional
from ..schemas.common import ErrorModel

def err(code: str, message: str, *, details: Optional[Dict[str, Any]] = None, hint: str | None = None, retryable: bool = False) -> ErrorModel:
    return ErrorModel(code=code, message=message, details=details or {}, hint=hint, retryable=retryable)
