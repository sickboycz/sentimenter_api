"""Universe registry data models."""

from pydantic import BaseModel, Field
from typing import Any


class UniverseDef(BaseModel):
    """Single universe definition."""

    universe_id: str = Field(..., pattern=r"^[a-z0-9_]{3,64}$")
    name_en: str
    description_en: str | None = None
    enabled: bool = True
    refresh: dict[str, Any] | None = None
    providers: list[dict[str, Any]]
    sector_taxonomy: dict[str, Any]


class UniverseRegistry(BaseModel):
    """Universe registry (validated)."""

    version: str
    universes: list[UniverseDef]

    def get_enabled(self) -> list[UniverseDef]:
        return [u for u in self.universes if u.enabled]
