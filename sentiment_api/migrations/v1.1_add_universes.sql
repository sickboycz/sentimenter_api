-- Migration v1.1: Add universes, sectors, securities, universe_memberships
-- Run after v1.0 schema. Safe to run multiple times (IF NOT EXISTS).

BEGIN;

-- asset_direction enum (for event_impacts)
DO $$ BEGIN
  CREATE TYPE asset_direction AS ENUM ('Up','Down','Neutral','Mixed','Unknown');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Extend object_type
ALTER TYPE object_type ADD VALUE IF NOT EXISTS 'security';

-- universes
CREATE TABLE IF NOT EXISTS universes (
  universe_id        text PRIMARY KEY,
  name_en            text NOT NULL,
  description_en     text,
  source             text NOT NULL,
  last_refreshed_at  timestamptz NOT NULL DEFAULT now(),
  meta               jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- sectors
CREATE TABLE IF NOT EXISTS sectors (
  sector_id          text PRIMARY KEY,
  name_en            text NOT NULL,
  taxonomy           text NOT NULL DEFAULT 'gics_like'
);

-- securities
CREATE TABLE IF NOT EXISTS securities (
  symbol             text PRIMARY KEY,
  name               text NOT NULL,
  exchange           text,
  sector_id          text REFERENCES sectors(sector_id) ON DELETE SET NULL,
  meta               jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_securities_sector ON securities (sector_id);

-- universe_memberships
CREATE TABLE IF NOT EXISTS universe_memberships (
  universe_id        text NOT NULL REFERENCES universes(universe_id) ON DELETE CASCADE,
  symbol             text NOT NULL REFERENCES securities(symbol) ON DELETE CASCADE,
  effective_from     date NOT NULL,
  effective_to       date,
  weight             double precision,
  PRIMARY KEY (universe_id, symbol, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_universe_memberships_symbol ON universe_memberships (symbol);
CREATE INDEX IF NOT EXISTS idx_universe_memberships_universe ON universe_memberships (universe_id, effective_from DESC);

COMMIT;
