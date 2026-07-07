"""
contracts/enums.py — U2 Enumerations (aditivo a U1)

Tipos de siniestro soportados.
"""

from enum import Enum


class TipoSiniestro(str, Enum):
    """Tipos de siniestro cubiertos por póliza."""
    AUTO_COLISION = "AUTO_COLISION"
    AUTO_HURTO = "AUTO_HURTO"
    HOGAR_AGUA = "HOGAR_AGUA"
    # SOAT diferido (Should) — no agregar en MVP


class CalidadDoc(str, Enum):
    """Calidad del documento según OCR/procesamiento."""
    LIMPIO = "LIMPIO"
    SUCIO = "SUCIO"
    ILEGIBLE = "ILEGIBLE"


class TipoOrigen(str, Enum):
    """Tipo de origen de un campo extraído."""
    SPAN = "SPAN"  # Encontrado directamente en el texto
    INFERIDO = "INFERIDO"  # Deducido por contexto
    AUSENTE = "AUSENTE"  # No encontrado
