# JSON Schemas (draft 2020-12)

These schemas define the wire contracts for sentiment_api v1.0.

- `defs.json` — shared definitions ($defs)
- `get_api_sp_sentiment.*.json` — Moodix-compatible export endpoint
- `get_v1_mood_now.*.json` — current mood snapshot
- `get_v1_index_intraday.*.json` — intraday index list
- `get_v1_news_clusters.*.json` — clusters list
- `get_v1_news_cluster_by_id.*.json` — cluster drilldown
- `get_v1_research_spy_event_study.*.json` — research endpoint
- `get_v1_sources.*.json` — source list endpoint
- `get_v1_health.response.json` — health endpoint

All responses use:
- `meta` (request_id, as_of)
- `errors[]` (always present; empty list on success)
- `pagination` where applicable
