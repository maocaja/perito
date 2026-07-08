"""Caso contract: FNOL case management (U4 Orchestration).

RULE-CTR-05 (P1): HITL is ÚNICO mutador de Caso.estado.
Caso.estado es frozen per-field (no model-wide) → direct assignment raises.
Terminal exige aprobado_por (validator enforce).
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import Field, field_validator, ConfigDict

from app.contracts import Contract
from app.contracts.enums import EstadoCaso, RolUsuario
from app.contracts.extraccion import AvisoNormalizado, ExtraccionValidada
from app.contracts.dictamen import Dictamen, AlertaFraude
from app.contracts.poliza import ResultadoPoliza


class Caso(Contract):
    """Caso FNOL (claim) — estado mutable solo vía HITL (C8).
    
    RULE-CTR-05 (P1): HITL es el ÚNICO componente que transiciona estado.
    Caso.estado frozen per-field (validate_assignment=True).
    Terminal (APROBADO/RECHAZADO) exige aprobado_por ≠ None.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    estado: EstadoCaso  # RECIBIDO → EN_PROCESO → ... → APROBADO/RECHAZADO
    
    aviso: AvisoNormalizado  # Entrada FNOL
    extraccion: Optional[ExtraccionValidada] = None  # C2 rellena
    poliza_match: Optional[ResultadoPoliza] = None  # C4 rellena
    dictamen: Optional[Dictamen] = None  # C5 rellena
    alerta_fraude: Optional[AlertaFraude] = None  # C6 rellena (informativo)
    
    aprobado_por: Optional[str] = None  # Usuario que aprobó (solo HITL setea)
    motivo_escalamiento: Optional[str] = None  # Razón si REQUIERE_REVISION
    
    timestamp_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp_actualizacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # RULE-CTR-05: Frozen per-field (not model-wide)
    model_config = ConfigDict(
        validate_assignment=True,
        # Campos congelados individualmente
        frozen=False  # Model NO es frozen (C7 puede adjuntar sub-objetos)
    )
    
    @field_validator('estado', mode='before')
    @classmethod
    def _validate_estado_enum(cls, v):
        """Estado debe estar en EstadoCaso enum."""
        if isinstance(v, str):
            try:
                return EstadoCaso(v)
            except ValueError:
                raise ValueError(f"estado inválido: {v}")
        return v
    
    @field_validator('aprobado_por')
    @classmethod
    def _aprobado_por_obligatorio_en_terminal(cls, v, info):
        """RULE-CTR-05: Terminal exige aprobado_por ≠ None."""
        estado = info.data.get('estado')
        if estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}:
            if v is None:
                raise ValueError(
                    f"RULE-CTR-05: estado terminal '{estado}' exige aprobado_por no-nulo (P1 auditabilidad)"
                )
        return v
    
    def __setattr__(self, name, value):
        """Frozen per-field: estado y aprobado_por no se pueden asignar directo.
        
        RULE-CTR-05 (P1): Solo HITL (vía model_validate) puede cambiar estado.
        Las asignaciones directas (caso.estado = X) → raises FrozenFieldError.
        """
        frozen_fields = {'estado', 'aprobado_por'}
        
        if name in frozen_fields and hasattr(self, name):
            # Field ya existe en la instancia → intento de reasignación
            raise ValueError(
                f"RULE-CTR-05: '{name}' es frozen. "
                f"Usa HITL.transicionar/aprobar/rechazar para cambiar estado."
            )
        
        super().__setattr__(name, value)


class Usuario(Contract):
    """Usuario del sistema (auditor, suscriptor, etc).
    
    Se usa en HITL.aprobar/rechazar como identificador de quién firma.
    """
    
    usuario_id: str = Field(min_length=1)
    rol: RolUsuario
