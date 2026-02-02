from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DEFAULT_REGISTRY_PATHS = [
    Path("./registry/sources.yaml"),
    Path("/app/registry/sources.yaml"),
]

@dataclass(frozen=True)
class SourceRef:
    source_id: str
    name: str
    type: str
    credibility_tier: str
    license_class: str

def load_registry(path: Optional[str] = None) -> Dict[str, Any]:
    candidates: List[Path] = []
    if path:
        candidates.append(Path(path))
    candidates.extend(DEFAULT_REGISTRY_PATHS)
    for p in candidates:
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("registry must be a mapping")
            return data
    return {"version":"0.0","defaults":{},"packs":{},"sources":[]}

def list_sources(enabled_only: bool = False, types: Optional[list[str]] = None, *, registry_path: Optional[str] = None) -> list[dict]:
    reg = load_registry(registry_path)
    out: list[dict] = []
    for s in reg.get("sources", []):
        if enabled_only and not s.get("enabled", False):
            continue
        if types and s.get("type") not in types:
            continue
        out.append({
            "source_id": s.get("source_id",""),
            "name": s.get("name",""),
            "type": s.get("type",""),
            "credibility_tier": s.get("credibility_tier","user_added"),
            "license_class": s.get("license_class","open"),
        })
    return out
