"""Módulo de reglas de cobertura (U3). Motor R1-R5: LLM-free, función pura.

P2 (determinismo): Este módulo contiene SOLO lógica determinística de cobertura.
Cero imports de anthropic o servicios LLM. Fraude (que sí usa LLM) vive en
backend.app.fraud, SEPARADO.
"""

from .motor_r1_r5 import motor_cobertura
from .precondiciones import prevalidar

__all__ = ["motor_cobertura", "prevalidar"]
