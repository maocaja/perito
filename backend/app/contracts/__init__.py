"""Contratos compartidos de Perito (U1 · H-17).

Todos los contratos son la fundación tipada de la que dependen U2-U5.
Base común: `Contract` (Pydantic strict + extra prohibido = fail-closed, PATTERN-U1-02).
"""

from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    """Base de todos los contratos.

    - strict=True: sin coerción silenciosa (float NO se acepta donde se espera Decimal/int).
    - extra="forbid": un campo desconocido ⇒ ValidationError (rechazo).
    Realiza PATTERN-U1-02 / NFR-U1-02 / RULE-CTR-02 (fail-closed) por construcción.
    """

    model_config = ConfigDict(strict=True, extra="forbid")
