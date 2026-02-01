"""Configuration and environment settings."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(
        env_prefix="SENTIMENT_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"
    database_url: str = Field(
        default="postgresql://sentiment:sentiment@localhost:5432/sentiment",
        validation_alias=AliasChoices("DATABASE_URL", "SENTIMENT_API_DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "SENTIMENT_API_REDIS_URL"),
    )
    artifact_root: Path = Path("/data/artifacts")
    source_registry_path: Path = Path("Docs/sentiment_api_tech_package_v1.0/registry/source_registry.yaml")

    openai_api_key: str | None = None
    model_summarizer_id: str = "openai:gpt-4.1-mini"
    model_embedding_id: str = "openai:text-embedding-3-large"

    api_host: str = "0.0.0.0"
    api_port: int = 8080

    def resolve_paths(self) -> None:
        """Resolve paths relative to project root if needed."""
        root = Path(__file__).resolve().parent.parent.parent
        if not self.source_registry_path.is_absolute():
            candidate = root / self.source_registry_path
            if candidate.exists():
                self.source_registry_path = candidate


def get_settings() -> Settings:
    s = Settings()
    s.resolve_paths()
    return s
