"""Pydantic schemas for chunked LLM asset targeting (v1.0)."""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

ChannelName = Literal[
    "rates","inflation","growth","liquidity","credit_stress","geopolitics","energy_supply","trade_controls","regulation","risk_appetite"
]
Horizon = Literal["intraday","1d","3d","1w","1m","unknown"]
Direction = Literal["RiskOn","RiskOff","Neutral","Mixed","Unknown"]
SignedDir = Literal["up","down","neutral","mixed"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class PacketImpact(StrictModel):
    impact_score: float = Field(ge=0, le=100)
    impact_level: str
    expected_direction: Direction
    confidence: float = Field(ge=0, le=1)

class PacketEvidence(StrictModel):
    id: int = Field(ge=1, le=32)
    url: str
    text_en: str

class DirectMention(StrictModel):
    symbol: str
    match_quality: float = Field(ge=0, le=1)
    evidence_ids: List[int] = Field(default_factory=list)

class NumericFact(StrictModel):
    key: str
    value: float

class ClusterPacket(StrictModel):
    cluster_id: str
    cluster_version: int
    headline_en: str
    summary_bullets_en: List[str]
    topics: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    impact: PacketImpact
    evidence: List[PacketEvidence] = Field(default_factory=list)
    direct_mentions: List[DirectMention] = Field(default_factory=list)
    numeric_facts: List[NumericFact] = Field(default_factory=list)

class ChannelItem(StrictModel):
    name: ChannelName
    sign: Literal[-1,0,1]
    strength: float = Field(ge=0, le=1)
    why_refs: List[int] = Field(default_factory=list)
    short_why_en: str = Field(max_length=220)

class ChannelInferResult(StrictModel):
    channels: List[ChannelItem]
    primary_horizon: Horizon
    confidence: float = Field(ge=0, le=1)
    rationale_bullets_en: List[str] = Field(min_length=1, max_length=6)
    contradictions: Optional[bool] = False
    notes_en: Optional[str] = Field(default=None, max_length=240)

class IndustryItem(StrictModel):
    industry_id: str
    industry_name_en: str
    direction: SignedDir
    strength: float = Field(ge=0, le=1)
    why_refs: List[int] = Field(default_factory=list)
    short_why_en: str = Field(max_length=220)

class SectorItem(StrictModel):
    sector_id: str
    sector_name_en: str
    direction: SignedDir
    strength: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    why_refs: List[int] = Field(default_factory=list)
    industries: List[IndustryItem] = Field(default_factory=list)
    short_why_en: str = Field(max_length=220)

class SectorMapResult(StrictModel):
    sectors: List[SectorItem]
    notes_en: Optional[str] = Field(default=None, max_length=240)

class TickerPick(StrictModel):
    symbol: str
    strength: float = Field(ge=0, le=1)
    why_refs: List[int] = Field(default_factory=list)
    short_why_en: str = Field(max_length=220)

class TickerSelectResult(StrictModel):
    winners: List[TickerPick] = Field(default_factory=list, max_length=15)
    losers: List[TickerPick] = Field(default_factory=list, max_length=15)
    notes_en: Optional[str] = Field(default=None, max_length=240)

class MarketAllocation(StrictModel):
    market_id: str
    label_en: str
    signed_score: float = Field(ge=-100, le=100)
    magnitude: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list)
    rationale_en: str
    evidence_ids: List[int] = Field(default_factory=list)

class SectorAllocation(StrictModel):
    sector_id: str
    sector_name_en: str
    signed_score: float = Field(ge=-100, le=100)
    impact_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list)
    rationale_en: str
    evidence_ids: List[int] = Field(default_factory=list)

class TickerAllocation(StrictModel):
    symbol: str
    universe: str
    signed_score: float = Field(ge=-100, le=100)
    expected_return_bps: float = Field(ge=-5000, le=5000)
    confidence: float = Field(ge=0, le=1)
    horizon: Horizon
    drivers: List[str] = Field(default_factory=list)
    rationale_en: str
    evidence_ids: List[int] = Field(default_factory=list)

class AllocationResult(StrictModel):
    cluster_id: str
    cluster_version: int
    horizon: Horizon
    markets: List[MarketAllocation]
    sectors: List[SectorAllocation]
    winners: List[TickerAllocation]
    losers: List[TickerAllocation]
    diagnostics: dict = Field(default_factory=dict)
