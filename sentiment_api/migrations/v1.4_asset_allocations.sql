-- v1.4: Cluster market/sector/ticker allocations (chunked LLM asset targeting)
-- Safe to re-run (IF NOT EXISTS).

BEGIN;

CREATE TABLE IF NOT EXISTS cluster_market_allocations (
  cluster_id TEXT NOT NULL,
  cluster_version INTEGER NOT NULL,
  market_id TEXT NOT NULL,
  label_en TEXT NOT NULL,
  signed_score DOUBLE PRECISION NOT NULL CHECK (signed_score >= -100 AND signed_score <= 100),
  magnitude DOUBLE PRECISION NOT NULL CHECK (magnitude >= 0 AND magnitude <= 1),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  horizon TEXT NOT NULL,
  channels JSONB NOT NULL DEFAULT '[]'::jsonb,
  rationale_en TEXT NOT NULL,
  evidence_ids INTEGER[] NOT NULL DEFAULT '{}',
  model_version TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cluster_id, cluster_version, market_id, model_version, config_hash)
);

CREATE TABLE IF NOT EXISTS cluster_sector_allocations (
  cluster_id TEXT NOT NULL,
  cluster_version INTEGER NOT NULL,
  sector_id TEXT NOT NULL,
  sector_name_en TEXT NOT NULL,
  signed_score DOUBLE PRECISION NOT NULL CHECK (signed_score >= -100 AND signed_score <= 100),
  impact_score DOUBLE PRECISION NOT NULL CHECK (impact_score >= 0 AND impact_score <= 100),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  horizon TEXT NOT NULL,
  channels JSONB NOT NULL DEFAULT '[]'::jsonb,
  rationale_en TEXT NOT NULL,
  evidence_ids INTEGER[] NOT NULL DEFAULT '{}',
  model_version TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cluster_id, cluster_version, sector_id, model_version, config_hash)
);

CREATE TABLE IF NOT EXISTS cluster_ticker_allocations (
  cluster_id TEXT NOT NULL,
  cluster_version INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  universe TEXT NOT NULL,
  signed_score DOUBLE PRECISION NOT NULL CHECK (signed_score >= -100 AND signed_score <= 100),
  expected_return_bps DOUBLE PRECISION NOT NULL CHECK (expected_return_bps >= -5000 AND expected_return_bps <= 5000),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  horizon TEXT NOT NULL,
  drivers JSONB NOT NULL DEFAULT '[]'::jsonb,
  rationale_en TEXT NOT NULL,
  evidence_ids INTEGER[] NOT NULL DEFAULT '{}',
  model_version TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cluster_id, cluster_version, symbol, model_version, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_cluster_ticker_allocations_symbol ON cluster_ticker_allocations (symbol);
CREATE INDEX IF NOT EXISTS idx_cluster_ticker_allocations_cluster ON cluster_ticker_allocations (cluster_id, cluster_version);

COMMIT;
