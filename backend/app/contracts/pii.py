"""Marcador de PII + registro introspectable (PATTERN-U1-01, pieza 1-2).

Un campo PII se declara así:

    from typing import Annotated
    texto_crudo: Annotated[str, PII]

`pii_fields(Modelo)` devuelve los nombres de campos marcados PII, recorriendo
la metadata de los campos Pydantic. Es la **fuente única de verdad** de qué es
PII (P5 / Habeas Data). Los redactores deny-by-default (security/redaction.py)
consumen esta función.
"""

from typing import Any


class _PIIMarker:
    """Sentinela que marca un campo como PII (Habeas Data, P5)."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - cosmético
        return "PII"


#: Instancia única para usar en `Annotated[str, PII]`.
PII = _PIIMarker()


def pii_fields(model: type[Any]) -> frozenset[str]:
    """Nombres de campos marcados PII en un contrato Pydantic.

    Recorre `model.model_fields[*].metadata` buscando el sentinela PII.
    """
    fields = getattr(model, "model_fields", {})
    marked: set[str] = set()
    for name, field in fields.items():
        if any(isinstance(m, _PIIMarker) for m in getattr(field, "metadata", ())):
            marked.add(name)
    return frozenset(marked)
