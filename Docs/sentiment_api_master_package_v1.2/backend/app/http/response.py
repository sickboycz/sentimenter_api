from __future__ import annotations

from typing import Any, List, Optional
from ..schemas.common import ErrorModel, Pagination, ResponseMeta
from ..utils.time import now_utc

def build_meta(request_id: str, *, trace_id: str | None = None, model_versions: dict[str, str] | None = None) -> ResponseMeta:
    return ResponseMeta(request_id=request_id, as_of=now_utc(), trace_id=trace_id, model_versions=model_versions or {})

def build_pagination(limit: int, returned: int, next_cursor: Optional[str]) -> Pagination:
    return Pagination(limit=limit, returned=returned, next_cursor=next_cursor)

def ok_envelope(request_id: str, data: Any, *, errors: Optional[List[ErrorModel]] = None, trace_id: str | None = None, model_versions: dict[str,str] | None = None) -> dict[str, Any]:
    return {"meta": build_meta(request_id, trace_id=trace_id, model_versions=model_versions).model_dump(mode="json"),
            "data": data,
            "errors": [e.model_dump(mode="json") for e in (errors or [])]}

def list_envelope(request_id: str, data_list: list[Any], *, limit: int, next_cursor: str | None, errors: Optional[List[ErrorModel]] = None, trace_id: str | None = None, model_versions: dict[str,str] | None = None) -> dict[str, Any]:
    return {"meta": build_meta(request_id, trace_id=trace_id, model_versions=model_versions).model_dump(mode="json"),
            "pagination": build_pagination(limit, len(data_list), next_cursor).model_dump(mode="json"),
            "data": data_list,
            "errors": [e.model_dump(mode="json") for e in (errors or [])]}
