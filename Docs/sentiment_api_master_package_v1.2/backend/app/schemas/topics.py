from __future__ import annotations

from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field

from .common import Direction

class TopicIndexPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ts: datetime
    topic_id: str = Field(..., min_length=2, max_length=32)
    topic_name_en: str = Field(..., min_length=2, max_length=64)
    index_value: float
    sentiment: Direction
    news_volume: int = Field(..., ge=0)

class TopicIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime
    points: List[TopicIndexPoint] = Field(default_factory=list, max_length=5000)
