-- Migration: cluster_asset_targeting_audit (AC-M5.5.5)
-- Store full scoring table for audit, not just top N.

BEGIN;

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
