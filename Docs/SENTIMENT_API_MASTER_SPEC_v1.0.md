# Sentiment_API — Master Specification v1.0 (Build‑Ready)

**Product name:** `sentiment_api`  
**Codename:** **Sentimeter**  
**Primary consumer:** IBKR dashboard/bot (**API-only**)  
**Operating mode:** 24/7 standalone daemon + workers (no manual babysitting)

---

## 0) Executive Summary

`sentiment_api` is a standalone news+market intelligence system that:

1. **Ingests** global macro, economic, political, and geopolitical news (major + minor).
2. **Normalizes to English-first** (translation + provenance preserved).
3. **Deduplicates and clusters** multi-source coverage into story clusters.
4. Produces multi-resolution **evidence-first memory** (L0→L4) and **vector memory** for retrieval.
5. Computes per-cluster **impact** (magnitude, direction, horizon, confidence) and aggregates into **intraday + daily sentiment indices**.
6. Runs historical **event studies and calibration** vs SPY (and optionally ES futures) with forward-only evaluation.
7. Exposes a stable **REST API** for dashboards/bots with:
   - Moodix-compatible “SP sentiment” series export,
   - event/cluster drill-down with citations,
   - research endpoints (correlation + event study),
   - optional RAG “ask” endpoint over your memory.

This document package is intentionally **implementation-complete**: it defines modules, acceptance criteria, schemas, data model, ops, and build order.

---

## 1) Non‑Negotiable Design Principles (System Constitution)

These principles govern every design choice:

1. **Standalone**: runs 24/7; crawls, stores, computes; no manual babysitting.
2. **Evidence-first**: every score must point back to sources (URLs + timestamps + extracted spans).
3. **Multi-resolution memory**: L0 raw → L1 facts → L2 micro → L3 structured → L4 delta (PaperScraper-like).
4. **No overfit**: calibrate weights via forward evaluation (expectation → reality), not hindsight tuning.
5. **Pluggable models**: embeddings/summarizer are swappable (OpenAI now; local later).
6. **Robots/ToS compliant**: crawl politely, cache, dedupe, respect robots.txt.

These come directly from the non-negotiable principles doc. (See package sources.)

---

## 2) Product Outputs (What the System Produces)

Think of outputs as *products*:

### 2.1 Sentiment Index (SPY-centric baseline)
- `sentiment_index ∈ [-1, +1]` — normalized market mood
- `uncertainty ∈ [0, 1]` — confidence / disagreement
- `impact_pressure ∈ [0, 1]` — expected magnitude / volatility pressure
- `regime_label` — e.g., RiskOn / RiskOff / Neutral, plus volatility expansion markers
- `dominant_themes[]` — inflation, war, trade, energy shock, liquidity stress, etc.

### 2.2 Impact‑Scored Events (story clusters → events)
Each cluster becomes an **Event** object with:
- event type: macro / geopolitics / trade / regulation / earnings / weather / rates / sanctions / energy / conflict
- affected assets: SPY baseline + sectors + tickers (future expansion)
- expected lag window: intraday / days / weeks
- confidence and unknowns
- evidence links (citations)

### 2.3 Queryable Memory (RAG)
You can query:
- “Why is sentiment negative?”
- “What moved markets last 24h?”
- “Top impact events for semis?”
- “Show ‘trade war’ events and correlation to SPY returns.”

---

## 3) Scope & Success Criteria

### 3.1 In-scope (v1.0)
- Global news ingestion via:
  - global aggregator/firehose,
  - official institutions,
  - sanctions lists,
  - conflict/humanitarian datasets,
  - energy/nuclear sources,
  - optional licensed feeds (metadata-only until licensed).
- English-first normalization + translation provenance.
- Clustering, multi-resolution memory, vector retrieval.
- Impact scoring + index aggregation.
- Historical research: event studies vs SPY/ES; forward-only calibration.
- REST API (documented in OpenAPI + JSON schemas).
- Ops: monitoring, health endpoints, persistence.

### 3.2 Out of scope (v1.0)
- Automated order execution (trading).
- Paywall bypass; restricted sources are metadata-only unless licensed.
- Heavy fine-tuning. Prefer prompt-locked schemas + calibration.

### 3.3 SLOs / targets
- Ingestion freshness p95 (RSS/API): < 10 minutes.
- Index update latency (qualifying clusters): < 5 minutes.
- English normalization coverage: 99% have English fields or explicit failure reasons.
- API uptime: 99.5% monthly.

---

## 4) Architecture Overview

### 4.1 Topology (logical)
```mermaid
flowchart LR
  RSS[RSS/Feeds] --> Q[Queue]
  WEB[Web Fetcher] --> Q
  ARC[Archive Backfill] --> Q
  GDELT[GDELT/API firehose] --> Q
  DATA[Structured datasets] --> Q

  Q --> ING[Normalize + Dedupe]
  ING --> RAW[(L0 Object Store)]
  ING --> SUM[Summaries L1-L4 + Embeddings]
  SUM --> DB[(Postgres)]
  SUM --> VEC[(Vector Store)]

  MK[Market Data (SPY/ES)] --> DB
  DB --> EVT[Event + Impact Engine]
  EVT --> IDX[Index Engine]

  DB --> CAL[Historical Calibration]
  CAL --> EVT
  EVT --> FWD[Forward Eval Ledger]

  API[API] --> DB
  API --> VEC
```

### 4.2 Runtime services (reference implementation)
- `api` — FastAPI (or equivalent) serving endpoints
- `worker` — queue consumers for ingestion, summaries, embeddings, scoring
- `daemon` — orchestration loop (source polling, backfill scheduler, budgets)
- `postgres` — canonical truth store + pgvector (default)
- `redis` — queue + caching (or NATS/RabbitMQ; Redis OK for v1)
- `object_store` — local disk path `/data/artifacts` (S3 later)

---

## 5) Data Plane: Ingestion → Memory → Scoring → Index

### 5.1 Ingestion pipeline (live)
1. **Discover**
   - Poll RSS feeds / official pages
   - Query global firehose by topics/regions
2. **Fetch**
   - HTTP fetch article HTML or API payload
   - Save L0 HTML snapshot (if allowed)
3. **Extract**
   - HTML → main text (trafilatura/readability)
   - Quality scoring (length, boilerplate ratio)
4. **Normalize**
   - canonical URL, timestamp UTC
   - language detect
   - translate to English (store provenance)
5. **Deduplicate**
   - URL hash for exact dupes
   - text fingerprint for near-dup
6. **Cluster**
   - embedding similarity clusters multi-source same-story coverage
7. **Summarize & Extract**
   - L1 facts
   - L2 micro summary
   - L3 cluster summary
   - L4 narrative delta state
8. **Score**
   - impact score + level + direction + horizon + confidence
9. **Index update**
   - update intraday index ticks + daily OHLC rollups

### 5.2 Historical pipeline (backfill)
Backfill uses the same pipeline, but:
- uses date partitioning per source,
- enforces **no lookahead** when generating expectations,
- runs event-study windows later for calibration.

---

## 6) Memory Model: L0 → L4 (Evidence-First)

### 6.1 L0 Raw
**Stored artifacts**
- raw HTML (where allowed)
- extracted clean text
- fetch metadata (headers, status, time)

**Object store layout**
```
/data/artifacts/news/{source_id}/{yyyy}/{mm}/{dd}/{article_id}.html
/data/artifacts/news/{source_id}/{yyyy}/{mm}/{dd}/{article_id}.txt
/data/artifacts/embeddings/{object_type}/{object_id}.json
/data/artifacts/summaries/{level}/{object_id}.json
```

### 6.2 L1 Facts (strict JSON)
Minimal structured extraction:
- entities (people/orgs/countries)
- numbers, dates
- key claims (with evidence pointers)
- uncertainty flags

### 6.3 L2 Micro Summary (strict JSON)
Per-article structured summary:
- headline_en
- topics[]
- tone (polarity/subjectivity)
- key_claims ≤ 3
- why_it_matters ≤ 2
- uncertainty_flags[]
- evidence_refs[]

### 6.4 L3 Cluster Summary (strict JSON)
For each story cluster:
- canonical_story
- what_changed (delta narrative)
- likely_channels: rates / inflation / supply shock / risk aversion / flows / sanctions / conflict
- affected_assets: SPY + sectors + tickers
- horizon: intraday/days/weeks
- confidence

### 6.5 L4 Delta (state machine)
Narrative state transitions:
- `state_key` (e.g., `trade_us_cn`, `middle_east_shipping`, `us_inflation`)
- `prev_state` → `new_state`
- change direction + confidence
- supports “trend in news reality” over time.

### 6.6 Summary caching
Every summary is deterministic per input + version:
```
dedupe_key = hash(object_id + text_hash + schema_version + model_id + prompt_version)
```

---

## 7) Vector Memory & Retrieval (Local, Auditable)

### 7.1 Vector objects to embed
- articles (English cleaned text)
- clusters (L3 canonical summary)
- events (structured L4 + impact)
- narrative deltas (state changes)
- historical research artifacts (event-study summaries)

### 7.2 Default store
- **Postgres + pgvector** (single-node ops, hybrid search, easy backups)
- optional: Qdrant/Milvus later if needed

### 7.3 Retrieval modes
- clustering similarity search (incoming article → nearest clusters)
- /ask RAG:
  - retrieve top K objects using hybrid search (vector + filters)
  - answer with citations (source URLs + evidence passage IDs)

---

## 8) Event & Impact Engine (Core Differentiator)

### 8.1 Separate “tone” from “market impact”
Tone sentiment is not market mood. We output:
- tone polarity (text)
- market direction (RiskOn/RiskOff)
- magnitude (impact score/level)
- horizon (how long effects likely persist)

### 8.2 Impact formula (canonical)
```
impact = severity × sensitivity × exposure × confidence
```

- **severity (0..1)**: credibility, source_count, novelty, scope, urgency  
- **sensitivity (0..1)**: current regime (vol/risk state), event type priority  
- **exposure (0..1)**: topic → sector/ticker mapping (SPY composition proxy)  
- **confidence (0..1)**: disagreement, extraction quality, evidence quality

### 8.3 Impact levels (published)
Map `impact_score (0..100)` → impact levels:
- L0 noise
- L1 low
- L2 medium
- L3 high (index mover)
- L4 very high (macro regime / multi-day)
- L5 crisis (liquidity/policy shock)

### 8.4 Event taxonomy (v1.0)
**Macro / policy**
- Monetary policy: hike/cut, guidance, QT/QE, facilities
- Inflation: CPI/PCE surprises, wage inflation, supply-driven inflation
- Growth/recession: GDP, PMIs, unemployment, earnings recession
- Fiscal policy: budget, stimulus, shutdowns, debt ceiling
- Financial stability: bank stress, credit spreads, liquidity events

**Geopolitics**
- War escalation/de-escalation
- sanctions / export controls
- elections / coups / domestic instability
- diplomatic breakdown / treaties
- shipping chokepoints / piracy

**Energy & commodities**
- supply cuts / disruptions
- pipeline attacks / refinery outages
- nuclear incidents / safety alerts

**Disasters / humanitarian**
- disasters affecting logistics, commodities, insurers
- major humanitarian escalations with geopolitical spillover

### 8.5 Mood vector (internal representation)
We compute an internal “risk vector” per cluster/day:
- `risk_appetite ∈ [-1, +1]`
- `volatility_pressure ∈ [0, 1]`
- `growth_outlook ∈ [-1, +1]`
- `inflation_pressure ∈ [-1, +1]`
- `rates_pressure ∈ [-1, +1]`
- `liquidity_stress ∈ [0, 1]`
- `geopolitical_risk ∈ [0, 1]`
- `energy_supply_risk ∈ [0, 1]`

Then map → `Direction` (RiskOn/RiskOff/Neutral) and `impact_pressure`.

### 8.6 Direction determination (two-mode)
**Expected direction** (fast, explainable):
- Derived from taxonomy + surprise vs narrative baseline

**Realized direction** (best):
- Measure market reaction around event timestamp (SPY/ES)
- Store both expected and realized; calibrate confidence over time.

---

## 9) Index Engine (Moodix-compatible + Enhanced)

### 9.1 Intraday index
A time series (1m/5m/15m bins):
- `index_value` (running sum / normalized)
- `news_volume` (count)
- `news_volatility` (impact intensity)
- `sentiment` label (RiskOn/RiskOff/Neutral)

### 9.2 Daily index
Daily OHLC derived from intraday:
- open/high/low/close
- daily `index` value (close)
- MA5, MA10, and `sentiment_wave = MA5 - MA10` for compatibility

### 9.3 Compatibility mode fields
We publish a Moodix-like shape to overlay easily:
- `moodix_index`, `ma5_moodix`, `ma10_moodix`, `sentiment_wave`
- intraday: `moodix_index_intraday`, `news_volume_intraday`, `news_volatility_intraday`

### 9.4 Enhanced fields
- impact_level_counts per day
- top themes and regions
- top contributing clusters (drivers)
- confidence index

---

## 10) Research Engine: SPY/ES Event Studies + Correlation

### 10.1 Market data ingestion
Minimum bars for v1:
- SPY: 5m, 1h, 1d OHLCV
Optional:
- ES futures, sector ETFs

### 10.2 Event alignment
Normalize timestamps to market session:
- Pre window: T-1d
- Reaction: T0..T+1d
- Drift: T+2..T+14d

### 10.3 Outputs
- Lag distributions per event type/topic
- Drift vs snap repricing classification
- False alarm rates
- Correlation and conditional expectation metrics

### 10.4 Forward-only learning (no overfit)
- Freeze expectations at event time
- Measure outcomes later
- Update calibration curves (meta), not hard-coded rules

---

## 10.5 Moodix reference contract (for compatibility)

Moodix’s public docs describe:
- A single endpoint that returns JSON time series:
  - `https://app.moodix.market/api/sp-sentiment/?api_key=<YOUR_KEY>`
- Fields for daily OHLC + index + MA5/MA10 wave + intraday volume/volatility.

We **copy the output contract**, not their internal methodology:
- We publish the same canonical field names in our compatibility endpoint `GET /api/sp-sentiment`
- We allow API keys in **query param (`api_key`)** or **header (`X-API-Key`)** to keep both Moodix-style and standard REST usage.

(See Moodix “Accessing the API” and “API Fields” in the web appendix.)


## 11) API Specification (Summary)

See:
- `openapi/sentiment_api.openapi.yaml`
- `schemas/` for JSON Schemas

**Core endpoints**
- Moodix-compatible:
  - `GET /api/sp-sentiment`
- Real-time mood:
  - `GET /v1/mood/now`
  - `GET /v1/index/intraday`
- News intelligence:
  - `GET /v1/news/clusters`
  - `GET /v1/news/clusters/{cluster_id}`
- Research:
  - `GET /v1/research/spy/event-study`
- Sources registry:
  - `GET /v1/sources`
- Ops:
  - `GET /v1/health`

**Optional /v1.1**
- `POST /v1/ask` (RAG query)
- `POST /v1/admin/ingest/run` (operator)

---

## 12) Source Strategy (Global Coverage in English)

### 12.1 Reality check: “complete list of sources”
There is no static “complete list” of every outlet worldwide that remains stable.

Therefore v1.0 defines **complete coverage** as:

1) **Global firehose** that already monitors a huge number of outlets across countries and languages; we ingest it and output English.  
2) **High-signal direct sources** (official institutions + structured datasets) that frequently drive markets.  
3) Optional direct RSS for major public news outlets that publish RSS legally.  
4) A **Source Registry** that is maintainable and extensible (packs + per-country expansion).

### 12.2 Source packs (v1.0)
- `global_firehose` (worldwide media, multilingual)
- `official_macro` (central banks, stats agencies, ministries)
- `geopolitics` (UN, State, EU institutions, etc.)
- `sanctions` (UN/EU/UK/US pages and lists)
- `conflict_humanitarian` (ACLED/UCDP/ReliefWeb/CrisisGroup)
- `energy_nuclear` (EIA/IAEA/OPEC, etc.)
- `major_public_media_rss` (BBC/Al Jazeera/DW/etc. — optional)

### 12.3 English-first enforcement
All objects published by the API default to English fields:
- `*_en` fields are mandatory unless `translation_status=failed`
- original language preserved for audit

---

## 13) Data Model (Postgres) — Canonical “Truth Store”

See `db/schema.sql` for full DDL. Summary:

### 13.1 Core tables
- `sources`
- `articles`
- `article_bodies`
- `clusters`
- `cluster_members`
- `summaries` (L1–L4 JSONB, schema-versioned)
- `events`
- `event_impacts`
- `sentiment_timeseries`
- `market_bars`
- `expectations`
- `outcomes`
- `runs` (audit + errors)

### 13.2 Id strategy
- `article_id = art_<base32url(hash(source_id + canonical_url + published_at))>`
- `cluster_id = clu_<base32url(hash(canonical_story_key + first_seen))>`
- `event_id = evt_<base32url(hash(cluster_id + event_type + first_seen))>`

All ingestion is **idempotent**:
- inserts use `ON CONFLICT DO NOTHING/UPDATE`
- processing uses dedupe keys and state markers.

---

## 14) Ops & Security (v1.0)

### 14.1 Deployment profile
- Single-server first:
  - Postgres (with pgvector)
  - Redis
  - API + workers
  - Local artifacts directory

### 14.2 Key management
- API keys stored hashed in Postgres
- Support key rotation and per-key rate limits

### 14.3 Backups
- nightly `pg_dump` + artifacts tar/rsync
- restore procedure tested monthly

### 14.4 Crawling etiquette
- respect robots.txt
- rate limiting
- caching
- identify user-agent and contact
- backoff on 429/5xx

---

## 15) Test Plan (v1.0)

### Unit tests
- URL canonicalization
- robots allow/deny rules
- schema validation (summaries + API)
- scoring math (impact aggregation)

### Integration tests
- crawl → extract → summarize using mocked HTTP fixtures
- cluster formation and updates
- historical replay alignment vs SPY bars

### Performance tests
- sustained ingestion throughput
- queue backpressure
- DB indexes effectiveness

---

## 16) Build Order (Cursor Implementation Checklist)

Implement in this order:

1. **M0 Source Registry + validator**
2. **M1 Collectors + queue**
3. **M2 Normalization + translation**
4. **M3 Dedup + clustering**
5. **M4 Summaries L1–L4**
6. **M7 Embeddings + vector retrieval**
7. **M5 Impact engine**
8. **M6 Index engine**
9. **M9 API**
10. **M8 Research engine**
11. **M10 Ops/monitoring**

---

## 17) Acceptance Criteria (v1.0) — Full List

This section is the authoritative checklist.

### M0 — Source Registry & Configuration
- AC-M0.1: loads registry (YAML/JSON), validates schema, refuses to start on invalid config  
- AC-M0.2: unique immutable `source_id`  
- AC-M0.3: per-source enable/disable without code  
- AC-M0.4: packs enable/disable  

### M1 — Collectors (Ingestion)
- AC-M1.1: p95 fetch < 10 min for RSS/API sources  
- AC-M1.2: each item has `source_id`, `source_type`, `url`, `published_at`, `fetched_at`, `title_raw`  
- AC-M1.3: retries + circuit breaker; per-source error ledger  
- AC-M1.4: backfill by date range where possible  

### M2 — English Normalization & Translation
- AC-M2.1: each item yields `title_en`, `content_en` OR translation failure reason  
- AC-M2.2: store `lang_original`, `translation_provider`, `translation_confidence`  
- AC-M2.3: UTC timestamps everywhere  

### M3 — Deduplication & Clustering
- AC-M3.1: exact URL duplicates never produce >1 `article_id`  
- AC-M3.2: near duplicates cluster via embeddings/fingerprint  
- AC-M3.3: stable `cluster_id`, `first_seen`, `last_seen`, `source_count`  
- AC-M3.4: cluster updates do not change `cluster_id`  

### M4 — Evidence + Summary (RAG)
- AC-M4.1: each cluster yields `summary_bullets_en`, `what_changed_en`, `why_it_matters_en`, `what_to_watch_en`  
- AC-M4.2: each summary references evidence (URLs + passages)  
- AC-M4.3: summaries cached by versioned dedupe key  

### M5 — Impact & Mood Engine
- AC-M5.1: every cluster has `impact_score`, `impact_level`, `expected_direction`  
- AC-M5.2: when market reaction available, store realized direction/move  
- AC-M5.3: produce `reason_codes[]`  
- AC-M5.4: confidence in [0,1] and decreases with weak evidence  

### M6 — Index Engine
- AC-M6.1: intraday index updates within 5 minutes of qualifying cluster change  
- AC-M6.2: daily OHLC computed with consistent day boundary  
- AC-M6.3: `sentiment_wave = MA5 - MA10` published  
- AC-M6.4: `news_volatility` increases with higher-impact events  

### M7 — Local + Vector Memory
- AC-M7.1: audit trail for any published value  
- AC-M7.2: vector retrieval supports similar clusters/events/analogs  
- AC-M7.3: delete/tombstone semantics for retention policy  

### M8 — Research Engine
- AC-M8.1: event studies for configurable windows  
- AC-M8.2: filters by topic/region/event_type/impact_level  
- AC-M8.3: store `research_run_id` for repeatability  

### M9 — API Service
- AC-M9.1: all endpoints require API key  
- AC-M9.2: consistent pagination + error shape  
- AC-M9.3: p95 latency < 300ms for list endpoints  

### M10 — Observability & Ops
- AC-M10.1: ingestion lag/error metrics per source  
- AC-M10.2: translation failure metrics  
- AC-M10.3: queue depth + throughput metrics  
- AC-M10.4: health endpoint exposes dependency status  

---

## 18) Appendices

- A) Prompt contracts: `/prompts/`
- B) JSON Schemas: `/schemas/`
- C) OpenAPI: `/openapi/`
- D) Source registry: `/registry/`
- E) DB schema: `/db/`
- F) Ops runbook: `/ops/`

