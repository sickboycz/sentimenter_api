"""Unit tests: chunk_ingest (chunk_text, ChunkDoc)."""

import pytest

from sentiment_api.retrieval.chunk_ingest import ChunkDoc, chunk_text


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_single_short():
    assert chunk_text("hello") == ["hello"]


def test_chunk_text_deterministic():
    t = "a" * 1000
    c1 = chunk_text(t, max_chars=200, overlap_chars=20)
    c2 = chunk_text(t, max_chars=200, overlap_chars=20)
    assert c1 == c2


def test_chunk_text_overlap():
    t = "one two three four five six seven eight nine ten"
    chunks = chunk_text(t, max_chars=15, overlap_chars=5)
    assert len(chunks) >= 2
    assert all(len(c) <= 15 for c in chunks)


def test_chunk_doc_minimal():
    d = ChunkDoc(text="x", doc_id="doc1")
    assert d.text == "x"
    assert d.doc_id == "doc1"
    assert d.source == ""
    assert d.url is None
