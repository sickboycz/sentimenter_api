"""Unit tests: embedding cache (hashing, serialization, hit/miss)."""

import tempfile
from pathlib import Path

import pytest

from sentiment_api.retrieval.embedding_cache_sqlite import (
    EmbeddingCacheSqlite,
    text_hash,
    _normalize_text,
    _vector_to_blob,
    _blob_to_vector,
)


def test_text_hash_deterministic():
    t = "  Hello   World  "
    h1 = text_hash(t)
    h2 = text_hash(t)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_text_hash_normalized():
    assert text_hash("  a  b  ") == text_hash("a b")
    assert text_hash("") == text_hash("   ")


def test_normalize_text():
    assert _normalize_text("  a  b  ") == "a b"
    assert _normalize_text("") == ""


def test_vector_blob_roundtrip():
    vec = [0.1, -0.2, 0.3]
    blob = _vector_to_blob(vec)
    back = _blob_to_vector(blob)
    assert len(back) == len(vec)
    for a, b in zip(back, vec):
        assert a == pytest.approx(b)


def test_embedding_cache_put_get():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.sqlite"
        cache = EmbeddingCacheSqlite(path)
        cache.put_cached_vector("model1", "hash1", [1.0, 2.0, 3.0])
        out = cache.get_cached_vector("model1", "hash1")
        assert out == [1.0, 2.0, 3.0]
        cache.close()


def test_embedding_cache_miss_returns_none():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.sqlite"
        cache = EmbeddingCacheSqlite(path)
        out = cache.get_cached_vector("model1", "nonexistent")
        assert out is None
        cache.close()


def test_embedding_cache_stats():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.sqlite"
        cache = EmbeddingCacheSqlite(path)
        cache.put_cached_vector("m", "h1", [1.0])
        cache.get_cached_vector("m", "h1")  # hit
        cache.get_cached_vector("m", "h2")  # miss
        hit, miss = cache.get_stats()
        assert hit == 1
        assert miss == 1
        cache.close()


def test_embedding_cache_overwrite():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.sqlite"
        cache = EmbeddingCacheSqlite(path)
        cache.put_cached_vector("m", "h", [1.0, 2.0])
        cache.put_cached_vector("m", "h", [3.0, 4.0])
        out = cache.get_cached_vector("m", "h")
        assert out == [3.0, 4.0]
        cache.close()
