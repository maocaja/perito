"""Configuración de Perito (U1 + U2).

Los valores salen de (en orden de prioridad): variables de entorno del shell > archivo `.env` de
la RAÍZ del repo > defaults. El `.env` se resuelve por ruta absoluta (robusto al cwd: funciona con
`make` desde la raíz y con pytest desde `backend/`). Plantilla pública: `env.example` (`cp` → `.env`).
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py → app → backend → raíz del repo (parents[2]).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Config validada e inmutable (U1 + U2)."""

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="forbid")

    # U1 Fields (optional for testing)
    database_url: str = Field(default="postgresql://localhost:5432/perito_test")

    # Persistencia (C1) — "memory" (default: tests/demo in-memory) | "postgres" (real, gated).
    # Con "postgres" el database_url debe incluir sslmode=require (TLS, RNF-15).
    persistence: str = Field(default="memory")
    faker_locale: str = "es_CO"
    embedding_dim: int | None = Field(default=None, gt=0)

    # Observabilidad — Langfuse (B1, Must #10). Sin keys → sink desactivado (solo floor JSON).
    # Si se activan las keys, requiere el SDK: pip install "perito-backend[obs]" (o pip install langfuse).
    langfuse_host: str | None = None
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")

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

    # Demo en vivo — poller de Gmail (Unit H). `off` por default: el poller NUNCA arranca (cero
    # costo, sin key). `deterministic` = presets sin LLM (ensayo gratis). `real` = pipeline real
    # (agentes Claude; requiere anthropic_api_key). Control de costo = riesgo #2 del PRD.
    demo_live: Literal["off", "deterministic", "real"] = Field(default="off")
    demo_gmail_address: str = Field(default="")       # SECRETO (buzón demo dedicado)
    demo_gmail_app_password: str = Field(default="")  # SECRETO (app-password de Gmail)
    imap_host: str = Field(default="imap.gmail.com")
    smtp_host: str = Field(default="smtp.gmail.com")
    poll_interval_s: int = Field(default=5, gt=0)     # segundos entre ciclos de lectura IMAP
    mail_total: int = Field(default=15, gt=0)         # tope de correos que envía el generador

    @field_validator("demo_live", mode="before")
    @classmethod
    def _normaliza_demo_live(cls, v):
        """Acepta variantes de shell (mayúsculas/espacios). Fail-closed a `off` si viene vacío."""
        s = str(v).strip().lower()
        return s or "off"

    @field_validator("demo_gmail_app_password", mode="before")
    @classmethod
    def _limpia_app_password(cls, v):
        """Google muestra la app-password en grupos con espacios; IMAP la necesita SIN espacios (16 chars)."""
        return str(v).replace(" ", "") if v else ""


# Initialize settings from environment
settings = Settings()

