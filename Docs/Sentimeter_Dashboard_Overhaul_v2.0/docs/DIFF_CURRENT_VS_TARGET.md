# Current implementation vs target mockups (UI diff)

This document exists to prevent “hand-wavy” UI upgrades. It lists concrete visual/UX gaps between:

- Current screenshots: `docs/reference/Screenshot_2026-02-02_*`
- Target mockups: `docs/reference/ChatGPT_Image_Feb_2_2026_*` and `docs/reference/A_*mockup*.png`

## Key gaps observed (must be fixed in v2.0)

### 1) Overview page density
**Current:** only 3–4 large empty cards, no charts, no ranked lists.  
**Target:** gauge + index chart + wave chart + volume/volatility + markets/sector tables + heatmaps + winners/losers + latest events.

**Fix:** v2 overview implements:
- Gauge (Mood indicator)
- Intraday index vs volatility line chart
- Market impacts list
- Sector performance table + heatmap
- Winners/losers
- Latest high-impact clusters grid

### 2) News feed richness
**Current:** page header only, no cluster cards.  
**Target:** event feed with impact labels, per-event tickers, sectors, quick tags.

**Fix:** v2 news page implements cluster cards with:
- headline + bullets
- impact badge
- winners/losers chips

### 3) Visual hierarchy & glass fidelity
**Current:** glass is present, but surfaces are too flat and panels feel empty.  
**Target:** subtle gradients, stronger section headers, consistent spacing, crisp tables.

**Fix:** v2 introduces:
- token-driven surfaces (`glass` / `glass-strong`)
- consistent radii/shadows
- tighter typography hierarchy
- table components with sticky headers + row hover

### 4) Degraded/empty states
**Current:** empty data shows blank cards.  
**Target expectation:** always show something meaningful (skeletons / “no data yet” guidance).

**Fix:** v2 provides:
- skeleton loaders
- demo mode (fixtures)
- empty-state cards for zero clusters

### 5) Reliability for demos/tests
**Current:** UI depends on live backend.  
**Fix:** v2 includes demo fixtures + Playwright runs with demo mode enabled by default.

## Acceptance criteria
- In demo mode, UI must look “finished” on every page.
- In live mode with empty backend data, UI must still show proper empty states (not blank).
