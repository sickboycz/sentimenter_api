from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTIMENT_API_", extra="ignore")

    # Security
    api_keys: str = Field(default="")  # comma-separated
    allow_metrics_unauthenticated: bool = Field(default=True)

    # DB
    database_url: str = Field(default="postgresql+psycopg2://sentiment:sentiment@db:5432/sentiment")

    # Runtime
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    # Observability
    otel_service_name: str = Field(default="sentiment_api")
    otel_exporter_otlp_endpoint: str | None = Field(default=None)

settings = Settings()
