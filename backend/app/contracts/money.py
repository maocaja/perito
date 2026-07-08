"""Tipo monetario `Money`: acepta `Decimal` y `str`, RECHAZA `float`.

Motivo: en modo `strict`, Pydantic v2 rechaza TANTO `float` como `str` para
`Decimal`. Para dinero queremos:
  - **rechazar `float`** (imprecisión de coma flotante rompería `deducible ≥ 0`),
  - **aceptar `str`** (representación segura; necesaria para el round-trip JSON,
    donde `Decimal` se serializa como `str`: Decimal→str→Decimal).

Un `BeforeValidator` coacciona `str`→`Decimal` y rechaza `float` ANTES de la
validación strict. `int`/`bool` también se rechazan (dinero se tipa explícito).
"""

from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BeforeValidator, Field


def _coerce_money(v: object) -> object:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, str):
        try:
            return Decimal(v)
        except InvalidOperation as exc:
            raise ValueError(f"monto str inválido: {v!r}") from exc
    raise ValueError(
        f"monto debe ser Decimal o str, no {type(v).__name__} "
        "(float/int prohibidos: float rompe la precisión de dinero)"
    )


#: Monto ≥ 0. Acepta `Decimal | str`; rechaza `float`, `int`, `bool`.
Money = Annotated[Decimal, BeforeValidator(_coerce_money), Field(ge=0)]
