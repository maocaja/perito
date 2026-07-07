"""Configuración de Perito (U1 + U2)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config validada e inmutable (U1 + U2)."""

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    # U1 Fields (optional for testing)
    database_url: str = Field(default="postgresql://localhost:5432/perito_test")
    faker_locale: str = "es_CO"
    embedding_dim: int | None = Field(default=None, gt=0)
    langfuse_host: str | None = None

    # U2 LLM MODELS
    extractor_model: str = "claude-haiku-4-5"
    verifier_model: str = "claude-sonnet-5"

    # U2 LLM BEHAVIOR
    extractor_max_tokens: int = 2000
    verifier_max_tokens: int = 3000

    # U2 ORCHESTRATION (P4)
    confidence_threshold: float = 0.70
    max_rounds: int = 1
    max_tokens_budget: int = 10_000

    # U2 API
    anthropic_api_key: str = Field(default="")


# Initialize settings from environment
settings = Settings()
