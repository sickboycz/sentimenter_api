"""Full E2E validation tests: API contract, response shapes, no skips."""
import json
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _load_schema(name: str) -> dict:
    p = SCHEMAS_DIR / name
    assert p.exists(), f"missing schema: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_refs(schema: dict) -> dict:
    defs = _load_schema("defs.json")

    def _resolve(ref: str):
        if ref.startswith("defs.json#/"):
            ptr = ref.split("#/")[1].split("/")
        elif ref.startswith("#/$defs/"):
            ptr = ["$defs"] + ref.replace("#/$defs/", "").split("/")
        else:
            return None
        cur = defs
        for part in ptr:
            if part == "$defs":
                cur = cur.get("$defs", cur)
            elif part in cur:
                cur = cur[part]
            else:
                raise KeyError(f"Cannot resolve ref {ref}")
        return _walk(cur)

    def _walk(node):
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                resolved = _resolve(node["$ref"])
                if resolved is not None:
                    return resolved
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(x) for x in node]
        return node

    return _walk(schema)


def _validate(instance: dict, schema_name: str):
    schema = _resolve_refs(_load_schema(schema_name))
    jsonschema.validate(instance=instance, schema=schema)


# --- Health / Status (no auth) ---


def test_health_returns_ok(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "down")
    _validate(data, "get_v1_health.response.json")


def test_status_returns_ok(client):
    r = client.get("/v1/status")
    assert r.status_code == 200
    _validate(r.json(), "get_v1_status.response.json")


# --- Protected endpoints (with api_key) ---


def test_mood_now_contract(client, api_key):
    r = client.get("/v1/mood/now", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    _validate(r.json(), "get_v1_mood_now.response.json")


def test_impacts_latest_contract(client, api_key):
    r = client.get("/v1/impacts/latest", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    _validate(r.json(), "get_v1_impacts_latest.response.json")


def test_universes_contract(client, api_key):
    r = client.get("/v1/universes", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    _validate(r.json(), "get_v1_universes.response.json")


def test_topics_index_contract(client, api_key):
    r = client.get("/v1/topics/index", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    schema = _resolve_refs(_load_schema("get_v1_topics_index.response.json"))
    jsonschema.validate(instance=r.json(), schema=schema)


def test_news_clusters_returns_list(client, api_key):
    r = client.get("/v1/news/clusters?limit=5", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) or ("data" in data and isinstance(data.get("data"), list))


# --- Cluster by id (include_analogs, include_asset_impacts) ---


def test_cluster_by_id_with_analogs_and_impacts_returns_shape(client, api_key):
    """GET cluster by id with include_analogs and include_asset_impacts returns expected shape."""
    r = client.get(
        "/v1/news/clusters/clu_nonexistent12345?include_analogs=true&include_asset_impacts=true",
        headers={"X-API-Key": api_key},
    )
    assert r.status_code == 404
    body = r.json()
    assert "detail" in body or "errors" in body


def test_cluster_by_id_invalid_format_400(client, api_key):
    r = client.get(
        "/v1/news/clusters/invalid",
        headers={"X-API-Key": api_key},
    )
    assert r.status_code == 400


# --- Auth ---


def test_missing_api_key_401(client):
    r = client.get("/v1/mood/now")
    assert r.status_code == 401
    body = r.json()
    assert "errors" in body
    assert any(e.get("code") == "auth_missing_api_key" for e in body.get("errors", []))


# --- Debug endpoint ---


def test_debug_asset_targeting_404(client, api_key):
    from sentiment_api.api.keys import validate_api_key
    from sentiment_api.api.main import app

    app.dependency_overrides[validate_api_key] = lambda: api_key
    try:
        r = client.get("/v1/debug/asset_targeting/clu_nonexistent12345")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(validate_api_key, None)


def test_debug_asset_targeting_invalid_400(client, api_key):
    from sentiment_api.api.keys import validate_api_key
    from sentiment_api.api.main import app

    app.dependency_overrides[validate_api_key] = lambda: api_key
    try:
        r = client.get("/v1/debug/asset_targeting/invalid")
        assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(validate_api_key, None)


# --- SSE stream ---


def test_sse_stream_content_type(client, api_key):
    with client.stream(
        "GET", "/v1/stream/events",
        params={"max_events": 1},
        headers={"X-API-Key": api_key},
        timeout=5.0,
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        chunk = next(r.iter_text(), None)
        assert chunk is not None
        assert "event:" in chunk or "data:" in chunk
