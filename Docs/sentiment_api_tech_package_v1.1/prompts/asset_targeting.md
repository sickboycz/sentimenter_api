# Asset Targeting — Contract v1.1

Purpose: Convert a **single story cluster** (L3 + evidence) into:
- most affected **market** (SP500 vs NASDAQ_COMPOSITE)
- **sector** impacts (GICS-like 11 sectors)
- **ticker** winners and losers (restricted to S&P 500 + Nasdaq Composite universes)

This output is used by:
- `GET /v1/impacts/clusters/{cluster_id}`
- `GET /v1/impacts/latest` (aggregated window)

**Hard rules** (non-negotiable):
1) Output **JSON ONLY** (no markdown, no commentary).
2) Be **evidence-first**: every non-trivial claim must be backed by `evidence_urls[]`.
3) Do not invent tickers. Choose from the provided candidate list unless the ticker is explicitly mentioned in the evidence.
4) Use **Up/Down** price-direction labels (not RiskOn/RiskOff).
5) Provide concise, falsifiable rationale bullets (no vague vibes).

---

## Input (provided to the model)

- `cluster_id`
- L3 summary fields:
  - `summary_en`, `topics`, `regions`, `entities`, `first_seen`, `last_seen`
- Evidence pack:
  - top evidence passages (English)
  - `source_urls[]` (canonical)
- Current regime context (optional):
  - recent SPY vol, VIX proxy, breadth
- Candidate universes:
  - `universes`: list of universe ids to restrict to (default: `["sp500","nasdaq_composite"]`)
- Candidate tickers list (precomputed upstream):
  - For each candidate: `symbol`, `name`, `sector_id`, `sector_name_en`, `universe_memberships[]`, optional `company_blurb_en`
  - Optional historical sensitivity features for that ticker:
    - `historical_edge[]`: prior event-study stats for similar event types (if available)

---

## Output (JSON ONLY)

Return an object matching `AssetImpactBundle` (see `schemas/defs.json#/$defs/AssetImpactBundle`).

Minimum expectations:
- `markets[]`: must include **both** SP500 and NASDAQ_COMPOSITE.
- `sectors[]`: include **at least** the top 3 impacted sectors (positive or negative).
- `winners[]` and `losers[]`: include 10–30 each (unless event is L0/L1, then allow fewer).

### Guidance for selecting winners/losers
- Use **channels** to connect news → business impact:
  - rates / inflation / FX
  - energy supply / commodities
  - regulation / sanctions / export controls
  - defense / security spending
  - supply chain / shipping
  - demand shocks (consumer, enterprise)
- Prefer tickers with:
  - direct mention in evidence, OR
  - strong channel exposure, OR
  - strong historical edge (high hit-rate)
- Avoid duplicates and avoid “obvious mega-cap spam” unless justified.

### Scoring calibration (keep consistent)
- `impact_score` ∈ [0,100]:
  - 80–100: very strong expected impact (headline driver)
  - 60–79: strong, tradeable impact
  - 40–59: moderate, watchlist
  - <40: weak
- `confidence` ∈ [0,1]:
  - lower if contradictory sources, unclear policy details, uncertain follow-through

### Required fields hygiene
- If you lack historical data: set `historical_edge: []` (empty array), do NOT fabricate.
- Always include `driver_clusters: ["<cluster_id>"]` for per-cluster outputs.
- Always include at least 1 evidence URL per asset (more is better, up to 50).

