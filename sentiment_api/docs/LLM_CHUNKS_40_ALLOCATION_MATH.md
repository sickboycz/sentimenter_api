# Allocation Math (v1.0)

This is deterministic. No hidden heuristics.

## Signed cluster score
direction_sign:
- RiskOn -> +1
- RiskOff -> -1
- Neutral/Mixed/Unknown -> 0

signed_score = impact_score * direction_sign

## Channel vector
For each channel k:
c_k = clamp(sign_k * strength_k, -1, +1)

## Market allocation
raw_m = Σ_k c_k * beta_market[m][k]
market_signed[m] = clamp(signed_score * tanh(raw_m), -100, +100)
market_conf[m] = cluster_conf * relevance(|raw_m|)

Relevance function:
- |raw| >= 0.15 => 1.0
- |raw| >= 0.05 => 0.7
- else => 0.4

Return top 5 markets by abs(market_signed).

## Sector allocation
raw_s = Σ_k c_k * beta_sector[s][k]
sector_signed_raw[s] = signed_score * tanh(raw_s)
mention boost:
  sector_signed_raw[s] *= (1 + 0.05*log(1 + mentions_in_sector))

Conservation:
  S = Σ_s |sector_signed_raw[s]|
  target = max(|equity_bucket|, 1)*1.15
  scale = min(1, target/max(S, eps))
  sector_signed[s] = sector_signed_raw[s]*scale

## Ticker allocation
Candidate set T is deterministic and allowlisted.
For each ticker t:

base = sector_signed[sector(t)] * 0.85

exposure = Σ_k c_k * exposure[t][k]   (0..1 weights)

mention_boost = 1 + 0.08*log(1 + mention_count(t))
llm_mult = 1 + 0.15*(llm_strength(t) - 0.5)   (bounded 0.925..1.075)

ticker_signed_raw = (base + signed_score*tanh(exposure)) * mention_boost * llm_mult
ticker_signed = clamp(ticker_signed_raw, -100, +100)

expected_return_bps (pre-calibration) = clamp(ticker_signed*2.0, -5000, +5000)

Winners = top 25 by ticker_signed
Losers = bottom 25 by ticker_signed

