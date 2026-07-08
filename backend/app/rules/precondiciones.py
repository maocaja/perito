"""Precondiciones del motor: validación pre-R1-R5 (P4).

Campos obligatorios ausentes → REQUIERE_REVISION (escalar, no pasar None a Rx).
Póliza incompleta (falta cláusula) → REQUIERE_REVISION.
Póliza no encontrada (solo candidatas) → REQUIERE_REVISION.
"""

from decimal import Decimal
from typing import Optional

from app.contracts.dictamen import Dictamen
from app.contracts.enums import ResultadoCobertura, TipoClausula
from app.contracts.extraccion import ExtraccionValidada
from app.contracts.poliza import Poliza, ResultadoPoliza


CAMPOS_OBLIGATORIOS_MOTOR = [
    "fecha_siniestro",
    "tipo_siniestro",
    "monto_reclamado"
]

CLAUSULAS_REQUERIDAS_MOTOR = [
    TipoClausula.VIGENCIA,
    TipoClausula.COBERTURA,
    TipoClausula.DEDUCIBLE
]


def _get_campo(extraccion: ExtraccionValidada, nombre: str) -> Optional[object]:
    """Busca un campo extraído por nombre."""
    for campo in extraccion.campos:
        if campo.nombre == nombre:
            return campo
    return None


def prevalidar(
    extraccion: ExtraccionValidada,
    resultado_poliza: ResultadoPoliza
) -> Optional[Dictamen]:
    """Valida precondiciones antes de invocar motor_cobertura.

    Si devuelve Dictamen, es un escalamiento (REQUIERE_REVISION).
    Si devuelve None, motor puede proceder.

    Args:
        extraccion: ExtraccionValidada
        resultado_poliza: ResultadoPoliza

    Returns:
        Dictamen de escalamiento, o None si OK
    """

    # --- Chequeo 1: Póliza encontrada ---
    if not resultado_poliza.encontrada:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,
            deducible_calculado=Decimal(0)
        )

    poliza = resultado_poliza.poliza
    if not poliza:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,
            deducible_calculado=Decimal(0)
        )

    # --- Chequeo 2: Campos obligatorios presentes ---
    for campo_nombre in CAMPOS_OBLIGATORIOS_MOTOR:
        campo = _get_campo(extraccion, campo_nombre)
        if campo is None or campo.ausente:
            return Dictamen(
                resultado=ResultadoCobertura.REQUIERE_REVISION,
                regla_aplicada="PRE_MOTOR",
                clausula=None,
                deducible_calculado=Decimal(0)
            )

    # --- Chequeo 3: Póliza completa (tiene cláusulas requeridas) ---
    tipos_presentes = {c.tipo for c in poliza.clausulas}
    for tipo_requerido in CLAUSULAS_REQUERIDAS_MOTOR:
        if tipo_requerido not in tipos_presentes:
            return Dictamen(
                resultado=ResultadoCobertura.REQUIERE_REVISION,
                regla_aplicada="PRE_MOTOR",
                clausula=None,
                deducible_calculado=Decimal(0)
            )

    return None  # OK, motor puede proceder

