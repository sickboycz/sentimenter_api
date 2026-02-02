# Sentiment_API — Scope + Tech Spec v1.2 (PRD-style, delta on v1.1)

**Version:** v1.2  
**Date:** 2026-02-02 (America/Chicago)  
**Primary consumer:** IBKR dashboard/bot (API-only)  
**Core objective:** Global news → English normalization → clustering → evidence-first RAG summaries → impact scoring → indices → **asset targeting (markets/sectors/tickers)** → API.

This v1.2 document is a **harmonization + modernization + completeness** layer over:
- v1.0 PRD + schemas
- v1.1 master spec (adds impacts/universes targeting)
- Design principles (evidence-first, multi-resolution memory, no overfit)

v1.2 adds:
- **Topic indices** (Moodix-inspired “follow key topics”)
- **Streaming** updates via SSE (optional)
- **Full observability** stack + health endpoints for all containers
- **Frontend dashboard spec** (glassy shell + graphs + drill-down)
- **Test suite package** (contracts + invariants + rate limiting + security)

---

## Pydantic schemas

> Canonical schemas live in `backend/app/schemas/`.  
> v1.2 adds: topic indices + SSE stream envelopes + stricter invariants around impacts.

### `backend/app/schemas/common.py`
```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ImpactLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

class Direction(str, Enum):
    RiskOn = "RiskOn"
    RiskOff = "RiskOff"
    Neutral = "Neutral"
    Mixed = "Mixed"
    Unknown = "Unknown"

class Horizon(str, Enum):
    intraday = "intraday"
    d1 = "1d"
    d3 = "3d"
    w1 = "1w"
    m1 = "1m"
    unknown = "unknown"

class CredibilityTier(str, Enum):
    official = "official"
    reputable_media = "reputable_media"
    local_media = "local_media"
    dataset = "dataset"
    user_added = "user_added"

class ErrorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    details: Dict[str, Any] = Field(default_factory=dict)
    hint: Optional[str] = None
    retryable: bool = False

class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., min_length=8)
    as_of: datetime
    trace_id: Optional[str] = None
    model_versions: Dict[str, str] = Field(default_factory=dict)

class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(..., ge=1, le=500)
    next_cursor: Optional[str] = None
    returned: int = Field(..., ge=0)
```

### `backend/app/schemas/api_envelopes.py`
```python
from __future__ import annotations
from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict, Field
from .common import ErrorModel, Pagination, ResponseMeta

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    meta: ResponseMeta
    data: T
    errors: List[ErrorModel] = Field(default_factory=list)

class ApiListResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    meta: ResponseMeta
    pagination: Pagination
    data: List[T]
    errors: List[ErrorModel] = Field(default_factory=list)
```

### `backend/app/schemas/impacts.py`
```python
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from .common import Direction, Horizon

class MarketImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market_id: str = Field(..., min_length=2, max_length=64)
    label_en: str = Field(..., min_length=2, max_length=64)
    expected_direction: Direction
    magnitude: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=2000)

class SectorImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sector_id: str = Field(..., min_length=2, max_length=32)          # GICS or ETF proxy id
    sector_name_en: str = Field(..., min_length=2, max_length=64)
    expected_direction: Direction
    impact_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=2000)

class TickerImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(..., min_length=1, max_length=16)
    company_name_en: Optional[str] = Field(default=None, max_length=128)
    universe: str = Field(..., min_length=1, max_length=32)           # sp500|nasdaq_composite|both
    sector_id: Optional[str] = Field(default=None, max_length=32)
    expected_direction: Direction
    expected_return_bps: float = Field(..., ge=-5000.0, le=5000.0)
    expected_volatility_delta: float = Field(..., ge=-5.0, le=5.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    drivers: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=3000)

class AssetImpacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    markets: List[MarketImpact] = Field(default_factory=list, max_length=30)
    sectors: List[SectorImpact] = Field(default_factory=list, max_length=50)
    winners: List[TickerImpact] = Field(default_factory=list, max_length=200)
    losers: List[TickerImpact] = Field(default_factory=list, max_length=200)
    methodology_version: str = Field(..., min_length=1, max_length=32)
```

### `backend/app/schemas/topics.py`
```python
from __future__ import annotations
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from .common import Direction

class TopicIndexPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ts: datetime
    topic_id: str = Field(..., min_length=2, max_length=32)
    topic_name_en: str = Field(..., min_length=2, max_length=64)
    index_value: float
    sentiment: Direction
    news_volume: int = Field(..., ge=0)

class TopicIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    points: List[TopicIndexPoint] = Field(default_factory=list, max_length=5000)
```

### `backend/app/schemas/stream.py`
```python
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["heartbeat","cluster_updated","mood_updated","impacts_updated","topics_updated"]
    ts: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
```

**Acceptance criteria**
- AC-S1: All impacts’ tickers MUST exist in `ticker_universe` and be `is_active=true`.
- AC-S2: Every impact object MUST include `rationale_en` and at least one `channels[]` or `drivers[]` item.
- AC-S3: Envelope `meta.request_id` always present.
- AC-S4: SSE payloads are schema-locked and never emit raw internal exceptions.

---

## DB schema / migrations

> v1.2 persists: ticker universe + cluster→asset allocations + topic indices + calibration ledger.

### `backend/db/schema/v1_2_tables.sql`
```sql
-- PostgreSQL schema (v1.2)

create table if not exists ticker_universe (
  symbol                text primary key,
  company_name_en       text not null,
  universe              text not null check (universe in ('sp500','nasdaq_composite','both')),
  sector_id             text,
  sector_name_en        text,
  industry_name_en      text,
  is_active             boolean not null default true,
  updated_at            timestamptz not null default now()
);

create table if not exists market_bucket (
  market_id     text primary key,
  label_en      text not null,
  sort_order    int not null default 0,
  is_active     boolean not null default true
);

create table if not exists cluster_market_impact (
  cluster_id           text not null,
  market_id            text not null references market_bucket(market_id),
  expected_direction   text not null,
  magnitude            double precision not null check (magnitude >= 0 and magnitude <= 1),
  confidence           double precision not null check (confidence >= 0 and confidence <= 1),
  horizon              text not null,
  channels             jsonb not null default '[]'::jsonb,
  rationale_en         text not null,
  created_at           timestamptz not null default now(),
  primary key (cluster_id, market_id)
);

create table if not exists cluster_sector_impact (
  cluster_id           text not null,
  sector_id            text not null,
  sector_name_en       text not null,
  expected_direction   text not null,
  impact_score         double precision not null check (impact_score >= 0 and impact_score <= 100),
  confidence           double precision not null check (confidence >= 0 and confidence <= 1),
  horizon              text not null,
  channels             jsonb not null default '[]'::jsonb,
  rationale_en         text not null,
  created_at           timestamptz not null default now(),
  primary key (cluster_id, sector_id)
);

create table if not exists cluster_ticker_impact (
  cluster_id               text not null,
  symbol                   text not null references ticker_universe(symbol),
  expected_direction       text not null,
  expected_return_bps      double precision not null check (expected_return_bps >= -5000 and expected_return_bps <= 5000),
  expected_vol_delta       double precision not null check (expected_vol_delta >= -5 and expected_vol_delta <= 5),
  confidence               double precision not null check (confidence >= 0 and confidence <= 1),
  horizon                  text not null,
  drivers                  jsonb not null default '[]'::jsonb,
  rationale_en             text not null,
  realized_return_bps      double precision,
  realized_window          text,
  realized_measured_at     timestamptz,
  created_at               timestamptz not null default now(),
  primary key (cluster_id, symbol)
);

create table if not exists topic_index_intraday (
  ts            timestamptz not null,
  topic_id      text not null,
  topic_name_en text not null,
  index_value   double precision not null,
  sentiment     text not null,
  news_volume   int not null default 0,
  primary key (ts, topic_id)
);

create table if not exists calibration_ledger (
  ledger_id            bigserial primary key,
  cluster_id           text not null,
  symbol               text,
  event_type           text not null,
  horizon              text not null,
  predicted_return_bps double precision,
  predicted_confidence double precision,
  realized_return_bps  double precision,
  realized_window      text,
  regime_label         text,
  created_at           timestamptz not null default now()
);
```

### `backend/db/migrations/2026_02_02_0002_add_impacts_and_topics.sql`
```sql
\ir ../schema/v1_2_tables.sql
```

**Acceptance criteria**
- AC-DB1: FK integrity enforces “no unknown tickers”.
- AC-DB2: Unique keys prevent duplicates (idempotent writes).
- AC-DB3: Intraday topic table can be partitioned later by time if needed.

---

## Validation rules

### Invariants
- cluster_id stability: once assigned, never changes for the same story.
- `expected_return_bps` bounded and shrinkage is applied.
- `confidence` ∈ [0..1] always.
- Contradictory evidence reduces confidence + direction becomes Mixed.

### `backend/app/validation/invariants.md`
```markdown
# invariants (v1.2)

## Tickers
- Every output ticker must exist in ticker_universe and be active.
- winners sorted desc by expected_return_bps; losers sorted asc.
- expected_return_bps within [-5000, 5000].
- rationale_en length >= 10.

## Clusters
- first_seen <= last_seen.
- impact_score 0..100.
- L3+ must have >=2 sources unless credibility includes official.
```

### Rate limiting
- Default: 60 req/min per api_key (list endpoints).
- Heavy endpoints: 10 req/min.
- SSE: max 10 concurrent streams per api_key.

**Acceptance criteria**
- AC-V1: Invalid params → 400 with standard error envelope.
- AC-V2: Rate limit exceeded → 429 + Retry-After.

---

## Error model

### `backend/app/errors/error_codes.md`
```markdown
# error codes (v1.2)

auth_missing_api_key
auth_invalid_api_key
auth_key_revoked

rate_limited

invalid_query_param
invalid_cursor
schema_violation
invariant_violation

ingest_upstream_timeout
ingest_robots_blocked
ingest_parse_failed
translate_failed
cluster_failed
rag_failed
impact_failed
allocation_failed
calibration_failed

not_found
conflict
too_large_range
dependency_unavailable

internal_error
degraded_mode
```

**Acceptance criteria**
- AC-E1: every response has meta.request_id.
- AC-E2: no stack traces in API responses.

---

## Observability plan (metrics/logs/tracing)

### Metrics (Prometheus)
- HTTP RPS + latency histograms
- ingestion lag per source
- translation failure rate
- cluster throughput
- impact level distribution
- allocation failures

### Logs
- JSON logs with request_id + trace_id
- Redaction: never log API keys; avoid full paywalled text

### Tracing (OpenTelemetry)
- api, worker, scheduler emit OTLP to Tempo

### Health endpoints
- `/v1/health` readiness checks
- every container has Docker healthcheck

**Acceptance criteria**
- AC-O1: `/metrics` is scrapeable.
- AC-O2: Grafana dashboards provision automatically.
- AC-O3: All containers expose a health endpoint or have a deterministic healthcheck.

---

## Threat model / privacy

Key threats and mitigations:
- Prompt injection via articles: sanitize input; schema-locked JSON; whitelist tickers only.
- Data poisoning: credibility tiers + corroboration requirement for L3+.
- SSRF in scrapers: domain allowlist + block private IP ranges.
- Licensing: store metadata/snippets unless licensed.

**Acceptance criteria**
- AC-T1: prompt injection cannot produce unknown tickers.
- AC-T2: fetchers block internal IP ranges.

---

## Test matrix + evidence checklist

### Test categories
- Contract tests: OpenAPI + JSON schema validation
- Unit tests: invariants, sorting, bounds, error envelopes
- Integration tests: ingestion->cluster->allocations persisted
- Security tests: SSRF blocked, injection blocked
- Performance tests: p95 latency budgets

### Evidence checklist
- CI logs
- Sample responses stored as golden files
- Grafana dashboard screenshots
- Calibration ledger rows for predicted vs realized

**Acceptance criteria**
- AC-Q1: tests cover all modules in scope.
- AC-Q2: evidence checklist items are producible from CI artifacts.

---

## Implementation steps in order

1) Repo bootstrap + CI (lint, tests, docker)
2) DB migration apply + ticker universe loader
3) Implement API envelopes + auth + error model + health/metrics
4) Implement impacts endpoints (latest + per cluster) with strict ticker whitelist
5) Implement topics index engine + endpoint
6) Implement SSE stream (optional), fallback to polling
7) Frontend integration: overview + news + impacts + topics + ops
8) Observability: Prometheus/Grafana/Loki/Tempo dashboards
9) Backfill + research: SPY event-study + calibration ledger
10) Hardening: rate limiting, idempotency, retries, rollback plan
