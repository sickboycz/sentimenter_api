"""M0 — Source Registry loader and validator.

AC-M0.1: loads registry (YAML/JSON), validates schema, refuses to start on invalid config
AC-M0.2: unique immutable source_id
AC-M0.3: per-source enable/disable without code
AC-M0.4: packs enable/disable
"""

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, ValidationError
from pydantic import ValidationError as PydanticValidationError

from sentiment_api.registry.models import (
    Pack,
    QueryProfile,
    RegistryDefaults,
    Source,
    SourceAuth,
    SourceRegistry,
)


class RegistryError(Exception):
    """Raised when registry validation fails."""

    pass


def _load_json_schema() -> dict:
    schema_path = (
        Path(__file__).resolve().parent.parent.parent
        / "Docs"
        / "sentiment_api_tech_package_v1.1"
        / "registry"
        / "source_registry.schema.json"
    )
    if not schema_path.exists():
        return {}
    return json.loads(schema_path.read_text())


def _validate_json_schema(data: dict) -> list[str]:
    """Validate against JSON Schema; return list of error messages."""
    schema = _load_json_schema()
    if not schema:
        return []
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in validator.iter_errors(data):
        errors.append(f"{err.json_path}: {err.message}")
    return errors


def _parse_source(raw: dict) -> Source:
    """Parse a single source, applying type-specific validation."""
    data = dict(raw)
    auth = data.get("auth")
    if auth and isinstance(auth, dict):
        data["auth"] = SourceAuth(**auth)
    qp = data.get("query_profiles")
    if qp:
        data["query_profiles"] = [QueryProfile(**p) for p in qp]
    src_type = data.get("type")
    if src_type == "rss" and not data.get("feed_url"):
        raise RegistryError(f"Source {data.get('source_id')}: type=rss requires feed_url")
    if src_type == "scrape" and not data.get("page_url"):
        raise RegistryError(f"Source {data.get('source_id')}: type=scrape requires page_url")
    if src_type == "gdelt" and not data.get("base_url"):
        raise RegistryError(f"Source {data.get('source_id')}: type=gdelt requires base_url")
    return Source(**data)


def load_registry(path: Path | str) -> SourceRegistry:
    """Load and validate source registry from YAML or JSON.

    Raises RegistryError on invalid config (AC-M0.1).
    """
    path = Path(path)
    if not path.exists():
        raise RegistryError(f"Registry file not found: {path}")

    raw = path.read_text()
    if path.suffix in (".json",):
        data = json.loads(raw)
    else:
        data = yaml.safe_load(raw)

    if not isinstance(data, dict):
        raise RegistryError("Registry must be a YAML/JSON object")

    # JSON Schema validation
    schema_errors = _validate_json_schema(data)
    if schema_errors:
        raise RegistryError("Registry schema validation failed:\n" + "\n".join(schema_errors))

    # Parse with Pydantic
    try:
        defaults = RegistryDefaults(**(data.get("defaults") or {}))
        packs = {
            k: Pack(**v) if isinstance(v, dict) else Pack(enabled=bool(v))
            for k, v in (data.get("packs") or {}).items()
        }
        sources_raw = data.get("sources") or []
        sources: list[Source] = []
        seen_ids: set[str] = set()
        for i, sraw in enumerate(sources_raw):
            try:
                src = _parse_source(dict(sraw))
            except (PydanticValidationError, RegistryError) as e:
                raise RegistryError(f"Source at index {i}: {e}") from e
            if src.source_id in seen_ids:
                raise RegistryError(f"Duplicate source_id: {src.source_id} (AC-M0.2)")
            seen_ids.add(src.source_id)
            sources.append(src)

        return SourceRegistry(
            version=data.get("version", "1.0"),
            defaults=defaults,
            packs=packs,
            sources=sources,
        )
    except PydanticValidationError as e:
        raise RegistryError(f"Registry validation failed: {e}") from e
