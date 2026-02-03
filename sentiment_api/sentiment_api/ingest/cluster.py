"""M3 — Clustering by embedding similarity."""

import hashlib
import base64
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sentiment_api.ingest.cluster")


def cluster_id(canonical_story_key: str, first_seen: datetime) -> str:
    """Generate stable cluster_id: clu_<hash>."""
    ts = first_seen.isoformat() if first_seen else ""
    key = f"{canonical_story_key}|{ts}"
    h = hashlib.sha256(key.encode()).digest()[:15]
    b32 = base64.urlsafe_b64encode(h).decode().rstrip("=").lower()
    return f"clu_{b32}"


def _to_float_vec(x: list[float] | list[Any] | str, dim_hint: int | None = None) -> Any:
    """Convert embedding-like value to np.float32 vector; return None if invalid."""
    import numpy as np
    if isinstance(x, str):
        try:
            import json
            x = json.loads(x)
        except (TypeError, ValueError):
            return None
    if not isinstance(x, list) or not x:
        return None
    try:
        arr = np.array(x, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if arr.ndim != 1 or arr.size == 0:
        return None
    if dim_hint is not None and arr.size != dim_hint:
        return None
    return arr


def find_nearest_cluster(
    embedding: list[float],
    clusters: list[tuple[str, list[float], datetime]],
    threshold: float = 0.85,
) -> tuple[str | None, float]:
    """Find nearest cluster by cosine similarity. Returns (cluster_id or None, best_sim). best_sim is the max similarity seen (for logging)."""
    import numpy as np
    vec = _to_float_vec(embedding)
    if vec is None or not clusters:
        return (None, 0.0)
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        return (None, 0.0)
    best_id = None
    best_sim = -1.0
    dim_hint = vec.size
    for cid, cvec, _ in clusters:
        c = _to_float_vec(cvec, dim_hint=dim_hint)
        if c is None:
            continue
        cn = np.linalg.norm(c)
        if cn == 0:
            continue
        sim = float(np.dot(vec, c) / (vec_norm * cn))
        if sim > best_sim:
            best_sim = sim
            best_id = cid if sim > threshold else None
    return (best_id, best_sim if best_sim >= 0 else 0.0)


def canonical_story_key(headline: str, topics: list[str]) -> str:
    """Derive stable key for clustering."""
    t = "|".join(sorted(topics)) if topics else "general"
    h = (headline or "")[:100].lower()
    return hashlib.sha256(f"{t}|{h}".encode()).hexdigest()[:32]
