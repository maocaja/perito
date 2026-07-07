"""C1 Intake: Crear Caso desde AvisoNormalizado (U4, Orquestación FNOL).

Responsabilidad: Construir Caso inicial en estado RECIBIDO.
- Valida CalidadDoc (ILEGIBLE → escalar inmediatamente)
- Delega todo cambio de estado a HITL
"""

from .c1 import intake_crear_caso

__all__ = ["intake_crear_caso"]
