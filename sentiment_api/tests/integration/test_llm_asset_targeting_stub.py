"""Integration test: chunked asset targeting with stub provider (no OpenAI calls)."""
import os
import pytest
from pathlib import Path

from sentiment_api.engines.llm_asset_targeting.schemas import ClusterPacket, ChannelInferResult, SectorMapResult, TickerSelectResult
from sentiment_api.engines.llm_asset_targeting.packet_builder import build_cluster_packet
from sentiment_api.engines.llm_asset_targeting.allocator import allocate
from sentiment_api.engines.llm_asset_targeting.cache_store import LLMCacheStore
from sentiment_api.engines.llm_asset_targeting.openai_provider import LLMUsage


class StubOpenAIProvider:
    """Stub that returns predefined JSON for channel_infer, sector_map, ticker_select."""

    def __init__(self):
        self.model = "stub"

    def call_structured(self, *, name, schema, system_prompt, user_prompt, max_output_tokens, temperature=0.0, metadata=None):
        if "ChannelInfer" in name:
            parsed = {
                "channels": [
                    {"name": "geopolitics", "sign": -1, "strength": 0.7, "why_refs": [1], "short_why_en": "Regional tensions."},
                    {"name": "energy_supply", "sign": -1, "strength": 0.5, "why_refs": [1], "short_why_en": "Supply concerns."},
                ],
                "primary_horizon": "1d",
                "confidence": 0.65,
                "rationale_bullets_en": ["Geopolitical risk elevated.", "Energy supply uncertainty."],
            }
        elif "SectorMap" in name:
            parsed = {
                "sectors": [
                    {"sector_id": "ENERGY", "sector_name_en": "Energy", "direction": "down", "strength": 0.7, "confidence": 0.6, "why_refs": [1], "industries": [], "short_why_en": "Energy exposure."},
                    {"sector_id": "IND", "sector_name_en": "Industrials", "direction": "down", "strength": 0.4, "confidence": 0.5, "why_refs": [], "industries": [], "short_why_en": "Defense sector."},
                ],
            }
        elif "TickerSelect" in name:
            parsed = {
                "winners": [],
                "losers": [
                    {"symbol": "XOM", "strength": 0.8, "why_refs": [1], "short_why_en": "Energy exposure."},
                    {"symbol": "LMT", "strength": 0.6, "why_refs": [], "short_why_en": "Defense."},
                ],
            }
        else:
            parsed = {}
        return parsed, LLMUsage(tokens_in=0, tokens_out=0, latency_ms=0)


class EmptyCacheStore(LLMCacheStore):
    """Cache that never has hits (always miss)."""

    async def get(self, cache_key: str):
        return None

    async def upsert_pending(self, cache_key: str, meta: dict) -> None:
        pass

    async def upsert_ok(self, cache_key: str, parsed_json: dict, raw_json: dict, usage: dict) -> None:
        pass

    async def upsert_failed(self, cache_key: str, error_code: str, error_message: str, raw_json: dict | None = None) -> None:
        pass


@pytest.mark.asyncio
async def test_allocator_deterministic_reproducibility(tmp_path):
    """Allocation math is deterministic for same inputs."""
    registry_dir = Path(__file__).resolve().parents[2] / "registry" / "llm_asset_targeting"
    beta_m = registry_dir / "beta_market.yaml"
    beta_s = registry_dir / "beta_sector.yaml"
    exp = registry_dir / "ticker_exposures.csv"
    assert beta_m.exists() and beta_s.exists() and exp.exists(), "Registry files not found"

    packet, ph = build_cluster_packet(
        cluster_id="clu_test",
        cluster_version=1,
        headline_en="Oil prices spike on supply concerns",
        summary_bullets_en=["OPEC cuts output.", "Geopolitical tension."],
        topics=["energy", "geopolitics"],
        regions=["US"],
        impact_score=35,
        impact_level="L3",
        expected_direction="RiskOff",
        confidence=0.7,
        evidence_rows=[{"url": "https://x.com", "text_en": "Oil up.", "relevance_score": 0.9}],
    )
    call_a = ChannelInferResult(
        channels=[
            {"name": "geopolitics", "sign": -1, "strength": 0.7, "why_refs": [1], "short_why_en": "x"},
            {"name": "energy_supply", "sign": -1, "strength": 0.6, "why_refs": [1], "short_why_en": "x"},
        ],
        primary_horizon="1d",
        confidence=0.65,
        rationale_bullets_en=["Risk off."],
    )
    call_b = SectorMapResult(
        sectors=[
            {"sector_id": "ENERGY", "sector_name_en": "Energy", "direction": "down", "strength": 0.7, "confidence": 0.6, "why_refs": [1], "industries": [], "short_why_en": "x"},
            {"sector_id": "IND", "sector_name_en": "Industrials", "direction": "down", "strength": 0.4, "confidence": 0.5, "why_refs": [], "industries": [], "short_why_en": "x"},
        ],
    )
    call_c = TickerSelectResult(
        winners=[],
        losers=[
            {"symbol": "XOM", "strength": 0.8, "why_refs": [1], "short_why_en": "x"},
            {"symbol": "LMT", "strength": 0.6, "why_refs": [], "short_why_en": "x"},
        ],
    )

    alloc1 = allocate(
        packet=packet,
        call_a=call_a,
        call_b=call_b,
        call_c=call_c,
        beta_market_path=str(beta_m),
        beta_sector_path=str(beta_s),
        exposures_csv_path=str(exp),
    )
    alloc2 = allocate(
        packet=packet,
        call_a=call_a,
        call_b=call_b,
        call_c=call_c,
        beta_market_path=str(beta_m),
        beta_sector_path=str(beta_s),
        exposures_csv_path=str(exp),
    )
    assert alloc1.model_dump() == alloc2.model_dump()
    assert alloc1.horizon == "1d"
    assert len(alloc1.markets) > 0
    assert len(alloc1.sectors) > 0


@pytest.mark.asyncio
async def test_runner_with_stub_provider_no_openai(tmp_path):
    """Pipeline run with stub LLM outputs; no OpenAI calls."""
    registry_dir = Path(__file__).resolve().parents[2] / "registry" / "llm_asset_targeting"
    assert (registry_dir / "beta_market.yaml").exists(), f"Registry not found: {registry_dir}"

    from sentiment_api.engines.llm_asset_targeting.runner import ChunkedAssetTargetingRunner
    from sentiment_api.engines.llm_asset_targeting.security_master import CSVSecurityMaster

    stub = StubOpenAIProvider()
    cache = EmptyCacheStore()
    sec = CSVSecurityMaster(exposures_csv=str(registry_dir / "ticker_exposures.csv"))

    runner = ChunkedAssetTargetingRunner(
        provider=stub,
        cache=cache,
        security_master=sec,
        rulesets_path=str(registry_dir / "channel_rulesets.yaml"),
        schema_dir=str(registry_dir),
        beta_market_path=str(registry_dir / "beta_market.yaml"),
        beta_sector_path=str(registry_dir / "beta_sector.yaml"),
        exposures_csv_path=str(registry_dir / "ticker_exposures.csv"),
    )

    packet, ph = build_cluster_packet(
        cluster_id="clu_stub_test",
        cluster_version=1,
        headline_en="Oil prices spike",
        summary_bullets_en=["OPEC cuts."],
        topics=["energy"],
        regions=["US"],
        impact_score=35,
        impact_level="L3",
        expected_direction="RiskOff",
        confidence=0.7,
        evidence_rows=[{"url": "https://x.com", "text_en": "Oil up.", "relevance_score": 0.9}],
    )

    alloc = await runner.run(packet, ph)
    assert alloc.cluster_id == "clu_stub_test"
    assert alloc.horizon == "1d"
    assert len(alloc.markets) > 0
    assert len(alloc.sectors) > 0
    assert "cache_keys" in alloc.diagnostics
    allowed = await sec.all_symbols()
    for t in alloc.winners + alloc.losers:
        assert t.symbol in allowed, f"Ticker {t.symbol} must be allowlisted"


def test_debug_asset_targeting_not_found_returns_404(client):
    """Debug endpoint returns 404 for non-existent cluster."""
    from sentiment_api.api.keys import validate_api_key
    from sentiment_api.api.main import app
    app.dependency_overrides[validate_api_key] = lambda: "test_key_1234567890abcdef"
    try:
        r = client.get("/v1/debug/asset_targeting/clu_nonexistent12345")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(validate_api_key, None)


def test_debug_asset_targeting_invalid_format_returns_400(client):
    """Debug endpoint returns 400 for invalid cluster_id format."""
    from sentiment_api.api.keys import validate_api_key
    from sentiment_api.api.main import app
    app.dependency_overrides[validate_api_key] = lambda: "test_key_1234567890abcdef"
    try:
        r = client.get("/v1/debug/asset_targeting/invalid")
        assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(validate_api_key, None)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_debug_endpoint_includes_required_fields():
    """Integration: create cluster + run stub runner, then debug endpoint returns required fields."""
    import httpx

    from sentiment_api.api.main import app
    from sentiment_api.db.pool import init_pool, close_pool, acquire
    from sentiment_api.db.repo import insert_cluster, insert_summary
    from sentiment_api.engines.llm_asset_targeting.store_allocations_postgres import store_allocations
    from sentiment_api.engines.llm_asset_targeting.security_master import CSVSecurityMaster

    db_url = os.environ.get("DATABASE_URL", "postgresql://sentiment:sentiment@localhost:5432/sentiment")
    await init_pool(db_url)

    registry_dir = Path(__file__).resolve().parents[2] / "registry" / "llm_asset_targeting"
    assert (registry_dir / "beta_market.yaml").exists(), f"Registry not found: {registry_dir}"

    cluster_id = "clu_debug_test_12345"
    try:
        async with acquire() as conn:
            await insert_cluster(
                conn, cluster_id, "Oil prices spike on supply concerns",
                "oil_prices_spike", ["energy"], ["US"],
                1, ["https://example.com/1"],
                {"polarity": 0, "subjectivity": 0.5},
                {"impact_score": 35, "impact_level": "L3", "expected_direction": "RiskOff",
                 "confidence": 0.7, "horizon": "1d", "reason_codes": []},
                {},
            )
            await insert_summary(
                conn, "cluster", cluster_id, "L3", "test.schema", "1.0",
                "stub", "1.0", "dedupe_debug",
                {"summary_bullets_en": ["OPEC cuts."]},
            )

        stub = StubOpenAIProvider()
        from sentiment_api.engines.llm_asset_targeting.cache_store_postgres import AsyncPostgresLLMCacheStore
        cache = AsyncPostgresLLMCacheStore()
        sec = CSVSecurityMaster(exposures_csv=str(registry_dir / "ticker_exposures.csv"))

        from sentiment_api.engines.llm_asset_targeting.runner import ChunkedAssetTargetingRunner

        runner = ChunkedAssetTargetingRunner(
            provider=stub,
            cache=cache,
            security_master=sec,
            rulesets_path=str(registry_dir / "channel_rulesets.yaml"),
            schema_dir=str(registry_dir),
            beta_market_path=str(registry_dir / "beta_market.yaml"),
            beta_sector_path=str(registry_dir / "beta_sector.yaml"),
            exposures_csv_path=str(registry_dir / "ticker_exposures.csv"),
        )
        packet, ph = build_cluster_packet(
            cluster_id=cluster_id,
            cluster_version=1,
            headline_en="Oil prices spike",
            summary_bullets_en=["OPEC cuts."],
            topics=["energy"],
            regions=["US"],
            impact_score=35,
            impact_level="L3",
            expected_direction="RiskOff",
            confidence=0.7,
            evidence_rows=[{"url": "https://x.com", "text_en": "Oil up.", "relevance_score": 0.9}],
        )
        alloc = await runner.run(packet, ph)
        await store_allocations(alloc, model_version="stub", config_hash="test")

        from sentiment_api.api.keys import validate_api_key
        app.dependency_overrides[validate_api_key] = lambda: "test_key_1234567890abcdef"
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                r = await ac.get(f"/v1/debug/asset_targeting/{cluster_id}", headers={"X-API-Key": "test_key_1234567890abcdef"})
            assert r.status_code == 200, (r.status_code, r.text)
            payload = r.json()
            data = payload.get("data") or payload
            required = {"cluster_id", "packet", "packet_hash", "prompt_hashes", "schema_hashes",
                       "cache_status", "cache_keys", "channels", "call_a", "call_b", "call_c",
                       "candidate_diagnostics", "allocations", "invariant_violations"}
            for k in required:
                assert k in data, f"Debug response must include '{k}'"
            alloc_data = data.get("allocations", {})
            assert "markets" in alloc_data and "sectors" in alloc_data
        finally:
            app.dependency_overrides.pop(validate_api_key, None)
    finally:
        await close_pool()
