"""C8 HITL: Human-in-the-Loop service for case transitions & approvals (U4).

CRITICAL INVARIANTS:
- transicionar/aprobar/rechazar use model_validate (re-runs validators)
- Never model_copy (model_copy bypasses validators, P1 breach)
- aprobar/rechazar require usuario ≠ None (H-12b dual gate)
- Terminal states (APROBADO/RECHAZADO) only via aprobar/rechazar, never direct mutation
"""

from .c8 import (
    HITLService,
    transicionar,
    aprobar,
    rechazar
)

__all__ = ["HITLService", "transicionar", "aprobar", "rechazar"]
