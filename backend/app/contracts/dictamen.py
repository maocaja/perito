"""Contratos de dictamen y fraude: Dictamen, AlertaFraude, Cotas."""

from pydantic import Field, model_validator

from app.contracts import Contract
from app.contracts.enums import ResultadoCobertura
from app.contracts.extraccion import EvidenciaOrigen
from app.contracts.money import Money
from app.contracts.poliza import Clausula


class Dictamen(Contract):
    """Dictamen de cobertura. El cálculo (R1-R5) es U3; el contrato es U1.

    RULE-CTR-03: `clausula` es OBLIGATORIA para resultados terminales
    (CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO) — un dictamen terminal
    sin cláusula es inválido (H-08 🔒, P2/P3).
    
    Para REQUIERE_REVISION (escalamiento), clausula puede ser None
    (no hay cláusula porque pre-validación falló o póliza incompleta).
    
    RULE-CTR-04: `deducible_calculado` ≥ 0 (Decimal, no float).
    """

    resultado: ResultadoCobertura
    regla_aplicada: str = Field(min_length=1)  # "R1".."R5", "PRE_MOTOR"
    clausula: Clausula | None = None  # None solo si REQUIERE_REVISION (validado)
    deducible_calculado: Money
    # --- U3 product-aware (aditivo, opcional): cita la cobertura específica aplicada ---
    cobertura_aplicada: str | None = None   # nombre de la cobertura del producto
    sublimite_aplicado: Money | None = None  # el sublímite efectivo usado en R4

    @model_validator(mode="after")
    def _clausula_obligatoria_en_terminal(self) -> "Dictamen":
        """RULE-CTR-03: Resultados terminales exigen cláusula citada (P2/P3 auditabilidad)."""
        terminales = {
            ResultadoCobertura.CUBIERTO,
            ResultadoCobertura.CUBIERTO_PARCIAL,
            ResultadoCobertura.NO_CUBIERTO
        }
        if self.resultado in terminales and self.clausula is None:
            raise ValueError(
                f"RULE-CTR-03: resultado terminal '{self.resultado}' exige clausula no-nula "
                "(P2/P3 auditabilidad: todo dictamen terminal cita la regla y cláusula)"
            )
        return self


class AlertaFraude(Contract):
    """Alerta de fraude explicable (P6). El razonamiento es U3; el contrato es U1.

    Evidencia OBLIGATORIA: `inconsistencias` no vacío (H-09 🔒). Una alerta sin
    evidencia es inválida. No produce transición de estado (P1).
    """

    severidad: str = Field(min_length=1)
    inconsistencias: list[EvidenciaOrigen] = Field(min_length=1)
    explicacion: str = Field(min_length=1)
    # --- U6 cross-claim (aditivo): toda señal lleva confianza; un falso positivo es
    # sugerencia con confianza, NUNCA verdad (P7). `lt=1.0` cierra la puerta: ninguna señal —
    # ni el chequeo duro intra-caso, ni la foto idéntica — es veredicto absoluto (spec U6 §7).
    # Default 0.99 (capas 1-2): señal fuerte de un hecho cierto, pero sigue siendo sugerencia (P6/P7).
    confianza: float = Field(default=0.99, ge=0.0, lt=1.0)
    capa: int = Field(default=1, ge=1, le=4)  # 1-2 intra-caso · 4 cross-claim (U6)


class Cotas(Contract):
    """Caps duros de terminación acotada (P4). Se usan en U4."""

    max_rondas: int = Field(gt=0)
    presupuesto_tokens: int = Field(gt=0)

# Rebuild Pydantic models to resolve forward references
Dictamen.model_rebuild()
