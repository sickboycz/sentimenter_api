from __future__ import annotations

from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict, Field

from .common import ErrorModel, Pagination, ResponseMeta

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    meta: ResponseMeta
    data: T
    errors: List[ErrorModel] = Field(default_factory=list)

class ApiListResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    meta: ResponseMeta
    pagination: Pagination
    data: List[T]
    errors: List[ErrorModel] = Field(default_factory=list)
