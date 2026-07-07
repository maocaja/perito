"""C9 Replay Store: almacenamiento simple (in-memory/JSON) de trazas por caso.

Demo-grade: permite reconstruir/inspeccionar una corrida.
"""

from typing import Dict, List, Optional
from app.observability.tracer import Tracer
import json
from datetime import datetime, timezone


class ReplayStore:
    """Almacén de trazas por caso (in-memory, dumpeable a JSON)."""
    
    def __init__(self):
        self.cases: Dict[str, Dict] = {}
    
    def save(self, tracer: Tracer, caso_estado: str, motivo: Optional[str] = None) -> None:
        """Guarda trace log de un caso en el store.
        
        Args:
            tracer: Tracer con eventos de traza
            caso_estado: estado final (RECIBIDO, EN_PROCESO, LISTO_PARA_APROBAR, etc.)
            motivo: motivo si escaló (opcional)
        """
        self.cases[tracer.caso_id] = {
            "caso_id": tracer.caso_id,
            "timestamp_saved": datetime.now(timezone.utc).isoformat(),
            "caso_estado": caso_estado,
            "motivo_escalamiento": motivo,
            "trace_events": tracer.get_trace_log(),
            "token_summary": tracer.get_token_summary()
        }
    
    def load(self, caso_id: str) -> Optional[Dict]:
        """Carga el replay de un caso."""
        return self.cases.get(caso_id)
    
    def dump_json(self) -> str:
        """Dumpea todas las trazas a JSON (para inspección/debugging)."""
        return json.dumps(self.cases, indent=2)
    
    def get_all_cases(self) -> List[str]:
        """Retorna lista de caso_ids guardados."""
        return list(self.cases.keys())


# Global replay store (demo-grade; en prod sería DB)
_global_replay_store = ReplayStore()


def get_replay_store() -> ReplayStore:
    """Retorna la instancia global de ReplayStore."""
    return _global_replay_store
