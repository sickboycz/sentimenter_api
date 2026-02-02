"""Retention policy: tombstone semantics (AC-M7.3)."""

import logging
from datetime import datetime, timedelta, timezone

from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.db.retention")


async def retire_old_articles(days: int = 90) -> int:
    """Mark articles older than N days as tombstoned (deleted_at). Returns count."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with acquire() as conn:
            try:
                result = await conn.execute(
                    """
                    UPDATE articles SET deleted_at = now()
                    WHERE fetched_at < $1 AND deleted_at IS NULL
                    """,
                    cutoff,
                )
            except Exception as col_err:
                if "deleted_at" in str(col_err) or "column" in str(col_err).lower():
                    logger.debug("deleted_at column missing; run migration v1.1_retention_tombstone")
                    return 0
                raise
            # result is "UPDATE N"
            n = int(result.split()[-1]) if result else 0
        logger.info("Retention: tombstoned %d articles older than %d days", n, days)
        return n
    except Exception as e:
        logger.warning("Retention retire failed: %s", e)
        return 0
