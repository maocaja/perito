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

        # Step 2: Handle missing/None numero_poliza (watch-item 2)
        if not numero_poliza:
            logger.info("Policy lookup: numero_poliza ausente/None → encontrada=False")
            return ResultadoPoliza(
                encontrada=False,
                poliza=None,
                candidatas=[]
            )

        # Step 3: Exact match (deterministic SQL simulation)
        poliza_exacta = _lookup_exact(numero_poliza)
        if poliza_exacta is not None:
            logger.info(f"Policy lookup: exact match for {numero_poliza}")
            return ResultadoPoliza(
                encontrada=True,
                poliza=poliza_exacta
            )

        # Step 4: No exact match → candidates by similarity (Trap 3: no forzar)
        candidatas = _lookup_candidates(numero_poliza, limit=5)
        logger.info(f"Policy lookup: no exact match, {len(candidatas)} candidates for {numero_poliza}")

        resultado = ResultadoPoliza(
            encontrada=False,
            poliza=None,  # NEVER promote candidate to poliza (Trap 3)
            candidatas=candidatas
        )

        # Step 5: Validate output against RULE-CTR-07 (Pydantic enforces)
        return resultado

    except PolicyLookupError as e:
        logger.error(f"Policy lookup error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Policy lookup unexpected error: {str(e)}")
        raise PolicyLookupError(f"Lookup failed: {str(e)}") from e


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
