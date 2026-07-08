"""CasoRepository — persistencia de Casos (C1).

Dos implementaciones detrás de la MISMA interfaz (Protocol): `InMemoryCasoRepository` (default,
tests/demo) y `SqlCasoRepository` (Postgres real, o SQLite en tests). La factory
`get_caso_repository()` elige según `settings.persistence`. Los callers (dashboard, ingesta,
seeder) no cambian.

El store es PASIVO (P1): persiste la instancia `Caso` que produjo HITL (`model_validate`), NO muta
`estado`. En SQL, el Caso se guarda como JSON (`model_dump_json`) y se reconstruye con
`model_validate_json` — que re-ejecuta los validators (un terminal exige `aprobado_por`: no se
revive un APROBADO sin firma desde la DB).
"""

from typing import Any, Optional, Protocol, runtime_checkable

from app.config import settings
from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso

# NOTA: sqlalchemy se importa LAZY (dentro de SqlCasoRepository / persistence.db) para que el
# módulo y la impl in-memory (default) funcionen sin sqlalchemy instalado. Solo el path SQL lo requiere.


@runtime_checkable
class CasoRepository(Protocol):
    """Interfaz de persistencia de casos (save/get/list/clear)."""
    def save(self, caso: Caso) -> Caso: ...
    def get(self, caso_id: str) -> Optional[Caso]: ...
    def list(self, estado: Optional[EstadoCaso] = None) -> list[Caso]: ...
    def clear(self) -> None: ...


class InMemoryCasoRepository:
    """Store in-memory (demo/tests). Orden estable por timestamp desc."""

    def __init__(self) -> None:
        self._casos: dict[str, Caso] = {}

    def save(self, caso: Caso) -> Caso:
        self._casos[caso.id] = caso
        return caso

    def get(self, caso_id: str) -> Optional[Caso]:
        return self._casos.get(caso_id)

    def list(self, estado: Optional[EstadoCaso] = None) -> list[Caso]:
        casos = list(self._casos.values())
        if estado is not None:
            casos = [c for c in casos if c.estado == estado]
        return sorted(casos, key=lambda c: c.timestamp_actualizacion, reverse=True)

    def clear(self) -> None:
        self._casos.clear()


class SqlCasoRepository:
    """Store SQL (Postgres real o SQLite en tests). JSON del Caso en columna Text."""

    def __init__(self, engine: Any) -> None:
        from app.persistence.db import init_db
        self.engine = engine
        init_db(engine)

    def save(self, caso: Caso) -> Caso:
        from sqlalchemy import delete, insert
        from app.persistence.db import casos_table
        with self.engine.begin() as conn:
            conn.execute(delete(casos_table).where(casos_table.c.id == caso.id))
            conn.execute(insert(casos_table).values(
                id=caso.id,
                estado=caso.estado.value,
                timestamp_actualizacion=caso.timestamp_actualizacion,
                data=caso.model_dump_json(),
            ))
        return caso

    def get(self, caso_id: str) -> Optional[Caso]:
        from sqlalchemy import select
        from app.persistence.db import casos_table
        with self.engine.connect() as conn:
            row = conn.execute(
                select(casos_table.c.data).where(casos_table.c.id == caso_id)
            ).first()
        return Caso.model_validate_json(row[0]) if row else None

    def list(self, estado: Optional[EstadoCaso] = None) -> list[Caso]:
        from sqlalchemy import select
        from app.persistence.db import casos_table
        stmt = select(casos_table.c.data).order_by(casos_table.c.timestamp_actualizacion.desc())
        if estado is not None:
            stmt = stmt.where(casos_table.c.estado == estado.value)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [Caso.model_validate_json(r[0]) for r in rows]

    def clear(self) -> None:
        from sqlalchemy import delete
        from app.persistence.db import casos_table
        with self.engine.begin() as conn:
            conn.execute(delete(casos_table))


_repo: Optional[CasoRepository] = None


def get_caso_repository() -> CasoRepository:
    """Factory cacheada: elige la impl según `settings.persistence`."""
    global _repo
    if _repo is None:
        if settings.persistence == "postgres":
            from app.persistence.db import get_engine
            _repo = SqlCasoRepository(get_engine())
        else:
            _repo = InMemoryCasoRepository()
    return _repo


def reset_caso_repository() -> None:
    """Resetea el singleton (para tests que cambian de backend)."""
    global _repo
    _repo = None
