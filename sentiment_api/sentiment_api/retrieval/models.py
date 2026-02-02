"""Data models for 2-tier retrieval (candidates, score breakdown, trace)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    """Single candidate from Tier A hybrid retrieval."""

    chunk_id: str
    text: str
    doc_id: str
    source: str
    url: str | None
    published_at: str | None
    tickers: list[str]
    sector: str | None
    language: str | None
    text_hash: str
    tier_a_score: float = 0.0
    bm25_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreBreakdown:
    """Per-result score breakdown (tierA, bm25, tierB, cross, final)."""

    tier_a: float = 0.0
    bm25: float = 0.0
    tier_b: float = 0.0
    cross: float = 0.0
    final: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "tierA": self.tier_a,
            "bm25": self.bm25,
            "tierB": self.tier_b,
            "cross": self.cross,
            "final": self.final,
        }


@dataclass
class SearchResult:
    """Final ranked result with snippet and score breakdown."""

    chunk_id: str
    doc_id: str
    snippet: str
    score_breakdown: ScoreBreakdown
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchTrace:
    """Audit-grade trace for retrieval (latencies, counts, cache stats)."""

    trace_id: str
    candidate_count: int = 0
    rerank_count: int = 0
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    latency_tiera_ms: float = 0.0
    latency_tierb_ms: float = 0.0
    latency_cross_ms: float = 0.0
    filter_summary: dict[str, Any] = field(default_factory=dict)
    model_tiera: str = ""
    model_tierb: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "candidate_count": self.candidate_count,
            "rerank_count": self.rerank_count,
            "cache_hit_count": self.cache_hit_count,
            "cache_miss_count": self.cache_miss_count,
            "latency_tiera_ms": round(self.latency_tiera_ms, 2),
            "latency_tierb_ms": round(self.latency_tierb_ms, 2),
            "latency_cross_ms": round(self.latency_cross_ms, 2),
            "filter_summary": self.filter_summary,
            "model_tiera": self.model_tiera,
            "model_tierb": self.model_tierb,
        }
