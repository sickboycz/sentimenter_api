-- Migration: tombstone/deleted_at for retention policy (AC-M7.3)

BEGIN;

ALTER TABLE articles ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_articles_deleted_at ON articles (deleted_at) WHERE deleted_at IS NOT NULL;

COMMIT;
