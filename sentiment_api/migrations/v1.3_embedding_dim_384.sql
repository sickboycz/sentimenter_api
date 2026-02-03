-- Migration v1.3: Switch embeddings to 384 dim (Tier A: text-embedding-3-small:384).
-- Drops and recreates embeddings table (existing vectors are lost).

BEGIN;

DROP TABLE IF EXISTS embeddings;

CREATE TABLE IF NOT EXISTS embeddings (
  object_type      object_type NOT NULL,
  object_id        text NOT NULL,
  model            text NOT NULL,
  dims             integer NOT NULL DEFAULT 384,
  embedding        vector(384) NOT NULL,
  metadata         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (object_type, object_id, model)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_object ON embeddings (object_type, object_id);

COMMIT;
