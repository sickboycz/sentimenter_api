-- v1.4: Asset prediction ledger for forward evaluation
-- Safe to re-run (IF NOT EXISTS).

BEGIN;

CREATE TABLE IF NOT EXISTS asset_prediction_ledger (
  ledger_id BIGSERIAL PRIMARY KEY,
  cluster_id TEXT NOT NULL,
  cluster_version INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  universe TEXT NOT NULL,
  predicted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  horizon TEXT NOT NULL,
  predicted_signed_score DOUBLE PRECISION NOT NULL,
  predicted_return_bps DOUBLE PRECISION,
  predicted_confidence DOUBLE PRECISION,
  realized_at TIMESTAMPTZ,
  realized_return_bps DOUBLE PRECISION,
  realized_abs_return_bps DOUBLE PRECISION,
  notes JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_asset_pred_cluster ON asset_prediction_ledger (cluster_id, cluster_version);
CREATE INDEX IF NOT EXISTS idx_asset_pred_symbol ON asset_prediction_ledger (symbol);

COMMIT;
