"""Configuration and environment settings."""

from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
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
    source_registry_path: Path = Field(
        default=Path("Docs/sentiment_api_tech_package_v1.1/registry/source_registry.yaml"),
        validation_alias=AliasChoices("SOURCE_REGISTRY_PATH", "SENTIMENT_API_SOURCE_REGISTRY_PATH"),
    )
    universe_registry_path: Path = Field(
        default=Path("Docs/sentiment_api_tech_package_v1.1/registry/universe_registry.yaml"),
        validation_alias=AliasChoices("UNIVERSE_REGISTRY_PATH", "SENTIMENT_API_UNIVERSE_REGISTRY_PATH"),
    )

    openai_api_key: str | None = None
    model_summarizer_id: str = "gpt-5-mini"
    model_embedding_id: str = "openai:text-embedding-3-large"
    # Escalation chain for LLM: try mini → 5.2 → 5.2-pro on failure
    # Override via SENTIMENT_API_MODEL_ESCALATION="gpt-5.2-mini,gpt-5.2,gpt-5.2-pro"
    model_escalation: list[str] = Field(
        default=["gpt-5-mini", "gpt-5.2", "gpt-5.2-pro"],
        description="LLM model escalation chain (GPT-5.2 family)",
    )

    @field_validator("model_escalation", mode="before")
    @classmethod
    def parse_escalation(cls, v):
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        if isinstance(v, list):
            return v
        return v

    api_host: str = "0.0.0.0"
    api_port: int = 8080
    retention_days: int = 90  # tombstone articles older than N days (AC-M7.3)
    api_keys: str = Field(default="", description="SENTIMENT_API_API_KEYS, comma-separated")
    # CORS: comma-separated origins (e.g. http://localhost:3000,http://80.211.210.49:3000)
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="CORS_ORIGINS: allowed origins for browser requests (comma-separated)",
        validation_alias=AliasChoices("CORS_ORIGINS", "SENTIMENT_API_CORS_ORIGINS"),
    )

    # Vector store: pgvector (default) | pinecone | weaviate (see docs/PINECONE_WEAVIATE_INTEGRATION.md)
    vector_store_backend: str = Field(
        default="pgvector",
        description="VECTOR_STORE_BACKEND: pgvector, pinecone, or weaviate",
    )
    # Pinecone (when vector_store_backend=pinecone)
    pinecone_api_key: str | None = Field(default=None, description="PINECONE_API_KEY")
    pinecone_index: str = Field(default="sentiment-api", description="PINECONE_INDEX")
    pinecone_environment: str | None = Field(default=None, description="PINECONE_ENVIRONMENT / host")
    # Weaviate (when vector_store_backend=weaviate)
    weaviate_url: str = Field(
        default="http://localhost:8080",
        description="WEAVIATE_URL (or SENTIMENT_API_WEAVIATE_URL)",
        validation_alias=AliasChoices("WEAVIATE_URL", "SENTIMENT_API_WEAVIATE_URL"),
    )
    weaviate_api_key: str | None = Field(default=None, description="WEAVIATE_API_KEY")
    weaviate_class: str = Field(default="Embedding", description="WEAVIATE_CLASS")

    # 2-tier retrieval (see docs/RETRIEVAL_TWOTIER.md)
    retrieval_tiera_model_id: str = Field(
        default="openai:text-embedding-3-small",
        description="RETRIEVAL_TIERA_MODEL_ID: cheap tier-A embedding (384/768 dim)",
    )
    retrieval_tierb_model_id: str = Field(
        default="openai:text-embedding-3-large",
        description="RETRIEVAL_TIERB_MODEL_ID: expensive tier-B rerank (3072 dim)",
    )
    retrieval_topn: int = Field(default=200, description="RETRIEVAL_TOPN: candidate count from hybrid search")
    retrieval_rerankn: int = Field(default=80, description="RETRIEVAL_RERANKN: top-N after tierB rerank")
    retrieval_alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="RETRIEVAL_ALPHA: hybrid weight (0=BM25 only, 1=vector only)")
    retrieval_weights: str = Field(
        default='{"tierA":0.2,"bm25":0.2,"tierB":0.6,"cross":0.0}',
        description="RETRIEVAL_WEIGHTS: JSON string tierA/bm25/tierB/cross",
    )
    embedding_cache_path: Path = Field(
        default=Path("/var/lib/sentiment_api/embedding_cache.sqlite"),
        description="EMBEDDING_CACHE_PATH: SQLite path for tierB vector cache",
    )
    weaviate_chunk_class: str = Field(
        default="RetrievalChunk",
        description="WEAVIATE_CHUNK_CLASS: collection for 2-tier chunk retrieval",
    )

    def resolve_paths(self) -> None:
        """Resolve registry paths relative to project root if needed."""
        root = Path(__file__).resolve().parent.parent.parent
        if not self.source_registry_path.is_absolute():
            candidate = root / self.source_registry_path
            if candidate.exists():
                self.source_registry_path = candidate
        if not self.universe_registry_path.is_absolute():
            candidate = root / self.universe_registry_path
            if candidate.exists():
                self.universe_registry_path = candidate


def get_settings() -> Settings:
    s = Settings()
    s.resolve_paths()
    return s
