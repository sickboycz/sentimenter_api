-- Migration v1.2: Switch embeddings to 768 dim (Tier B: text-embedding-3-small:768).
-- Run after v1.1 migrations. Drops and recreates embeddings table (existing vectors are lost).
-- For fresh installs, 00_base_schema already uses vector(768); this migration is for DBs created with vector(3072).

BEGIN;

DROP TABLE IF EXISTS embeddings;

CREATE TABLE IF NOT EXISTS embeddings (
  object_type      object_type NOT NULL,
  object_id        text NOT NULL,
  model            text NOT NULL,
  dims             integer NOT NULL DEFAULT 768,
  embedding        vector(768) NOT NULL,
  metadata         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (object_type, object_id, model)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_object ON embeddings (object_type, object_id);

COMMIT;
