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

import re
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Protocol, runtime_checkable

from app.config import settings
from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso

# NOTA: sqlalchemy se importa LAZY (dentro de SqlCasoRepository / persistence.db) para que el
# módulo y la impl in-memory (default) funcionen sin sqlalchemy instalado. Solo el path SQL lo requiere.

# Código de siniestro: SIN-<año>-<NNNN>. El número (NNNN) es el consecutivo ÚNICO; el año es legibilidad.
_PATRON_CONSECUTIVO = re.compile(r"SIN-\d{4}-(\d+)$")


def _max_consecutivo(ids: Iterable[str]) -> int:
    """Mayor consecutivo entre unos ids `SIN-AÑO-NNNN` (0 si no hay ninguno). Ignora ids provisionales."""
    return max((int(m.group(1)) for m in (_PATRON_CONSECUTIVO.search(i) for i in ids) if m), default=0)


def _codigo_siniestro(consecutivo: int) -> str:
    return f"SIN-{datetime.now(timezone.utc).year}-{consecutivo:04d}"


@runtime_checkable
class CasoRepository(Protocol):
    """Interfaz de persistencia de casos (save/get/list/clear + reservar_codigo)."""
    def save(self, caso: Caso) -> Caso: ...
    def get(self, caso_id: str) -> Optional[Caso]: ...
    def list(self, estado: Optional[EstadoCaso] = None, limite: Optional[int] = None) -> list[Caso]: ...
    def clear(self) -> None: ...
    def reservar_codigo(self) -> str: ...


class InMemoryCasoRepository:
    """Store in-memory (demo/tests). Orden estable por timestamp desc."""

    def __init__(self) -> None:
        self._casos: dict[str, Caso] = {}
        self._lock = threading.Lock()   # el poller crea casos en un hilo aparte del request
        self._consecutivo = 0           # alto de marca de la secuencia de siniestros

    def reservar_codigo(self) -> str:
        """Código de siniestro consecutivo y ÚNICO (`SIN-AÑO-NNNN`). El store es la fuente de la secuencia.
        Reinicia con `clear()` → reseed limpio desde 0001. In-memory no sobrevive al reinicio, pero el store
        también arranca vacío, así que no hay colisión (el dataset es nuevo)."""
        with self._lock:
            self._consecutivo += 1
            return _codigo_siniestro(self._consecutivo)

    def save(self, caso: Caso) -> Caso:
        with self._lock:
            self._casos[caso.id] = caso
        return caso

    def get(self, caso_id: str) -> Optional[Caso]:
        return self._casos.get(caso_id)

    def list(self, estado: Optional[EstadoCaso] = None, limite: Optional[int] = None) -> list[Caso]:
        casos = list(self._casos.values())
        if estado is not None:
            casos = [c for c in casos if c.estado == estado]
        casos = sorted(casos, key=lambda c: c.timestamp_actualizacion, reverse=True)
        return casos[:limite] if limite is not None else casos

    def clear(self) -> None:
        with self._lock:
            self._casos.clear()
            self._consecutivo = 0


class SqlCasoRepository:
    """Store SQL (Postgres real o SQLite en tests). JSON del Caso en columna Text."""

    def __init__(self, engine: Any) -> None:
        from app.persistence.db import init_db
        self.engine = engine
        init_db(engine)
        self._lock = threading.Lock()
        self._consecutivo = self._max_persistido()  # arranca del máximo ya guardado → durable, sin colisión

    def _max_persistido(self) -> int:
        """Mayor consecutivo ya persistido (para continuar la secuencia tras un reinicio)."""
        from sqlalchemy import select
        from app.persistence.db import casos_table
        with self.engine.connect() as conn:
            ids = [r[0] for r in conn.execute(select(casos_table.c.id)).all()]
        return _max_consecutivo(ids)

    def reservar_codigo(self) -> str:
        """Código de siniestro consecutivo y ÚNICO. Continúa desde el máximo persistido → tras un reinicio
        NO reusa un código ya guardado. ⚠️ Gap declarado (P7): a escala/concurrencia real esto debe ser una
        SEQUENCE de la BD (aquí un alto de marca en memoria inicializado del máximo, suficiente para un
        único escritor)."""
        with self._lock:
            self._consecutivo += 1
            return _codigo_siniestro(self._consecutivo)

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

    def list(self, estado: Optional[EstadoCaso] = None, limite: Optional[int] = None) -> list[Caso]:
        from sqlalchemy import select
        from app.persistence.db import casos_table
        stmt = select(casos_table.c.data).order_by(casos_table.c.timestamp_actualizacion.desc())
        if estado is not None:
            stmt = stmt.where(casos_table.c.estado == estado.value)
        if limite is not None:
            stmt = stmt.limit(limite)  # P4: cota de carga a nivel DB (LIMIT SQL)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [Caso.model_validate_json(r[0]) for r in rows]

    def clear(self) -> None:
        from sqlalchemy import delete
        from app.persistence.db import casos_table
        with self.engine.begin() as conn:
            conn.execute(delete(casos_table))
        with self._lock:
            self._consecutivo = 0


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


def con_codigo_de_siniestro(caso: Caso) -> Caso:
    """Asigna a un caso RECIÉN creado su código de siniestro definitivo (consecutivo del store).

    Se llama al crear el caso —antes de procesarlo— para que su `id` sea estable durante huellas, traza y
    persistencia. Usa el repositorio activo como fuente de la secuencia."""
    return caso.model_copy(update={"id": get_caso_repository().reservar_codigo()})
