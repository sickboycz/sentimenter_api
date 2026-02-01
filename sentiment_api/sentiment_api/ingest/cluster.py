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


def find_nearest_cluster(
    embedding: list[float],
    clusters: list[tuple[str, list[float], datetime]],
    threshold: float = 0.85,
) -> str | None:
    """Find nearest cluster by cosine similarity. Returns cluster_id or None."""
    import numpy as np
    if not embedding or not clusters:
        return None
    vec = np.array(embedding, dtype=np.float32)
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        return None
    best_id = None
    best_sim = threshold
    for cid, cvec, _ in clusters:
        c = np.array(cvec, dtype=np.float32)
        cn = np.linalg.norm(c)
        if cn == 0:
            continue
        sim = float(np.dot(vec, c) / (vec_norm * cn))
        if sim > best_sim:
            best_sim = sim
            best_id = cid
    return best_id


def canonical_story_key(headline: str, topics: list[str]) -> str:
    """Derive stable key for clustering."""
    t = "|".join(sorted(topics)) if topics else "general"
    h = (headline or "")[:100].lower()
    return hashlib.sha256(f"{t}|{h}".encode()).hexdigest()[:32]
