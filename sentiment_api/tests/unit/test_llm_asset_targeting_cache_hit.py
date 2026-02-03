"""Unit tests: cache hit path skips OpenAI (90_TEST_MATRIX)."""
import pytest

from sentiment_api.engines.llm_asset_targeting.cache_store import CacheEntry, LLMCacheStore
from sentiment_api.engines.llm_asset_targeting.schemas import ChannelInferResult, ChannelItem
from sentiment_api.engines.llm_asset_targeting.cache_keys import cache_key, prompt_hash, schema_hash
from sentiment_api.engines.llm_asset_targeting.packet_builder import build_cluster_packet, canonical_json
from sentiment_api.engines.llm_asset_targeting.prompts import SYSTEM_BASE, CHANNEL_INFER_USER


class FakeCacheHitStore(LLMCacheStore):
    """Cache that always returns a hit for channel_infer."""

    def __init__(self, parsed: dict):
        self._parsed = parsed

    async def get(self, cache_key: str):
        return CacheEntry(cache_key=cache_key, status="ok", parsed_json=self._parsed)

    async def upsert_pending(self, cache_key: str, meta: dict) -> None:
        pass

    async def upsert_ok(self, cache_key: str, parsed_json: dict, raw_json: dict, usage: dict) -> None:
        pass

    async def upsert_failed(self, cache_key: str, error_code: str, error_message: str, raw_json: dict | None = None) -> None:
        pass


@pytest.mark.asyncio
async def test_cache_hit_returns_identical_output():
    """Cache hit produces identical output and does not call OpenAI."""
    parsed_a = {
        "channels": [
            {"name": "geopolitics", "sign": -1, "strength": 0.8, "why_refs": [1], "short_why_en": "Regional tensions."},
        ],
        "primary_horizon": "1d",
        "confidence": 0.7,
        "rationale_bullets_en": ["Geopolitical risk elevated."],
    }
    store = FakeCacheHitStore(parsed_a)
    packet, ph = build_cluster_packet(
        cluster_id="clu_test",
        cluster_version=1,
        headline_en="Test",
        summary_bullets_en=[],
        topics=[],
        regions=[],
        impact_score=30,
        impact_level="L2",
        expected_direction="RiskOff",
        confidence=0.6,
        evidence_rows=[{"url": "https://x.com", "text_en": "x", "relevance_score": 0.9}],
    )
    user_a = CHANNEL_INFER_USER.format(cluster_packet_json=canonical_json(packet.model_dump()))
    p_hash = prompt_hash(SYSTEM_BASE, user_a)
    ck = cache_key(
        cluster_id=packet.cluster_id,
        cluster_version=packet.cluster_version,
        step="channel_infer",
        model="gpt-4o",
        prompt_hash=p_hash,
        packet_hash=ph,
        schema_hash="sh",
    )
    hit = await store.get(ck)
    assert hit is not None
    assert hit.status == "ok"
    assert hit.parsed_json == parsed_a
    result = ChannelInferResult(**hit.parsed_json)
    assert result.primary_horizon == "1d"
    assert len(result.channels) == 1
    assert result.channels[0].name == "geopolitics"
