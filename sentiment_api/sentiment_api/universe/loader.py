"""Load and validate universe registry."""

import json
from pathlib import Path

import yaml

from sentiment_api.universe.models import UniverseDef, UniverseRegistry


def load_universe_registry(path: Path | str) -> UniverseRegistry:
    """Load universe registry from YAML/JSON."""
    path = Path(path)
    if not path.exists():
        return UniverseRegistry(version="1.1", universes=[])
    raw = path.read_text()
    data = yaml.safe_load(raw) if path.suffix in (".yaml", ".yml") else json.loads(raw)
    universes = [UniverseDef(**u) for u in (data.get("universes") or [])]
    return UniverseRegistry(version=data.get("version", "1.1"), universes=universes)
