"""Registry data models."""

from typing import Any

from pydantic import BaseModel, Field


class RegistryDefaults(BaseModel):
    """Default values for all sources."""

    enabled: bool = True
    translate_to_en: bool = True
    update_interval_sec: int = Field(ge=10, default=300)
    credibility_tier: str = "reputable_media"
    license_class: str = "open"
    max_fetch_retries: int = Field(ge=0, le=20, default=3)
    request_timeout_sec: int = Field(ge=1, le=120, default=20)
    respect_robots_txt: bool = True
    max_article_age_days: int = Field(ge=0, le=3650, default=30)


class Pack(BaseModel):
    """Source pack configuration."""

    enabled: bool


class SourceAuth(BaseModel):
    """Source authentication config."""

    method: str | None = None
    key_name: str | None = None
    location: str | None = None  # query | header


class QueryProfile(BaseModel):
    """GDELT-style query profile."""

    profile_id: str
    query: str


class Source(BaseModel):
    """Single source definition."""

    source_id: str = Field(..., pattern=r"^[a-z0-9_\-]{3,64}$")
    name: str = Field(..., min_length=1)
    pack: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(gdelt|rss|api|scrape|dataset)$")
    enabled: bool | None = None
    translate_to_en: bool | None = None
    update_interval_sec: int | None = None
    credibility_tier: str | None = None
    license_class: str | None = None
    regions: list[str] = Field(default_factory=list, max_length=50)
    topics: list[str] = Field(default_factory=list, max_length=50)
    feed_url: str | None = None
    page_url: str | None = None
    base_url: str | None = None
    language_hint: str | None = None
    parser_profile: str | None = None
    auth: SourceAuth | dict[str, Any] | None = None
    query_profiles: list[QueryProfile] | None = None
    notes: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        # Type-specific URL requirements (validated in load_registry)
        pass

    def effective_enabled(self, pack_enabled: bool, defaults: RegistryDefaults) -> bool:
        """Whether this source is effectively enabled."""
        return (
            (self.enabled if self.enabled is not None else defaults.enabled)
            and pack_enabled
        )

    def to_db_config(self, defaults: RegistryDefaults) -> dict[str, Any]:
        """Build config dict for DB sources table."""
        cfg: dict[str, Any] = {}
        if self.type == "rss" and self.feed_url:
            cfg["feed_url"] = self.feed_url
        elif self.type == "scrape" and self.page_url:
            cfg["page_url"] = self.page_url
        elif self.type == "gdelt" and self.base_url:
            cfg["base_url"] = self.base_url
            if self.query_profiles:
                cfg["query_profiles"] = [p.model_dump() for p in self.query_profiles]
        elif self.type in ("api", "dataset") and self.base_url:
            cfg["base_url"] = self.base_url
        if self.auth:
            cfg["auth"] = self.auth if isinstance(self.auth, dict) else self.auth.model_dump()
        return cfg


class SourceRegistry(BaseModel):
    """Full source registry (validated)."""

    version: str
    defaults: RegistryDefaults
    packs: dict[str, Pack]
    sources: list[Source]

    def get_enabled_sources(self) -> list[Source]:
        """Return sources that are enabled (source + pack)."""
        result: list[Source] = []
        for s in self.sources:
            pack = self.packs.get(s.pack)
            pack_ok = pack.enabled if pack else True
            if s.effective_enabled(pack_ok, self.defaults):
                result.append(s)
        return result

    def get_source_by_id(self, source_id: str) -> Source | None:
        for s in self.sources:
            if s.source_id == source_id:
                return s
        return None

    def source_ids_unique(self) -> bool:
        seen: set[str] = set()
        for s in self.sources:
            if s.source_id in seen:
                return False
            seen.add(s.source_id)
        return True
