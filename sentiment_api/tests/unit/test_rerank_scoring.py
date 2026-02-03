"""Unit tests: rerank scoring (cosine deterministic, fake provider)."""

import pytest

from sentiment_api.retrieval.models import Candidate, ScoreBreakdown
from sentiment_api.retrieval.provider import FakeEmbeddingProvider
from sentiment_api.retrieval.tierb_rerank import cosine_similarity, _parse_weights


def test_cosine_similarity_deterministic():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)
    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_fake_provider_deterministic():
    prov = FakeEmbeddingProvider()
    v1 = prov.embed_query("tierB_large", "hello")
    v2 = prov.embed_query("tierB_large", "hello")
    assert v1 == v2
    assert len(v1) == 768


def test_fake_provider_different_text_different_vector():
    prov = FakeEmbeddingProvider()
    v1 = prov.embed_query("tierB", "hello")
    v2 = prov.embed_query("tierB", "world")
    assert v1 != v2


def test_parse_weights():
    w = _parse_weights('{"tierA":0.2,"bm25":0.2,"tierB":0.6,"cross":0.0}')
    assert w["tierA"] == 0.2
    assert w["tierB"] == 0.6
    w2 = _parse_weights("invalid")
    assert w2["tierB"] == 0.6  # default


def test_score_breakdown_to_dict():
    s = ScoreBreakdown(tier_a=0.1, bm25=0.2, tier_b=0.7, cross=0.0, final=0.5)
    d = s.to_dict()
    assert d["tierA"] == 0.1
    assert d["final"] == 0.5
