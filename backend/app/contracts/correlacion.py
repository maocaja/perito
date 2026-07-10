"""app/contracts/correlacion.py — contrato `Correlacion` (M3 · Evidence Correlator). 🔒 P6.

Overlay de correlación cross-fuente para UN campo lógico (placa/fecha/nombre): compara el MISMO dato desde
distintas fuentes (correo, PDF, foto) y dice si **coinciden** (sube confianza) o **divergen** (emite
inconsistencia citando ambas fuentes). Es un OVERLAY: NO reescribe `CampoExtraido.confianza`; W17 lo consulta
además del contrato de extracción.

INVARIANTES 🔒 P6:
- **Solo sugiere:** una divergencia es una inconsistencia "míralo", NUNCA cambia estado/dictamen ni decide
  fraude. `confianza_ajustada ∈ [0,1)` — jamás 1.0 (no es un veredicto, P7).
- **Determinístico:** la detección es comparación de valores normalizados; el LLM solo explica (no detecta).
- **P5:** cita la FUENTE (etiqueta del documento), no PII cruda extra; los valores se redactan en el display.
"""

from typing import Optional

from pydantic import Field, field_validator

from app.contracts import Contract

# Confianza consolidada por correlación (🔒 P6/P7: NUNCA 1.0). Fuente única (la usan el correlador y la vista).
CONFIANZA_COINCIDENCIA = 0.95   # varias fuentes concuerdan → sube
CONFIANZA_DIVERGENCIA = 0.4     # las fuentes se contradicen → baja + inconsistencia


class Correlacion(Contract):
    """Correlación cross-fuente de un campo lógico (overlay M3). `coincide=False` ⇒ `inconsistencia` no-nula."""

    campo_nombre: str = Field(min_length=1)          # nombre técnico del campo (p.ej. "placa")
    campo_label: str = Field(min_length=1)           # etiqueta humana ("Placa")
    valores_por_fuente: dict[str, str]               # fuente (etiqueta) → valor hallado en esa fuente
    fuentes: list[str] = Field(min_length=2)         # ≥2 fuentes (correlación exige multi-fuente)
    coincide: bool
    confianza_ajustada: float = Field(ge=0.0, lt=1.0)  # 🔒 P6/P7: nunca 1.0
    inconsistencia: Optional[str] = None             # frase "míralo" si divergen; None si coinciden

    @field_validator("inconsistencia")
    @classmethod
    def _divergencia_exige_evidencia(cls, v, info):
        """Una divergencia (coincide=False) DEBE traer su inconsistencia; una coincidencia no la lleva."""
        coincide = info.data.get("coincide")
        if coincide is False and not v:
            raise ValueError("Correlacion: coincide=False exige 'inconsistencia' (P6: evidencia obligatoria)")
        if coincide is True and v:
            raise ValueError("Correlacion: coincide=True no lleva inconsistencia")
        return v
