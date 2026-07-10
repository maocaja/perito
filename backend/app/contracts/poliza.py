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


class CoberturaContratada(Contract):
    """Cobertura específica de un producto, con su PROPIO sublímite/deducible/exclusiones (U3, product-aware).

    `nombre` coincide con un valor de `TipoSiniestro` (ej. "AUTO_COLISION"). `tope_smmlv` (opcional) modela
    productos con tope legal en salarios mínimos (SOAT): el límite efectivo = min(sublimite, tope_smmlv·SMMLV).
    """

    nombre: str = Field(min_length=1)
    sublimite: Money
    deducible: Money
    exclusiones: list[str] = Field(default_factory=list)
    tope_smmlv: int | None = None


class Poliza(Contract):
    """Póliza sintética. Montos como Decimal (nunca float, PATTERN-U1-02).

    U3 (product-aware, ADITIVO): si `coberturas` está poblado, el motor lo prefiere (sublímite/deducible por
    cobertura); si está vacío, cae al modelo plano (`coberturas_contratadas`/`suma_asegurada`/`deducible`).
    Los campos planos quedan como retro-compat hasta migrar todo (limpieza en unit posterior).
    """

    numero: str = Field(min_length=1)
    vigencia: RangoFechas
    coberturas_contratadas: list[str] = Field(default_factory=list)  # PLANO (retro-compat)
    exclusiones: list[str] = Field(default_factory=list)             # PLANO (retro-compat)
    suma_asegurada: Money
    deducible: Money
    es_soat: bool = False
    clausulas: list[Clausula] = Field(default_factory=list)
    # --- U3 product-aware (aditivo; si presente, gana sobre los campos planos) ---
    producto: str | None = None
    coberturas: list[CoberturaContratada] = Field(default_factory=list)
    # --- U8 entity resolution (aditivo): claves alternativas para el fallback de C4 cuando no
    # viene el número de póliza. Todas opcionales → retro-compat total. PII (P5): se muestran/loguean
    # redactadas; aquí viven en el store de pólizas (dato de negocio), no en display.
    placa: str | None = None
    asegurado_cedula: str | None = None
    asegurado_nombre: str | None = None


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
