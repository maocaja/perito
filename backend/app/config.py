"""Configuración de Perito (U1).

Se lee de variables de entorno (dev local). Sin `pydantic-settings` para no
introducir deps nuevas: un `BaseModel` estricto + un cargador desde `os.environ`.

Variables de entorno (copiar a un `.env` local, que está en .gitignore):
    DATABASE_URL   postgresql://perito_dev:<pwd>@localhost:5432/perito
    EMBEDDING_DIM  (opcional) dimensión del vector pgvector — SIN fijar en U1
                   (PATTERN-U1-03: se confirma al elegir el embedding en U2/U3)
    FAKER_LOCALE   es_CO
    LANGFUSE_HOST  (opcional) — observabilidad diferida a U5

SECURITY-09/12: sin default credentials — DATABASE_URL debe venir del entorno.
"""

import os

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Config validada e inmutable."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    database_url: str = Field(min_length=1)
    faker_locale: str = "es_CO"
    # PATTERN-U1-03: la dimensión NO se hardcodea ni se pre-compromete a un modelo.
    # Queda como parámetro; se fija al confirmar el embedding local en U2/U3.
    # None en U1 = "aún no fijada" (el esquema RAG la recibe como argumento explícito).
    embedding_dim: int | None = Field(default=None, gt=0)
    langfuse_host: str | None = None


def load_settings() -> Settings:
    """Construye Settings desde el entorno. Falla si DATABASE_URL no está (fail-closed)."""
    dim = os.getenv("EMBEDDING_DIM")
    return Settings(
        database_url=os.environ["DATABASE_URL"],  # KeyError si falta — no hay default de credenciales
        faker_locale=os.getenv("FAKER_LOCALE", "es_CO"),
        embedding_dim=int(dim) if dim else None,
        langfuse_host=os.getenv("LANGFUSE_HOST") or None,
    )
