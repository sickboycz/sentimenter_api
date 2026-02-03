# Chunked LLM Calls (v1.0)

All calls use OpenAI **Responses API** with **Structured Outputs** (strict json_schema).
Each call must be cached and validated by Pydantic.

## Call A — Channel Inference
Inputs: cluster packet
Output: channel vector
Schema: openai_schemas/channel_infer.schema.json

Channels are fixed enum:
- rates, inflation, growth, liquidity, credit_stress
- geopolitics, energy_supply, trade_controls, regulation, risk_appetite

Output must include:
- channels[] with sign and strength
- primary_horizon
- confidence
- rationale_bullets_en (2-5)

## Call B — Sector/Industry Mapping
Inputs: channel vector + sector taxonomy
Output: sector impacts (and optional industries)
Schema: openai_schemas/sector_map.schema.json

Output must include:
- sectors[]: sector_id, direction, strength, confidence, why_refs
- industries[] optional, max 5 per sector

## Call C — Ticker Select (Allowlist Only)
Inputs:
- channel vector
- top sectors
- allowed_symbols[] (deterministic candidates; max 600)
Output:
- winners[] max 15
- losers[] max 15
Schema: openai_schemas/ticker_select.schema.json

HARD RULE:
- model may only pick symbols from allowed list
- allocator rejects any other symbol

## Call D — Deterministic allocator
Uses docs/40_ALLOCATION_MATH.md
Produces final allocations and writes them to DB tables.

