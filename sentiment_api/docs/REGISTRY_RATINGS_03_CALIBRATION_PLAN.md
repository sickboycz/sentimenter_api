# Calibration plan (forward-only) — how to improve these priors

The matrices in beta_market.yaml and beta_sector.yaml are **priors** (rule-based starting points).
They become competitive only after calibration using your forward evaluation ledger.

## Data we need (already in your architecture)
For each cluster at time t:
- channel vector c_k (from Call A)
- predicted allocations:
  - market_signed_score[m]
  - sector_signed_score[s]
  - ticker_signed_score[t]
  - expected_return_bps[t] (initially from mapping)
Store these in:
- cluster_*_allocations tables
- asset_prediction_ledger (for tickers)

Then later at t + Δ (30m / 2h / 1d / 3d / 1w):
- realized returns:
  - SPY / QQQ / sector ETF returns (or sector baskets)
  - ticker returns
Write realized_* into asset_prediction_ledger.

## Calibration targets
We calibrate in 3 layers:

### Layer 1 — Score → bps mapping (monotonic calibration)
For each horizon h:
- Input: predicted_signed_score
- Target: realized_return_bps
Fit a monotonic mapping:
- isotonic regression OR binned median smoothing (recommended first)
Store mapping table:
- bins of signed_score (e.g., -100..100 step 5)
- expected bps and hit rate

This replaces the naive:
  expected_return_bps = signed_score * 2.0

### Layer 2 — Market betas (beta_market.yaml)
For each market m and horizon h:
Fit a regularized regression:
- y = realized_return_m (or z-scored by realized volatility)
- X = channel vector c_k
Use ridge regression (L2) with:
- coefficient caps [-1..1]
- optional sector regime splits (risk-on vs risk-off)
Update betas monthly, using expanding window only (no future data).

### Layer 3 — Sector betas (beta_sector.yaml) and industry betas
Same as markets, but targets are:
- sector ETF returns (XLK, XLE, etc) OR equal-weight sector baskets
- industry baskets built from tickers in the industry

Use hierarchical shrinkage:
- industry beta = sector beta + small residual
- ticker exposure residuals shrink toward industry mean

## Walk-forward protocol (no cheating)
- Train on [start..t0]
- Validate on (t0..t1]
- Freeze parameters for a period (weekly/monthly)
- Repeat (expanding window)

## Guardrails in calibration
- never update betas intraday
- cap coefficient changes per update (e.g., |Δ| <= 0.10)
- if coverage is low or drift is high, reduce output confidence

## What becomes "competitive"
- calibration curves show your expected_return_bps is not biased
- hit rates by bucket stabilize
- regime-conditioned betas improve direction accuracy
