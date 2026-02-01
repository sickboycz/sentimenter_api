1) Target outcome

You end up with a standalone service — sentiment_api — that:

Ingests major + minor macro + geopolitical news continuously.

Deduplicates & clusters “same story” across sources.

Summarizes each story cluster “paperscraper style” (tight, cited, structured).

Scores each cluster on:

sentiment (tone),

market stance (RiskOn/RiskOff),

impact level (how much it should move markets),

impacted assets (SPY first, later expand),

horizon (intraday vs multi‑day).

Builds indices similar to Moodix fields (daily + intraday + wave + volatility).

Learns from history: event studies + correlation + regime‑aware modeling vs SPY.

Exposes everything via an API your IBKR dashboard/bot can poll.

Moodix-like “wave + volatility” is a good shape to copy because it’s dashboard‑friendly and compresses a lot of info into time series. Moodix explicitly exposes fields like sentiment_wave, news_volume_intraday, and news_volatility_intraday.

2) The big architectural decision: replace local Gemma with PaperQA-style RAG

Your replacement is a retrieval + summarization + scoring pipeline, not “chat with an LLM”.

PaperQA’s core loop is basically:

embed docs,

embed query,

retrieve top passages,

summarize each passage relevant to query,

score/select summaries,

answer using selected summaries.

We reuse this logic, but swap “papers” → news articles + clusters + historical market episodes.

Result: your IBKR side stays deterministic + light; all LLM work is centralized in sentiment_api.

You’ll use OpenAI for:

embeddings (vector memory),

structured extraction,

summarization and final “impact reasoning”.

3) System blueprint (services + data flow)
3.1 Services (logical components)
A) Ingestion Layer (collectors)

RSS collectors (fast, legal-ish, stable)

API collectors (if you have licensed feeds)

Web scrapers (only where allowed)

Aggregator collectors (e.g., GDELT)

Recommendation: use GDELT Project as a baseline firehose for global coverage. It’s explicitly positioned as open data, global news monitoring, and provides historical archives (and updates frequently).
Then layer in your “must-have” premium sources later.

B) Normalization Layer

Clean HTML → text

Extract metadata: time, source, author, language, tickers/entities, locations

Standardize timestamps to UTC

C) Dedup + Story Clustering

Hashing + fuzzy matching + embedding similarity

Cluster into StoryCluster objects:

“Fed holds rates” across 30 sources becomes one cluster.

D) Summarization + Extraction (PaperQA-style)

For each StoryCluster:

choose canonical text(s) (best source, earliest timestamp, highest credibility)

extract structured facts (numbers, entities, actions, who/what/when)

produce “paperscraper-style summary”:

3–6 bullets of facts

“what changed”

“why it matters”

“what to watch next”

citations (source URLs)

E) Vector Memory & Local Memory

Vector store: embeddings for articles, clusters, events, historical episodes

Local memory (relational): structured objects + time series

F) Scoring Engines

Sentiment engine (tone)

Market stance engine (RiskOn/RiskOff)

Impact engine (the hard part)

Aggregation → index builder

G) Analytics / Research Layer

SPY event studies

correlation / lead-lag analysis

model training + calibration

“impact priors” per topic

H) API Layer

Everything IBKR needs is served via REST/JSON.

4) Data sources: “major and minor” macro + geopolitics

You want breadth and redundancy. My opinion: don’t rely on a single vendor; combine:

Tier 1: Open/global aggregation

GDELT for global, multilingual reach and historical depth.

Tier 2: Official institutions (high signal, low noise)

Central banks, finance ministries, statistical agencies

Sanctions lists / official releases (where relevant)

Tier 3: Market-moving media (often licensed)

News wires & major financial press (licensing matters; scraping often violates ToS)

Tier 4: “minor but useful” sources

Regional outlets, sector press, niche macro blogs (lower credibility weighting)

Key design point: you don’t treat every source equally. You assign:

credibility score,

timeliness score,

historical “market reaction alignment” score (learned).

5) Memory design: local memory + vector memory
5.1 Local memory (structured DB)

This is your “truth store” for:

Article

StoryCluster

Event (normalized market-relevant event)

Scores (sentiment/impact outputs)

Index ticks (intraday/daily)

Backtest results

5.2 Vector memory (embeddings)

This is your “semantic recall”:

Similar story retrieval (“have we seen this pattern before?”)

Historical analogs (“what happened last time a tanker attack happened?”)

Regime recall (“when inflation surprise was +X, SPY did what?”)

Retrieval patterns you’ll want

By topic: “oil supply shock”

By entity: “China–Taiwan”

By mechanism: “rate cut → duration rally”

By similarity: nearest-neighbor analogs

6) “Competitive sentiment measurement” vs Moodix

Moodix exposes a compact daily series with:

OHLC of its index,

moodix_index,

MA5/MA10,

sentiment_wave (difference between MA5 and MA10),

qualitative labels like RiskOn/RiskOff,

intraday news volume + volatility.

Moodix also provides an S&P sentiment API endpoint shape like:
.../api/sp-sentiment/?api_key=...

You should intentionally copy this shape

Not the internals — the output contract.

Because it makes integration dead simple:

your dashboard shows Moodix and your index side-by-side,

you compute divergence signals (“Moodix RiskOff but our model says neutral”).

7) Impact scoring: how to “think about impact” systematically

This is the core differentiator. Sentiment alone is shallow. Impact means:

7.1 Separate “tone” from “impact”

A headline can be emotionally negative but market-irrelevant (noise),
or emotionally neutral but market-critical (FOMC statement).

So create two orthogonal outputs:

Tone score (−1..+1)

Impact magnitude (0..100)

Impact direction (RiskOn/RiskOff, plus asset-specific direction)

7.2 Impact factors (the model’s feature set)

I’d score each story cluster using these factors (each 0–1), then combine:

Surprise

Is it new vs already priced-in narrative?

Compare to recent narrative memory.

Market linkage

Does it touch rates, inflation, growth, energy supply, war escalation, credit stress?

Credibility / authority

Official statement > rumor > anonymous tweet.

Breadth

Single stock vs sector vs whole market.

Urgency / immediacy

“Starting now” vs “proposal next year”.

Second-order effects

sanctions → supply chain → inflation → rates

Regime sensitivity

In high‑vol regimes, same news moves more.

Persistence

One-off vs persistent trend.

7.3 Impact levels (human-friendly)

I’d publish both numeric (0–100) and discrete levels:

L0 noise

L1 low (headline risk)

L2 medium (sector / intraday)

L3 high (index mover)

L4 very high (macro regime / multi-day)

L5 crisis (liquidity / policy shock)

This gives your dashboard easy color-coding.

8) Index construction: your “News Impact Index” (Moodix-like)

You’ll produce these time series:

Intraday (e.g., 1-min or 5-min)

index_intraday (your net market mood)

news_volume_intraday

news_volatility_intraday (strength of impact of breaking news — Moodix has this exact concept)

risk_state (RiskOn/RiskOff/Neutral)

confidence

Daily OHLC (dashboard-friendly)

open/high/low/close of index

MA5, MA10

sentiment_wave = MA5 - MA10 (normalized to roughly −1..+1)

daily news volume

Here’s a compact field set that mirrors Moodix without long prose:

Field	Meaning
index	daily value
ma5	5d avg
ma10	10d avg
wave	ma5−ma10
risk	RiskOn/RiskOff/Neutral
trend	Growing/Fading/Sideways
vol_intra	impact strength
vol_news	news count

(That’s intentionally similar to Moodix’s published schema.)

9) API design: inspired by Moodix + Mood Metrics

You said: “Use Moodix documentation as inspiration for how we operate and which endpoint we need.”

So: two API styles.

9.1 Moodix-style “simple GET time series”

Moodix exposes S&P sentiment via a single endpoint with API key.
You should do the same for your index:

GET /v1/sp-sentiment

params: from, to, interval (daily/intraday)

returns: array of records with fields above

9.2 Mood Metrics-style async analysis jobs

Mood Metrics uses a job-based pattern for sentiment analysis and mentions long-term tracking via feed IDs.
This is perfect for your “submit article text/url → get structured result” flows.

Suggested endpoints:

Endpoint	Purpose
POST /v1/analyses	submit text/url
GET /v1/jobs/{id}	job status
GET /v1/analyses/{id}	final result
GET /v1/news	filtered clusters
GET /v1/events/{id}	event object
GET /v1/index/intraday	latest ticks
GET /v1/research/spy	correlations
Core payload outputs (what IBKR dashboard wants)

For each StoryCluster:

cluster_id

timestamp_first_seen

summary_bullets[]

topics[]

tone_score

risk_score (RiskOn/RiskOff continuum)

impact_score (0–100)

impact_level (L0–L5)

horizon (intraday, 1–3d, 1–4w)

assets (SPY weight first)

confidence

sources[] (urls)

10) Historical learning vs SPY: “does this stuff correlate?”

You want to “dig deep into history and compare with historical data of SPY”.

10.1 Data alignment

You must align:

event timestamps (news time)

market timestamps (SPY price bars)

You can source SPY bars from Interactive Brokers historical data endpoints (TWS API or Client Portal Gateway). IBKR explicitly supports retrieving historical market data through its APIs.

10.2 Methods that actually answer “impact or not?”
A) Event study (best first step)

For each event/cluster:

compute SPY return in windows:

0–30m, 0–2h, close-to-close, 1–3 days

compare to baseline volatility

compute “abnormal” move (vs rolling mean/vol)

Then aggregate by:

topic,

impact_level,

surprise bucket.

B) Correlation & lead/lag

Compute:

correlation between daily index and SPY returns

cross-correlation at lags (does sentiment lead returns?)

but: beware endogeneity (market moves cause news).

C) Predictive modeling (calibration, not prophecy)

Train a model on historical features to predict:

probability of positive SPY return next horizon

expected move magnitude

expected volatility expansion

Use:

out-of-sample splits by time,

calibration checks (Brier score / reliability).

D) “Market memory” priors

Store per-topic distributions like:

“CPI upside surprise historically → median SPY reaction = X”
Then your impact engine stops being purely “LLM vibes” and becomes learned & calibrated.

11) How this plugs into your IBKR dashboard/bot (API-only)

IBKR side does not run any LLM.

Your bot/dashboard polls:

GET /v1/index/intraday (current risk state + volatility)

GET /v1/news?impact>=L3&since=... (only actionable news)

GET /v1/events/{id} (drilldown)

optionally GET /v1/research/spy?topic=... (historical analog view)

Your existing TA/Market Cognition logic can then:

use impact_level as a filter (ignore L0–L1 noise),

use risk_state as a regime switch (trend-follow vs mean-revert),

use news_volatility as a position sizing dampener.

12) Practical roadmap (so it actually ships)
Phase 1 — MVP (2–4 weeks of real work)

ingest news (start with GDELT + RSS)

dedup + clustering

PaperQA-style summary per cluster

vector store + local DB schema

impact_level heuristic (rules + LLM extraction)

/v1/sp-sentiment + /v1/news endpoints

Phase 2 — “Competitive” (next step)

regime-aware impact scoring

topic taxonomy refinement

Moodix side-by-side overlay

daily index OHLC + wave

Phase 3 — Historical learning loop

automated event study builder

per-topic impact priors

“this looks like 2018 trade-war escalation” analog retrieval

13) Baselines & sanity checks (optional but smart)

If you want to benchmark:

Finnhub exposes “news sentiment” style outputs (bullish/bearish percents, news score) for companies.
You don’t need it for production, but it’s useful as a reference for what “commercial sentiment APIs” look like.