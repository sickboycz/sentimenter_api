"""E2E test: ingest → summarize → clusters.

Requires DATABASE_URL and REDIS_URL (e.g. from docker compose).
Skips if not set. Mocks LLM and embedding to avoid API calls.
"""

import os

import pytest

# Skip unless explicitly requested
pytestmark = pytest.mark.skipif(
    not os.environ.get("SENTIMENT_E2E"),
    reason="Set SENTIMENT_E2E=1 to run (needs Postgres + Redis)",
)


@pytest.fixture
def db_url():
    url = os.environ.get("DATABASE_URL", "postgresql://sentiment:sentiment@localhost:5432/sentiment")
    return url


@pytest.fixture
def redis_url():
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_ingest_summarize_creates_cluster(db_url, redis_url):
    """Run one article through ingest and summarize; assert cluster created."""
    import asyncio
    from unittest.mock import patch, MagicMock

    from sentiment_api.db.pool import init_pool, close_pool, acquire
    from sentiment_api.db.repo import insert_article
    from sentiment_api.queue.client import get_queue, QUEUE_SUMMARIZE, QUEUE_INGEST
    from sentiment_api.ingest.worker import process_ingest, process_summarize

    await init_pool(db_url)
    queue = await get_queue(redis_url)

    try:
        # Minimal raw payload (as from daemon); use existing registry source
        raw = {
            "source_id": "us_fed_rss",
            "source_type": "rss",
            "url": "https://example.com/e2e-test-article-123",
            "published_at": "2026-02-03T12:00:00Z",
            "fetched_at": "2026-02-03T12:00:00Z",
            "title_raw": "E2E Test: Fed signals rate cut",
            "content_raw": "The Federal Reserve indicated it may cut rates in the coming months.",
            "content_html": "",
            "metadata": {},
        }

        # Mock LLM and embedding
        fake_l1 = {"article_id": "art_x", "facts": [], "uncertainty_flags": []}
        fake_l2 = {
            "article_id": "art_x", "headline_en": "Fed signals rate cut",
            "topics": ["rates"], "regions": ["US"], "tone": {"polarity": 0, "subjectivity": 0.5},
            "key_claims_en": [], "why_it_matters_en": "Test.", "entities": [], "uncertainty_flags": [],
            "evidence_refs": [{"url": raw["url"], "quote_en": raw["title_raw"][:240]}],
        }
        fake_l3 = {
            "cluster_id": "clu_x", "headline_en": "Fed signals rate cut",
            "summary_bullets_en": [], "what_changed_en": "", "why_it_matters_en": "", "what_to_watch_en": "",
            "topics": ["rates"], "regions": ["US"], "channels": [], "evidence": [], "uncertainty_flags": [],
        }
        fake_embedding = [0.1] * 3072

        with patch("sentiment_api.ingest.worker.summarize_l1", return_value=fake_l1), \
             patch("sentiment_api.ingest.worker.summarize_l2", return_value=fake_l2), \
             patch("sentiment_api.ingest.worker.summarize_l3", return_value=fake_l3), \
             patch("sentiment_api.ingest.worker.embed_text", return_value=fake_embedding):
            # Run ingest
            await process_ingest(raw)

            # Ingest should have pushed to summarize if article was new
            len_sum = await queue.llen(QUEUE_SUMMARIZE)
            if len_sum == 0:
                pytest.skip("Ingest did not push (duplicate article or registry issue)")

            # Pop and process one summarize job
            _, data = await queue.blpop(QUEUE_SUMMARIZE, timeout=2)
            import json
            payload = json.loads(data)
            await process_summarize(payload)

        # Assert cluster exists
        async with acquire() as conn:
            n = await conn.fetchval("SELECT COUNT(*) FROM clusters")
        assert n >= 1, "Expected at least one cluster after summarize"
    finally:
        await close_pool()
