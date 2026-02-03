"""Deterministic allocator (docs/40_ALLOCATION_MATH)."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from .schemas import (
    AllocationResult,
    ChannelInferResult,
    SectorMapResult,
    TickerSelectResult,
    ClusterPacket,
    MarketAllocation,
    SectorAllocation,
    TickerAllocation,
)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def direction_sign(direction: str) -> int:
    if direction == "RiskOn":
        return 1
    if direction == "RiskOff":
        return -1
    return 0


def channel_vector(call_a: ChannelInferResult) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for c in call_a.channels:
        out[c.name] = clamp(float(c.sign) * float(c.strength), -1.0, 1.0)
    return out


def relevance(raw: float) -> float:
    a = abs(raw)
    if a >= 0.15:
        return 1.0
    if a >= 0.05:
        return 0.7
    return 0.4


def load_beta_market(path: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    betas: Dict[str, Dict[str, float]] = {}
    labels: Dict[str, str] = {}
    for mid, m in (cfg.get("markets") or {}).items():
        labels[mid] = m.get("label_en", mid)
        betas[mid] = {k: float(v) for k, v in (m.get("beta") or {}).items()}
    return betas, labels


def load_beta_sector(path: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    betas: Dict[str, Dict[str, float]] = {}
    labels: Dict[str, str] = {}
    for sid, s in (cfg.get("sectors") or {}).items():
        labels[sid] = s.get("sector_name_en", sid)
        betas[sid] = {k: float(v) for k, v in (s.get("beta") or {}).items()}
    return betas, labels


def load_exposures(path: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, str]]]:
    exp: Dict[str, Dict[str, float]] = {}
    meta: Dict[str, Dict[str, str]] = {}
    p = Path(path)
    if not p.exists():
        return exp, meta
    with open(p, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sym = (row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            meta[sym] = {
                "universe": (row.get("universe") or "unknown").strip(),
                "sector_id": (row.get("sector_id") or "UNKNOWN").strip().upper(),
            }
            exp[sym] = {}
            for k, v in row.items():
                if k in ("symbol", "universe", "sector_id", "industry_id"):
                    continue
                try:
                    exp[sym][k] = float(v) if v not in (None, "") else 0.0
                except Exception:
                    exp[sym][k] = 0.0
    return exp, meta


def allocate(
    *,
    packet: ClusterPacket,
    call_a: ChannelInferResult,
    call_b: SectorMapResult,
    call_c: TickerSelectResult,
    beta_market_path: str,
    beta_sector_path: str,
    exposures_csv_path: str,
    top_k_markets: int = 5,
    top_k_sectors: int = 11,
    top_k_tickers: int = 25,
) -> AllocationResult:
    signed_score = float(packet.impact.impact_score) * float(direction_sign(packet.impact.expected_direction))
    cluster_conf = float(packet.impact.confidence)

    cvec = channel_vector(call_a)
    horizon = call_a.primary_horizon

    beta_m, labels_m = load_beta_market(beta_market_path)
    beta_s, labels_s = load_beta_sector(beta_sector_path)
    exp, meta = load_exposures(exposures_csv_path)

    markets: List[MarketAllocation] = []
    for mid, betas in beta_m.items():
        raw = 0.0
        for ck, cv in cvec.items():
            raw += cv * betas.get(ck, 0.0)
        signed = clamp(signed_score * math.tanh(raw), -100.0, 100.0)
        markets.append(
            MarketAllocation(
                market_id=mid,
                label_en=labels_m.get(mid, mid),
                signed_score=signed,
                magnitude=clamp(abs(signed) / 100.0, 0.0, 1.0),
                confidence=clamp(cluster_conf * relevance(raw), 0.0, 1.0),
                horizon=horizon,
                channels=[k for k, v in cvec.items() if abs(v) >= 0.2],
                rationale_en=f"market beta allocation (raw={raw:.2f})",
                evidence_ids=[],
            )
        )
    markets.sort(key=lambda x: abs(x.signed_score), reverse=True)
    top_markets = markets[:top_k_markets]
    equities_abs = abs(top_markets[0].signed_score) if top_markets else abs(signed_score)

    raw_sector: Dict[str, float] = {}
    conf_sector: Dict[str, float] = {}
    for sid, betas in beta_s.items():
        raw = 0.0
        for ck, cv in cvec.items():
            raw += cv * betas.get(ck, 0.0)
        raw_sector[sid] = clamp(signed_score * math.tanh(raw), -100.0, 100.0)
        conf_sector[sid] = clamp(cluster_conf * relevance(raw), 0.0, 1.0)

    S = sum(abs(v) for v in raw_sector.values())
    target = max(equities_abs, 1.0) * 1.15
    scale = 1.0 if S <= 1e-9 else min(1.0, target / S)

    sectors: List[SectorAllocation] = []
    for sid, sraw in raw_sector.items():
        s = clamp(sraw * scale, -100.0, 100.0)
        sectors.append(
            SectorAllocation(
                sector_id=sid,
                sector_name_en=labels_s.get(sid, sid),
                signed_score=s,
                impact_score=abs(s),
                confidence=conf_sector.get(sid, cluster_conf),
                horizon=horizon,
                channels=[k for k, v in cvec.items() if abs(v) >= 0.2],
                rationale_en="sector beta allocation (conserved)",
                evidence_ids=[],
            )
        )
    sectors.sort(key=lambda x: abs(x.signed_score), reverse=True)
    top_sectors = sectors[:top_k_sectors]
    sector_scores = {s.sector_id: s.signed_score for s in sectors}

    llm_strength: Dict[str, float] = {}
    for p in call_c.winners + call_c.losers:
        llm_strength[p.symbol.upper()] = max(llm_strength.get(p.symbol.upper(), 0.5), float(p.strength))

    mention_count: Dict[str, int] = {}
    for dm in packet.direct_mentions:
        mention_count[dm.symbol.upper()] = mention_count.get(dm.symbol.upper(), 0) + 1

    candidates = set(exp.keys()) | set(llm_strength.keys()) | set(mention_count.keys())
    ticker_signed: Dict[str, float] = {}

    for sym in candidates:
        sym_u = sym.upper()
        sec = meta.get(sym_u, {}).get("sector_id", "UNKNOWN")
        base = sector_scores.get(sec, 0.0) * 0.85

        expo = 0.0
        for ck, cv in cvec.items():
            expo += cv * exp.get(sym_u, {}).get(ck, 0.0)

        mention_mult = 1.0 + 0.08 * math.log(1.0 + mention_count.get(sym_u, 0))
        w = llm_strength.get(sym_u, 0.5)
        llm_mult = 1.0 + 0.15 * (w - 0.5)

        sc = (base + signed_score * math.tanh(expo)) * mention_mult * llm_mult
        ticker_signed[sym_u] = clamp(sc, -100.0, 100.0)

    winners_sorted = sorted(ticker_signed.items(), key=lambda kv: kv[1], reverse=True)[:top_k_tickers]
    losers_sorted = sorted(ticker_signed.items(), key=lambda kv: kv[1])[:top_k_tickers]

    winners: List[TickerAllocation] = []
    losers: List[TickerAllocation] = []

    for sym, sc in winners_sorted:
        winners.append(
            TickerAllocation(
                symbol=sym,
                universe=meta.get(sym, {}).get("universe", "unknown"),
                signed_score=sc,
                expected_return_bps=clamp(sc * 2.0, -5000.0, 5000.0),
                confidence=clamp(cluster_conf, 0.0, 1.0),
                horizon=horizon,
                drivers=[k for k, v in cvec.items() if abs(v) >= 0.2],
                rationale_en="deterministic ticker allocation",
                evidence_ids=[],
            )
        )

    for sym, sc in losers_sorted:
        losers.append(
            TickerAllocation(
                symbol=sym,
                universe=meta.get(sym, {}).get("universe", "unknown"),
                signed_score=sc,
                expected_return_bps=clamp(sc * 2.0, -5000.0, 5000.0),
                confidence=clamp(cluster_conf, 0.0, 1.0),
                horizon=horizon,
                drivers=[k for k, v in cvec.items() if abs(v) >= 0.2],
                rationale_en="deterministic ticker allocation",
                evidence_ids=[],
            )
        )

    return AllocationResult(
        cluster_id=packet.cluster_id,
        cluster_version=packet.cluster_version,
        horizon=horizon,
        markets=top_markets,
        sectors=top_sectors,
        winners=winners,
        losers=losers,
        diagnostics={
            "signed_score": signed_score,
            "channels": cvec,
            "notes": "v1 deterministic allocator",
            "call_b_note": getattr(call_b, "notes_en", None),
            "call_c_note": getattr(call_c, "notes_en", None),
        },
    )
