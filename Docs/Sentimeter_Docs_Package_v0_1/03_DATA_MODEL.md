# 03_DATA_MODEL.md
## Postgres tables (core)
- sources, articles, article_bodies
- clusters, cluster_members
- summaries (L1–L4, jsonb)
- events, event_impacts
- sentiment_timeseries
- market_bars (SPY)
- expectations, outcomes (forward eval)
- runs (audit)

## Object store layout (L0)
/data/artifacts/news/{source}/{yyyy}/{mm}/{dd}/{article_id}.html
/data/artifacts/news/{source}/{yyyy}/{mm}/{dd}/{article_id}.txt
/data/artifacts/embeddings/{type}/{id}.json
