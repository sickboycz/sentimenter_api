from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

class ImpactLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

class Direction(str, Enum):
    RiskOn = "RiskOn"
    RiskOff = "RiskOff"
    Neutral = "Neutral"
    Mixed = "Mixed"
    Unknown = "Unknown"

class Horizon(str, Enum):
    intraday = "intraday"
    d1 = "1d"
    d3 = "3d"
    w1 = "1w"
    m1 = "1m"
    unknown = "unknown"

class CredibilityTier(str, Enum):
    official = "official"
    reputable_media = "reputable_media"
    local_media = "local_media"
    dataset = "dataset"
    user_added = "user_added"

class ErrorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    details: Dict[str, Any] = Field(default_factory=dict)
    hint: Optional[str] = None
    retryable: bool = False

class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., min_length=8)
    as_of: datetime
    trace_id: Optional[str] = None
    model_versions: Dict[str, str] = Field(default_factory=dict)

class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(..., ge=1, le=500)
    next_cursor: Optional[str] = None
    returned: int = Field(..., ge=0)
