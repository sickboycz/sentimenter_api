# Research Methods — SPY Impact Calibration (v1.0)

This document specifies how sentiment_api measures whether news impacts SPY and how it learns calibration **without overfitting**.

## 1) What we are measuring
We keep two separate questions:

1) **Does this kind of event move SPY?** (impact magnitude)
2) **Does it move SPY up or down?** (direction)
3) **When does it move?** (lag/horizon)
4) **How reliable is the signal?** (confidence / hit rate)

## 2) Event timestamping rules
Each cluster has:
- `first_seen`: first time we observed the story
- `event_ts`: canonical time used for market alignment

Default for v1:
- If the cluster references a scheduled release (CPI, FOMC), set `event_ts` to the release time if extractable.
- Else, use `first_seen`.

## 3) Market alignment
For SPY:
- Use regular trading hours (RTH) session boundaries for intraday windows.
- If `event_ts` occurs outside RTH:
  - treat next market open as `T0_open`,
  - measure overnight gap separately (close→next open).

## 4) Return windows (default)
- 30m, 2h, 1d, 3d, 1w

Compute:
- simple returns
- absolute returns
- signed direction classification:
  - up if return > +eps
  - down if return < -eps
  - neutral otherwise
  - eps default: 0.10% intraday, 0.25% daily

## 5) Baseline / abnormal returns (optional v1.1)
To reduce regime bias:
- subtract market baseline (SPY itself doesn't have baseline)
- for sectors/tickers, subtract SPY or relevant sector ETF

## 6) Conditioning / stratification (avoid Simpson’s paradox)
Report results conditioned on:
- volatility regime (low/med/high)
- time-of-day liquidity (open, mid, close)
- impact_level (L0..L5)
- event_type

## 7) Forward-only calibration (no hindsight)
Store expectation at event time:
- expected_direction
- expected_impact_score
- horizon

Later compute outcomes and update:
- calibration curves:
  - P(move | impact_level, event_type)
  - E(|return| | impact_score, event_type)
- direction hit rates:
  - P(sign correct | event_type, regime)

Never rewrite historical expectations.

## 8) Correlation vs causation
We provide correlation and event-study summaries, but:
- multiple events can overlap,
- macro regime and earnings season confound.

Therefore v1.0 explicitly supports:
- “Top driver” decomposition (which clusters contributed to index)
- “Overlap penalty” (reduce confidence when many clusters overlap)

## 9) Output artifacts
Research endpoints return:
- sample sizes
- mean/median returns
- mean absolute returns
- hit rates
- confidence intervals (optional v1.1 bootstrap)

