"""Build allowed_symbols for Call C (deterministic allowlist)."""
from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .schemas import ClusterPacket, ChannelInferResult, SectorMapResult
from .security_master import SecurityMaster

@dataclass(frozen=True)
class CandidateDiagnostics:
    direct_mentions: int
    sector_top: int
    ruleset: int
    total_before_cap: int
    total_after_cap: int
    cap_reason: str

def load_rulesets(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

async def build_allowed_symbols(
    *,
    packet: ClusterPacket,
    call_a: ChannelInferResult,
    call_b: SectorMapResult,
    security_master: SecurityMaster,
    rulesets_path: str,
    max_allowed: int = 600,
    top_per_sector: int = 40,
) -> Tuple[List[str], CandidateDiagnostics]:
    """Deterministically build allowed_symbols list for Call C."""

    allowed: List[str] = []
    seen: Set[str] = set()

    dm_count = 0
    for dm in sorted(packet.direct_mentions, key=lambda x: (-x.match_quality, x.symbol)):
        sym = dm.symbol.upper()
        if await security_master.is_allowed(sym) and sym not in seen:
            allowed.append(sym)
            seen.add(sym)
            dm_count += 1

    sector_count = 0
    top_sectors = sorted(call_b.sectors, key=lambda s: (-s.strength, s.sector_id))[:5]
    for s in top_sectors:
        for info in await security_master.by_sector(s.sector_id, top_per_sector):
            if info.symbol not in seen:
                allowed.append(info.symbol)
                seen.add(info.symbol)
                sector_count += 1

    rules_cfg = load_rulesets(rulesets_path)
    rules = (rules_cfg or {}).get("rules", {})
    ruleset_count = 0
    for ch in call_a.channels:
        if ch.strength < 0.35:
            continue
        r = rules.get(ch.name)
        if not r:
            continue
        for sym in (r.get("include_symbols") or []):
            sym_u = str(sym).upper()
            if await security_master.is_allowed(sym_u) and sym_u not in seen:
                allowed.append(sym_u)
                seen.add(sym_u)
                ruleset_count += 1

    total_before = len(allowed)

    cap_reason = "none"
    if len(allowed) > max_allowed:
        cap_reason = f"capped_to_{max_allowed}"
        allowed = allowed[:max_allowed]

    diag = CandidateDiagnostics(
        direct_mentions=dm_count,
        sector_top=sector_count,
        ruleset=ruleset_count,
        total_before_cap=total_before,
        total_after_cap=len(allowed),
        cap_reason=cap_reason,
    )
    return allowed, diag
