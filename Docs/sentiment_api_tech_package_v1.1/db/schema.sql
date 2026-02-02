-- sentiment_api v1.1 — Postgres DDL (canonical truth store)
-- Target: Postgres 15+ (recommended) + pgvector
-- Notes:
-- - Keep raw L0 artifacts in object storage (/data/artifacts) and store pointers here.
-- - Keep DB as "audit-grade": every computed output can be traced to sources.
-- - All timestamps are UTC (timestamptz).

BEGIN;

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- Enums
-- -----------------------------------------------------------------------------
DO $$ BEGIN
  CREATE TYPE source_type AS ENUM ('gdelt','rss','api','scrape','dataset');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE credibility_tier AS ENUM ('official','reputable_media','local_media','dataset','user_added');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE license_class AS ENUM ('open','key_required','paid','restricted');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE direction AS ENUM ('RiskOn','RiskOff','Neutral','Mixed','Unknown');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE asset_direction AS ENUM ('Up','Down','Neutral','Mixed','Unknown');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE impact_level AS ENUM ('L0','L1','L2','L3','L4','L5');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE summary_level AS ENUM ('L1','L2','L3','L4');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE object_type AS ENUM ('article','cluster','event','state','security');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- -----------------------------------------------------------------------------
-- API Keys (auth)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
  api_key_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name               text NOT NULL,
  key_hash           text NOT NULL UNIQUE, -- store a strong hash (argon2/bcrypt)
  enabled            boolean NOT NULL DEFAULT true,
  rate_limit_per_min integer NOT NULL DEFAULT 120,
  created_at         timestamptz NOT NULL DEFAULT now(),
  last_used_at       timestamptz,
  notes              text
);

-- -----------------------------------------------------------------------------
-- Sources (registry snapshot)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
  source_id          text PRIMARY KEY,
  name               text NOT NULL,
  pack               text NOT NULL,
  type               source_type NOT NULL,
  enabled            boolean NOT NULL DEFAULT true,
  credibility        credibility_tier NOT NULL DEFAULT 'reputable_media',
  license            license_class NOT NULL DEFAULT 'open',
  regions            text[] NOT NULL DEFAULT '{}',
  topics             text[] NOT NULL DEFAULT '{}',
  config             jsonb NOT NULL DEFAULT '{}'::jsonb,  -- full source config (feed_url/page_url/base_url, auth, etc.)
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sources_pack_enabled ON sources (pack, enabled);

-- -----------------------------------------------------------------------------
-- -----------------------------------------------------------------------------
-- Security Master (universes, sectors, securities)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS universes (
  universe_id        text PRIMARY KEY,           -- e.g. "sp500", "nasdaq_composite"
  name_en            text NOT NULL,
  description_en     text,
  source             text NOT NULL,              -- e.g. "wikipedia", "nasdaqtrader"
  last_refreshed_at  timestamptz NOT NULL DEFAULT now(),
  meta               jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS sectors (
  sector_id          text PRIMARY KEY,           -- canonical id, e.g. "health_care"
  name_en            text NOT NULL,
  taxonomy           text NOT NULL DEFAULT 'gics_like'
);

CREATE TABLE IF NOT EXISTS securities (
  symbol             text PRIMARY KEY,           -- ticker
  name               text NOT NULL,
  exchange           text,
  sector_id          text REFERENCES sectors(sector_id) ON DELETE SET NULL,
  meta               jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities (sector_id);

CREATE TABLE IF NOT EXISTS universe_memberships (
  universe_id        text NOT NULL REFERENCES universes(universe_id) ON DELETE CASCADE,
  symbol             text NOT NULL REFERENCES securities(symbol) ON DELETE CASCADE,
  effective_from     date NOT NULL,
  effective_to       date,
  weight             double precision,           -- optional index weight (if available)
  PRIMARY KEY (universe_id, symbol, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_universe_memberships_symbol ON universe_memberships (symbol);
CREATE INDEX IF NOT EXISTS idx_universe_memberships_universe ON universe_memberships (universe_id, effective_from DESC);

-- -----------------------------------------------------------------------------
-- Articles (normalized, English-first)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
  article_id            text PRIMARY KEY,  -- art_<hash>
  source_id             text NOT NULL REFERENCES sources(source_id) ON UPDATE CASCADE,
  url                   text NOT NULL,
  canonical_url         text NOT NULL,
  published_at          timestamptz,
  fetched_at            timestamptz NOT NULL,
  lang_original         text,
  title_raw             text,
  title_en              text,
  content_en            text,
  translation_status    text NOT NULL DEFAULT 'ok', -- ok|failed|skipped
  translation_provider  text,
  translation_confidence double precision,
  content_hash          text, -- sha256 of content_en for dedupe
  metadata              jsonb NOT NULL DEFAULT '{}'::jsonb, -- author, section, tags, etc.
  created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_canonical_url ON articles (canonical_url);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source_published ON articles (source_id, published_at DESC);

-- -----------------------------------------------------------------------------
-- Article bodies & artifacts (L0 pointers)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS article_bodies (
  article_id        text PRIMARY KEY REFERENCES articles(article_id) ON DELETE CASCADE,
  raw_html_path     text,
  extracted_text_path text,
  extracted_len     integer,
  extraction_quality double precision,
  http_status       integer,
  fetched_headers   jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- -----------------------------------------------------------------------------
-- Clusters (story-level)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clusters (
  cluster_id          text PRIMARY KEY, -- clu_<hash>
  first_seen          timestamptz NOT NULL,
  last_seen           timestamptz NOT NULL,
  headline_en         text NOT NULL,
  canonical_story_key text NOT NULL, -- stable key for clustering identity
  topics              text[] NOT NULL DEFAULT '{}',
  regions             text[] NOT NULL DEFAULT '{}',
  source_count        integer NOT NULL DEFAULT 1,
  source_urls         text[] NOT NULL DEFAULT '{}',
  -- cached scoring outputs (for list endpoints)
  tone                jsonb NOT NULL DEFAULT '{}'::jsonb,     -- {polarity, subjectivity}
  impact              jsonb NOT NULL DEFAULT '{}'::jsonb,     -- {impact_score, impact_level, expected_direction, ...}
  risk_vector         jsonb NOT NULL DEFAULT '{}'::jsonb,     -- internal dimensions
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clusters_last_seen ON clusters (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_impact_level ON clusters (((impact->>'impact_level')));
CREATE INDEX IF NOT EXISTS idx_clusters_topics_gin ON clusters USING GIN (topics);
CREATE INDEX IF NOT EXISTS idx_clusters_regions_gin ON clusters USING GIN (regions);

-- membership
CREATE TABLE IF NOT EXISTS cluster_members (
  cluster_id  text NOT NULL REFERENCES clusters(cluster_id) ON DELETE CASCADE,
  article_id  text NOT NULL REFERENCES articles(article_id) ON DELETE CASCADE,
  added_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (cluster_id, article_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_article ON cluster_members (article_id);

-- -----------------------------------------------------------------------------
-- Summaries (L1-L4) — schema-locked JSONB with versioning and caching keys
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS summaries (
  summary_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  object_type     object_type NOT NULL,
  object_id       text NOT NULL,
  level           summary_level NOT NULL,
  schema_id       text NOT NULL,         -- e.g. "sentiment_api.summary.cluster.L3"
  schema_version  text NOT NULL,         -- e.g. "1.0"
  model_id        text NOT NULL,         -- e.g. "openai:gpt-4.1-mini"
  prompt_version  text NOT NULL,         -- e.g. "2026-02-01.a"
  dedupe_key      text NOT NULL,         -- hash(...) for reproducibility caching
  content         jsonb NOT NULL,        -- strict JSON output
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (object_type, object_id, level, dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_summaries_object ON summaries (object_type, object_id, level, created_at DESC);

-- -----------------------------------------------------------------------------
-- Events (normalized market-relevant events; 1 cluster can map to >=1 event)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
  event_id           text PRIMARY KEY, -- evt_<hash>
  cluster_id         text REFERENCES clusters(cluster_id) ON DELETE SET NULL,
  event_type         text NOT NULL,     -- taxonomy key, e.g. "monetary_policy"
  event_subtype      text,
  event_ts           timestamptz NOT NULL, -- canonical event time
  headline_en        text NOT NULL,
  description_en     text,
  regions            text[] NOT NULL DEFAULT '{}',
  topics             text[] NOT NULL DEFAULT '{}',
  expected_direction direction NOT NULL DEFAULT 'Unknown',
  horizon            text NOT NULL DEFAULT 'unknown', -- intraday|1d|3d|1w|1m|unknown
  confidence         double precision NOT NULL DEFAULT 0.0,
  reason_codes       text[] NOT NULL DEFAULT '{}',
  impact_score       double precision NOT NULL DEFAULT 0.0,
  impact_level       impact_level NOT NULL DEFAULT 'L0',
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events (event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_impact_level ON events (impact_level);

-- -----------------------------------------------------------------------------
-- Event impacts (per-asset impacts; SPY baseline + sector ETFs + tickers)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_impacts (
  event_id          text NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  instrument        text NOT NULL, -- e.g. "SPY", "ES", "XLF", "AAPL"
  instrument_type   text NOT NULL DEFAULT 'ticker', -- ticker|etf|future|fx|rate
  direction         asset_direction NOT NULL DEFAULT 'Unknown',
  impact_score      double precision NOT NULL DEFAULT 0.0,
  weight            double precision NOT NULL DEFAULT 1.0,
  horizon           text NOT NULL DEFAULT 'unknown',
  confidence        double precision NOT NULL DEFAULT 0.0,
  details           jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (event_id, instrument)
);

CREATE INDEX IF NOT EXISTS idx_event_impacts_instrument ON event_impacts (instrument);

-- -----------------------------------------------------------------------------
-- Sentiment time series (intraday + daily rollups)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sentiment_timeseries (
  ts               timestamptz NOT NULL,
  interval         text NOT NULL, -- 1m|5m|15m|1h|1d
  index_value      double precision NOT NULL,
  news_volume      integer NOT NULL DEFAULT 0,
  news_volatility  double precision NOT NULL DEFAULT 0.0,
  sentiment        direction NOT NULL,
  confidence       double precision NOT NULL DEFAULT 0.0,
  drivers          jsonb NOT NULL DEFAULT '[]'::jsonb, -- list of cluster_id + contribution
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ts, interval)
);

CREATE INDEX IF NOT EXISTS idx_sentiment_interval_ts ON sentiment_timeseries (interval, ts DESC);

-- Daily OHLC computed at end of day boundary
CREATE TABLE IF NOT EXISTS sentiment_daily (
  date             date PRIMARY KEY,
  update_time      timestamptz NOT NULL,
  open             double precision NOT NULL,
  high             double precision NOT NULL,
  low              double precision NOT NULL,
  close            double precision NOT NULL,
  moodix_index     double precision NOT NULL,
  ma5_moodix       double precision,
  ma10_moodix      double precision,
  sentiment_wave   double precision,
  sentiment        text,
  trend            text,
  moodix_index_intraday double precision,
  news_volume_intraday integer NOT NULL DEFAULT 0,
  news_volatility_intraday double precision NOT NULL DEFAULT 0.0,
  moodix_index_week double precision,
  news_volume_week integer,
  moodix_index_month double precision,
  news_volume_month integer,
  moodix_index_year double precision,
  news_volume_year integer
);

-- -----------------------------------------------------------------------------
-- Market data (SPY/ES bars)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market_bars (
  symbol           text NOT NULL, -- SPY, ES, etc.
  tf               text NOT NULL, -- 5m|1h|1d
  ts               timestamptz NOT NULL,
  open             double precision NOT NULL,
  high             double precision NOT NULL,
  low              double precision NOT NULL,
  close            double precision NOT NULL,
  volume           double precision,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (symbol, tf, ts)
);

CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_tf_ts ON market_bars (symbol, tf, ts DESC);

-- -----------------------------------------------------------------------------
-- Forward evaluation ledger (expectations → outcomes)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expectations (
  expectation_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         text NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  created_at       timestamptz NOT NULL DEFAULT now(),
  market           text NOT NULL DEFAULT 'SPY',
  expected_direction direction NOT NULL DEFAULT 'Unknown',
  expected_magnitude double precision, -- 0..1 or % (define in model metadata)
  windows          text[] NOT NULL DEFAULT '{30m,2h,1d,3d,1w}',
  details          jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_expectations_event ON expectations (event_id);

CREATE TABLE IF NOT EXISTS outcomes (
  expectation_id   uuid NOT NULL REFERENCES expectations(expectation_id) ON DELETE CASCADE,
  window           text NOT NULL, -- 30m|2h|1d|3d|1w
  realized_return  double precision,
  realized_abs_return double precision,
  realized_direction direction NOT NULL DEFAULT 'Unknown',
  measured_at      timestamptz NOT NULL DEFAULT now(),
  details          jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (expectation_id, window)
);

-- -----------------------------------------------------------------------------
-- Embeddings (vector memory; pgvector)
-- -----------------------------------------------------------------------------
-- NOTE: dimension fixed to 3072 (text-embedding-3-large). If you change embedding model,
-- you must migrate dims + re-embed.
CREATE TABLE IF NOT EXISTS embeddings (
  object_type      object_type NOT NULL,
  object_id        text NOT NULL,
  model            text NOT NULL,
  dims             integer NOT NULL DEFAULT 3072,
  embedding        vector(3072) NOT NULL,
  metadata         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (object_type, object_id, model)
);

-- Vector index (IVFFLAT) — adjust lists for your scale
CREATE INDEX IF NOT EXISTS idx_embeddings_ivfflat
  ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_object
  ON embeddings (object_type, object_id);

-- -----------------------------------------------------------------------------
-- Runs (audit + errors)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
  run_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type         text NOT NULL, -- ingest|backfill|summarize|embed|score|index|research
  source_id        text,
  started_at       timestamptz NOT NULL DEFAULT now(),
  ended_at         timestamptz,
  status           text NOT NULL DEFAULT 'running', -- running|ok|fail|degraded
  stats            jsonb NOT NULL DEFAULT '{}'::jsonb,
  error            jsonb
);

CREATE INDEX IF NOT EXISTS idx_runs_type_time ON runs (run_type, started_at DESC);

-- -----------------------------------------------------------------------------
-- Cluster asset targeting audit (AC-M5.5.5 — full scoring table stored)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cluster_asset_targeting_audit (
  audit_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cluster_id     text NOT NULL,
  as_of          timestamptz NOT NULL,
  scope          jsonb NOT NULL DEFAULT '{}'::jsonb,
  bundle         jsonb NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cluster_asset_targeting_audit_cluster ON cluster_asset_targeting_audit (cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_asset_targeting_audit_as_of ON cluster_asset_targeting_audit (as_of DESC);

COMMIT;
