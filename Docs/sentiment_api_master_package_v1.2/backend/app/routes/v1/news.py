from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from ...deps import require_api_key
from ...http.response import list_envelope, ok_envelope
from ...errors.http import http_error

router = APIRouter(prefix="/v1", tags=["news"])

@router.get("/news/clusters")
def list_clusters(
    request: Request,
    _api_key: str = Depends(require_api_key),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    min_impact_level: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    include_source_urls: bool = Query(default=False),
):
    # Placeholder: real implementation returns recent clusters from DB.
    data: list[dict] = []
    return list_envelope(request.state.request_id, data, limit=limit, next_cursor=None)

@router.get("/news/clusters/{cluster_id}")
def get_cluster(
    cluster_id: str,
    request: Request,
    _api_key: str = Depends(require_api_key),
    include_articles: bool = Query(default=True),
    include_evidence: bool = Query(default=True),
    include_analogs: bool = Query(default=True),
):
    # Placeholder: real implementation loads cluster by id.
    raise http_error(404, "not_found", f"Cluster not found: {cluster_id}")
