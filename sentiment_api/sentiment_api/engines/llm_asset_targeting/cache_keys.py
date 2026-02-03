"""Cache key generation for LLM call cache."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def schema_hash(schema: Dict[str, Any]) -> str:
    return sha256_str(canonical_json(schema))

def prompt_hash(system_prompt: str, user_prompt: str) -> str:
    return sha256_str(system_prompt + "\n---\n" + user_prompt)

def cache_key(
    *,
    cluster_id: str,
    cluster_version: int,
    step: str,
    model: str,
    prompt_hash: str,
    packet_hash: str,
    schema_hash: str,
) -> str:
    raw = f"{cluster_id}:{cluster_version}:{step}:{model}:{prompt_hash}:{packet_hash}:{schema_hash}"
    return sha256_str(raw)
