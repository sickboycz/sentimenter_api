Sentiment_API — Scope + Tech Spec v1.0 (PRD-style)

Date: 2026-02-01 (America/Chicago)
Audience: You + IBKR dashboard/bot integrator (API-only)

0) Document control

Product name: sentiment_api

Version: v1.0

Primary consumer: IBKR dashboard + trading bot (via HTTP API only)

Core idea: Global news → English normalization → clustering → RAG summaries → impact scoring → indices → API

1) Problem statement

You need a standalone, production-usable service that continuously ingests global economic, political, and geopolitical news (major + minor), converts everything into English-first structured intelligence, and outputs a competitive market-mood/impact index comparable to Moodix, plus drill-down explanations and historical SPY correlation/event studies.

Constraints:

No local LLM dependency inside IBKR bot (local Gemma removed).

Local memory + vector memory stores all internal knowledge (OpenAI used as model provider, but memory is local).

English output even for non-English sources (translate + preserve provenance).

2) Goals, non-goals, and success metrics
2.1 Goals

Global coverage, English-first

Include worldwide sources and multilingual news (via a global firehose + official sources).

Breaking-news signal extraction

Deduplicate + cluster + identify “market-moving” subsets.

Impact scoring + mood classification

Provide event-level impact (L0–L5) and aggregated indices.

Moodix compatibility mode

Offer a Moodix-field-compatible dataset and endpoint style for easy dashboard overlay. Moodix documents its API endpoint and field list.

Historical learning

Event-study and correlation vs SPY (and optionally ES) to validate predictive value.

2.2 Non-goals (v1.0)

Autonomous trade execution logic or order management.

Redistribution of paywalled full text without licensing (store metadata/snippets + derived features; full text only when permitted).

2.3 Success metrics (v1.0 targets)

Ingestion freshness: ≥ 95% of items available within 10 minutes of publication for RSS/API sources (best-effort for scraped sources).

English normalization coverage: ≥ 99% of ingested items have title_en and summary_en (or explicit failure reason).

Cluster quality: ≥ 85% of high-impact clusters (L3+) contain ≥ 2 independent sources.

API uptime: 99.5% monthly.

Index latency: index updates within < 5 minutes of qualifying cluster formation.
3) Users & key use cases
Primary user stories

Dashboard overlay

“Show my intraday mood index, yesterday vs today, and drivers.”

Bot consumption

“Give me a risk regime label + confidence for gating strategies.”

Research

“Do geopolitical L4 events correlate with SPY downside in 1d/3d windows?”

4) Scope overview
In scope

Continuous ingestion from configured global sources

Translation to English + provenance

Deduplication + clustering (story-level)

RAG summaries (paperscraper/PaperQA-style pipeline)

Impact scoring and mood classification

Intraday and daily indices

Event-study endpoints vs SPY

Source registry configuration (YAML/JSON)

Architecture inspiration

We adopt a PaperQA-style evidence workflow: embed documents, embed query, retrieve top passages, summarize relevant passages, re-score/select, then generate structured outputs.

5) System architecture (high-level)
5.1 Data flow

Collect (RSS/API/scrape/datasets + global firehose)

Normalize

parse → clean → language detect → translate → canonicalize times/entities

Dedup + cluster

Summarize & extract

evidence passages + structured event

Impact engine

direction (RiskOn/RiskOff/Neutral), magnitude (0–100), impact level (L0–L5), confidence

Index engine

intraday index + daily OHLC + wave metrics

Persist

relational “local memory” + vector store “vector memory”

Serve

API endpoints for dashboard/bot/research

5.2 Storage layers

Relational store (local memory): canonical entities, articles, clusters, scores, time series

Vector store (vector memory): embeddings for clusters/evidence/historical analogs
6) Modules & acceptance criteria (v1.0)

Format: AC-Mx.y acceptance criteria (testable).

M0 — Source Registry & Configuration

Responsibilities

Define all sources, auth methods, update intervals, parsing rules, licensing class.

Acceptance criteria

AC-M0.1: System loads a registry file (YAML or JSON) on boot; validates schema; refuses to start on invalid config.

AC-M0.2: Each source_id is unique and immutable once deployed (changes require migration).

AC-M0.3: Supports enabled=false per source without code changes.

AC-M0.4: Registry supports “packs” (e.g., official_macro_pack) and per-pack enable/disable.

M1 — Collectors (Ingestion)

Responsibilities

Poll RSS feeds, call APIs, scrape permitted pages, ingest structured datasets, query global firehose.

Acceptance criteria

AC-M1.1: For RSS/API sources, new items are fetched within 10 minutes (p95) of publication when upstream permits.

AC-M1.2: Each ingested item contains: source_id, source_type, url, published_at, fetched_at, title_raw.

AC-M1.3: Retries with backoff + circuit breaker; errors recorded per source.

AC-M1.4: Supports backfill by date range for sources that allow historical querying.

M2 — Normalization & English-first Translation

Responsibilities

Language detect, translate to English, canonicalize timestamps, normalize punctuation, standardize metadata.

Acceptance criteria

AC-M2.1: Every item yields title_en and content_en OR an explicit translation_status=failed with reason.

AC-M2.2: Store lang_original, translation_provider, and translation_confidence.

AC-M2.3: All times stored in UTC (published_at, fetched_at, translated_at) as ISO-8601.

Design note

For global multilingual coverage, leverage a translingual source that machine-translates monitored coverage and supports English search across many languages (e.g., GDELT’s “search across 65 machine translated languages using English keywords”).

M3 — Deduplication & Story Clustering

Responsibilities

Merge duplicates, group multi-source coverage into clusters.

Acceptance criteria

AC-M3.1: Exact duplicate URLs never create >1 article record.

AC-M3.2: Near-duplicates are grouped into the same cluster (embedding similarity + fingerprint).

AC-M3.3: Cluster contains a stable cluster_id, first_seen, last_seen, source_count.

AC-M3.4: Cluster supports “updates” as new articles arrive, without changing the core cluster identity.

M4 — Evidence + Summary (RAG)

Responsibilities

Produce “paperscraper-style” summaries with evidence; store passages for auditability.

Acceptance criteria

AC-M4.1: Each cluster produces summary_bullets_en[] and what_changed_en, why_it_matters_en, what_to_watch_en.

AC-M4.2: Each summary references supporting evidence (source_urls[] + evidence_passages[]).

AC-M4.3: Summaries are cached by (cluster_id, model_version, config_hash) for reproducibility.

M5 — Impact & Mood Engine

Responsibilities

Compute impact score, impact level, direction, horizon, confidence, and reason codes.

Impact level scale

L0 noise, L1 low, L2 medium, L3 high, L4 very high, L5 crisis

Acceptance criteria

AC-M5.1: Every cluster has impact_score (0–100), impact_level (L0–L5), expected_direction.

AC-M5.2: If market reaction data is available, compute realized_direction + realized_move metrics.

AC-M5.3: Provide reason_codes[] (e.g., RATE_SURPRISE, SANCTIONS_EXPANSION, WAR_ESCALATION, ENERGY_SUPPLY_SHOCK).

AC-M5.4: Confidence is always present (0–1) and decreases when evidence is weak/contradictory.

Mood mapping (core logic)

Mood is market risk appetite, not “text positivity.”

Primary internal dimensions (stored): risk_appetite, volatility_pressure, growth_outlook, inflation_pressure, rates_pressure, liquidity_stress, geopolitical_risk, energy_supply_risk.

M6 — Index Engine (intraday + daily)

Responsibilities

Aggregate cluster impacts into indices usable by your dashboard and strategy gating.

Moodix compatibility
Moodix documents fields for daily OHLC, intraday index, and “news volatility” strength, plus moving averages/wave.

Acceptance criteria

AC-M6.1: Intraday index updates within 5 minutes of a qualifying cluster update.

AC-M6.2: Daily record includes OHLC computed over the defined day boundary.

AC-M6.3: sentiment_wave = MA5 - MA10 is computed and published (compatibility mode).

AC-M6.4: News volatility metric exists and increases with higher-impact clusters.

M7 — Local Memory & Vector Memory

Responsibilities

Store everything needed to explain decisions and retrieve analogs.

Acceptance criteria

AC-M7.1: Relational store contains complete audit trail for any published cluster/index point.

AC-M7.2: Vector store supports semantic retrieval:

similar clusters

similar events (taxonomy-based)

historical analogs (cluster summaries)

AC-M7.3: Deleting a cluster removes embeddings or tombstones them (configurable retention policy).

M8 — Research Engine (SPY/ES event studies)

Responsibilities

Quantify whether cluster types/impact levels correlate with SPY returns.

Acceptance criteria

AC-M8.1: Provide event-study output for configurable windows (e.g., 30m, 2h, 1d, 3d).

AC-M8.2: Results can be filtered by topic, region, event_type, and impact_level.

AC-M8.3: Store research snapshots with research_run_id for repeatability.

M9 — API Service (integration layer)

Responsibilities

Serve indices, clusters, sources, and research results securely and reliably.

Acceptance criteria

AC-M9.1: All endpoints require API key auth (query param or header).

AC-M9.2: Consistent pagination and error shape across endpoints.

AC-M9.3: p95 API latency < 300ms for list endpoints (excluding very large ranges).

M10 — Observability & Ops

Responsibilities

Logging, metrics, health checks, alerting.

Acceptance criteria

AC-M10.1: Per-source ingestion lag and error rate metrics.

AC-M10.2: Translation failure metrics.

AC-M10.3: Cluster throughput + queue depth + processing time.

AC-M10.4: /v1/health exposes readiness and dependency status.

7) News sources (v1.0 baseline)

You get global political & geopolitical coverage by combining:

A global multilingual firehose that can be searched in English across many languages (e.g., GDELT translingual DOC API).

Official macro/policy sources (central banks, statistics agencies, governments).

Sanctions + conflict datasets (structured and high signal).

Energy/nuclear supply shock sources.

7.1 Official macro & central bank sources (examples included in v1.0)

US macro + rates: Fed RSS, BLS RSS, BEA releases, Census RSS, TreasuryDirect RSS

Europe/UK: ECB RSS, Eurostat RSS, Council of the EU RSS, Bank of England RSS

Global finance: BIS RSS

Expand globally: BIS directory of central bank/monetary authority websites

7.2 Political & geopolitical institutions

UN General Assembly RSS

UN Security Council consolidated list updates RSS

US Department of State RSS

European Parliament RSS

7.3 Sanctions sources

UK Sanctions List (and its search tool); UK moved to a single sanctions list on 2026-01-28

EU Sanctions Map

OFAC: RSS retired on 2025-01-31 → use page monitoring + email updates instead

7.4 Conflict & humanitarian (structured + news)

ACLED API

UCDP API

ReliefWeb API (note: v0 deprecated; newer API requires approved appname starting 2025-11-01)

International Crisis Group RSS (CrisisWatch + regions/countries)

7.5 Energy & nuclear (supply shock drivers)

EIA RSS feeds

IAEA RSS feeds

(Optional add-ons) commercial news APIs (licensed): NewsAPI.ai, etc.
8) API contract (v1.0)
8.1 Authentication

Required: API key

Accepted as:

query: ?api_key=...

header: X-API-Key: ... (preferred)

8.2 Conventions

Time format: ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)

Date format: YYYY-MM-DD

Pagination: limit + cursor (opaque)

Error model: consistent across /v1/* endpoints

8.3 Endpoint list (v1.0)

GET /api/sp-sentiment (Moodix-compatible raw series)

GET /v1/mood/now

GET /v1/index/intraday

GET /v1/news/clusters

GET /v1/news/clusters/{cluster_id}

GET /v1/research/spy/event-study

GET /v1/sources

GET /v1/health

9) JSON Schemas (precise) — v1.0

JSON Schema draft: 2020-12
Notes:

GET request “schemas” represent query params as an object.

Path params are documented as separate schema objects.

9.1 Shared schemas ($defs)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/defs.json",
  "title": "sentiment_api v1 shared definitions",
  "type": "object",
  "$defs": {
    "Error": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "code": { "type": "string", "minLength": 1 },
        "message": { "type": "string", "minLength": 1 },
        "details": { "type": "object", "additionalProperties": true },
        "hint": { "type": "string" }
      },
      "required": ["code", "message"]
    },
    "ResponseMeta": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "request_id": { "type": "string", "minLength": 8 },
        "as_of": { "type": "string", "format": "date-time" }
      },
      "required": ["request_id", "as_of"]
    },
    "Pagination": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "limit": { "type": "integer", "minimum": 1, "maximum": 500 },
        "next_cursor": { "type": ["string", "null"] },
        "returned": { "type": "integer", "minimum": 0 }
      },
      "required": ["limit", "next_cursor", "returned"]
    },
    "ImpactLevel": {
      "type": "string",
      "enum": ["L0", "L1", "L2", "L3", "L4", "L5"]
    },
    "Direction": {
      "type": "string",
      "enum": ["RiskOn", "RiskOff", "Neutral", "Mixed", "Unknown"]
    },
    "Tone": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "polarity": { "type": "number", "minimum": -1, "maximum": 1 },
        "subjectivity": { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "required": ["polarity", "subjectivity"]
    },
    "Impact": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "impact_score": { "type": "number", "minimum": 0, "maximum": 100 },
        "impact_level": { "$ref": "#/$defs/ImpactLevel" },
        "expected_direction": { "$ref": "#/$defs/Direction" },
        "realized_direction": { "$ref": "#/$defs/Direction" },
        "horizon": {
          "type": "string",
          "enum": ["intraday", "1d", "3d", "1w", "1m", "unknown"]
        },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "reason_codes": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "maxItems": 50
        }
      },
      "required": ["impact_score", "impact_level", "expected_direction", "horizon", "confidence", "reason_codes"]
    },
    "SourceRef": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "source_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{3,64}$" },
        "name": { "type": "string", "minLength": 1 },
        "type": { "type": "string", "enum": ["gdelt", "rss", "api", "scrape", "dataset"] },
        "credibility_tier": { "type": "string", "enum": ["official", "reputable_media", "local_media", "dataset", "user_added"] },
        "license_class": { "type": "string", "enum": ["open", "key_required", "paid", "restricted"] }
      },
      "required": ["source_id", "name", "type", "credibility_tier", "license_class"]
    },
    "ArticleRef": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "article_id": { "type": "string", "pattern": "^art_[a-zA-Z0-9]{10,64}$" },
        "source_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{3,64}$" },
        "url": { "type": "string", "format": "uri" },
        "published_at": { "type": "string", "format": "date-time" },
        "title_en": { "type": "string", "minLength": 1 },
        "lang_original": { "type": "string", "minLength": 2, "maxLength": 16 }
      },
      "required": ["article_id", "source_id", "url", "published_at", "title_en", "lang_original"]
    },
    "EvidencePassage": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "url": { "type": "string", "format": "uri" },
        "text_en": { "type": "string", "minLength": 1 },
        "relevance_score": { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "required": ["url", "text_en", "relevance_score"]
    },
    "ClusterSummary": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "cluster_id": { "type": "string", "pattern": "^clu_[a-zA-Z0-9]{10,64}$" },
        "first_seen": { "type": "string", "format": "date-time" },
        "last_seen": { "type": "string", "format": "date-time" },
        "headline_en": { "type": "string", "minLength": 1 },
        "summary_bullets_en": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1,
          "maxItems": 12
        },
        "topics": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "maxItems": 30
        },
        "regions": {
          "type": "array",
          "items": { "type": "string", "minLength": 2, "maxLength": 8 },
          "maxItems": 50
        },
        "tone": { "$ref": "#/$defs/Tone" },
        "impact": { "$ref": "#/$defs/Impact" },
        "source_count": { "type": "integer", "minimum": 1 },
        "source_urls": {
          "type": "array",
          "items": { "type": "string", "format": "uri" },
          "maxItems": 200
        }
      },
      "required": [
        "cluster_id",
        "first_seen",
        "last_seen",
        "headline_en",
        "summary_bullets_en",
        "topics",
        "regions",
        "tone",
        "impact",
        "source_count",
        "source_urls"
      ]
    },
    "ClusterDetail": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "cluster": { "$ref": "#/$defs/ClusterSummary" },
        "articles": {
          "type": "array",
          "items": { "$ref": "#/$defs/ArticleRef" },
          "minItems": 1,
          "maxItems": 500
        },
        "evidence": {
          "type": "array",
          "items": { "$ref": "#/$defs/EvidencePassage" },
          "minItems": 1,
          "maxItems": 50
        },
        "what_changed_en": { "type": "string" },
        "why_it_matters_en": { "type": "string" },
        "what_to_watch_en": { "type": "string" },
        "impact_explanation_en": { "type": "string" },
        "historical_analogs": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "cluster_id": { "type": "string", "pattern": "^clu_[a-zA-Z0-9]{10,64}$" },
              "similarity": { "type": "number", "minimum": 0, "maximum": 1 },
              "label_en": { "type": "string" },
              "date": { "type": "string", "format": "date" }
            },
            "required": ["cluster_id", "similarity", "label_en", "date"]
          },
          "maxItems": 20
        }
      },
      "required": ["cluster", "articles", "evidence"]
    },
    "MoodSnapshot": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "as_of": { "type": "string", "format": "date-time" },
        "sentiment": { "$ref": "#/$defs/Direction" },
        "trend": { "type": "string", "minLength": 1 },
        "index_intraday": { "type": "number" },
        "news_volume_intraday": { "type": "integer", "minimum": 0 },
        "news_volatility_intraday": { "type": "number", "minimum": 0 },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "drivers": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "cluster_id": { "type": "string", "pattern": "^clu_[a-zA-Z0-9]{10,64}$" },
              "headline_en": { "type": "string" },
              "impact_score": { "type": "number", "minimum": 0, "maximum": 100 },
              "direction": { "$ref": "#/$defs/Direction" },
              "contribution": { "type": "number" }
            },
            "required": ["cluster_id", "headline_en", "impact_score", "direction", "contribution"]
          },
          "maxItems": 25
        },
        "risk_vector": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "risk_appetite": { "type": "number", "minimum": -1, "maximum": 1 },
            "volatility_pressure": { "type": "number", "minimum": 0, "maximum": 1 },
            "growth_outlook": { "type": "number", "minimum": -1, "maximum": 1 },
            "inflation_pressure": { "type": "number", "minimum": -1, "maximum": 1 },
            "rates_pressure": { "type": "number", "minimum": -1, "maximum": 1 },
            "liquidity_stress": { "type": "number", "minimum": 0, "maximum": 1 },
            "geopolitical_risk": { "type": "number", "minimum": 0, "maximum": 1 },
            "energy_supply_risk": { "type": "number", "minimum": 0, "maximum": 1 }
          },
          "required": [
            "risk_appetite",
            "volatility_pressure",
            "growth_outlook",
            "inflation_pressure",
            "rates_pressure",
            "liquidity_stress",
            "geopolitical_risk",
            "energy_supply_risk"
          ]
        }
      },
      "required": [
        "as_of",
        "sentiment",
        "trend",
        "index_intraday",
        "news_volume_intraday",
        "news_volatility_intraday",
        "confidence",
        "drivers",
        "risk_vector"
      ]
    },
    "IntradayIndexPoint": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "ts": { "type": "string", "format": "date-time" },
        "index_value": { "type": "number" },
        "news_volume": { "type": "integer", "minimum": 0 },
        "news_volatility": { "type": "number", "minimum": 0 },
        "sentiment": { "$ref": "#/$defs/Direction" }
      },
      "required": ["ts", "index_value", "news_volume", "news_volatility", "sentiment"]
    },
    "EventStudyWindow": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "window": { "type": "string", "enum": ["30m", "2h", "1d", "3d", "1w"] },
        "mean_return": { "type": "number" },
        "median_return": { "type": "number" },
        "mean_abs_return": { "type": "number", "minimum": 0 },
        "hit_rate": { "type": "number", "minimum": 0, "maximum": 1 },
        "sample_size": { "type": "integer", "minimum": 1 }
      },
      "required": ["window", "mean_return", "median_return", "mean_abs_return", "hit_rate", "sample_size"]
    }
  }
}
9.2 GET /api/sp-sentiment — Moodix-compatible raw series

Moodix documents the endpoint style and field names; we mirror them for easy overlay.

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_api_sp_sentiment.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "from": { "type": "string", "format": "date" },
    "to": { "type": "string", "format": "date" }
  },
  "required": ["api_key"]
}


Response schema (raw array, no wrapper)

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_api_sp_sentiment.response.json",
  "type": "array",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "date": { "type": "string", "format": "date" },
      "update_time": { "type": "string", "format": "date-time" },

      "open": { "type": "number" },
      "high": { "type": "number" },
      "low": { "type": "number" },
      "close": { "type": "number" },

      "moodix_index": { "type": "number" },
      "ma10_moodix": { "type": "number" },
      "ma5_moodix": { "type": "number" },
      "sentiment_wave": { "type": "number" },

      "sentiment": { "type": "string" },
      "trend": { "type": "string" },

      "moodix_index_intraday": { "type": "number" },
      "news_volume_intraday": { "type": "integer", "minimum": 0 },
      "news_volatility_intraday": { "type": "number", "minimum": 0 },

      "moodix_index_week": { "type": "number" },
      "news_volume_week": { "type": "integer", "minimum": 0 },

      "moodix_index_month": { "type": "number" },
      "news_volume_month": { "type": "integer", "minimum": 0 },

      "moodix_index_year": { "type": "number" },
      "news_volume_year": { "type": "integer", "minimum": 0 }
    },
    "required": ["date", "update_time", "open", "high", "low", "close", "moodix_index"]
  }
}

9.3 GET /v1/mood/now

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_mood_now.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 }
  },
  "required": ["api_key"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_mood_now.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "data": { "$ref": "defs.json#/$defs/MoodSnapshot" },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "data", "errors"]
}

9.4 GET /v1/index/intraday

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_index_intraday.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "interval": { "type": "string", "enum": ["1m", "5m", "15m", "1h"] },
    "since": { "type": "string", "format": "date-time" },
    "until": { "type": "string", "format": "date-time" },
    "limit": { "type": "integer", "minimum": 1, "maximum": 500 },
    "cursor": { "type": "string" }
  },
  "required": ["api_key", "interval"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_index_intraday.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "pagination": { "$ref": "defs.json#/$defs/Pagination" },
    "data": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/IntradayIndexPoint" }
    },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "pagination", "data", "errors"]
}
9.5 GET /v1/news/clusters

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_news_clusters.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "since": { "type": "string", "format": "date-time" },
    "until": { "type": "string", "format": "date-time" },
    "min_impact_level": { "$ref": "defs.json#/$defs/ImpactLevel" },
    "direction": { "$ref": "defs.json#/$defs/Direction" },
    "topics": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "maxItems": 20
    },
    "regions": {
      "type": "array",
      "items": { "type": "string", "minLength": 2, "maxLength": 8 },
      "maxItems": 20
    },
    "limit": { "type": "integer", "minimum": 1, "maximum": 200 },
    "cursor": { "type": "string" },
    "include_source_urls": { "type": "boolean" }
  },
  "required": ["api_key"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_news_clusters.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "pagination": { "$ref": "defs.json#/$defs/Pagination" },
    "data": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/ClusterSummary" }
    },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "pagination", "data", "errors"]
}

9.6 GET /v1/news/clusters/{cluster_id}

Path params schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_news_cluster_by_id.path.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "cluster_id": { "type": "string", "pattern": "^clu_[a-zA-Z0-9]{10,64}$" }
  },
  "required": ["cluster_id"]
}


Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_news_cluster_by_id.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "include_articles": { "type": "boolean" },
    "include_evidence": { "type": "boolean" },
    "include_analogs": { "type": "boolean" }
  },
  "required": ["api_key"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_news_cluster_by_id.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "data": { "$ref": "defs.json#/$defs/ClusterDetail" },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "data", "errors"]
}

9.7 GET /v1/research/spy/event-study

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_research_spy_event_study.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "from": { "type": "string", "format": "date" },
    "to": { "type": "string", "format": "date" },
    "topics": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "maxItems": 20
    },
    "regions": {
      "type": "array",
      "items": { "type": "string", "minLength": 2, "maxLength": 8 },
      "maxItems": 20
    },
    "min_impact_level": { "$ref": "defs.json#/$defs/ImpactLevel" },
    "direction": { "$ref": "defs.json#/$defs/Direction" },
    "windows": {
      "type": "array",
      "items": { "type": "string", "enum": ["30m", "2h", "1d", "3d", "1w"] },
      "minItems": 1,
      "maxItems": 5
    },
    "market": { "type": "string", "enum": ["SPY", "ES"] }
  },
  "required": ["api_key", "from", "to", "windows", "market"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_research_spy_event_study.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "data": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "market": { "type": "string", "enum": ["SPY", "ES"] },
        "from": { "type": "string", "format": "date" },
        "to": { "type": "string", "format": "date" },
        "filters": { "type": "object", "additionalProperties": true },
        "sample_size": { "type": "integer", "minimum": 0 },
        "windows": {
          "type": "array",
          "items": { "$ref": "defs.json#/$defs/EventStudyWindow" }
        }
      },
      "required": ["market", "from", "to", "filters", "sample_size", "windows"]
    },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "data", "errors"]
}

9.8 GET /v1/sources

Request (query params) schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_sources.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "api_key": { "type": "string", "minLength": 16 },
    "enabled_only": { "type": "boolean" },
    "types": {
      "type": "array",
      "items": { "type": "string", "enum": ["gdelt", "rss", "api", "scrape", "dataset"] }
    }
  },
  "required": ["api_key"]
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_sources.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "meta": { "$ref": "defs.json#/$defs/ResponseMeta" },
    "data": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/SourceRef" }
    },
    "errors": {
      "type": "array",
      "items": { "$ref": "defs.json#/$defs/Error" }
    }
  },
  "required": ["meta", "data", "errors"]
}
9.9 GET /v1/health

Request schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_health.request.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}


Response schema

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sentiment-api.local/schemas/v1/get_v1_health.response.json",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "status": { "type": "string", "enum": ["ok", "degraded", "down"] },
    "as_of": { "type": "string", "format": "date-time" },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["ok", "fail"] },
          "details": { "type": "object", "additionalProperties": true }
        },
        "required": ["name", "status"]
      }
    }
  },
  "required": ["status", "as_of", "checks"]
}

10) Source Registry template (maintainable YAML + JSON)
10.1 Registry requirements

Must support: RSS, API, scrape, datasets, and global firehose

Must encode licensing + auth notes (e.g., ReliefWeb appname requirement)

Must allow per-source enable/disable without code

10.2 YAML template (recommended)

Below is a starter registry containing the v1.0 baseline sources described earlier (you can add/remove freely). The cited pages document that these feeds/APIs exist.

version: "1.0"
defaults:
  enabled: true
  translate_to_en: true
  update_interval_sec: 300
  credibility_tier: reputable_media
  license_class: open
  max_fetch_retries: 3
  request_timeout_sec: 20

packs:
  global_firehose:
    enabled: true
  official_macro:
    enabled: true
  geopolitics:
    enabled: true
  sanctions:
    enabled: true
  conflict_humanitarian:
    enabled: true
  energy_nuclear:
    enabled: true

sources:
  # --- Global firehose ---
  - source_id: gdelt_doc_v2
    name: "GDELT DOC 2.0"
    pack: global_firehose
    type: gdelt
    enabled: true
    base_url: "https://api.gdeltproject.org/api/v2/doc/doc"
    language_hint: auto
    translate_to_en: true
    update_interval_sec: 300
    credibility_tier: dataset
    license_class: open
    topics: ["macro", "geopolitics", "politics", "economy", "energy"]
    regions: ["GLOBAL"]
    notes: "Translingual: search across machine-translated languages with English keywords."

  # --- US official macro/policy ---
  - source_id: us_fed_rss
    name: "Federal Reserve Board RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.federalreserve.gov/feeds/feeds.htm"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["rates", "liquidity", "policy", "macro"]

  - source_id: us_bls_rss
    name: "Bureau of Labor Statistics RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.bls.gov/feed/"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["inflation", "employment", "macro"]

  - source_id: us_bea_releases
    name: "Bureau of Economic Analysis Releases"
    pack: official_macro
    type: scrape
    page_url: "https://www.bea.gov/news/current-releases"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["gdp", "macro"]

  - source_id: us_census_rss
    name: "US Census RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.census.gov/about/contact-us/feeds.html"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["macro", "trade", "housing"]

  - source_id: us_treasurydirect_rss
    name: "TreasuryDirect RSS"
    pack: official_macro
    type: rss
    feed_url: "https://treasurydirect.gov/rss/"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["auctions", "debt", "policy"]

  # --- Europe / UK official ---
  - source_id: ecb_rss
    name: "European Central Bank RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.ecb.europa.eu/home/html/rss.en.html"
    credibility_tier: official
    license_class: open
    regions: ["EU"]
    topics: ["rates", "policy", "macro"]

  - source_id: eurostat_rss
    name: "Eurostat RSS"
    pack: official_macro
    type: rss
    page_url: "https://ec.europa.eu/eurostat/web/rss"
    credibility_tier: official
    license_class: open
    regions: ["EU"]
    topics: ["macro", "inflation", "trade", "energy"]

  - source_id: eu_council_rss
    name: "Council of the EU RSS"
    pack: geopolitics
    type: rss
    feed_url: "https://www.consilium.europa.eu/en/about-site/rss/"
    credibility_tier: official
    license_class: open
    regions: ["EU"]
    topics: ["geopolitics", "sanctions", "policy"]

  - source_id: boe_rss
    name: "Bank of England RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.bankofengland.co.uk/rss"
    credibility_tier: official
    license_class: open
    regions: ["GB"]
    topics: ["rates", "policy", "macro"]

  - source_id: bis_rss
    name: "BIS RSS"
    pack: official_macro
    type: rss
    feed_url: "https://www.bis.org/rss/index.htm"
    credibility_tier: official
    license_class: open
    regions: ["GLOBAL"]
    topics: ["banking", "liquidity", "macro"]

  - source_id: bis_central_banks_directory
    name: "BIS Central Bank Directory"
    pack: official_macro
    type: scrape
    page_url: "https://www.bis.org/cbanks.htm"
    enabled: false
    credibility_tier: official
    license_class: open
    regions: ["GLOBAL"]
    topics: ["directory"]
    notes: "Use to generate additional country central bank sources."

  # --- UN / diplomacy ---
  - source_id: un_ga_rss
    name: "UN General Assembly RSS"
    pack: geopolitics
    type: rss
    feed_url: "https://www.un.org/en/ga/rss/index.shtml"
    credibility_tier: official
    license_class: open
    regions: ["GLOBAL"]
    topics: ["geopolitics", "diplomacy"]

  - source_id: unsc_consolidated_list_rss
    name: "UNSC Consolidated List Updates (RSS)"
    pack: sanctions
    type: rss
    feed_url: "https://main.un.org/securitycouncil/en/rss-updates-unsc-consolidated-list"
    credibility_tier: official
    license_class: open
    regions: ["GLOBAL"]
    topics: ["sanctions", "geopolitics"]

  - source_id: us_state_rss
    name: "US State Department RSS"
    pack: geopolitics
    type: rss
    feed_url: "https://www.state.gov/rss-feeds"
    credibility_tier: official
    license_class: open
    regions: ["US", "GLOBAL"]
    topics: ["geopolitics", "diplomacy"]

  # --- Sanctions ---
  - source_id: uk_sanctions_list
    name: "UK Sanctions List"
    pack: sanctions
    type: scrape
    page_url: "https://www.gov.uk/government/publications/the-uk-sanctions-list"
    credibility_tier: official
    license_class: open
    regions: ["GB"]
    topics: ["sanctions"]

  - source_id: eu_sanctions_map
    name: "EU Sanctions Map"
    pack: sanctions
    type: scrape
    page_url: "https://www.sanctionsmap.eu/"
    credibility_tier: official
    license_class: open
    regions: ["EU"]
    topics: ["sanctions"]

  - source_id: us_ofac_recent_actions
    name: "OFAC Recent Actions"
    pack: sanctions
    type: scrape
    page_url: "https://ofac.treasury.gov/recent-actions"
    credibility_tier: official
    license_class: open
    regions: ["US"]
    topics: ["sanctions"]
    notes: "OFAC RSS retired; monitor page + email updates."

  # --- Conflict & humanitarian ---
  - source_id: acled_api
    name: "ACLED API"
    pack: conflict_humanitarian
    type: api
    base_url: "https://acleddata.com/acled-api-documentation"
    auth:
      method: api_key
      key_name: "key"
      location: query
    credibility_tier: dataset
    license_class: key_required
    regions: ["GLOBAL"]
    topics: ["conflict", "political_violence"]

  - source_id: ucdp_api
    name: "UCDP API"
    pack: conflict_humanitarian
    type: api
    base_url: "https://ucdp.uu.se/apidocs/"
    credibility_tier: dataset
    license_class: open
    regions: ["GLOBAL"]
    topics: ["conflict"]

  - source_id: reliefweb_api
    name: "ReliefWeb API"
    pack: conflict_humanitarian
    type: api
    base_url: "https://apidoc.reliefweb.int/"
    auth:
      method: appname
      key_name: "appname"
      location: query
    credibility_tier: official
    license_class: key_required
    regions: ["GLOBAL"]
    topics: ["disasters", "humanitarian"]
    notes: "Check latest API version; v0 deprecated. appname approval required."

  - source_id: crisisgroup_rss
    name: "International Crisis Group RSS"
    pack: conflict_humanitarian
    type: rss
    feed_url: "https://www.crisisgroup.org/rss-0"
    credibility_tier: reputable_media
    license_class: open
    regions: ["GLOBAL"]
    topics: ["conflict", "geopolitics"]

  # --- Energy & nuclear ---
  - source_id: eia_rss
    name: "EIA RSS Feeds"
    pack: energy_nuclear
    type: rss
    feed_url: "https://www.eia.gov/tools/rssfeeds/"
    credibility_tier: official
    license_class: open
    regions: ["US", "GLOBAL"]
    topics: ["energy", "oil", "gas", "inventory"]

  - source_id: iaea_rss
    name: "IAEA RSS Feeds"
    pack: energy_nuclear
    type: rss
    feed_url: "https://www.iaea.org/feeds"
    credibility_tier: official
    license_class: open
    regions: ["GLOBAL"]
    topics: ["nuclear", "energy", "security"]

10.3 JSON template (alternative)
{
  "version": "1.0",
  "defaults": {
    "enabled": true,
    "translate_to_en": true,
    "update_interval_sec": 300,
    "credibility_tier": "reputable_media",
    "license_class": "open",
    "max_fetch_retries": 3,
    "request_timeout_sec": 20
  },
  "packs": {
    "global_firehose": { "enabled": true },
    "official_macro": { "enabled": true },
    "geopolitics": { "enabled": true },
    "sanctions": { "enabled": true },
    "conflict_humanitarian": { "enabled": true },
    "energy_nuclear": { "enabled": true }
  },
  "sources": [
    {
      "source_id": "gdelt_doc_v2",
      "name": "GDELT DOC 2.0",
      "pack": "global_firehose",
      "type": "gdelt",
      "enabled": true,
      "base_url": "https://api.gdeltproject.org/api/v2/doc/doc",
      "language_hint": "auto",
      "translate_to_en": true,
      "update_interval_sec": 300,
      "credibility_tier": "dataset",
      "license_class": "open",
      "topics": ["macro", "geopolitics", "politics", "economy", "energy"],
      "regions": ["GLOBAL"]
    }
  ]
}

11) Notes for v1.0 build sequencing (recommended)

Source Registry + Ingestion + English normalization

Dedup + clustering

RAG summaries + evidence storage

Impact engine + intraday index

Moodix-compatible export endpoint

Research/event study module

Hardening: observability, rate limiting, caching