-- Migration v1.1: Add industries table (GICS industries under sectors)
-- Run after v1.1_add_universes. Safe to run multiple times (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS industries (
  industry_id        text PRIMARY KEY,
  name_en            text NOT NULL,
  sector_id          text REFERENCES sectors(sector_id) ON DELETE SET NULL,
  meta               jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_industries_sector ON industries (sector_id);
