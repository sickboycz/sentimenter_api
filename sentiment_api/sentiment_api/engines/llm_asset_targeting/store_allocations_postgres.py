"""Store AllocationResult into cluster_*_allocations (asyncpg)."""
from __future__ import annotations

import json

from sentiment_api.db.pool import acquire

from .schemas import AllocationResult


async def store_allocations(alloc: AllocationResult, *, model_version: str, config_hash: str) -> None:
    """Insert allocations into cluster_market/sector/ticker_allocations."""
    async with acquire() as conn:
        for m in alloc.markets:
            await conn.execute(
                """
                INSERT INTO cluster_market_allocations
                  (cluster_id, cluster_version, market_id, label_en, signed_score, magnitude, confidence, horizon,
                   channels, rationale_en, evidence_ids, model_version, config_hash)
                VALUES
                  ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11,$12,$13)
                ON CONFLICT DO NOTHING
                """,
                alloc.cluster_id,
                alloc.cluster_version,
                m.market_id,
                m.label_en,
                m.signed_score,
                m.magnitude,
                m.confidence,
                alloc.horizon,
                json.dumps(m.channels),
                m.rationale_en,
                m.evidence_ids,
                model_version,
                config_hash,
            )

        for s in alloc.sectors:
            await conn.execute(
                """
                INSERT INTO cluster_sector_allocations
                  (cluster_id, cluster_version, sector_id, sector_name_en, signed_score, impact_score, confidence, horizon,
                   channels, rationale_en, evidence_ids, model_version, config_hash)
                VALUES
                  ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11,$12,$13)
                ON CONFLICT DO NOTHING
                """,
                alloc.cluster_id,
                alloc.cluster_version,
                s.sector_id,
                s.sector_name_en,
                s.signed_score,
                s.impact_score,
                s.confidence,
                alloc.horizon,
                json.dumps(s.channels),
                s.rationale_en,
                s.evidence_ids,
                model_version,
                config_hash,
            )

        for t in alloc.winners + alloc.losers:
            await conn.execute(
                """
                INSERT INTO cluster_ticker_allocations
                  (cluster_id, cluster_version, symbol, universe, signed_score, expected_return_bps, confidence, horizon,
                   drivers, rationale_en, evidence_ids, model_version, config_hash)
                VALUES
                  ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11,$12,$13)
                ON CONFLICT DO NOTHING
                """,
                alloc.cluster_id,
                alloc.cluster_version,
                t.symbol,
                t.universe,
                t.signed_score,
                t.expected_return_bps,
                t.confidence,
                alloc.horizon,
                json.dumps(t.drivers),
                t.rationale_en,
                t.evidence_ids,
                model_version,
                config_hash,
            )
