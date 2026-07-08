"""C11 Dashboard (U5) — vitrina demo-grade FastAPI + Jinja/HTMX.

INVARIANTES (component-dependency, P1):
- Passive/read-only: NO importa `rules/` ni `orchestrator/`, sin lógica de dominio.
- Delega TODA decisión en `hitl/` (C8); nunca asigna `caso.estado` ni alcanza terminal.
- P5: el aviso se muestra redactado (reusa `security.redaction.redact_pii_spans_es_co`).
"""
