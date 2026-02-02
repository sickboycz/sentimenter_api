# Strategy Robot — Income Options Decision Engine (SPEC.md)

> **Owner:** Lukas  
> **Stack:** Python 3.x + FastAPI  
> **Scope:** Deterministic **signals + order intents** engine for an income-options portfolio (CSP / CC / PCS / optional PMCC).  
> **Critical:** This engine **does not execute trades**. It only produces **signals**. Execution (IBKR) is a separate module and (initially) manual approval.

---

## 1. Objectives

### 1.1 Primary goal
Produce **daily/periodic** decisions for a rules-based income portfolio:
- **CSP** (Cash-Secured Put)
- **CC** (Covered Call)
- **PCS** (Put Credit Spread)
- **PMCC** (Poor Man’s Covered Call) — optional

Output must be:
- deterministic
- auditable (replayable)
- explainable (reason codes)
- safe (hard risk gates)

### 1.2 Outputs (what the robot delivers)
- `DecisionEnvelope` containing:
  - portfolio snapshot summary
  - bucket allocation vs targets
  - **0..N** `Signal` items (OPEN/CLOSE/ROLL/SKIP)
  - **OrderIntent** objects (paper/live-approval later)
  - reason codes
  - computed risk metrics (assignment probability estimate / sigma distance / return on risk)

### 1.3 Non-goals
- No brokerage order submission in this module.
- No discretionary “intuition”; no hidden heuristics.
- No earnings/macro prediction.

---

## 2. Operating Modes

- `DRY_RUN`: compute and log signals only.
- `PAPER`: emit order intents suitable for paper execution.
- `LIVE_APPROVAL`: emit order intents but **require manual approval**.
- `LIVE_AUTO`: **future**. Not in MVP.

---

## 3. Portfolio Blueprint (constant ratio)

### 3.1 Target allocation (keep constant, rebalance; do not chase winners)
For **$50k** (scale linearly with equity):

- **40% CSP** (entry engine)
- **30% CC** (income on owned shares)
- **20% PCS** (defined-risk income)
- **10% PMCC** (optional; may start at 0%)

These targets are expressed as **bucket budgets**. The engine always fills the **most under-allocated bucket first**.

### 3.2 Hard exposure caps
- `MAX_SINGLE_UNDERLYING_EXPOSURE_PCT = 20%` (shares + option-equivalent notional)
- `MAX_SECTOR_EXPOSURE_PCT = 35%`
- `MAX_TOTAL_SHORT_PUT_NOTIONAL_PCT = 80%` (CSP + PCS short legs)
- `MAX_NOTIONAL_EXPOSURE_PCT = 125%` (all-in, including shares & option equivalents)
- `MAX_POSITIONS_PER_SYMBOL = 2`
- `MAX_NEW_TRADES_PER_DAY = 1`

---

## 4. Hard Safety Gates (must pass before any new position)

### 4.1 Margin gate
- `free_margin_pct >= 30%` required for **any new openings**
- If fail → `SKIP_ALL_NEW_TRADES` with reason `MARGIN_LOW`

### 4.2 Notional gate
- `notional_exposure_pct <= 125%`
- If fail → only allow risk reduction actions (close/roll-to-reduce)

### 4.3 Drawdown kill-switch
Track peak equity and current equity:
- If `portfolio_dd_pct <= -20%` → `HALT_NEW_TRADES`
- Allow only: close, roll-to-reduce-risk, hedge (if enabled)

---

## 5. Universe & Eligibility

### 5.1 Allowed symbols
Engine trades only from a configured allowlist:
- Core examples: `OXY, DELL, EBAY, KR, GIS`
- Satellites examples (smaller sizing): `HAL, KGC, PSTG`
- Index/ETF for PCS: `SPY` (or other approved ETFs)

### 5.2 Options liquidity checks (hard)
A symbol is tradable only if:
- options available
- spreads are acceptable:
  - **Single-leg** spread <= `3%` of mid (or abs <= `0.10–0.20` for SPY, configurable)
- OI/volume above thresholds (configurable):
  - `min_oi`, `min_option_volume`

If fail → `UNTRADABLE_SYMBOL` for the run.

---

## 6. Volatility Regime Filter (edge gate)

### 6.1 Preferred input: IV Percentile (30D)
Default rule:
- Trade premium strategies only when `IVP_30D ∈ [60, 85]`
- If `IVP_30D < 60` → `SKIP_LOW_EDGE`
- If `IVP_30D > 85` → `SKIP_EVENT_RISK` (unless explicit event strategy)

### 6.2 Fallback when IVP not available
Use one of:
- `IV_RANK >= 30` OR
- `raw_IV_30D >= 25%` for single stocks (lower for SPY/ETFs)

### 6.3 Special rule for SPY PCS
If `SPY_IV_RANK <= 20` then:
- `PCS_DISABLED_LOW_IV` (do not open PCS on SPY)
Rationale: low IV = low premium, poor edge.

---

## 7. Earnings / Event Blackout (hard)

For **single stocks**:
- If earnings occurs within `EARNINGS_BLACKOUT_DAYS = 21` of the option expiry → **do not open** short premium.

For **SPY**:
- no earnings; optional macro blackout can be added later (CPI/FOMC days).

---

## 8. Strategy Selection Logic (deterministic)

### 8.1 Bucket priority order
At each run:
1) **CC** if shares exist with no CC written
2) **CSP** if CSP bucket under target
3) **PCS** if PCS bucket under target **and** vol regime supports
4) **PMCC** if enabled and PMCC bucket under target

### 8.2 One-trade-per-day throttle
Default:
- Open at most `MAX_NEW_TRADES_PER_DAY = 1` new position per day (reduces timing risk).

---

## 9. Entry Rules (per strategy)

### 9.1 CSP (Cash-Secured Put)
**When:**
- all safety gates pass
- IV regime passes
- earnings blackout passes
- bucket under target

**Selection:**
- `DTE ∈ [21, 45]` (target 30–45)
- `PUT_DELTA ∈ [0.15, 0.25]` (target 0.20)
- premium threshold: `premium/strike >= 1.2%` (baseline for ~30 DTE; configurable)
- prefer short strike near `≥ 1.0σ` below spot (sigma rule)

**Sizing:**
- CSP risk unit = 100 shares assignment
- Respect caps:
  - single underlying exposure cap
  - total short put notional cap

### 9.2 CC (Covered Call)
**Precondition:** own 100 shares (or multiples)

**Selection:**
- `DTE ∈ [21, 45]`
- `CALL_DELTA ∈ [0.20, 0.30]` (target 0.25)
- strike ≥ configured “happy sell price” (or ≥ cost basis, policy-defined)
- premium threshold: `premium/spot >= 0.8–1.0%` per cycle (configurable)

**Sizing:** 1 call per 100 shares (never naked).

### 9.3 PCS (Put Credit Spread)
**When:**
- all safety gates pass
- IV regime passes (SPY special rule must pass)
- bucket under target

**Selection:**
- `DTE ∈ [21, 45]` (target 30–45)
- short put:
  - delta target `0.20–0.30` OR sigma distance ≥ `1.0σ`
- width:
  - SPY: `5` or `10` points (configurable)
- **minimum edge rule:**
  - `return_on_max_risk >= 10%` (prefer 15%+)
  - if < 10% → `SKIP_LOW_EDGE`

**Sizing (explicit):**
- `max_risk_per_spread <= 2%` of equity
- for $50k:
  - 10-wide spread typically = **1 contract**
  - 2 contracts only under strict conditions (no other PCS risk, caps satisfied)

### 9.4 PMCC (optional, advanced)
Enabled only after core system is stable.

- LEAPS call:
  - delta `0.70–0.85`, expiry `9–18 months`
- short call:
  - `DTE ∈ [21,45]`, delta `0.20–0.25`
- PMCC bucket <= 10% equity
- Avoid buying LEAPS in high IV spikes

---

## 10. Exit Rules (all strategies)

### 10.1 Profit targets (default)
- Close at **50–60%** of maximum profit (credit captured)
- Avoid holding to 100% (gamma risk)

### 10.2 Time-based exit
- Close when `DTE <= 14` regardless of small remaining premium

### 10.3 Risk triggers
Intervene if:
- short option `abs(delta) > 0.35`
- underlying breaks defined support (policy-defined; can be a simple MA or swing low)
- IV spikes + position becomes threatened
- portfolio caps are breached

---

## 11. Rolling Rules (mechanical)

### 11.1 Principle
Rolling moves risk in time; it does not “erase” losses.

### 11.2 Roll PUT (CSP / threatened short puts)
Roll if:
- short delta > 0.35 OR
- spot near strike OR
- DTE < 14

Method:
- roll out to 30–45 DTE
- same strike or lower strike
- prefer credit/flat
- if large debit required → consider closing

### 11.3 Roll PCS
Preferred action when threatened: **close early**.
Roll only if:
- roll reduces risk / increases cushion
- no increase in contract count
- flat/credit roll achievable
Never:
- add size (no martingale)
- remove long leg to “turn it into CSP”

### 11.4 Roll CC
If price runs and CC becomes deep ITM:
- accept assignment (often best), OR
- roll up/out if credit/flat and within delta band

---

## 12. PCS Ladder Rules (time diversification)

- `MAX_ACTIVE_PCS = 3`
- open new PCS at most once per `7–10 days`
- `TOTAL_PCS_MAX_RISK <= 6%` equity

**Note:** if SPY IV rank is very low (e.g., ~13 observed), ladder should be disabled for SPY PCS.

---

## 13. Probability & Sigma Metrics (for reporting)

For each candidate:
- `sigma_DTE = IV * sqrt(DTE/365)`
- `pct_distance = (spot - strike)/spot`
- `sigma_distance = pct_distance / sigma_DTE`
- Approximate `P(ITM)` using normal tail probability of `sigma_distance`

This is used for:
- signal explainability
- UI display (“short strike is 1.05σ below spot → ~14–15% ITM”)

---

## 14. Decision Output Contracts

### 14.1 Enums

```json
{
  "Mode": ["DRY_RUN","PAPER","LIVE_APPROVAL","LIVE_AUTO"],
  "Action": ["OPEN_CSP","OPEN_CC","OPEN_PCS","OPEN_PMCC","CLOSE","ROLL","SKIP","HALT"],
  "InstrumentType": ["STK","OPT"],
  "OptionRight": ["C","P"],
  "Side": ["BUY","SELL"]
}
```

### 14.2 Reason Codes (stable enum; do not invent at runtime)

```json
{
  "ReasonCode": [
    "MARGIN_LOW",
    "DD_HALT",
    "NOTIONAL_TOO_HIGH",
    "IVP_TOO_LOW",
    "IVP_TOO_HIGH",
    "IV_RANK_TOO_LOW",
    "EARNINGS_BLACKOUT",
    "SPREAD_TOO_WIDE",
    "LIQUIDITY_TOO_LOW",
    "RISK_REWARD_TOO_LOW",
    "BUCKET_UNDERALLOCATED_CSP",
    "BUCKET_UNDERALLOCATED_CC",
    "BUCKET_UNDERALLOCATED_PCS",
    "BUCKET_UNDERALLOCATED_PMCC",
    "OPEN_CSP",
    "OPEN_CC",
    "OPEN_PCS",
    "OPEN_PMCC",
    "CLOSE_PROFIT_TARGET",
    "CLOSE_DTE_TOO_LOW",
    "ROLL_DELTA_TOO_HIGH",
    "PCS_DISABLED_LOW_IV",
    "SKIP_NO_EDGE"
  ]
}
```

### 14.3 `Snapshot` (input)

```json
{
  "timestamp_utc": "2026-01-18T18:00:00Z",
  "account": {
    "equity_usd": 50000.0,
    "cash_usd": 12000.0,
    "buying_power_usd": 90000.0,
    "free_margin_pct": 35.0,
    "notional_exposure_pct": 95.0,
    "portfolio_dd_pct": -3.2
  },
  "market": [
    {
      "symbol": "SPY",
      "spot": 683.42,
      "iv_30d": 0.18,
      "ivp_30d": 0.62,
      "iv_rank_52w": 13,
      "earnings_date_utc": null
    }
  ],
  "positions": [
    {
      "symbol": "DELL",
      "qty_shares": 100,
      "avg_price": 72.10,
      "open_options": []
    }
  ]
}
```

### 14.4 `Candidates` (input)
Candidates are **pre-filtered** option legs/spreads the engine is allowed to choose from (keeps decisions deterministic and safe).

```json
{
  "symbol": "SPY",
  "csp": [],
  "cc": [],
  "pcs": [
    {
      "expiry": "2026-02-20",
      "dte": 30,
      "short_put": {"strike": 650, "delta": 0.23, "bid": 4.48, "ask": 4.50, "mid": 4.49},
      "long_put":  {"strike": 640, "delta": 0.18, "bid": 3.42, "ask": 3.44, "mid": 3.43},
      "width": 10,
      "credit_mid": 1.06,
      "max_risk": 894.0,
      "return_on_risk": 0.118
    }
  ]
}
```

### 14.5 `Signal` + `OrderIntent` (output)

```json
{
  "decision_envelope": {
    "request_id": "uuid",
    "timestamp_utc": "2026-01-18T18:00:05Z",
    "mode": "DRY_RUN",
    "bucket_targets": {"csp": 0.40, "cc": 0.30, "pcs": 0.20, "pmcc": 0.10},
    "bucket_actuals": {"csp": 0.10, "cc": 0.20, "pcs": 0.00, "pmcc": 0.00},
    "signals": [
      {
        "action": "OPEN_PCS",
        "symbol": "SPY",
        "reason_codes": ["BUCKET_UNDERALLOCATED_PCS","OPEN_PCS"],
        "risk": {
          "max_loss_usd": 894.0,
          "max_profit_usd": 106.0,
          "return_on_risk": 0.118,
          "sigma_distance": 1.05,
          "prob_itm_est": 0.15
        },
        "order_intents": [
          {"side":"SELL","instrument":"OPT","right":"P","strike":650,"expiry":"2026-02-20","qty":1,"limit_price":4.49},
          {"side":"BUY","instrument":"OPT","right":"P","strike":640,"expiry":"2026-02-20","qty":1,"limit_price":3.43}
        ],
        "notes": "Close at 50–60% profit; close if DTE<=14 or short delta>0.35."
      }
    ]
  }
}
```

---

## 15. Implementation Plan (step-by-step)

### Phase 1 — Freeze rules + schemas (first)
1) Create `StrategyProfile` config (YAML/JSON): targets, caps, delta bands, DTE bands, thresholds.
2) Implement JSON Schema validation for: `Snapshot`, `Candidates`, `DecisionEnvelope`.
3) Implement reason code enum (single source of truth).
4) Build **golden snapshot fixtures** + expected outputs (unit tests).

### Phase 2 — Market data ingestion (next)
5) IBKR data collector (quotes, greeks, chain, account, positions).  
6) Normalizer produces `Snapshot`.
7) Candidate builder produces `Candidates` (filter chain to eligible legs/spreads).

### Phase 3 — Deterministic decision engine (then)
8) Compute bucket actuals vs targets.
9) Apply hard safety gates.
10) Select under-allocated bucket and generate signals.
11) Risk metrics + sigma/ITM estimate + return-on-risk.
12) Logging: JSONL + snapshot hashes (replayable).

### Phase 4 — UI + paper (then)
13) UI view: “Daily Decisions” with reason codes, metrics, and approve button.
14) Paper trading: send `OrderIntent`s to paper executor module.

### Phase 5 — Live approval (later)
15) Manual approval workflow + kill switch.
16) Alerts for margin low / DD halt.

### Phase 6 — Live auto (last)
17) Live auto execution with strict monitoring.

---

## 16. Testing & Evidence (must-have)

### 16.1 Unit tests
- bucket allocation math
- hard gates (margin/dd/notional)
- delta & DTE filters
- return-on-risk thresholding
- sigma/ITM estimation

### 16.2 Scenario tests (golden fixtures)
- normal day (IV in range) → OPEN signal
- low IV (SPY IV rank low) → PCS_DISABLED_LOW_IV
- earnings blackout → skip
- margin low → SKIP_ALL_NEW_TRADES
- drawdown halt → HALT_NEW_TRADES

### 16.3 Logging requirements
Each run logs:
- snapshot (or hash + stored snapshot)
- candidate set
- decision envelope
- reason codes
- computed metrics
- deterministic “decision_hash” for replay

---

## 17. Notes from live observations (embedded policy)

Observed on SPY:
- IV Rank can be ~13 with low premium.
Rule:
- if SPY IV Rank <= 20 and PCS return_on_risk < 10–12% → skip PCS.

This prevents “must trade” behavior and protects edge.

---

## 18. Appendix — Default parameter set (starter)

- `DTE_RANGE = [21,45]`
- CSP delta = `[0.15,0.25]` target `0.20`
- CC delta = `[0.20,0.30]` target `0.25`
- PCS short delta = `[0.20,0.30]`
- PCS width = `5 or 10` (SPY)
- Profit take = `55%`
- Close at `DTE <= 14`
- Roll trigger delta = `0.35`
- Min free margin = `30%`
- Max DD halt = `-20%`
- IVP range = `[60,85]`
