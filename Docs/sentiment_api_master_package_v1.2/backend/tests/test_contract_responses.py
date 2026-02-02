import json
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "openapi" / "schemas"

def _load_schema(name: str) -> dict:
    p = SCHEMAS_DIR / name
    assert p.exists(), f"missing schema: {p}"
    return json.loads(p.read_text(encoding="utf-8"))

def _resolve_refs(schema: dict) -> dict:
    # Minimal ref resolver for local defs.json references used by this project.
    # jsonschema supports ref resolution with a resolver, but we keep it simple here:
    # only handle refs like "defs.json#/$defs/Thing".
    defs = _load_schema("defs.json")
    def _walk(node):
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("defs.json#/"):
                ptr = node["$ref"].split("#/")[1]
                parts = ptr.split("/")
                cur = defs
                for part in parts:
                    if part in cur:
                        cur = cur[part]
                    else:
                        raise KeyError(f"Cannot resolve ref {node['$ref']}")
                return _walk(cur)
            return {k: _walk(v) for k,v in node.items()}
        if isinstance(node, list):
            return [_walk(x) for x in node]
        return node
    return _walk(schema)

def _validate(instance: dict, schema_name: str):
    schema = _resolve_refs(_load_schema(schema_name))
    jsonschema.validate(instance=instance, schema=schema)

def test_health_contract(client):
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_health.response.json")

def test_mood_now_contract(client, api_key):
    resp = client.get("/v1/mood/now", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_mood_now.response.json")

def test_impacts_latest_contract(client, api_key):
    resp = client.get("/v1/impacts/latest", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_impacts_latest.response.json")

def test_universes_contract(client, api_key):
    resp = client.get("/v1/universes", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_universes.response.json")
