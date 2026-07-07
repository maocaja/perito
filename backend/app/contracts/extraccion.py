"""Contratos de ingesta/extracción: EvidenciaOrigen, CampoExtraido,
ExtraccionValidada, AvisoNormalizado."""

from typing import Annotated

from pydantic import Field, model_validator

from app.contracts import Contract
from app.contracts.enums import CalidadDoc, TipoOrigen
from app.contracts.pii import PII


class EvidenciaOrigen(Contract):
    """Puntero al origen de un dato, para trazabilidad (P3)."""

    tipo: TipoOrigen
    referencia: str = Field(min_length=1)


class CampoExtraido(Contract):
    """Un campo extraído + su procedencia.

    NFR-U1-04 / no-invención por construcción: ausente=True ⇒ valor=None
    (el contrato NO permite inventar un valor). La métrica de campos inventados
    ≈0 se MIDE en U2 (aquí es invariante de contrato).
    """

    nombre: str = Field(min_length=1)
    valor: str | None = None
    origen: EvidenciaOrigen | None = None
    confianza: float | None = None
    ausente: bool = False

    @model_validator(mode="after")
    def _no_invencion(self) -> "CampoExtraido":
        if self.ausente and self.valor is not None:
            raise ValueError(
                "CampoExtraido: ausente=True no admite 'valor' (no-invención, P4)"
            )
        return self


class ExtraccionValidada(Contract):
    """Conjunto de campos extraídos que valida contra el contrato."""

    campos: list[CampoExtraido] = Field(default_factory=list)


class AvisoNormalizado(Contract):
    """Representación interna uniforme del aviso FNOL.

    `texto_crudo` es PII: puede contener nombres, cédulas, direcciones es-CO.
    Marcado con PII para que los redactores deny-by-default lo protejan (P5).
    """

    texto_crudo: Annotated[str, PII]
    calidad: CalidadDoc = CalidadDoc.LIMPIO
