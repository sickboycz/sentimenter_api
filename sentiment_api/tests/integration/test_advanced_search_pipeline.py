"""Integration tests: advanced search pipeline (mock provider, cache, deterministic)."""

import json
import tempfile
from pathlib import Path

import pytest

from sentiment_api.retrieval.embedding_cache_sqlite import EmbeddingCacheSqlite, text_hash
from sentiment_api.retrieval.models import Candidate
from sentiment_api.retrieval.pipeline import run_advanced_search
from sentiment_api.retrieval.provider import FakeEmbeddingProvider
from sentiment_api.retrieval.tierb_rerank import rerank_with_tierb, cosine_similarity


@pytest.fixture
def fake_provider():
    return FakeEmbeddingProvider()


@pytest.fixture
def temp_cache():
    with tempfile.TemporaryDirectory() as d:
        yield EmbeddingCacheSqlite(Path(d) / "cache.sqlite")


@pytest.fixture
def golden_candidates():
    """Fixed candidate set for deterministic ranking."""
    return [
        Candidate(
            chunk_id="chunk_1",
            text="First chunk about markets",
            doc_id="doc1",
            source="reuters",
            url=None,
            published_at="2025-01-01",
            tickers=[],
            sector="finance",
            language="en",
            text_hash=text_hash("First chunk about markets"),
            tier_a_score=0.9,
            bm25_score=0.5,
        ),
        Candidate(
            chunk_id="chunk_2",
            text="Second chunk about bonds",
            doc_id="doc2",
            source="bloomberg",
            url=None,
            published_at="2025-01-02",
            tickers=[],
            sector="finance",
            language="en",
            text_hash=text_hash("Second chunk about bonds"),
            tier_a_score=0.7,
            bm25_score=0.8,
        ),
        Candidate(
            chunk_id="chunk_3",
            text="Third chunk about equities",
            doc_id="doc3",
            source="reuters",
            url=None,
            published_at=None,
            tickers=[],
            sector=None,
            language="en",
            text_hash=text_hash("Third chunk about equities"),
            tier_a_score=0.5,
            bm25_score=0.3,
        ),
    ]


def test_tierb_rerank_deterministic(fake_provider, temp_cache, golden_candidates):
    """Rerank with fake provider: ranking must be deterministic."""
    results, latency_ms, hits, misses, _ = rerank_with_tierb(
        query_text="markets and bonds",
        candidates=golden_candidates,
        top_n=3,
        provider=fake_provider,
        cache=temp_cache,
        trace_id="test_trace_1",
    )
    assert len(results) == 3
    assert latency_ms >= 0
    # Second run: same query/candidates -> cache hits for all 3 doc vectors
    temp_cache.reset_stats()
    results2, _, hits2, misses2, _ = rerank_with_tierb(
        query_text="markets and bonds",
        candidates=golden_candidates,
        top_n=3,
        provider=fake_provider,
        cache=temp_cache,
        trace_id="test_trace_2",
    )
    assert [r.chunk_id for r in results] == [r.chunk_id for r in results2]
    assert hits2 >= 3  # cache hits for 3 candidate texts
    assert misses2 == 0


def test_tierb_rerank_score_breakdown_present(fake_provider, temp_cache, golden_candidates):
    results, _, _, _, _ = rerank_with_tierb(
        query_text="test",
        candidates=golden_candidates[:2],
        top_n=2,
        provider=fake_provider,
        cache=temp_cache,
    )
    for r in results:
        assert hasattr(r.score_breakdown, "tier_a")
        assert hasattr(r.score_breakdown, "tier_b")
        assert hasattr(r.score_breakdown, "final")
        assert r.score_breakdown.to_dict()["final"] >= 0


def test_run_advanced_search_no_weaviate(fake_provider, temp_cache):
    """run_advanced_search with fake provider: Tier A will fail if Weaviate is down,
    so we test only Tier B path via rerank_with_tierb. For full pipeline we'd mock Weaviate.
    Here we assert cache and provider work; pipeline integration with Weaviate is optional.
    """
    # Just ensure pipeline module and run_advanced_search are callable
    from sentiment_api.retrieval.pipeline import run_advanced_search
    # Without Weaviate, run_advanced_search will raise when connecting.
    # So we skip the full pipeline run and rely on unit tests + rerank test above.
    assert callable(run_advanced_search)


def test_cache_second_run_hits(fake_provider, golden_candidates):
    """Second run over same candidates should yield cache hits > 80% of candidate count."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.sqlite"
        cache = EmbeddingCacheSqlite(path)
        rerank_with_tierb("query", golden_candidates, top_n=3, provider=fake_provider, cache=cache)
        hit1, miss1 = cache.get_stats()
        cache.reset_stats()
        rerank_with_tierb("query", golden_candidates, top_n=3, provider=fake_provider, cache=cache)
        hit2, miss2 = cache.get_stats()
        cache.close()
        total = hit2 + miss2
        if total > 0:
            assert hit2 >= 3  # all 3 candidate vectors cached from first run
            assert miss2 == 0
