"""C1 Intake: Crear Caso desde aviso FNOL.

Responsabilidad:
- Construir Caso(estado=RECIBIDO, aviso, ...)
- Validar CalidadDoc=ILEGIBLE → raise (no procesar)
- Delegar todo cambio de estado a HITL (C8)
"""

from datetime import datetime, timezone

from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado
from app.contracts.caso import Caso


def intake_crear_caso(aviso: AvisoNormalizado) -> Caso:
    """Crea Caso inicial desde aviso FNOL.

    Args:
        aviso: AvisoNormalizado (texto_crudo + calidad)

    Returns:
        Caso(estado=RECIBIDO, aviso, todos los demás campos None/defaults)

    Raises:
        ValueError: si CalidadDoc=ILEGIBLE (no se puede procesar)
    """
    
    # --- Validación: ¿Documento procesable? ---
    if aviso.calidad == CalidadDoc.ILEGIBLE:
        raise ValueError(
            "Aviso ILEGIBLE: no se puede procesar automáticamente. "
            "Requiere escalamiento manual a REQUIERE_REVISION."
        )
    
    # --- Crear Caso inicial ---
    caso = Caso(
        estado=EstadoCaso.RECIBIDO,
        aviso=aviso,
        extraccion=None,  # Se rellena en C2
        poliza_match=None,  # Se rellena en C4
        dictamen=None,  # Se rellena en C5
        alerta_fraude=None,  # Se rellena en C6
        aprobado_por=None,  # Solo via HITL.aprobar/rechazar
        motivo_escalamiento=None
    )
    
    return caso
