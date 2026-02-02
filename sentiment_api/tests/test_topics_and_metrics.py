"""Topics index and metrics (v1.2)."""
import json
from pathlib import Path
import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"


def _load(name):
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _resolve_refs(schema: dict) -> dict:
    defs = _load("defs.json")

    def _resolve(ref: str):
        if ref.startswith("defs.json#/"):
            ptr = ref.split("#/")[1].split("/")
        elif ref.startswith("#/$defs/"):
            ptr = ["$defs"] + ref.replace("#/$defs/", "").split("/")
        else:
            return None
        cur = defs
        for part in ptr:
            cur = cur[part]
        return _walk(cur)

    def _walk(node):
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                r = _resolve(node["$ref"])
                if r is not None:
                    return r
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(x) for x in node]
        return node

    return _walk(schema)


def test_topics_index_contract(client, api_key):
    resp = client.get("/v1/topics/index", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    schema = _resolve_refs(_load("get_v1_topics_index.response.json"))
    jsonschema.validate(instance=resp.json(), schema=schema)


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
