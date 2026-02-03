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

    openai_api_key: str | None = Field(
        default=None,
        description="OPENAI_API_KEY for LLM/embeddings",
        validation_alias=AliasChoices("OPENAI_API_KEY", "SENTIMENT_API_OPENAI_API_KEY"),
    )
    # Cost-effective defaults: 384-dim embeddings (cheaper), single-model (no escalation)
    cost_effective: bool = Field(
        default=True,
        description="COST_EFFECTIVE: use 384-dim embeddings, mini-only LLM, skip LLM asset targeting; set False for best quality",
        validation_alias=AliasChoices("COST_EFFECTIVE", "SENTIMENT_API_COST_EFFECTIVE"),
    )
    model_summarizer_id: str = "gpt-5-mini"
    model_embedding_id: str = Field(
        default="openai:text-embedding-3-small:384",
        description="MODEL_EMBEDDING_ID: 384=cheaper, 768=higher quality",
    )
    # Escalation: cost_effective uses only mini; otherwise mini → 5.2 → 5.2-pro
    model_escalation: list[str] = Field(
        default=["gpt-5-mini"],
        description="MODEL_ESCALATION: LLM chain (comma-separated); cost_effective keeps mini only",
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
    # Clustering: cosine similarity threshold to merge article into existing cluster.
    # Use ~0.86–0.92 for "same story across outlets"; 0.95+ is near-duplicate only (dedup).
    cluster_similarity_threshold: float = Field(
        default=0.88,
        ge=0.0,
        le=1.0,
        description="CLUSTER_SIMILARITY_THRESHOLD: merge if similarity > this (0.88=topic clustering, 0.95=dedup only)",
        validation_alias=AliasChoices("CLUSTER_SIMILARITY_THRESHOLD", "SENTIMENT_API_CLUSTER_SIMILARITY_THRESHOLD"),
    )
    # Worker: prefer fullest queue when polling (work division by queue depth)
    queue_work_division: bool = Field(
        default=True,
        description="QUEUE_WORK_DIVISION: when True, workers poll queues by weighted depth (earlier stages get more workers)",
        validation_alias=AliasChoices("QUEUE_WORK_DIVISION", "SENTIMENT_API_QUEUE_WORK_DIVISION"),
    )
    # Stage weights for E2E flow: higher = more workers at that stage. News reduce at each gate (dedupe, cluster), so ingest > normalize > summarize > score > index.
    queue_stage_weights: dict[str, int] = Field(
        default_factory=lambda: {"ingest": 4, "normalize": 3, "summarize": 2, "score": 1, "index": 1},
        description="QUEUE_STAGE_WEIGHTS: comma-separated key:value e.g. ingest:4,normalize:3,summarize:2,score:1,index:1; higher = more workers at that stage",
        validation_alias=AliasChoices("QUEUE_STAGE_WEIGHTS", "SENTIMENT_API_QUEUE_STAGE_WEIGHTS"),
    )

    @field_validator("queue_stage_weights", mode="before")
    @classmethod
    def parse_queue_stage_weights(cls, v):
        default_weights = {"ingest": 4, "normalize": 3, "summarize": 2, "score": 1, "index": 1}
        if v is None:
            return default_weights
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            out: dict[str, int] = {}
            for part in v.split(","):
                part = part.strip()
                if ":" in part:
                    k, _, val = part.partition(":")
                    k, val = k.strip(), val.strip()
                    try:
                        out[k] = int(val)
                    except ValueError:
                        pass
            return out if out else default_weights
        return v
    api_keys: str = Field(default="", description="SENTIMENT_API_API_KEYS, comma-separated")
    # Worker scale from API: set COMPOSE_PROJECT_DIR to path containing docker-compose.yml to allow scale from UI
    compose_project_dir: str | None = Field(
        default=None,
        description="COMPOSE_PROJECT_DIR: path to run docker compose (enables scale from API); leave unset if API runs in container",
        validation_alias=AliasChoices("COMPOSE_PROJECT_DIR", "SENTIMENT_API_COMPOSE_PROJECT_DIR"),
    )
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
        default="openai:text-embedding-3-small:384",
        description="RETRIEVAL_TIERA_MODEL_ID: tier-A embedding (384 dim)",
    )
    retrieval_tierb_model_id: str = Field(
        default="openai:text-embedding-3-small:768",
        description="RETRIEVAL_TIERB_MODEL_ID: tier-B rerank (768 dim)",
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
