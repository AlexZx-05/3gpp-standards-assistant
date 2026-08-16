from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str | None = None
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "three_gpp_chunks"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    ingestion_batch_size: int = Field(default=32, ge=1, le=128)
    top_k_dense: int = Field(default=20, ge=1, le=50)
    top_k_bm25: int = Field(default=20, ge=1, le=50)
    top_k_rerank: int = Field(default=5, ge=1, le=10)
    min_evidence_count: int = Field(default=1, ge=1)
    min_rerank_score: float = Field(default=0.15)
    request_max_question_length: int = Field(default=1000, ge=50, le=5000)

    @field_validator("llm_api_key", "qdrant_api_key", mode="before")
    @classmethod
    def normalize_optional_secrets(cls, value: str | None) -> str | None:
        """Avoid invisible whitespace or empty strings being passed as credentials."""
        if value is None:
            return None
        value = value.strip()
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
