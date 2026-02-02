from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI = ROOT / "openapi" / "sentiment_api.openapi.v1.2.yaml"
SCHEMAS_DIR = ROOT / "openapi" / "schemas"

def test_openapi_file_exists_and_parses():
    assert OPENAPI.exists()
    data = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")
    assert "paths" in data

def test_openapi_schema_refs_exist():
    data = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    dumped = yaml.safe_dump(data)
    refs = re.findall(r"\$ref:\s*([^\s]+)", dumped)
    # We only care about refs into ../schemas/ or ../schemas/*.json
    for ref in refs:
        if ref.startswith("../schemas/"):
            rel = ref.replace("../schemas/", "")
            # strip any fragment
            rel = rel.split("#", 1)[0]
            p = SCHEMAS_DIR / rel
            assert p.exists(), f"Missing schema referenced by OpenAPI: {ref} -> {p}"
