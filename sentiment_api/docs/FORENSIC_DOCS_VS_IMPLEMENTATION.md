# Forensic Report: Docs vs Implementation

**Date:** 2026-02-02  
**Scope:** Compare `Docs/` packages to current `sentiment_api/` state. Identify and close gaps.

---

## 1. Sentimeter_LLM_Chunks_AssetTargeting_v1.0

| Requirement | Status | Notes |
|-------------|--------|-------|
| engines/llm_asset_targeting/* | ✓ | All files present |
| Migrations 005/006/007 | ✓ | v1.4_llm_call_cache, v1.4_asset_allocations, v1.4_forward_eval_asset |
| DB cache store | ✓ | AsyncPostgresLLMCacheStore |
| OpenAI structured call (temp=0, store=false) | ✓ | openai_provider.py |
| Runner (cached A/B/C, allocator, persist) | ✓ | runner.py, store_allocations_postgres |
| Debug endpoint | ✓ | /v1/debug/asset_targeting/{cluster_id} |
| prompt_hashes, schema_hashes in debug | ✓ | Added 2026-02-02 |
| Allocations endpoint | ✓ | /v1/impacts/clusters/{cluster_id}; GET cluster includes market_impacts, sector_impacts, ticker_impacts |
| Unit tests (cache, allowlist, sector) | ✓ | test_llm_asset_targeting_* |
| Integration test (stub provider) | ✓ | test_llm_asset_targeting_stub |
| docs/90_TEST_MATRIX | ✓ | In sentiment_api/docs |
| LLM Chunks docs (10–130) | ✓ | LLM_CHUNKS_*.md in sentiment_api/docs |

---

## 2. Sentimeter_Registry_Ratings_v1.0

| Requirement | Status | Notes |
|-------------|--------|-------|
| beta_market.yaml (with US_RATES, CREDIT, VIX) | ✓ | In registry/llm_asset_targeting |
| beta_sector.yaml (11 sectors) | ✓ | |
| beta_industry.yaml | ✓ | |
| sector_default_exposures.yaml | ✓ | |
| industry_to_sector.csv | ✓ | |
| ticker_exposures.csv | ✓ | From seed_exposures.py |
| Docs (01–04) | ✓ | REGISTRY_RATINGS_01–04 in sentiment_api/docs |
| seed_exposures script | ✓ | scripts/seed_exposures.py |

---

## 3. Sentiment_API_Master_Package v1.2

| Requirement | Status | Notes |
|-------------|--------|-------|
| API endpoints | ✓ | Per IMPLEMENTATION_GAP_DIFF_V1_2 |
| Rate limiting, Idempotency, SSRF | ✓ | |
| Observability (Prometheus, Grafana, Loki) | ✓ | infra/ |
| Frontend (Topics, SSE, Zod) | ✓ | |
| Tests | ✓ | Contract + spec |

---

## 4. Sentimeter_Dashboard_Overhaul_v2.0

| Gap | Status | Notes |
|-----|--------|-------|
| Overview density (gauge, charts, tables) | ⚠️ | DIFF_CURRENT_VS_TARGET.md; frontend has components |
| News feed richness (cluster cards) | ⚠️ | Partial |
| Visual hierarchy & glass | ⚠️ | Token-driven surfaces in v2 |
| Empty/degraded states | ⚠️ | Skeleton, demo mode |
| Demo fixtures for Playwright | ⚠️ | Per DASHBOARD_V2_INTEGRATION_REPORT |

---

## 5. Sentimeter_Docs_Package v0.1

| Doc | Main Repo Equivalent |
|-----|----------------------|
| 01_SCOPE | INSTALLATION_MANUAL, SENTIMENT_API_* specs |
| 02_ARCHITECTURE | NEWS_TO_SENTIMENT_DATA_FLOW, CLUSTERING_HOW_IT_WORKS |
| 03_DATA_MODEL | DB schema, migrations |
| 04_CRAWLING_INGESTION | Collectors, daemon |
| 05_SUMMARY_MEMORY | LLM summaries, CLUSTERING |
| 06_VECTOR_RETRIEVAL | RETRIEVAL_TWOTIER, PINECONE_WEAVIATE |
| 07_MARKET_DATA_SPY | engines/outcomes, yahoo_finance |
| 08_IMPACT_SCORING | llm/impact, asset_targeting |
| 09_HISTORICAL_CALIBRATION | REGISTRY_RATINGS_03 |
| 10_FORWARD_EVAL | v1.4_forward_eval_asset |
| 11_API_SPEC | OpenAPI, main.py |
| 12_OPS_SECURITY | OBSERVABILITY_RUNBOOK |
| 13_TEST_PLAN | TEST_PACK, 90_TEST_MATRIX |

Coverage: Distributed across existing docs. No dedicated 01–13 copies; content reflected elsewhere.

---

## 6. Migration Naming

| Package (LLM Chunks) | Main Repo |
|----------------------|-----------|
| 005_llm_call_cache.sql | v1.4_llm_call_cache.sql |
| 006_asset_allocations.sql | v1.4_asset_allocations.sql |
| 007_forward_eval_asset.sql | v1.4_forward_eval_asset.sql |

See `LLM_CHUNKS_70_DATABASE_SCHEMA.md`.

---

## 7. Summary

| Package | Gaps Closed |
|---------|-------------|
| LLM Chunks | prompt_hashes, schema_hashes in debug; LLM_CHUNKS_* docs added |
| Registry Ratings | Complete |
| Master v1.2 | Complete (per gap analysis) |
| Dashboard v2 | UI improvements tracked in DIFF |
| Docs v0.1 | Content covered by existing docs |
