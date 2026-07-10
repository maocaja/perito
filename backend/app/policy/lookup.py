"""
app/policy/lookup.py — C4 Policy Lookup / Grounding (deterministic)

Deterministic policy matching: given numero_poliza from extraction,
return exact match or similarity-based candidates without LLM involvement.

INVARIANTS:
- P4 (no forzar match): encontrada=False ⇒ poliza=None, candidatas allowed
- P2-adjacent (cero LLM): SQL deterministic, zero anthropic imports
- RULE-CTR-07: ResultadoPoliza validator enforces encontrada=False ⇒ poliza=None
"""

import logging
from typing import Optional
from difflib import SequenceMatcher

from app.config import settings
from app.contracts.extraccion import ExtraccionValidada
from app.contracts.poliza import Poliza, ResultadoPoliza


logger = logging.getLogger(__name__)


class PolicyLookupError(Exception):
    """Raised if policy lookup fails (fail-closed)."""
    pass


# Mock in-memory Poliza store for testing/demo.
# In production, this would be a real Postgres query.
_POLIZA_STORE: dict[str, Poliza] = {}


def set_poliza_store(store: dict[str, Poliza]) -> None:
    """Setea el repositorio de pólizas. En 'memory' → dict; en 'postgres' → tabla polizas."""
    global _POLIZA_STORE
    if settings.persistence == "postgres":
        from sqlalchemy import delete, insert
        from app.persistence.db import get_engine, init_db, polizas_table
        eng = get_engine()
        init_db(eng)
        with eng.begin() as conn:
            conn.execute(delete(polizas_table))
            for numero, p in store.items():
                conn.execute(insert(polizas_table).values(numero=numero, data=p.model_dump_json()))
    else:
        _POLIZA_STORE = store


def _polizas_source() -> dict[str, Poliza]:
    """Fuente activa de pólizas (memoria o Postgres, según settings.persistence). Lógica de lookup intacta."""
    if settings.persistence == "postgres":
        from sqlalchemy import select
        from app.persistence.db import get_engine, init_db, polizas_table
        eng = get_engine()
        init_db(eng)
        with eng.connect() as conn:
            rows = conn.execute(select(polizas_table.c.data)).all()
        return {p.numero: p for p in (Poliza.model_validate_json(r[0]) for r in rows)}
    return _POLIZA_STORE


def call_c4_policy_lookup(extraccion: ExtraccionValidada) -> ResultadoPoliza:
    """
    C4 Policy Lookup: Extract numero_poliza from ExtraccionValidada,
    search for exact match or candidates.

    CRITICAL TRAP COMPLIANCE:
    1. Cero LLM — pure SQL/dict logic, zero anthropic imports
    2. .campos access — read numero_poliza via .campos iteration, not flat attribute
    3. No forzar match — candidatas ≠ poliza; RULE-CTR-07 enforced by Pydantic
    4. Mock BD testable — no real Postgres in unit tests

    Args:
        extraccion: ExtraccionValidada from C2 (contains .campos)

    Returns:
        ResultadoPoliza(encontrada=True, poliza=<obj>) or
        ResultadoPoliza(encontrada=False, poliza=None, candidatas=[...])

    Raises:
        PolicyLookupError: if lookup logic fails (fail-closed)
    """
    try:
        # Step 1: Extract numero_poliza via .campos (Trap 2)
        numero_poliza = next(
            (c.valor for c in extraccion.campos
             if c.nombre == "numero_poliza" and not c.ausente),
            None
        )

        # Step 2: Exact match por número (camino principal)
        if numero_poliza:
            poliza_exacta = _lookup_exact(numero_poliza)
            if poliza_exacta is not None:
                logger.info(f"Policy lookup: exact match for {numero_poliza}")
                return ResultadoPoliza(encontrada=True, poliza=poliza_exacta)

        # Step 3: FALLBACK U8 — sin número o sin match exacto → buscar por claves alternativas
        # (placa → cédula → nombre). Determinístico; ambigüedad → escala (no fuerza match, P4).
        resultado_alt = _lookup_por_claves_alternativas(extraccion)
        if resultado_alt is not None:
            return resultado_alt

        # Step 4: Sin número y sin claves alternativas útiles → candidatas por similitud del número
        # (si lo había) o vacío. NUNCA promueve candidata a match (Trap 3 / P4).
        candidatas = _lookup_candidates(numero_poliza, limit=5) if numero_poliza else []
        logger.info("Policy lookup: sin match exacto ni por claves; %d candidatas.", len(candidatas))
        return ResultadoPoliza(encontrada=False, poliza=None, candidatas=candidatas)

    except PolicyLookupError as e:
        logger.error(f"Policy lookup error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Policy lookup unexpected error: {str(e)}")
        raise PolicyLookupError(f"Lookup failed: {str(e)}") from e


# ------------------------------------------------------------------ U8 entity resolution (fallback)

def _norm_id(valor: Optional[str]) -> str:
    """Normaliza placa/cédula: conserva SOLO alfanuméricos, en mayúscula.

    'ABC-123' == 'abc123'; '1.020.3' == '10203'. Nota: `str.isalnum()` es unicode-aware, así que letras
    acentuadas/no-ASCII se conservan (no se transliteran) — placa/cédula colombianas son ASCII en la
    práctica, así que no hay sobre-normalización relevante. Ante cualquier duda de igualdad, P4 protege:
    la ambigüedad (>1 match) escala, nunca fuerza."""
    return "".join(ch for ch in (valor or "") if ch.isalnum()).upper()


def _norm_nombre(valor: Optional[str]) -> str:
    """Normaliza nombre: casefold + colapsa espacios (match exacto/normalizado; difuso queda fuera, U8 §4)."""
    return " ".join((valor or "").split()).casefold()


def _campo_alt(extraccion: ExtraccionValidada, *nombres: str) -> Optional[str]:
    """Lee la primera clave alternativa presente en la extracción (acepta alias)."""
    for c in extraccion.campos:
        if c.nombre in nombres and not c.ausente and c.valor:
            return c.valor
    return None


def _lookup_por_claves_alternativas(extraccion: ExtraccionValidada) -> Optional["ResultadoPoliza"]:
    """FALLBACK U8: resuelve por placa → cédula → nombre cuando no hay número/no hizo match.

    Determinístico. Reglas (P4, no forzar):
    - Clave FUERTE (placa/cédula) con **1** match normalizado → resuelve (encontrada=True).
    - Clave fuerte con **>1** match → candidatas (ambigüedad → escala).
    - Nombre: NUNCA auto-resuelve (no es único) → siempre candidatas (escala a confirmación humana).
    Devuelve None SOLO si no hay ninguna clave alternativa (el caller sigue con la similitud del número).
    """
    # Nombre canónico del campo en la extracción = el primero de cada tupla; los siguientes son alias
    # tolerados (U4 aún no fija el esquema rico — cuando lo haga, canonizar a: placa / cedula / nombre_asegurado).
    placa = _campo_alt(extraccion, "placa")
    cedula = _campo_alt(extraccion, "cedula", "asegurado_cedula", "cédula")
    nombre = _campo_alt(extraccion, "nombre_asegurado", "asegurado_nombre", "nombre")
    if not (placa or cedula or nombre):
        return None  # sin claves alternativas → no aplica el fallback

    polizas = list(_polizas_source().values())

    # Claves fuertes (identificadores únicos): placa, luego cédula.
    for valor, atributo in ((placa, "placa"), (cedula, "asegurado_cedula")):
        objetivo = _norm_id(valor)
        if not objetivo:
            continue
        matches = [p for p in polizas if _norm_id(getattr(p, atributo, None)) == objetivo]
        if len(matches) == 1:
            logger.info("Policy lookup: resuelto por clave alternativa '%s' (1 match).", atributo)
            return ResultadoPoliza(encontrada=True, poliza=matches[0])
        if len(matches) > 1:
            logger.info("Policy lookup: '%s' ambiguo (%d) → candidatas, escala (P4).", atributo, len(matches))
            return ResultadoPoliza(encontrada=False, poliza=None, candidatas=matches[:5])

    # Nombre: identificador débil → siempre candidatas (nunca fuerza un match).
    objetivo = _norm_nombre(nombre)
    if objetivo:
        matches = [p for p in polizas if _norm_nombre(getattr(p, "asegurado_nombre", None)) == objetivo]
        logger.info("Policy lookup: nombre → %d candidata(s), escala (no único, P4).", len(matches))
        return ResultadoPoliza(encontrada=False, poliza=None, candidatas=matches[:5])

    # Había claves pero ninguna produjo match → escala (ninguna encontrada), no inventa.
    return ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])


def _lookup_exact(numero_poliza: str) -> Optional[Poliza]:
    """
    Exact match by numero_poliza (Trap 1: deterministic, no LLM).

    In production, replace with:
        SELECT * FROM polizas WHERE numero = %s LIMIT 1
    """
    return _polizas_source().get(numero_poliza)


def _lookup_candidates(numero_poliza: str, limit: int = 5) -> list[Poliza]:
    """
    Similarity-based candidates using difflib (stdlib, no new deps — watch-item 1).

    Deterministic similarity score: SequenceMatcher ratio.
    Returns sorted list, but does NOT promote any to poliza= (Trap 3).
    """
    polizas = _polizas_source()
    if not numero_poliza or not polizas:
        return []

    # Calculate similarity scores
    scored = []
    for stored_numero, poliza in polizas.items():
        ratio = SequenceMatcher(None, numero_poliza, stored_numero).ratio()
        if ratio > 0.6:  # Threshold for relevance
            scored.append((ratio, poliza))

    # Sort by score descending, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [poliza for _, poliza in scored[:limit]]
