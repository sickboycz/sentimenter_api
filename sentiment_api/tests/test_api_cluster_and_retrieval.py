"""API tests: GET cluster by id (validation, 404), POST retrieval/ingest (validation)."""

import pytest


@pytest.fixture(autouse=True)
def override_auth(client):
    """Use env API key so tests do not require DB for auth."""
    from sentiment_api.api.keys import validate_api_key
    from sentiment_api.api.main import app
    app.dependency_overrides[validate_api_key] = lambda: "test_key_1234567890abcdef"
    yield
    app.dependency_overrides.pop(validate_api_key, None)


def test_cluster_by_id_invalid_format_returns_400(client):
    """Invalid cluster_id format (not clu_...) returns 400."""
    r = client.get("/v1/news/clusters/invalid")
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body or "errors" in body


def test_cluster_by_id_short_id_returns_400(client):
    """cluster_id too short (clu_ + < 10 chars) returns 400."""
    r = client.get("/v1/news/clusters/clu_short")
    assert r.status_code == 400


def test_cluster_by_id_not_found_returns_404(client):
    """Valid format but non-existent cluster returns 404."""
    r = client.get("/v1/news/clusters/clu_nonexistent12345")
    assert r.status_code == 404
    body = r.json()
    assert "detail" in body or "errors" in body


def test_retrieval_ingest_empty_body_returns_400(client):
    """POST /v1/retrieval/ingest with empty body or missing documents returns 400."""
    r = client.post("/v1/retrieval/ingest", json={})
    assert r.status_code == 400
    assert "documents" in (r.json().get("detail") or "").lower() or "errors" in r.json()


def test_retrieval_ingest_empty_documents_array_returns_400(client):
    """POST /v1/retrieval/ingest with documents=[] returns 400."""
    r = client.post("/v1/retrieval/ingest", json={"documents": []})
    assert r.status_code == 400


def test_retrieval_ingest_doc_missing_text_returns_400(client):
    """Each document must have text and doc_id."""
    r = client.post("/v1/retrieval/ingest", json={"documents": [{"doc_id": "d1"}]})
    assert r.status_code == 400


def test_retrieval_ingest_doc_missing_doc_id_returns_400(client):
    """Each document must have text and doc_id."""
    r = client.post("/v1/retrieval/ingest", json={"documents": [{"text": "Hello world"}]})
    assert r.status_code == 400


def test_search_advanced_missing_query_returns_400(client):
    """POST /v1/search/advanced with empty query returns 400."""
    r = client.post("/v1/search/advanced", json={"query": ""})
    assert r.status_code == 400


def test_search_advanced_no_body_returns_400(client):
    """POST /v1/search/advanced with no body returns 400."""
    r = client.post("/v1/search/advanced", json={})
    assert r.status_code == 400
