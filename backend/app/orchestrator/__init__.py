"""C7 Orchestrator: Main FNOL case processing loop (U4).

CRITICAL INVARIANTS:
- Never mutates Caso.estado directly (HITL.transicionar only)
- Never produces terminal (APROBADO/RECHAZADO) — orchestrator leaves case in LISTO_PARA_APROBAR or REQUIERE_REVISION
- Respects Cotas (max_rondas=1, presupuesto_tokens=20000, REAL token usage)
- Exception capture → escape, never propagate
- Cycle detection via snapshot/hash
- CORONA TEST: assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}
"""

from .c7 import orquestar_fnol

__all__ = ["orquestar_fnol"]
