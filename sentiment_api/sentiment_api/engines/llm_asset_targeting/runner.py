"""Orchestrates Call A/B/C + allocate with DB cache."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from pydantic import ValidationError

from .cache_keys import cache_key, prompt_hash as phash, schema_hash as shash
from .packet_builder import canonical_json
from .prompts import SYSTEM_BASE, CHANNEL_INFER_USER, SECTOR_MAP_USER, TICKER_SELECT_USER
from .schemas import (
    ClusterPacket,
    ChannelInferResult,
    SectorMapResult,
    TickerSelectResult,
    AllocationResult,
)
from .openai_provider import OpenAIResponsesProvider, OpenAIResponsesError
from .cache_store import LLMCacheStore
from .candidate_generator import build_allowed_symbols
from .security_master import SecurityMaster
from .allocator import allocate


def load_json_schema(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ChunkedAssetTargetingRunner:
    """
    Orchestrates:
      A) channel_infer
      B) sector_map
      C) ticker_select
      D) deterministic allocate
    with DB cache in front of A/B/C.
    """

    def __init__(
        self,
        *,
        provider: OpenAIResponsesProvider,
        cache: LLMCacheStore,
        security_master: SecurityMaster,
        rulesets_path: str,
        schema_dir: str,
        beta_market_path: str,
        beta_sector_path: str,
        exposures_csv_path: str,
        config_hash: str = "llm_chunks_v1",
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.security_master = security_master
        self.rulesets_path = rulesets_path
        self.schema_dir = Path(schema_dir)
        self.beta_market_path = beta_market_path
        self.beta_sector_path = beta_sector_path
        self.exposures_csv_path = exposures_csv_path
        self.config_hash = config_hash

        self.schema_a = load_json_schema(str(self.schema_dir / "channel_infer.schema.json"))
        self.schema_b = load_json_schema(str(self.schema_dir / "sector_map.schema.json"))
        self.schema_c = load_json_schema(str(self.schema_dir / "ticker_select.schema.json"))

        self.schema_hash_a = shash(self.schema_a)
        self.schema_hash_b = shash(self.schema_b)
        self.schema_hash_c = shash(self.schema_c)

    async def _cached_call(
        self,
        *,
        step: str,
        name: str,
        schema: Dict[str, Any],
        schema_hash: str,
        packet: ClusterPacket,
        packet_hash: str,
        user_prompt: str,
        max_output_tokens: int,
    ) -> Tuple[Dict[str, Any], str]:
        p_hash = phash(SYSTEM_BASE, user_prompt)
        ck = cache_key(
            cluster_id=packet.cluster_id,
            cluster_version=packet.cluster_version,
            step=step,
            model=self.provider.model,
            prompt_hash=p_hash,
            packet_hash=packet_hash,
            schema_hash=schema_hash,
        )

        hit = await self.cache.get(ck)
        if hit and hit.status == "ok" and hit.parsed_json:
            return hit.parsed_json, ck

        meta = {
            "cluster_id": packet.cluster_id,
            "cluster_version": packet.cluster_version,
            "step": step,
            "model": self.provider.model,
            "prompt_hash": p_hash,
            "packet_hash": packet_hash,
            "schema_hash": schema_hash,
        }
        await self.cache.upsert_pending(ck, meta)

        try:
            parsed, usage = self.provider.call_structured(
                name=name,
                schema=schema,
                system_prompt=SYSTEM_BASE,
                user_prompt=user_prompt,
                max_output_tokens=max_output_tokens,
                temperature=0.0,
                metadata={"cluster_id": packet.cluster_id, "step": step},
            )
            await self.cache.upsert_ok(
                ck,
                parsed,
                parsed,
                {"latency_ms": usage.latency_ms, "tokens_in": usage.tokens_in, "tokens_out": usage.tokens_out},
            )
            return parsed, ck
        except OpenAIResponsesError as e:
            await self.cache.upsert_failed(ck, "openai_error", str(e), raw_json={"body": getattr(e, "body", None)})
            raise
        except Exception as e:
            await self.cache.upsert_failed(ck, "call_failed", str(e))
            raise

    async def run(self, packet: ClusterPacket, packet_hash: str) -> AllocationResult:
        if packet.impact.impact_score < 10 or packet.impact.confidence < 0.2:
            return AllocationResult(
                cluster_id=packet.cluster_id,
                cluster_version=packet.cluster_version,
                horizon="unknown",
                markets=[],
                sectors=[],
                winners=[],
                losers=[],
                diagnostics={"skipped": True, "reason": "low_impact_or_confidence"},
            )

        user_a = CHANNEL_INFER_USER.format(cluster_packet_json=canonical_json(packet.model_dump()))
        parsed_a, ck_a = await self._cached_call(
            step="channel_infer",
            name="ChannelInferResult",
            schema=self.schema_a,
            schema_hash=self.schema_hash_a,
            packet=packet,
            packet_hash=packet_hash,
            user_prompt=user_a,
            max_output_tokens=450,
        )
        call_a = ChannelInferResult(**parsed_a)

        sector_tax = [
            {"sector_id": "TECH", "sector_name_en": "Technology"},
            {"sector_id": "HEALTH", "sector_name_en": "Health Care"},
            {"sector_id": "ENERGY", "sector_name_en": "Energy"},
            {"sector_id": "FIN", "sector_name_en": "Financials"},
            {"sector_id": "IND", "sector_name_en": "Industrials"},
        ]
        evidence_index = [{"id": e.id, "url": e.url} for e in packet.evidence]
        user_b = SECTOR_MAP_USER.format(
            channel_json=canonical_json(call_a.model_dump()),
            sector_taxonomy_json=canonical_json(sector_tax),
            evidence_index_json=canonical_json(evidence_index),
        )
        parsed_b, ck_b = await self._cached_call(
            step="sector_map",
            name="SectorMapResult",
            schema=self.schema_b,
            schema_hash=self.schema_hash_b,
            packet=packet,
            packet_hash=packet_hash,
            user_prompt=user_b,
            max_output_tokens=700,
        )
        call_b = SectorMapResult(**parsed_b)

        allowed, cand_diag = await build_allowed_symbols(
            packet=packet,
            call_a=call_a,
            call_b=call_b,
            security_master=self.security_master,
            rulesets_path=self.rulesets_path,
        )

        top_sectors = [s.model_dump() for s in sorted(call_b.sectors, key=lambda x: -x.strength)[:5]]
        user_c = TICKER_SELECT_USER.format(
            channel_json=canonical_json(call_a.model_dump()),
            top_sectors_json=canonical_json(top_sectors),
            allowed_symbols_json=canonical_json({"allowed_symbols": allowed}),
            evidence_index_json=canonical_json(evidence_index),
        )
        parsed_c, ck_c = await self._cached_call(
            step="ticker_select",
            name="TickerSelectResult",
            schema=self.schema_c,
            schema_hash=self.schema_hash_c,
            packet=packet,
            packet_hash=packet_hash,
            user_prompt=user_c,
            max_output_tokens=700,
        )
        call_c = TickerSelectResult(**parsed_c)

        allowed_set = set(allowed)
        for p in call_c.winners + call_c.losers:
            if p.symbol.upper() not in allowed_set:
                raise ValueError(f"LLM returned non-allowlisted ticker: {p.symbol}")

        alloc = allocate(
            packet=packet,
            call_a=call_a,
            call_b=call_b,
            call_c=call_c,
            beta_market_path=self.beta_market_path,
            beta_sector_path=self.beta_sector_path,
            exposures_csv_path=self.exposures_csv_path,
        )
        alloc.diagnostics.update({
            "cache_keys": {"A": ck_a, "B": ck_b, "C": ck_c},
            "candidate_diagnostics": cand_diag.__dict__,
            "config_hash": self.config_hash,
            "model": self.provider.model,
        })
        return alloc
