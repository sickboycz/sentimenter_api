"""M3 — Deduplication (URL + content hash)."""

import hashlib
import base64


def article_id(source_id: str, canonical_url: str, published_at_str: str) -> str:
    """Generate stable article_id: art_<base32url(hash)> (AC id strategy)."""
    key = f"{source_id}|{canonical_url}|{published_at_str}"
    h = hashlib.sha256(key.encode()).digest()[:15]
    b32 = base64.urlsafe_b64encode(h).decode().rstrip("=").lower()
    return f"art_{b32}"


def content_fingerprint(text: str) -> str:
    """MinHash-style fingerprint for near-dedup (simplified: hash of normalized text)."""
    normalized = " ".join(text.lower().split())[:10000]
    return hashlib.sha256(normalized.encode()).hexdigest()
