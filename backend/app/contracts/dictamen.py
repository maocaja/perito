"""Contratos de dictamen y fraude: Dictamen, AlertaFraude, Cotas."""

from pydantic import Field

from app.contracts import Contract
from app.contracts.enums import ResultadoCobertura
from app.contracts.extraccion import EvidenciaOrigen
from app.contracts.money import Money
from app.contracts.poliza import Clausula


class Dictamen(Contract):
    """Dictamen de cobertura. El cálculo (R1-R5) es U3; el contrato es U1.

    RULE-CTR-03: `clausula` es OBLIGATORIA (campo no opcional) — un dictamen
    sin cláusula es inválido (H-08 🔒, P2/P3).
    RULE-CTR-04: `deducible_calculado` ≥ 0 (Decimal, no float).
    """

    resultado: ResultadoCobertura
    regla_aplicada: str = Field(min_length=1)  # "R1".."R5"
    clausula: Clausula
    deducible_calculado: Money


class AlertaFraude(Contract):
    """Alerta de fraude explicable (P6). El razonamiento es U3; el contrato es U1.

    Evidencia OBLIGATORIA: `inconsistencias` no vacío (H-09 🔒). Una alerta sin
    evidencia es inválida. No produce transición de estado (P1).
    """

    severidad: str = Field(min_length=1)
    inconsistencias: list[EvidenciaOrigen] = Field(min_length=1)
    explicacion: str = Field(min_length=1)


class Cotas(Contract):
    """Caps duros de terminación acotada (P4). Se usan en U4."""

    max_rondas: int = Field(gt=0)
    presupuesto_tokens: int = Field(gt=0)

# Rebuild Pydantic models to resolve forward references
Dictamen.model_rebuild()
