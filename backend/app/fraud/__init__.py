"""Módulo de fraude (U3). Capas 1-3: determinísticas + LLM (separado de rules/).

P2/P6 (Determinismo + Explicabilidad):
- Capa 1: Chequeos duros determinísticos (función pura)
- Capa 2: Mapa severidad determinístico (función pura)
- Capa 3: Razonamiento LLM (mockeable en tests, deny-by-default via LLMPayloadBuilder de U1)

P5 (PII): Redacción via backend.app.security.redaction.LLMPayloadBuilder (verificado U1).

INVARIANTE: fraud/ NO importa rules/ (frontera P2).
"""

from .fraude import (
    detectar_inconsistencias_fraude,
    calcular_severidad,
    construir_alerta_fraude,
)

__all__ = [
    "detectar_inconsistencias_fraude",
    "calcular_severidad",
    "construir_alerta_fraude",
]
