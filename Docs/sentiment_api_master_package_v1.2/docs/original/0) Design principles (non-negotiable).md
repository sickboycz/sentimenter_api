0) Design principles (non-negotiable)

Standalone: runs 24/7, crawls, stores, computes; no manual babysitting.

Evidence-first: every score must point back to sources (URLs + timestamps + extracted spans).

Multi-resolution memory: L0 raw → L1 facts → L2 micro → L3 structured → L4 delta (same pattern as PaperScraper).

No overfit: weights are calibrated via forward evaluation (expectation → reality), not tuned on hindsight.

Pluggable models: summarizer/embeddings are swappable (OpenAI now; local later).

Robots/ToS compliant: crawl politely, cache, dedupe, respect robots.txt.

1) What the system produces (outputs)

Think of outputs as products:

A) Sentiment Index (SPY-centric baseline)

sentiment_index in [-1, +1]

uncertainty in [0, 1]

impact_pressure (expected magnitude, 0..1)

regime label (risk-on/risk-off, vol-expansion, etc.)

dominant_themes (inflation, war, trade, AI bubble, energy shock…)

B) Impact-scored events

Each news cluster becomes an Event:

event type: macro / geopolitics / trade / regulation / earnings / weather / rates

affected assets: SPY, sectors, tickers

expected lag window

confidence and unknowns

C) Queryable memory

You can ask:

“Why is sentiment negative?”

“What moved markets last 24h?”

“What are the top impact events for semis?”

“Show all ‘trade war’ events and correlation to SPY returns.”

2) Architecture overview (services + data plane)
Core services

Crawler/Collectors

RSS ingest (fast, cheap)

“full text fetcher” (article HTML extraction)

Archive backfill worker (historical crawl)

Normalizer + Deduper

canonical article IDs (hash)

near-duplicate clustering (same story across sources)

Summarization Engine (L0→L4)

L1 factual extraction (entities, numbers, locations, dates)

L2/L3 summaries schema-locked

L4 delta vs previous narrative state

Vector Memory + Retrieval

embeddings for articles, clusters, events, “belief snapshots”

hybrid search: vector + keyword + metadata filters

Event/Impact Engine

event taxonomy classification

causal mapping (resource → sector → ticker)

impact scoring (magnitude + lag + confidence)

Market Data Engine

SPY history bars (1m/5m/1h/1d)

volatility, drawdown, realized vol

alignment of event timestamps to market sessions

Forward Evaluation + Calibration

freeze expectations at event time

measure reaction at T+1/3/7/14

update calibration curves (not rules)

API Gateway

endpoints similar in spirit to Moodix: index + parameters + historical access

plus “ask” endpoints (RAG over your memory)

3) Storage model (modern + robust)
A) Relational “truth store” (Postgres)

Use Postgres as canonical truth:

articles (metadata)

article_bodies (extracted text pointers)

clusters (dedupe groups)

events (structured event records)

event_impacts (ticker/sector mapping + scores)

sentiment_timeseries (index by time)

expectations + outcomes (forward eval ledger)

runs + errors (audit)

B) Object storage (raw L0)

HTML snapshots

extracted clean text

JSON summaries

compressed archives

C) Vector store (choose one)

You want “modern but not fragile”:

Recommended default: Postgres + pgvector

simplest ops (one DB)

good enough for your scale

supports hybrid retrieval with metadata filters

Alternative if you want dedicated vector performance:

Qdrant (excellent filters + reliability)

Milvus (bigger ops)

Weaviate (bigger ops)

For your “single server, audit-grade” preference: pgvector wins.

4) Summarization + “brain” layer (L2/L3/L4 schemas)
Article L2 (micro)

headline

entities (countries, orgs, people, commodities)

tone: neg/neutral/pos

topics: list

key_claims: <=3 bullets

why_it_matters: <=2 bullets

uncertainty_flags: list

Cluster L3 (structured)

canonical_story

what_changed (delta)

likely_channels: rates / inflation / supply shock / risk aversion / flows

time_horizon: intraday / days / weeks

confidence

Event L4 (delta over time)

This is your “narrative state machine”:

“Trade tensions increasing” vs “trade tensions easing”

“Weather threat now confirmed” etc.

All schema-locked, no essays.

5) Impact scoring (how we avoid noise)
A) Event severity (0..1)

Inputs:

source credibility weight

number of independent sources

novelty (delta vs prior state)

proximity (is it actionable now?)

scope (local vs global)

B) Market sensitivity multiplier

current regime (vol high? risk-off? liquidity thin?)

event type (rates > geopolitics > earnings in SPY context, conditional)

C) Asset exposure mapping

sector exposure (SPDR sector ETFs)

known upstream/downstream mapping

country exposure (China/India focus multiplier when calendar says so)

D) Final impact score

impact = severity × sensitivity × exposure × confidence

Store this per ticker, and aggregate to SPY.

6) Correlation + attribution engine (SPY + event stream)
A) Event windows

For each event:

define windows: pre (T-1d), reaction (T0..T+1d), drift (T+2..T+14)

B) Market metrics

SPY return, vol, volume anomaly

relative performance: sector ETFs

C) Attribution outputs

“Events that historically precede vol spikes”

“Events that drift (slow repricing)”

“False alarms”

This is where the system learns.

7) API design (Moodix-inspired + more)

Moodix-style “index + derived parameters + historical access” idea is exactly right.

Core endpoints

GET /sentiment/index?at=...&tf=...

GET /sentiment/history?from=...&to=...

GET /events?from=...&to=...&type=...&min_impact=...

GET /events/{event_id} (evidence + sources)

GET /impacts?event_id=... (tickers ranked)

GET /clusters?topic=... (canonical story groups)

GET /correlations?event_type=...&horizon=...

POST /ask (RAG over vector memory; returns answer + citations + evidence IDs)

Operator endpoints

POST /ingest/run (kick)

GET /ingest/status

GET /health

GET /budget/status (token spend + caps)

8) Crawling sources (practical starting set)

Start with RSS + a few high-quality outlets, then expand:

Financial: Reuters (RSS where available), WSJ (paywall = metadata only), FT (paywall), major finance blogs

Macro: central banks, gov releases

Geopolitics: AP/Reuters world, official statements

Weather: NOAA, EIA/USDA releases (events are structured)

Archive backfill:

focus on major events: CPI/FOMC windows, 2020 crash, 2022 inflation shock, etc.

9) Implementation plan (phased, minimal risk)
Phase 1: Live RSS + dedupe + L2 summaries

prove throughput

build vector memory for articles + clusters

produce daily sentiment series (basic)

Phase 2: Event engine + impact scoring

taxonomy + exposure map v0

publish /events and /impacts

Phase 3: SPY history + correlation engine

attach market outcomes to events

compute lag profiles, drift vs snap

Phase 4: Forward calibration loop

expectation ledger + outcomes

adjust confidence/lag priors

Phase 5: Archive backfill

replay historical news + SPY

start building correlation library

10) Tooling choices (modern + practical)

Python + FastAPI + workers (same pattern as PaperScraper)

Postgres + pgvector

Object storage on disk (later S3)

RSS parser + article extraction (readability-lxml / trafilatura)

Embeddings: OpenAI embeddings now, local later

Summaries: schema-locked, Responses API