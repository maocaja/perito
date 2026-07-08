"""C9 Observabilidad: Tracer — instrumentación por nodo sin mutar lógica.

INVARIANTES:
- P3 (Trazabilidad): emite {caso_id, nodo, ts, resultado, tokens, latencia_ms}
- P4 (Tokens): accumula response.usage REAL (no estimados) — feed para cap
- P5 (PII): reusa redact_pii_spans_es_co verificado (single redactor, P5 invariant)
- No muta: solo observa, no toca rules/, orchestrator/ lógica
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Any, Dict
import json
import logging

from app.security.redaction import redact_pii_spans_es_co

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """Evento de traza por nodo (P3 trazabilidad)."""
    caso_id: str
    nodo: str  # "intake" | "extractor" | "verifier" | "policy" | "motor" | "fraude" | "hitl"
    timestamp: str  # ISO 8601
    resultado: str  # breve descripción del resultado
    tokens_in: int = 0  # tokens consumidos (entrada)
    tokens_out: int = 0  # tokens producidos (salida)
    latencia_ms: float = 0.0  # milliseconds
    error: Optional[str] = None  # si hubo error


class PIIRedactingLogSerializer:
    """Serializador que redacta PII antes de guardar trazas (P5 Habeas Data).
    
    Reusa redact_pii_spans_es_co verificado (single redactor principle).
    """
    
    REDACTION_MARKER = "[REDACTED]"
    
    def serialize(self, event: TraceEvent) -> Dict[str, Any]:
        """Redacta PII en TraceEvent antes de serializar."""
        event_dict = asdict(event)
        
        # Redactar resultado (puede contener PII)
        if event_dict.get("resultado"):
            event_dict["resultado"] = redact_pii_spans_es_co(event_dict["resultado"])
        
        # Redactar error si existe
        if event_dict.get("error"):
            event_dict["error"] = redact_pii_spans_es_co(event_dict["error"])
        
        return event_dict
    
    def to_json(self, event: TraceEvent) -> str:
        """Serializa a JSON con redacción."""
        return json.dumps(self.serialize(event))


class Tracer:
    """Tracer: emite eventos de traza por nodo (observabilidad sin mutación)."""
    
    def __init__(self, caso_id: str):
        self.caso_id = caso_id
        self.serializer = PIIRedactingLogSerializer()
        self.events: list[TraceEvent] = []
        self.total_tokens_in = 0
        self.total_tokens_out = 0
    
    def emit(
        self,
        nodo: str,
        resultado: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latencia_ms: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """Emite evento de traza por nodo.
        
        Args:
            nodo: nombre del nodo (intake, extractor, etc.)
            resultado: descripción breve del resultado
            tokens_in: tokens consumidos
            tokens_out: tokens producidos
            latencia_ms: latencia en milliseconds
            error: si hubo error, descripción (será redactada)
        """
        event = TraceEvent(
            caso_id=self.caso_id,
            nodo=nodo,
            timestamp=datetime.now(timezone.utc).isoformat(),
            resultado=resultado,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latencia_ms=latencia_ms,
            error=error
        )
        
        self.events.append(event)
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        
        # Log (redactado)
        logger.debug(f"[{self.caso_id}] {nodo}: {self.serializer.to_json(event)}")
    
    def get_trace_log(self) -> list[Dict[str, Any]]:
        """Retorna trace log (redactado, listo para serializar/guardar)."""
        return [self.serializer.serialize(event) for event in self.events]
    
    def get_token_summary(self) -> Dict[str, int]:
        """Retorna resumen de tokens (feed para P4 cap)."""
        return {
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "tokens_total": self.total_tokens_in + self.total_tokens_out
        }
    
    def assert_no_pii(self) -> None:
        """FAIL-CLOSED P5: verifica que no hay PII obvio en trazas (test guard rail)."""
        import re
        for event in self.events:
            serialized = self.serializer.serialize(event)
            
            # Buscar patrones PII obvios (números 8-10 dígitos sin redaction)
            for key, value in serialized.items():
                if isinstance(value, str):
                    # Si hay número largo sin redaction, falla
                    if re.search(r'\d{8,10}', value) and key not in ("timestamp",):
                        raise AssertionError(f"PII detectada en {key}: {value}")
