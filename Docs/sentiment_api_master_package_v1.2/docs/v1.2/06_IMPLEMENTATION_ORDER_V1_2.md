# Implementation steps in order — v1.2

1) **Contracts first**
   - freeze OpenAPI and JSON schemas
   - generate Pydantic models if desired, but keep schemas as truth

2) **Backend skeleton**
   - FastAPI app
   - auth middleware + api_key handling
   - request_id + error envelope
   - health + metrics endpoints

3) **Database**
   - apply migrations
   - implement ticker universe loader job
   - implement basic repositories (articles/clusters/impacts)

4) **Impact allocation**
   - implement whitelist enforcement (ticker_universe)
   - implement outputs for:
     - /v1/impacts/latest
     - /v1/impacts/clusters/{cluster_id}

5) **Topics**
   - compute per-topic index
   - serve /v1/topics/index

6) **Streaming**
   - implement SSE stream events (optional)
   - implement fallback to polling

7) **Frontend**
   - shell + routing
   - overview charts
   - news feed + drilldowns
   - impacts + topics pages
   - ops page

8) **Observability**
   - Prometheus scrape
   - Grafana dashboards
   - Loki logs
   - Tempo traces

9) **Research / SPY event studies**
   - market data ingestion
   - event window calculations
   - store + serve results

10) **Hardening**
   - rate limiting + retry policies
   - idempotency policies
   - rollback plan + feature flags
