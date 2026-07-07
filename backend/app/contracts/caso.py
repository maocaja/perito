"""Entidad Caso + Usuario (identidad que firma).

Este es el módulo cúspide: `Caso` referencia el resto de contratos. No hay
ciclos (los demás módulos no importan `caso`).
"""

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from app.contracts import Contract
from app.contracts.dictamen import AlertaFraude, Dictamen
from app.contracts.enums import ESTADOS_TERMINALES, EstadoCaso, RolUsuario
from app.contracts.extraccion import AvisoNormalizado, ExtraccionValidada
from app.contracts.poliza import ResultadoPoliza


class Usuario(Contract):
    """Identidad que firma un estado terminal (linchpin de P1).

    Mínimo, coherente con auth real = Won't (selector de rol stub, RNF-14):
    id + rol, sin password ni sesión.
    """

    usuario_id: str = Field(min_length=1)
    rol: RolUsuario


class Caso(Contract):
    """Aggregate raíz del caso FNOL.

    CONTRATO DE INMUTABILIDAD P1 (HITL) — Defensa en capas
    ════════════════════════════════════════════════════════

    Capa 1 — Construcción y asignación directa (aquí, U1):
    ───────────────────────────────────────────────────
    - `estado` y `aprobado_por` son frozen=True → bloquean asignación directa.
      Ejemplo: `caso.estado = APROBADO` lanza ValidationError.
    - Validador @model_validator _terminal_exige_firma refuerza en construcción:
      `Caso(estado=APROBADO, aprobado_por=None)` lanza ValueError.

    Limitación Pydantic v2 (CONOCIDA Y DOCUMENTADA):
    ────────────────────────────────────────────────
    - `model_copy(update={...})` evade TANTO frozen como @model_validator.
    - Ejemplo problema: `caso.model_copy(update={"estado": APROBADO})` produce
      un Caso terminal SIN firma y NINGÚN validador dispara.
    - Esto NO se puede cerrar en U1 (es comportamiento de Pydantic v2).
    - SE CIERRA EN U4 (ver Capa 2 abajo).

    Capa 2 — Transición de estado (U4/hitl — FUTURA):
    ─────────────────────────────────────────────────
    - La máquina de estados de hitl (U4) es la ÚNICA autorizada a transicionar.
    - hitl NUNCA confía en que Caso valide solo (porque model_copy se salta
      el validador). ANTES de cualquier transición a terminal, hitl:
      1. Verifica que nuevo_estado ∈ ESTADOS_TERMINALES
      2. Verifica que aprobado_por ≠ None
      3. RECIÉN ENTONCES hace model_copy (ahora es seguro)
    - Refuerzo: import-boundary (agents/ no importa hitl) + test fail-closed H-12.

    Sub-objetos (extraccion, dictamen, ...):
    ───────────────────────────────────────
    SÍ son asignables durante el flujo porque:
    - El orquestador (U4) los adjunta durante procesamiento.
    - validate_assignment=True permite asignación con validación.
    - Estos cambios son transitorios (estado llena campos, no los muta).

    CARRY-FORWARD:
    ──────────────
    U4/hitl (Unidad 4, Estación 5) debe implementar transition_to_terminal()
    que valida aprobado_por ANTES de model_copy. Ver U4/hitl/transition.py.
    """

    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True)

    caso_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    estado: EstadoCaso = Field(default=EstadoCaso.RECIBIDO, frozen=True)
    aprobado_por: Usuario | None = Field(default=None, frozen=True)

    aviso: AvisoNormalizado
    extraccion: ExtraccionValidada | None = None
    poliza_match: ResultadoPoliza | None = None
    dictamen: Dictamen | None = None
    alerta_fraude: AlertaFraude | None = None

    es_duplicado: bool = False
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

    @model_validator(mode="after")
    def _terminal_exige_firma(self) -> "Caso":
        """RULE-CTR-08 (P1 HITL): un estado terminal exige `aprobado_por`.

        Cierra DOS paths:
        1. Path de CONSTRUCCIÓN: Caso(estado=APROBADO, aprobado_por=None) → lanza
        2. Path de ASIGNACIÓN DIRECTA: caso.estado = APROBADO → lanza (frozen)

        LIMITACIÓN CONOCIDA (Pydantic v2):
        model_copy(update={"estado": APROBADO}) evade este validador.
        Se cierra en U4/hitl (máquina de estados que NUNCA confía en Caso solo).
        Ver docstring de clase para detalles del cierre en Capa 2.
        """
        if self.estado in ESTADOS_TERMINALES and self.aprobado_por is None:
            raise ValueError(
                "Caso: estado terminal (APROBADO/RECHAZADO) exige 'aprobado_por' "
                "(RULE-CTR-08, P1 HITL)"
            )
        return self


# Rebuild Pydantic models to resolve forward references (Pydantic v2)
Caso.model_rebuild()
