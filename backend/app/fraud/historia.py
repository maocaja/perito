"""app/fraud/historia.py — historia + consultas cross-claim (U5). Base del fraude cross-claim (U6).

Determinístico, sin LLM. Consulta sobre el `CasoRepository` (C1). Devuelve FOOTPRINTS (caso_id, póliza,
fecha), NUNCA el `Caso` con PII (P5). Todas las consultas llevan **cota dura** (`limite`) — P4.
Requiere `PERSISTENCE=postgres` para historia real; con `memory` la historia = la sesión (degrada).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Cotas duras (P4): ninguna consulta devuelve/carga sin límite.
LIMITE_CONSULTA = 500
CARGA_MAX = 5000  # tope de carga desde el repo (bound del escaneo; ver nota de eficiencia abajo)

# NOTA DE EFICIENCIA / DEUDA (declarada, P7): el `Caso` se persiste como JSON blob (C1), así que filtrar por
# póliza/entidad NO puede hacerse con WHERE indexado hoy — se carga (acotado a CARGA_MAX) y se filtra en Python.
# Consultas eficientes reales requieren columnas indexadas (póliza/asegurado/entidad) en C1 → unidad futura.


@dataclass(frozen=True)
class Footprint:
    """Huella mínima de un caso para análisis cross-claim. SIN PII (P5): no incluye texto_crudo ni campos.

    `asegurado_id`/`entidad`/`hash` quedan en el contrato para U6, pero hoy son None: dependen de la
    extracción rica (asegurado/placa) de U4 y del índice de huellas — se poblarán cuando existan (P7).
    """
    caso_id: str
    numero_poliza: Optional[str]
    fecha_actualizacion: datetime
    asegurado_id: Optional[str] = None   # pendiente: extracción de asegurado (U4/unidad futura)
    entidad: Optional[str] = None        # pendiente: placa/tercero (U4 extracción rica)
    hash: Optional[str] = None           # pendiente: huella de media (U4 multimodal → U5 store)


def _numero_poliza(caso) -> Optional[str]:
    if not caso.extraccion:
        return None
    for c in caso.extraccion.campos:
        if c.nombre == "numero_poliza" and not c.ausente:
            return c.valor
    return None


def _footprint(caso) -> Footprint:
    return Footprint(caso_id=caso.id, numero_poliza=_numero_poliza(caso),
                     fecha_actualizacion=caso.timestamp_actualizacion)


def casos_por_poliza(repo, numero_poliza: str, ventana_dias: int = 365,
                     limite: int = LIMITE_CONSULTA, excluir_id: Optional[str] = None) -> list[Footprint]:
    """Footprints de casos de la MISMA póliza dentro de la ventana (para frecuencia). Cota dura (P4)."""
    if not numero_poliza:
        return []
    desde = datetime.now(timezone.utc) - timedelta(days=ventana_dias)
    out: list[Footprint] = []
    for c in repo.list(limite=CARGA_MAX):  # P4: carga acotada (además de la cota del resultado)
        if len(out) >= limite:
            break
        if c.id == excluir_id:
            continue
        if _numero_poliza(c) == numero_poliza and c.timestamp_actualizacion >= desde:
            out.append(_footprint(c))
    return out


def casos_por_entidad(repo, entidad: str, limite: int = LIMITE_CONSULTA) -> list[Footprint]:
    """Casos que comparten una entidad (placa/tercero/taller). Cota dura (P4).

    HOY devuelve [] siempre: la entidad (placa/tercero) requiere la extracción rica de U4, aún no disponible
    (P7: no se inventa). El contrato queda listo para U6 cuando la extracción exista.
    """
    return []


# ------------------------------------------------ Índice de huellas perceptuales (media) ------------

def _hamming_hex(h1: str, h2: str) -> int:
    """Distancia de Hamming entre dos hashes hex (bits distintos). Determinístico. inf si inválido/distinta long."""
    if not h1 or not h2 or len(h1) != len(h2):
        return 10**9
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except ValueError:  # no es hex válido → tratar como no-coincidencia (fail-closed)
        return 10**9


class HuellaStore:
    """Índice `hash_perceptual → caso_id` (P5: guarda la HUELLA, no la imagen). In-memory (demo/tests).

    En producción sería una tabla `hash_perceptual (hash_value, caso_id)` sobre C1 (misma interfaz).
    """

    def __init__(self) -> None:
        self._huellas: list[tuple[str, str]] = []  # (hash_hex, caso_id)
        if settings.persistence != "postgres":  # sin C1, la historia = la sesión (degrada, avisa — P7)
            logger.warning("HuellaStore in-memory (PERSISTENCE=%s); sin Postgres la historia no persiste.",
                           settings.persistence)

    def registrar(self, hash_hex: str, caso_id: str) -> None:
        self._huellas.append((hash_hex, caso_id))

    def buscar(self, hash_hex: str, distancia_max: int = 3,
               excluir_id: Optional[str] = None, limite: int = LIMITE_CONSULTA) -> list[tuple[str, int]]:
        """Casos con una huella a distancia ≤ `distancia_max` (foto reutilizada). Devuelve (caso_id, distancia)."""
        out: list[tuple[str, int]] = []
        for h, cid in self._huellas:
            if len(out) >= limite:  # P4
                break
            if cid == excluir_id:
                continue
            d = _hamming_hex(hash_hex, h)
            if d <= distancia_max:
                out.append((cid, d))
        return sorted(out, key=lambda x: x[1])

    def clear(self) -> None:
        self._huellas.clear()
