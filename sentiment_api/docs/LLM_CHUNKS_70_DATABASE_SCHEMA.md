# Database Schema (v1.0)

Migrations included (package names → main repo equivalents):
- 005_llm_call_cache.sql → `migrations/v1.4_llm_call_cache.sql`
- 006_asset_allocations.sql → `migrations/v1.4_asset_allocations.sql`
- 007_forward_eval_asset.sql → `migrations/v1.4_forward_eval_asset.sql`

If your repo already has allocations tables, map these schemas to existing tables instead of duplicating.

Required persistence:
- LLM cache (llm_call_cache)
- allocations (market/sector/ticker)
- forward evaluation ledger (asset_prediction_ledger)

