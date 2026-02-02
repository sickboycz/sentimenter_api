from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["heartbeat","cluster_updated","mood_updated","impacts_updated","topics_updated"]
    ts: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
