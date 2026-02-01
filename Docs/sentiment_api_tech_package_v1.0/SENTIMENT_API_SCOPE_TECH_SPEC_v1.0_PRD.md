# Sentiment_API — Scope + Tech Spec v1.0 (PRD‑style)

**Codename:** Sentimeter  
**Target integration:** IBKR dashboard/bot via HTTP API  
**English-first:** yes (translate everything; preserve provenance)

---

## 1) Problem Statement

Markets move on **narrative + surprise + uncertainty**, not on article tone alone.
Current setups typically:
- read only a handful of “major” news sources,
- lack systematic geopolitical coverage,
- can’t explain impact with evidence,
- and overfit rules (“this news is bad”) without measuring how markets actually reacted.

We need a system that:
- ingests global macro + geopolitical news at scale,
- summarizes and stores it as auditable memory,
- outputs **market-impact intelligence** and a stable sentiment index,
- and learns over time by comparing expectations vs SPY outcomes (forward-only).

---

## 2) Goals (v1.0)

### G1 — Global coverage
- Collect major + minor news worldwide using a firehose + direct official sources.

### G2 — English-first intelligence
- Normalize all outputs to English while storing original language metadata.

### G3 — Impact scoring that is explainable
- Every score must cite sources and show reasoning codes.

### G4 — Moodix-compatible export
- Provide a Moodix-like endpoint and field names to overlay easily.

### G5 — Research feedback loop
- Run event studies vs SPY/ES and store outcomes to improve calibration without overfitting.

---

## 3) Non‑Goals (v1.0)
- Automated trade execution.
- Paywall bypass or redistribution of restricted content.
- Full causal inference; v1 provides correlation/event study, not proof of causality.

---

## 4) Personas

1. **Trader (dashboard user)**
   - needs “what’s moving the market now” and “why” with evidence.
2. **Bot (IBKR integrator)**
   - needs stable endpoints, low latency, and deterministic fields.
3. **Researcher**
   - needs historical clusters/events and event study outputs.
4. **Operator**
   - needs health checks, source controls, error dashboards.

---

## 5) User Stories

- US1: As a trader, I can see the current sentiment regime and top drivers in <1 second.
- US2: As a trader, I can click an event and see evidence quotes + sources.
- US3: As a bot, I can poll intraday index and clusters and adjust risk exposure.
- US4: As a researcher, I can filter events by topic/region/impact and compute SPY drift.
- US5: As an operator, I can disable a broken source without redeploy.

---

## 6) Functional Requirements (by module)

> The acceptance criteria in Section 10 are binding.

### M0 — Source Registry
- registry file (YAML/JSON) defines sources, packs, rate limits, compliance flags.
- hot reload supported (SIGHUP or periodic re-read).

### M1 — Collectors (RSS/API/Scrape/Firehose)
- schedule and fetch new items.
- store L0 artifacts where allowed.

### M2 — Normalization + Translation
- language detect
- translate to English
- preserve provenance: original text hash, language, provider.

### M3 — Dedup + Clustering
- exact dedupe: canonical URL + hashes
- near dedupe: embeddings + fingerprint
- cluster updates are stable.

### M4 — Summaries L1–L4
- schema-locked JSON
- evidence refs required
- caching by dedupe key.

### M5 — Impact Engine
- output impact_score/level/direction/horizon/confidence/reason_codes
- store both expected and realized (when market reaction measured).

### M6 — Index Engine
- compute intraday and daily index series
- compute MA5/MA10 and wave.

### M7 — Vector Memory (local)
- embeddings stored locally (pgvector default)
- hybrid search and similarity.

### M8 — Research Engine
- event studies vs SPY/ES
- forward evaluation ledger.

### M9 — API Service
- stable REST
- API-key auth
- pagination and error schema.

### M10 — Ops/Observability
- health endpoint
- metrics, logs
- run ledger.

---

## 7) Non‑Functional Requirements (NFR)

- NFR1: Uptime ≥ 99.5% monthly (single node)
- NFR2: p95 list endpoints < 300ms
- NFR3: idempotent ingestion (safe retries)
- NFR4: explainability: evidence links mandatory for clusters L2+
- NFR5: compliance: respect robots/ToS; no restricted redistribution

---

## 8) Data Contracts

See:
- `schemas/` (JSON Schema)
- `openapi/` (OpenAPI 3.1)

---

## 9) Source Coverage

- v1 default sources: `registry/source_registry.yaml`
- catalog and expansion strategy: `registry/source_catalog.md`

---

## 10) Acceptance Criteria (per module)

See `SENTIMENT_API_MASTER_SPEC_v1.0.md` Section 17 (AC‑M0..AC‑M10).

---

## 11) Deliverables (v1.0)

- Postgres schema + migrations based on `db/schema.sql`
- Source registry loader + validator
- Collectors + workers
- Scoring + index engines
- REST API per OpenAPI
- Ops runbook and health endpoint

