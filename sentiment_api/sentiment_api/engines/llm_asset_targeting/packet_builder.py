"""Build ClusterPacket from cluster/summary data."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple

from .schemas import ClusterPacket, PacketEvidence, PacketImpact, DirectMention, NumericFact

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def build_cluster_packet(
    *,
    cluster_id: str,
    cluster_version: int,
    headline_en: str,
    summary_bullets_en: List[str],
    topics: List[str],
    regions: List[str],
    impact_score: float,
    impact_level: str,
    expected_direction: str,
    confidence: float,
    evidence_rows: List[Dict[str, Any]],
    direct_mentions: List[Dict[str, Any]] | None = None,
    numeric_facts: List[Dict[str, Any]] | None = None,
    max_evidence: int = 6,
    max_chars_per_passage: int = 420,
    max_total_chars: int = 2400,
) -> Tuple[ClusterPacket, str]:
    rows = sorted(
        evidence_rows,
        key=lambda r: (-float(r.get("relevance_score", 0.0)), str(r.get("url", ""))),
    )

    picked: List[PacketEvidence] = []
    total = 0
    eid = 1
    for r in rows[: max_evidence * 2]:
        txt = str(r.get("text_en", r.get("quote_en", ""))).strip()
        if not txt:
            continue
        txt = txt[:max_chars_per_passage]
        if total + len(txt) > max_total_chars:
            break
        picked.append(PacketEvidence(id=eid, url=str(r.get("url", "")), text_en=txt))
        total += len(txt)
        eid += 1
        if len(picked) >= max_evidence:
            break

    dm: List[DirectMention] = []
    for m in (direct_mentions or []):
        sym = str(m.get("symbol", "")).upper().strip()
        if not sym:
            continue
        dm.append(
            DirectMention(
                symbol=sym,
                match_quality=float(m.get("match_quality", 0.0)),
                evidence_ids=list(m.get("evidence_ids", []) or []),
            )
        )

    nf: List[NumericFact] = []
    for f in (numeric_facts or []):
        key = str(f.get("key", "")).strip()
        if not key:
            continue
        nf.append(NumericFact(key=key, value=float(f.get("value", 0.0))))

    packet = ClusterPacket(
        cluster_id=cluster_id,
        cluster_version=cluster_version,
        headline_en=headline_en,
        summary_bullets_en=summary_bullets_en,
        topics=topics,
        regions=regions,
        impact=PacketImpact(
            impact_score=impact_score,
            impact_level=impact_level,
            expected_direction=expected_direction,
            confidence=confidence,
        ),
        evidence=picked,
        direct_mentions=dm,
        numeric_facts=nf,
    )
    packet_hash = sha256_str(canonical_json(packet.model_dump()))
    return packet, packet_hash
