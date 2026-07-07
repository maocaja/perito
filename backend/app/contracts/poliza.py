"""Contratos de póliza: RangoFechas, Clausula, Poliza, ResultadoPoliza."""

from datetime import date

from pydantic import Field, model_validator

from app.contracts import Contract
from app.contracts.enums import TipoClausula
from app.contracts.money import Money


class RangoFechas(Contract):
    """VO de apoyo: rango [desde, hasta]. Base de R1 vigencia (U3)."""

    desde: date
    hasta: date

    @model_validator(mode="after")
    def _orden(self) -> "RangoFechas":
        if self.desde > self.hasta:
            raise ValueError("RangoFechas: 'desde' no puede ser posterior a 'hasta'")
        return self


class Clausula(Contract):
    """Cláusula de póliza — fuente citada de todo dictamen (P3)."""

    id: str = Field(min_length=1)
    texto: str = Field(min_length=1)
    tipo: TipoClausula
    referencia: str = Field(min_length=1)


class Poliza(Contract):
    """Póliza sintética. Montos como Decimal (nunca float, PATTERN-U1-02)."""

    numero: str = Field(min_length=1)
    vigencia: RangoFechas
    coberturas_contratadas: list[str] = Field(default_factory=list)
    exclusiones: list[str] = Field(default_factory=list)
    suma_asegurada: Money
    deducible: Money
    es_soat: bool = False  # forward-compat (RF-14); SOAT diferido
    clausulas: list[Clausula] = Field(default_factory=list)


class ResultadoPoliza(Contract):
    """Contrato de grounding (P4). Semántica RF-10: no forzar match.

    RULE-CTR-07: encontrada=True ⇒ poliza≠None; encontrada=False ⇒ poliza=None
    (las candidatas NUNCA se promueven a match). El comportamiento de búsqueda
    es U2; el invariante de contrato vive aquí (U1).
    """

    encontrada: bool
    poliza: Poliza | None = None
    candidatas: list[Poliza] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistencia(self) -> "ResultadoPoliza":
        if self.encontrada and self.poliza is None:
            raise ValueError("ResultadoPoliza: encontrada=True exige 'poliza' no nula")
        if not self.encontrada and self.poliza is not None:
            raise ValueError(
                "ResultadoPoliza: encontrada=False no admite 'poliza' (no forzar match, P4)"
            )
        return self
