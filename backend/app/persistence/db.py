"""Persistencia SQL (C1) — engine + tablas para casos y pólizas.

Gated por `settings.persistence`. El objeto Pydantic se guarda como JSON en una columna Text
(`model_dump_json()` / `model_validate_json()` — round-trip robusto con datetime-tz / Decimal /
enums; NO `model_dump`/`model_validate` sobre dicts). `model_validate_json` re-ejecuta los
validators → reconstruir un estado terminal exige `aprobado_por` (P1 intacto: no revive sin firma).

Funciona en Postgres (target real, TLS + cifrado en reposo = RNF-15) y en SQLite (tests). Sin
alembic: `create_all` al arranque (demo). Fail-closed: si el engine no conecta, la excepción
propaga (persistencia es requisito, a diferencia de la observabilidad fail-open).
"""

import logging
from typing import Optional

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, create_engine
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

metadata = MetaData()

casos_table = Table(
    "casos",
    metadata,
    Column("id", String, primary_key=True),
    Column("estado", String, nullable=False, index=True),
    Column("timestamp_actualizacion", DateTime(timezone=True), nullable=False),
    Column("data", Text, nullable=False),  # Caso.model_dump_json()
)

polizas_table = Table(
    "polizas",
    metadata,
    Column("numero", String, primary_key=True),
    Column("data", Text, nullable=False),  # Poliza.model_dump_json()
)

_engine: Optional[Engine] = None
_initialized_engines: set = set()


def get_engine() -> Engine:
    """Engine SQLAlchemy (singleton). Fail-closed: si no conecta, la excepción propaga."""
    global _engine
    if _engine is None:
        url = settings.database_url
        if url.startswith("postgresql") and "sslmode" not in url:
            logger.warning("database_url sin sslmode=require — TLS no garantizado (RNF-15).")
        _engine = create_engine(url)
    return _engine


def init_db(engine: Optional[Engine] = None) -> None:
    """Crea las tablas si no existen (create_all; sin alembic, demo). No-op si el engine ya se inicializó."""
    eng = engine or get_engine()
    if id(eng) in _initialized_engines:
        return
    metadata.create_all(eng)
    _initialized_engines.add(id(eng))


def reset_engine() -> None:
    """Resetea el engine cacheado + el registro de inicializados (para tests que cambian de DB)."""
    global _engine
    _engine = None
    _initialized_engines.clear()
