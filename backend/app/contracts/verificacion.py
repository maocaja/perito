"""
contracts/verificacion.py — U2 Verification Contracts (nuevo)

Tipos para verificación, señalamiento, y resultado de U2.
Todos strict + extra=forbid (como en U1 Contract base).
"""

from enum import Enum
from app.contracts.extraccion import EvidenciaOrigen
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class TipoSenal(str, Enum):
    """Tipos de señal de escalamiento."""
    CONFIANZA_BAJA = "CONFIANZA_BAJA"
    VERIFIER_RECHAZA = "VERIFIER_RECHAZA"
    CAMPO_OBLIGATORIO_FALTANTE = "CAMPO_OBLIGATORIO_FALTANTE"
    DOCUMENTO_SUCIO = "DOCUMENTO_SUCIO"


class SeñalEscalamiento(BaseModel):
    """
    Señal de U2 → U4: propone revisión manual, no decide nada.
    
    INVARIANTE P1: NO setea Caso.estado. Solo tipado para U4 consumo.
    U4 decide si escalar, humano firma.
    """
    motivo: str = Field(..., description="Por qué se escala")
    tipo: TipoSenal = Field(..., description="Tipo de señal")
    evidencia: List[EvidenciaOrigen] = Field(default_factory=list, description="Dónde/por qué")
    datos_contexto: Dict[str, Any] = Field(default_factory=dict, description="Info para humano")
    
    model_config = ConfigDict(extra="forbid", frozen=True)


class VerificacionAdversarial(BaseModel):
    """
    Resultado C3 Capa 1 (Sonnet adversarial re-read).
    
    Confianza que extracción es fiel al source.
    """
    confianza: float = Field(ge=0.0, le=1.0, description="Confianza [0,1]")
    inconsistencias: List[str] = Field(default_factory=list, description="Campos que parecen inventados")
    recomendacion: Literal["ACEPTA", "REVISA", "RECHAZA"] = Field(..., description="Recomendación")
    
    model_config = ConfigDict(extra="forbid", frozen=True)


class VerificacionConsistencia(BaseModel):
    """
    Resultado C3 Capa 2 (deterministic consistency checks, no LLM).
    
    Valida reglas simples (fecha ≤ hoy, monto > 0, tipo en enum, etc).
    """
    checks: Dict[str, bool] = Field(..., description="Resultados de cada check")
    aprobado: bool = Field(..., description="¿Todos los checks pasaron?")
    
    model_config = ConfigDict(extra="forbid", frozen=True)
