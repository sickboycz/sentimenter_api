-- v1.4: LLM call cache for chunked asset targeting (channel_infer, sector_map, ticker_select)
-- Safe to re-run (IF NOT EXISTS).

BEGIN;

CREATE TABLE IF NOT EXISTS llm_call_cache (
  cache_key TEXT PRIMARY KEY,
  cluster_id TEXT NOT NULL,
  cluster_version INTEGER NOT NULL,
  step TEXT NOT NULL CHECK (step IN ('channel_infer','sector_map','ticker_select')),
  model TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  packet_hash TEXT NOT NULL,
  schema_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok','failed','pending')),
  parsed_json JSONB,
  raw_json JSONB,
  latency_ms INTEGER,
  tokens_in INTEGER,
  tokens_out INTEGER,
  error_code TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_call_cache_cluster ON llm_call_cache (cluster_id, cluster_version);
CREATE INDEX IF NOT EXISTS idx_llm_call_cache_step ON llm_call_cache (step);
CREATE INDEX IF NOT EXISTS idx_llm_call_cache_status ON llm_call_cache (status);

COMMIT;
