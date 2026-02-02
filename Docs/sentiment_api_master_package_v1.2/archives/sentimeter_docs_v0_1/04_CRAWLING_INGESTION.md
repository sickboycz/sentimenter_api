# 04_CRAWLING_INGESTION.md
## Live sources
- RSS (primary)
- official releases (Fed/ECB/gov stats)
- weather agencies (NOAA), commodity releases (USDA/EIA)

## Archive backfill
- date-partitioned crawling by source
- keyword/topic guided backfill for major regimes

## Crawl rules
- robots.txt, rate limits, caching
- user-agent + contact
- backoff on 429/5xx

## Extraction
- HTML→text via trafilatura/readability
- store raw + extracted
- quality scoring

## Dedupe/clustering
- canonical hash for exact dedupe
- embeddings for near-duplicate clustering
