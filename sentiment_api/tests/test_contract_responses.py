"""Contract tests: responses must match JSON schemas (v1.2)."""
import json
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


def _load_schema(name: str) -> dict:
    p = SCHEMAS_DIR / name
    assert p.exists(), f"missing schema: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_refs(schema: dict) -> dict:
    defs = _load_schema("defs.json")
    defs_map = defs.get("$defs", defs)

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


def test_health_contract(client):
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_health.response.json")


def test_status_contract(client):
    resp = client.get("/v1/status")
    assert resp.status_code == 200
    _validate(resp.json(), "get_v1_status.response.json")


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
