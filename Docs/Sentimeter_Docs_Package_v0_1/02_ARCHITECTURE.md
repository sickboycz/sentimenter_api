# 02_ARCHITECTURE.md
## Topology
```mermaid
flowchart LR
  RSS[RSS/Feeds] --> Q[Queue]
  WEB[Web Crawler] --> Q
  ARC[Archive Backfill] --> Q

  Q --> ING[Normalize + Dedupe]
  ING --> RAW[(L0 Object Store)]
  ING --> SUM[Summaries L1-L4]
  SUM --> DB[(Postgres)]
  SUM --> VEC[(Vector Store)]

  MK[SPY Market Data] --> DB
  DB --> EVT[Event + Impact Engine]
  EVT --> IDX[Sentiment Index Engine]

  DB --> CAL[Historical Calibration]
  CAL --> EVT
  EVT --> FWD[Forward Eval Ledger]

  API[API] --> DB
  API --> VEC
```
## Services
- api (FastAPI)
- worker (queue consumers)
- daemon (continuous loop + caps)
- postgres, redis
- object store (/data/artifacts)
- vector store (pgvector default)

## Pipelines
- Live: discover→fetch→dedupe→summarize→embed→event/impact→index
- Historical: backfill→same pipeline→align to SPY→initial calibration priors
