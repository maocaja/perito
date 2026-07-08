"""Sink de observabilidad a Langfuse — el target real del Must #10 (el floor JSON es el fallback).

Diseño (spec `specs/aidlc/evolution/langfuse-observability.md`):
- **Fail-open:** cualquier fallo del SDK/servicio se captura y loguea — NUNCA rompe el caso ni el floor
  JSON. A diferencia del pipeline de dominio (fail-*closed*): una traza perdida no es una decisión de negocio.
- **P5:** `motivo` es texto libre (puede traer PII) → se redacta con `redact_pii_spans_es_co` antes de enviar.
  Los `trace_events` ya vienen redactados desde `Tracer.get_trace_log()`.
- **No-bloqueante:** el SDK v4 encola + hace flush en un thread de fondo (no agrega latencia al HTTP).
- **Passive:** vive en `observability/`; no importa `rules/`/`orchestrator/` ni muta dominio.
"""

import logging
from typing import Any, Optional

from app.config import settings
from app.security.redaction import redact_pii_spans_es_co

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_init_failed = False


def is_enabled() -> bool:
    """True si hay credenciales de Langfuse configuradas."""
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def _get_client() -> Optional[Any]:
    """Cliente Langfuse (lazy, cacheado). Fail-open: si el init falla, devuelve None y no reintenta."""
    global _client, _init_failed
    if _client is not None or _init_failed:
        return _client
    try:
        from langfuse import Langfuse
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host or None,
        )
    except Exception as e:  # fail-open: nunca romper por observabilidad
        logger.warning("Langfuse init falló (fail-open): %s", e)
        _init_failed = True
    return _client


def emit_trace(caso_id, caso_estado, motivo, trace_events, token_summary) -> bool:
    """Emite una traza (span raíz + un span por nodo) a Langfuse.

    Devuelve True si emitió, False si estaba desactivado o falló. **Nunca propaga excepciones** (fail-open).
    `motivo` (texto libre) se redacta antes de enviar (P5); `trace_events` ya vienen redactados.
    """
    if not is_enabled():
        return False
    client = _get_client()
    if client is None:
        return False
    try:
        motivo_red = redact_pii_spans_es_co(motivo) if motivo else None
        root = client.start_observation(
            name="fnol-case",
            metadata={
                "caso_id": caso_id,
                "caso_estado": caso_estado,
                "motivo_escalamiento": motivo_red,
                "tokens_total": token_summary.get("tokens_total") if token_summary else None,
            },
        )
        try:
            for ev in trace_events:  # ya redactados (get_trace_log)
                child = root.start_observation(
                    name=ev.get("nodo", "nodo"),
                    output=ev.get("resultado"),
                    metadata={
                        "tokens_in": ev.get("tokens_in", 0),
                        "tokens_out": ev.get("tokens_out", 0),
                        "latencia_ms": ev.get("latencia_ms"),
                        "error": ev.get("error"),
                    },
                )
                child.end()
        finally:
            root.end()
        client.flush()
        return True
    except Exception as e:  # fail-open
        logger.warning("Langfuse emit falló (fail-open) caso=%s: %s", caso_id, e)
        return False
