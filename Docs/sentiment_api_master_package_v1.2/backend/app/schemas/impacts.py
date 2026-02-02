from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .common import Direction, Horizon

class MarketImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market_id: str = Field(..., min_length=2, max_length=64)
    label_en: str = Field(..., min_length=2, max_length=64)
    expected_direction: Direction
    magnitude: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=2000)

class SectorImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sector_id: str = Field(..., min_length=2, max_length=32)
    sector_name_en: str = Field(..., min_length=2, max_length=64)
    expected_direction: Direction
    impact_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    channels: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=2000)

class TickerImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(..., min_length=1, max_length=16)
    company_name_en: Optional[str] = Field(default=None, max_length=128)
    universe: str = Field(..., min_length=1, max_length=32)
    sector_id: Optional[str] = Field(default=None, max_length=32)
    expected_direction: Direction
    expected_return_bps: float = Field(..., ge=-5000.0, le=5000.0)
    expected_volatility_delta: float = Field(..., ge=-5.0, le=5.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: Horizon
    drivers: List[str] = Field(default_factory=list, max_length=16)
    rationale_en: str = Field(..., min_length=10, max_length=3000)

class AssetImpacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    markets: List[MarketImpact] = Field(default_factory=list, max_length=30)
    sectors: List[SectorImpact] = Field(default_factory=list, max_length=50)
    winners: List[TickerImpact] = Field(default_factory=list, max_length=200)
    losers: List[TickerImpact] = Field(default_factory=list, max_length=200)
    methodology_version: str = Field(..., min_length=1, max_length=32)
