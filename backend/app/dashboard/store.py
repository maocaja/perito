"""CasoRepository — store in-memory de Casos para el dashboard (MVP).

NO es persistencia real (demo-grade, RNF persistencia diferida; Postgres del
compose queda para después). Patrón singleton como `get_replay_store()`.

El dashboard LEE de aquí (bandeja/detalle) y, tras una acción HITL, re-guarda
el Caso NUEVO que devuelve `hitl.aprobar/rechazar` (que usa model_validate).
El store NO muta estado — solo persiste la instancia que HITL produjo.
"""

from typing import Optional

from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso


class CasoRepository:
    """Store in-memory de Casos, indexado por id."""

    def __init__(self) -> None:
        self._casos: dict[str, Caso] = {}

    def save(self, caso: Caso) -> Caso:
        """Guarda (o reemplaza) el caso por su id. Devuelve el caso guardado."""
        self._casos[caso.id] = caso
        return caso

    def get(self, caso_id: str) -> Optional[Caso]:
        return self._casos.get(caso_id)

    def list(self, estado: Optional[EstadoCaso] = None) -> list[Caso]:
        """Lista los casos, filtrando por estado si se indica.

        Orden estable: por timestamp_actualizacion descendente (más reciente arriba).
        """
        casos = list(self._casos.values())
        if estado is not None:
            casos = [c for c in casos if c.estado == estado]
        return sorted(casos, key=lambda c: c.timestamp_actualizacion, reverse=True)

    def clear(self) -> None:
        """Vacía el store (útil en tests/seed)."""
        self._casos.clear()


_repo: Optional[CasoRepository] = None


def get_caso_repository() -> CasoRepository:
    """Singleton del repositorio de casos."""
    global _repo
    if _repo is None:
        _repo = CasoRepository()
    return _repo
