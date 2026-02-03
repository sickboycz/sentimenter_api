"""Unit tests: LLM asset targeting cache keys (v1.0)."""
from sentiment_api.engines.llm_asset_targeting.cache_keys import cache_key


def test_cache_key_stable():
    k1 = cache_key(
        cluster_id="clu_x",
        cluster_version=1,
        step="channel_infer",
        model="m",
        prompt_hash="p",
        packet_hash="ph",
        schema_hash="sh",
    )
    k2 = cache_key(
        cluster_id="clu_x",
        cluster_version=1,
        step="channel_infer",
        model="m",
        prompt_hash="p",
        packet_hash="ph",
        schema_hash="sh",
    )
    assert k1 == k2


def test_cache_key_different_per_step():
    k_a = cache_key(
        cluster_id="clu_x", cluster_version=1, step="channel_infer",
        model="m", prompt_hash="p", packet_hash="ph", schema_hash="sh",
    )
    k_b = cache_key(
        cluster_id="clu_x", cluster_version=1, step="sector_map",
        model="m", prompt_hash="p", packet_hash="ph", schema_hash="sh",
    )
    assert k_a != k_b
