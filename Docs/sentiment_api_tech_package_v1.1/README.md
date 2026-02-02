# Sentiment_API — Technical Document Package v1.1

**Codename:** Sentimeter  
**Date:** 2026-02-01  
**Audience:** Builder (Cursor), operator, IBKR dashboard/bot integrator (API-only)

This package is a build-ready specification for a standalone system that ingests global macro + political + geopolitical news, converts everything to English-first structured intelligence, computes market mood + impact scores, backtests vs SPY/ES, and serves an API.

## Contents

- `SENTIMENT_API_MASTER_SPEC_v1.1.md` — single “source of truth” mega-doc.
- `openapi/sentiment_api.openapi.yaml` — OpenAPI 3.1 contract (API-only integration).
- `schemas/` — JSON Schemas for API payloads (draft 2020-12).
- `registry/` — Source registry templates + schema validator.
- `db/` — Postgres DDL (tables, indexes) + notes.
- `ops/` — runbook, deployment notes, systemd/docker templates.
- `prompts/` — schema-locked prompt contracts for L1–L4 summaries + impact scoring.
- `examples/` — example API responses and registry examples.

## How to use this in Cursor

1. Open `SENTIMENT_API_MASTER_SPEC_v1.1.md`.
2. Implement modules in order (M0 → M10).
3. Use the OpenAPI file to scaffold the API layer.
4. Use `/db/schema.sql` to create DB + migrations.
5. Use `/registry/source_registry.yaml` as initial ingestion set.

**No local LLM is required** in the IBKR bot: the bot only calls HTTP endpoints.


- `examples/RESEARCH_METHODS.md` — research methodology spec (event studies)

- `SENTIMENT_API_SCOPE_TECH_SPEC_v1.1_PRD.md` — PRD-style scope + requirements
