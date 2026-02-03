"""Unit tests: RealEmbeddingProvider timeout/retry config (no network)."""

import pytest

from sentiment_api.retrieval.provider import RealEmbeddingProvider


def test_real_provider_has_timeout_and_retries():
    """RealEmbeddingProvider reads timeout and retries from settings."""
    prov = RealEmbeddingProvider()
    assert hasattr(prov, "_timeout_sec")
    assert hasattr(prov, "_retries")
    assert prov._timeout_sec > 0
    assert prov._retries >= 0
