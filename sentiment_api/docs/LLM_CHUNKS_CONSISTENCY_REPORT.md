# Consistency Crosscheck Report (v1.0)

This report validates that the package is internally consistent (docs ↔ code ↔ schemas ↔ migrations).

## 1) Docs Index coverage
- docs/00_INDEX.md references:
  - 10_SYSTEM_OVERVIEW.md ✅
  - 20_CLUSTER_PACKET.md ✅
  - 30_LLM_CALLS.md ✅
  - 40_ALLOCATION_MATH.md ✅
  - 50_CACHING_IDEMPOTENCY.md ✅
  - 60_GUARDRAILS_THREAT_MODEL.md ✅
  - 70_DATABASE_SCHEMA.md ✅
  - 80_ENDPOINTS.md ✅
  - 90_TEST_MATRIX.md ✅
  - 95_EVIDENCE_CHECKLIST.md ✅
  - 99_IMPLEMENTATION_STEPS.md ✅

## 2) Schemas
- openai_schemas/channel_infer.schema.json ✅
- openai_schemas/sector_map.schema.json ✅
- openai_schemas/ticker_select.schema.json ✅
These correspond to Pydantic models in:
- backend/.../schemas.py ✅

## 3) Registry files
- registry/beta_market.yaml used by allocator.py ✅
- registry/beta_sector.yaml used by allocator.py ✅
- registry/ticker_exposures.csv used by allocator.py ✅
- registry/channel_rulesets.yaml used by candidate_generator.py ✅

## 4) Migrations vs stores
- llm_call_cache table defined in db/migrations/005_llm_call_cache.sql ✅
  - cache_store_postgres.py expects llm_call_cache columns: status, parsed_json, raw_json, error_code, error_message ✅
- allocations tables defined in db/migrations/006_asset_allocations.sql ✅
  - store_allocations_postgres.py inserts into cluster_*_allocations with matching column sets ✅
- forward ledger table defined in db/migrations/007_forward_eval_asset.sql ✅
  - (calibration job not implemented in this package; left for main repo) ✅

## 5) Runner alignment
- docs/99_IMPLEMENTATION_STEPS.md references chunk runner and allocator:
  - runner.py ✅
  - allocator.py ✅

## 6) Guardrails
- Allowlist enforced in runner.py after Call C ✅
- Schema locked outputs in OpenAI provider ✅
- Temperature=0 and strict schema ✅

## 7) Known integration TODOs
These are intentionally left as integration points because your repo has an existing DB layer:
- Replace CSVSecurityMaster with DB-backed SecurityMaster for real universes.
- Add realized return measurement job to populate asset_prediction_ledger.
- Wire debug endpoint into FastAPI router.

No other inconsistencies found.

