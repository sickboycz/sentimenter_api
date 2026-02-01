Sentiment_API — Global Macro + Political + Geopolitical News Impact System

High‑level technical scope & technical specification (English‑first)

This document defines a standalone sentiment_api service that ingests worldwide economic + political + geopolitical news, normalizes it into English, summarizes in a “paperscraper/RAG” style, computes mood/sentiment + impact levels, and exposes everything via API for your IBKR dashboard and bot.

It is explicitly designed to remove any local LLM dependency from the IBKR bot (no Gemma runtime needed). The only integration point is HTTP API.

1) Goals & key outcomes
Primary goals

Global news ingestion (major + minor): economy, policy, central banks, geopolitics, conflict, sanctions, energy/nuclear, disasters/humanitarian, trade/export controls.

English-first output: everything served to you in English, even if the source language is not English (translation included).

Competitive market mood measurement alongside Moodix:

Provide a Moodix‑compatible endpoint schema (so your dashboard can overlay both).

Provide a richer “explainable impact” layer (clusters → evidence → impact reasoning).

Impact scoring that learns:

Compute impact levels per story and aggregate indices.

Backtest / event‑study vs SPY (and optionally ES futures) to learn if correlation/predictiveness exists.

Local memory + vector memory:

Local structured store (facts, events, timeseries).

Vector store for semantic retrieval (stories ↔ historical analogs ↔ explanations).

Non-goals (explicitly out of scope v1)

Automated trading execution logic in IBKR (your IBKR side consumes signals; it doesn’t execute from this system unless you choose later).

Reproducing paywalled content without licensing. We design for compliance (store metadata/snippets; full text only where permitted).

2) System overview
2.1 Core concept (what “mood” means here)

We separate tone from market mood:

Tone Sentiment: emotional polarity/valence of the text (negative/neutral/positive).

Market Mood: risk appetite and volatility pressure implied by news and/or measured market reaction:

RiskOn vs RiskOff vs Neutral

Strength/impact level (how market‑moving)

Horizon (intraday vs multi‑day)

Moodix’s published schema already separates a daily index, an intraday index, and intraday “news volatility” (strength of impact). We’ll mirror that shape.

2.2 Architectural pattern (PaperQA/paperscraper‑style RAG)

We adopt the RAG loop:

embed documents

embed query/event

retrieve top passages

summarize relevant passages

score/select summaries

generate structured answer/explanation

This is the documented “paper‑qa process.”

In our case:

“documents” = articles, official releases, event datasets, and historical market episodes

“query” = a story cluster, a topic, or “what’s driving RiskOff today?”

2.3 High-level components

Collectors (ingest)

Normalizer (clean, translate to English, metadata)

Dedup + clustering (“same story” merges)

Extractor + summarizer (structured summary w/ citations)

Impact engine (impact magnitude + direction + horizon)

Index engine (intraday + daily index with wave metrics)

Research engine (SPY correlation/event studies)

Memory:

relational store (local memory)

vector DB (vector memory)

API gateway (for dashboard/bot)

3) Complete source plan (worldwide) — English-first

You asked for “complete list of sources” and “all around the world.” The only practical way to be truly global is:

Use one global aggregator/firehose that monitors a huge number of outlets internationally (including non‑English), then

Layer high‑signal official sources and structured geopolitical/conflict datasets that are reliably market-moving.

3.1 Global news firehose (worldwide media, multilingual → English)

GDELT Project

Use GDELT as baseline global coverage (politics, geopolitics, economy, local narratives).

Key capability: search across 65 machine-translated languages using English keywords; GDELT machine translates monitored coverage into English.

GDELT 2.0 is described as updating every 15 minutes and covering 65 live translated languages in some documentation.

What we ingest from GDELT

Articles/URLs + metadata (language, time, source)

(Optional) GDELT “tone” and basic sentiment features as a baseline feature, not your final mood.

English-first handling

Prefer GDELT’s English machine translation when available.

Store both:

text_original (if available and permitted)

text_en (English version)

3.2 Official macro / central bank / statistics sources (high signal)

These sources are direct, authoritative, and often market-moving.

United States

Federal Reserve Board — RSS feeds covering news, press releases, speeches/testimony, stats & more.

Bureau of Labor Statistics — RSS feeds including economic news releases.

Bureau of Economic Analysis — releases page indicates a “News Release Feed (RSS)”.

U.S. Census Bureau — RSS feeds including economic indicator feeds.

U.S. Treasury:

Press releases page (scrape/monitor).

TreasuryDirect RSS feeds (auctions, debt, etc.).

Europe / UK

European Central Bank — RSS feeds for press releases, speeches, publications, FX, etc.

Eurostat — RSS feeds / alert system with common feeds, including economy/finance.

European Commission — press releases RSS feed.

Council of the European Union — RSS feeds including press releases.

Bank of England — RSS feeds covering news, speeches, stats, publications.

Global / cross-border finance

Bank for International Settlements — RSS feeds for BIS updates.

BIS also maintains a directory of central bank and monetary authority websites worldwide (useful for expanding coverage country-by-country).

World Bank — news page exposes an API endpoint for querying news/press releases (useful structured ingestion).

Organisation for Economic Co-operation and Development — newsroom for press releases (scrape/monitor; RSS may vary by section).

3.3 Geopolitical / diplomatic / international institutions (worldwide)

These are key for geopolitical risk, sanctions, war/peace, and policy coordination.

United Nations — General Assembly RSS feeds.

UN Security Council consolidated list updates RSS (sanctions list changes).

NATO — official news/press can be monitored; (RSS availability varies, but integration can be via monitored pages and/or official subscriptions).

U.S. Department of State — RSS feeds for State Department updates.

3.4 Sanctions / export controls / enforcement (policy shock sources)

Sanctions and export controls create immediate repricing risk (energy, banks, defense, shipping, FX).

Office of Foreign Assets Control — OFAC announced retirement of its RSS feed as of Jan 31, 2025; ingestion should use email updates or monitored pages.

UK Sanctions List is the UK government’s single sanctions designations source; OFSI consolidated list closed Jan 28, 2026 (important operational detail).

EU Sanctions Map (monitor updates; also provides the consolidated logic by topic).

Implementation note: sanctions are best treated as structured events (entity designated, date effective, sector, jurisdiction) rather than “news text”.

3.5 Conflict / security / humanitarian structured sources (worldwide)

These sources complement “news articles” with structured event data.

Armed Conflict Location & Event Data Project — ACLED API documentation (conflict event dataset).

Uppsala Conflict Data Program — UCDP API docs and dataset downloads.

ReliefWeb — ReliefWeb API (all content available via API; returns JSON).

International Crisis Group — RSS feeds (CrisisWatch, regional/country feeds).

3.6 Energy / nuclear / supply shock sources (worldwide)

Energy shocks and nuclear events are frequent macro‑market drivers.

U.S. Energy Information Administration — RSS feeds including press releases.

OPEC — press releases page (monitor/scrape).

International Atomic Energy Agency — RSS feeds.

IRENA — RSS feed for releases/publications.

3.7 “Complete world political news” coverage plan (how we ensure it)

You do not want to maintain a static list of every newspaper on earth. The system design is:

GDELT provides broad global news media coverage (multilingual) and English search/translation capability.

“High‑signal official sources” above are monitored directly (RSS/API/scrape).

A Source Registry allows you to add/override sources by country, region, topic.

Source Registry (technical spec)
Each source is defined as:

source_id (stable)

name

type: rss | api | scrape | dataset

domain_allowlist

language_hint: en | auto

translate_to_en: bool

update_interval_sec

credibility_tier: official | reputable_media | local_media | user_added

license_class: open | key_required | paid | restricted

topics: array (macro, rates, geopolitics, conflict, sanctions, energy, etc.)

region: ISO region/country tags

parser_profile: HTML parsing rules if scrape

4) English-first translation & normalization specification
4.1 Requirements

System ingests content from any language it can access.

System serves to you only English fields by default.

Always store:

lang_original

translation_confidence

translated_by = gdelt | openai | local_model

4.2 Translation strategy

For GDELT sources: use GDELT’s translingual machine translation where available.

For non‑GDELT sources: run an internal translation step (OpenAI or local translation model) and standardize output to English.

4.3 Canonicalization rules

Normalize timestamps → UTC

Normalize numbers and units (bps, %, $, barrels/day)

Normalize named entities (countries, leaders, institutions)

Extract “event facts” into structured fields

5) Processing pipeline specification
5.1 Ingestion → clustering → scoring

Fetch

Pull RSS/API

Scrape allowed pages

Query GDELT periodically by topic & region

Parse & clean

Language detect

Translate → English

Deduplicate

exact URL match

near-duplicate text fingerprint

embedding similarity

Cluster

multi-source cluster per story

Extract structured event

event type taxonomy (see section 6)

entities, locations, instruments, policy actions

Summarize (paperscraper style)

bullet facts

what changed

why it matters

what to watch

citations (URLs)

Impact scoring

Index update

Persist

relational + vector stores

5.2 Latency targets (practical)

Ingestion-to-index update: < 5 minutes for most sources (comparable to Moodix’s near-real-time concept; Moodix describes its index updating based on breaking news, with measurement on ES futures).

6) Mood & impact: decision framework (how news impacts “mood”)
6.1 Mood dimensions (internal representation)
Dimension	Range
risk_appetite	-1..+1
volatility_pressure	0..1
growth_outlook	-1..+1
inflation_pressure	-1..+1
rates_pressure	-1..+1
liquidity_stress	0..1
geopolitical_risk	0..1
energy_supply_risk	0..1

These feed the final SP mood score (RiskOn/RiskOff).

6.2 Event taxonomy (what we classify)

Monetary policy: rate hike/cut, guidance, QT/QE, emergency facilities

Inflation: CPI/PCE surprises, wage inflation, supply-driven inflation

Growth / recession: GDP, PMIs, unemployment, earnings recession narratives

Fiscal policy: budget, stimulus, shutdowns, debt ceiling, tax policy

Financial stability: bank stress, credit spreads, liquidity events

Geopolitics: war escalation/de-escalation, sanctions, elections, coups, diplomatic breakdown

Energy & commodities: supply cuts, pipeline attacks, nuclear risk, shipping chokepoints

Trade / export controls: semiconductor export bans, tariffs, supply chain restrictions

Disasters / humanitarian: major disruptions affecting commodities/logistics/insurers

6.3 Impact level scale (published output)
Level	Meaning
L0	noise
L1	low
L2	medium
L3	high
L4	very high
L5	crisis

Impact score (0–100) maps into levels (configurable), e.g.:

0–9 → L0

10–24 → L1

25–44 → L2

45–69 → L3

70–89 → L4

90–100 → L5

6.4 How we determine direction (RiskOn vs RiskOff)

We support two modes:

A) Expected direction (fast, explainable)

Based on event taxonomy + extracted “surprise” vs baseline narrative

Example priors:

Hawkish surprise → RiskOff pressure

Dovish pivot → RiskOn

War escalation / sanctions expansion → RiskOff + volatility pressure

Ceasefire / de-escalation → RiskOn

Energy supply shock → RiskOff via inflation_pressure + geopolitical_risk

B) Realized direction (best)

Measure market reaction in ES or SPY immediately after the headline

Moodix describes measuring breaking-news reaction on ES futures and accumulating those impacts intraday.

Your system will do the same measurement approach (using your market data provider) and store:

expected_direction

realized_direction

direction_confidence

7) Index specification (Moodix-compatible + enhanced)
7.1 Compatibility fields (so your dashboard can overlay Moodix & yours)

Moodix documents these fields; we mirror names and meanings:

date, update_time

open, high, low, close

moodix_index (we will publish our index value under the same field in compatibility mode)

ma5_moodix, ma10_moodix

sentiment_wave (defined as MA5 - MA10; oscillates roughly -1..1 in Moodix docs)

sentiment (RiskOn/RiskOff/Neutral)

trend (Growing/Fading/Sideways)

Intraday:

moodix_index_intraday

news_volume_intraday

news_volatility_intraday

7.2 Enhanced fields (your differentiators)

Add fields your dashboard can use (without breaking compatibility):

impact_level_counts (L0..L5 counts per day)

top_topics[] (with topic index contributions)

top_regions[]

top_clusters[] (IDs for drill-down)

confidence_index (0..1)

explanations[] (short “why RiskOff today”)

8) Local memory + vector memory specification
8.1 Storage layers

Relational (local memory)

Best choice: Postgres (transactions, joins, time series tables)

Vector store (vector memory)

Options:

Postgres + pgvector (simplest)

Dedicated: Qdrant/Milvus (higher scale)

8.2 What gets embedded

Cluster summaries (English)

Key evidence paragraphs

Event objects (“rate hike surprise +50bps”)

Historical episode summaries (“Aug 2011 US downgrade” style analogs)

8.3 Retrieval patterns (must support)

Similar story search

Similar event search (taxonomy + embeddings)

“What’s driving RiskOff” explanation retrieval (top contributors)

“Historical analog” retrieval for market reaction expectations

9) API specification (API-only integration for IBKR dashboard)
9.1 Authentication

API key in query or header (Moodix uses query param api_key). Moodix’s docs directory shows an S&P sentiment endpoint with API key.

9.2 Core endpoints
A) Moodix-compatible endpoint

GET /api/sp-sentiment?api_key=...&from=YYYY-MM-DD&to=YYYY-MM-DD

Returns array of daily records with Moodix-compatible fields (moodix_index, sentiment_wave, etc.).

B) Intraday index

GET /v1/index/intraday?api_key=...&interval=5m&since=...

C) News clusters (actionable feed)

GET /v1/news/clusters?api_key=...&min_impact=L2&topic=geopolitics&since=...

Returns:

cluster_id

first_seen, last_seen

headline_en

summary_bullets_en[]

topics[], regions[]

tone_score

impact_score, impact_level

expected_direction, realized_direction

horizon

sources[] (URLs)

D) Cluster drill-down

GET /v1/news/clusters/{cluster_id}?api_key=...

E) Event research / SPY correlation

GET /v1/research/spy/event-study?api_key=...&topic=inflation&window=1d&from=...&to=...

10) Historical learning vs SPY (and optionally ES)
10.1 Market data ingestion

Use Interactive Brokers historical data to build SPY/ES time series for event study and correlation. IBKR documents using TWS API for historical data retrieval.

10.2 Event study specification

For each cluster/event:

compute returns in windows:

0–30m, 0–2h, 0–1d, 0–3d

compute abnormal move vs rolling volatility

bucket by:

topic

region

impact_level

surprise bucket

Outputs:

“Does L3 geopolitics tend to move SPY meaningfully?”

“Which topics have stable correlation vs which are noise?”

10.3 Calibration feedback loop

Use learned distributions to improve:

breaking-news detector thresholds

impact score scaling

direction confidence

11) Operational specs
11.1 Backfill

Backfill by date ranges:

GDELT historical queries

structured datasets (UCDP/ACLED)

official RSS archives

11.2 Monitoring

ingestion lag per source

dedup ratio

translation failure rate

summarization throughput

index update interval

API latency and error rates

11.3 Data retention

Keep:

metadata + summaries long-term

raw scraped full text only when license permits

12) Compliance & licensing notes (important)

Many major media outlets are paywalled or restrict redistribution/scraping.

The system should be designed to:

prefer APIs/RSS where allowed

store only metadata/snippets + derived features unless licensed

keep citations/URLs so humans can click through

honor robots.txt and terms where applicable

13) Deliverables (what “done” looks like)

Source Registry populated with the global + official + structured sources listed above

Ingestion + translation pipeline (English-first)

Dedup + clustering

RAG summaries (paperscraper style)

Impact engine producing impact_score + L0–L5

Mood index:

intraday

daily OHLC

MA5/MA10 wave + trend labels

API endpoints (Moodix-compatible + extended)

Research module: SPY event studies + correlation dashboards (API output)