"""Contratos del generador sintético: FilaEntrada (puerto), GroundTruth."""

from typing import Any

from pydantic import Field, model_validator

from app.contracts import Contract
from app.contracts.enums import ResultadoCobertura
from app.contracts.extraccion import EvidenciaOrigen


class FilaEntrada(Contract):
    """Puerto abstracto de entrada del generador (Q3 / RULE-GEN-03).

    Kaggle es un adaptador que produce FilaEntrada; el generador no se acopla
    al esquema Kaggle (respeta el Plan B del riesgo #1).
    """

    datos_siniestro: dict[str, Any] = Field(default_factory=dict)
    etiqueta_fraude: bool = False
    metadatos: dict[str, Any] = Field(default_factory=dict)


class GroundTruth(Contract):
    """Verdad esperada de un caso sintético (para eval).

    RULE-GEN-02 (contrato): etiqueta_fraude=True ⇒ inconsistencia_esperada≠None.
    (El generador, además, garantiza que la inconsistencia esté ENCODADA en el
    documento, con assert fail-closed — synthetic/generator.py.)
    """

    campos_esperados: dict[str, Any] = Field(default_factory=dict)
    resultado_cobertura_esperado: ResultadoCobertura
    etiqueta_fraude: bool = False
    inconsistencia_esperada: EvidenciaOrigen | None = None

    @model_validator(mode="after")
    def _fraude_exige_inconsistencia(self) -> "GroundTruth":
        if self.etiqueta_fraude and self.inconsistencia_esperada is None:
            raise ValueError(
                "GroundTruth: etiqueta_fraude=True exige 'inconsistencia_esperada' (RULE-GEN-02)"
            )
        return self
