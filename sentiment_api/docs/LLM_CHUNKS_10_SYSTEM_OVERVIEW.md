# System Overview (v1.0)

## Problem
The current `asset_targeting.py` flow described by Cursor is consistent, but too literal:
it largely copies a single cluster score into SP500/NASDAQ and then “fractions” it to sectors/tickers.

That approach has two weaknesses:
1) It ignores *mechanism* (rates vs oil vs geopolitics vs regulation).
2) It lacks conservation and calibration (sector/ticker totals can exceed market reality).

## Solution
Add a **chunked OpenAI pipeline** that produces:
- a **channel vector** explaining the mechanism
- a **sector/industry map**
- a **ticker selection** constrained to an allowlist
and then runs a deterministic allocator that enforces:
- conservation (bounded total “mass”)
- no hallucinated tickers
- evidence-first rationale
- cache/idempotency
- forward calibration

## Pipeline (hard order)
Cluster -> Packet -> (A) Channels -> (B) Sectors -> (C) Ticker picks -> (D) Deterministic allocation

Calls A/B/C use **Structured Outputs** (strict JSON schema) with temperature 0.
Call D is deterministic local math.

## Outputs
For each cluster version:
- `cluster_market_allocations[]` (top 5 markets)
- `cluster_sector_allocations[]` (all 11 sectors, return top 11)
- `cluster_ticker_allocations[]` (top 25 winners + top 25 losers per universe)
- `asset_prediction_ledger` entry per ticker impact (forward evaluation)

## Compatibility
- Existing cluster scoring remains: one impact_score + direction.
- This module adds channel vector + allocations and can embed them in existing endpoints.

