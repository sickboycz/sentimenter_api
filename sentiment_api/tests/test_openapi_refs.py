"""OpenAPI schema refs exist (v1.2)."""
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "openapi" / "sentiment_api.openapi.v1.2.yaml"
SCHEMAS_DIR = ROOT / "schemas"


def test_openapi_file_exists_and_parses():
    assert OPENAPI.exists()
    data = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")
    assert "paths" in data


def test_openapi_schema_refs_exist():
    data = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    dumped = yaml.safe_dump(data)
    refs = re.findall(r"\$ref:\s*([^\s]+)", dumped)
    for ref in refs:
        if ref.startswith("../schemas/") or "schemas/" in ref:
            rel = ref.replace("../schemas/", "").split("#", 1)[0]
            if rel:
                p = SCHEMAS_DIR / rel
                assert p.exists(), f"Missing schema referenced by OpenAPI: {ref} -> {p}"
