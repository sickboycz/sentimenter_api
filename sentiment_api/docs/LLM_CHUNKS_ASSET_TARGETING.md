# Chunked LLM Asset Targeting (v1.0)

Implements `Docs/Sentimeter_LLM_Chunks_AssetTargeting_v1.0/` in the main repo.  
**Full doc index:** `LLM_CHUNKS_00_INDEX.md`

## Hard rules
- No API guessing: align to existing DB/session layer (asyncpg pool).
- Deterministic & audit-grade.
- Schema locked outputs for OpenAI calls (Structured Outputs).
- Tickers strictly allowlisted.
- Cache all LLM calls in DB.

## Files
- `engines/llm_asset_targeting/` — packet_builder, cache_keys, cache_store, cache_store_postgres, openai_provider, prompts, candidate_generator, security_master, allocator, runner, store_allocations_postgres, debug
- `registry/llm_asset_targeting/` — beta_market.yaml, beta_sector.yaml, beta_industry.yaml, sector_default_exposures.yaml, channel_rulesets.yaml, ticker_exposures.csv, industry_to_sector.csv, openai schemas
- `migrations/v1.4_*.sql` — llm_call_cache, cluster_*_allocations, asset_prediction_ledger
- `GET /v1/debug/asset_targeting/{cluster_id}` — debug endpoint

## Implementation order
1. Apply migrations: v1.4_llm_call_cache, v1.4_asset_allocations, v1.4_forward_eval_asset
2. Wire DB cache store (AsyncPostgresLLMCacheStore)
3. OpenAI Responses structured call (temperature=0, store=false)
4. Runner orchestration (cached A/B/C, deterministic allocator)
5. Debug endpoint
6. Unit tests (cache keys, allowlist)

## Usage
- Run migrations via `./scripts/reset_db_fresh.sh` or `./scripts/apply_schema_from_zero.sh`
- Seed universe: `uv run python scripts/seed_universes.py` (sectors, industries, sp500, nasdaq100)
- Seed ticker exposures: `uv run python scripts/seed_exposures.py` (deterministic rule from sector_default_exposures + beta_industry; see docs/REGISTRY_RATINGS_02_SEEDING_TICKER_EXPOSURES.md)
- Debug: `GET /v1/debug/asset_targeting/{cluster_id}` (requires API key)
- Full runner integration: wire `ChunkedAssetTargetingRunner` into summarize/score flow when `cost_effective=false` and cluster impact >= L2
