"""Pytest: Validación fail-closed (NFR-U1-02, RULE-CTR-02).

Los contratos deben rechazar malformados, no aceptarlos.
"""

import pytest
from pydantic import ValidationError
from app.contracts.poliza import RangoFechas, Poliza
from app.contracts.extraccion import CampoExtraido
from app.contracts.dictamen import Dictamen, AlertaFraude
from app.contracts.enums import ResultadoCobertura


def test_rango_fechas_rechaza_desde_mayor_que_hasta():
    """RangoFechas: desde > hasta → ValidationError."""
    from datetime import date
    with pytest.raises(ValueError, match="desde"):
        RangoFechas(desde=date(2025, 1, 2), hasta=date(2025, 1, 1))


def test_poliza_rechaza_float_en_decimal():
    """Poliza.suma_asegurada: float en lugar de Decimal → ValidationError (strict=True)."""
    with pytest.raises(ValidationError):
        Poliza(
            numero="P001",
            vigencia={"desde": "2025-01-01", "hasta": "2025-12-31"},
            suma_asegurada=1000.5,  # ← float, no Decimal
            deducible=100,
        )


def test_campo_extraido_ausente_true_con_valor_rechazado():
    """CampoExtraido: ausente=True + valor≠None → ValidationError."""
    with pytest.raises(ValueError, match="ausente"):
        CampoExtraido(nombre="campo1", valor="algo", ausente=True)


def test_dictamen_clausula_obligatoria():
    """Dictamen.clausula: OBLIGATORIA (no puede ser None)."""
    with pytest.raises(ValidationError):
        Dictamen(
            resultado=ResultadoCobertura.CUBIERTO,
            regla_aplicada="R1",
            clausula=None,  # ← Falta
            deducible_calculado=0,
        )


def test_alerta_fraude_inconsistencias_vacia():
    """AlertaFraude.inconsistencias: min_length=1 (no vacío)."""
    with pytest.raises(ValidationError):
        AlertaFraude(
            severidad="ALTA",
            inconsistencias=[],  # ← Vacío, no válido
            explicacion="test",
        )


def test_strict_rechaza_extra_fields():
    """extra="forbid": campos desconocidos → ValidationError."""
    with pytest.raises(ValidationError):
        Poliza(
            numero="P001",
            vigencia={"desde": "2025-01-01", "hasta": "2025-12-31"},
            suma_asegurada=1000,
            deducible=100,
            unknown_field="should_fail",  # ← Campo no conocido
        )
