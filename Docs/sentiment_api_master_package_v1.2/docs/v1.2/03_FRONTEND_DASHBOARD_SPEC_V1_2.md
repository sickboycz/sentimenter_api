# Frontend dashboard spec — v1.2 (glassy research shell)

## Goals
- Provide a single place to evaluate market conditions from:
  - mood index + wave
  - breaking news clusters
  - impact allocations (markets/sectors/tickers)
  - topic indices
  - research/event studies
  - ops (health/lag/errors/cost)

## Visual design
- Dark, glassy UI:
  - blurred panel surfaces
  - subtle border + shadow
  - restrained color usage (let charts convey variation)
- Left rail navigation + top header
- Search-first:
  - global search in header
  - filters pinned in left panel for each page

## Navigation (left rail)
- Overview
- News
- Markets
- Sectors
- Tickers
- Topics
- Research
- Sources
- Ops

## Pages

### Overview
- Intraday mood index chart (line)
- Sentiment wave (MA5 - MA10) chart
- News volume + volatility (two charts)
- Top driver clusters list (cards)
- Top markets/sectors/tickers (tables)
- Topic contribution ranking (table)

### News
- Cluster feed with:
  - filters (impact level, region, topic, market bucket, sector, ticker)
  - sort by last_seen desc
- Cluster card:
  - headline + bullets
  - impact badge (L0–L5)
  - direction + horizon + confidence
  - chips: markets/sectors
  - winners/losers tickers (top 5 each)
  - evidence URLs
- Drilldown page:
  - evidence passages
  - historical analogs
  - per-asset allocation explanation

### Markets
- Market bucket scoreboard (US EQ, US Rates, USD, Oil, Gold, Credit)
- contribution by channel (stacked bar)
- drilldown: clusters contributing to selected market

### Sectors
- sector heatmap
- sector time series
- drilldown: top tickers and clusters per sector

### Tickers
- search + watchlist
- ticker impact timeline:
  - clusters affecting this ticker
  - expected vs realized return (when measured)
- compare vs SPY and sector ETF (when market data available)

### Topics
- topic index chart (multi-series selectable)
- topic ranking table + sparkline
- drilldown: clusters belonging to topic

### Research
- event study builder UI:
  - pick topic/region/impact filters
  - choose windows: 30m, 2h, 1d, 3d, 1w
- outputs:
  - mean/median returns
  - hit rate
  - sample size
  - distribution charts

### Sources
- registry list by pack/type
- status: enabled, last_success, lag, errors

### Ops
- health summary card
- ingestion lag by source chart
- translation errors
- pipeline stage throughput
- cost widgets (optional if tracked)

## Frontend engineering requirements
- Next.js + TypeScript
- TanStack Query for caching/polling
- Zod runtime validation of API responses
- Virtualized lists for large feeds
- SSE support:
  - auto-reconnect
  - merge updates into query cache

## Acceptance criteria
- AC-F1: all pages render with mock mode and live mode.
- AC-F2: global search filters clusters + tickers.
- AC-F3: runtime validation errors are user-friendly (no blank screen).
- AC-F4: feed handles 10k clusters without UI freezing.
