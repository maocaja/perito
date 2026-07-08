"""Unit tests para motor R1-R5 (casos específicos y edge cases)."""

from datetime import date
from decimal import Decimal

import pytest

from app.contracts.enums import ResultadoCobertura, TipoClausula, TipoSiniestro
from app.contracts.poliza import Clausula, Poliza, RangoFechas, ResultadoPoliza
from app.rules.motor_r1_r5 import motor_cobertura
from tests.test_u3_motor_r1_r5_pbt import make_poliza, make_extraccion


class TestMotorHappyPath:
    """Happy path: siniestro dentro de vigencia, tipo cubierto, deducible aplicado."""

    def test_motor_happy_path(self):
        """Flujo: R1✓, R2✓, R4✓, R5 aplica deducible → CUBIERTO."""
        poliza = make_poliza()
        extraccion = make_extraccion(fecha=date(2025, 6, 15), monto=Decimal("10000"))
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen.resultado in [ResultadoCobertura.CUBIERTO, ResultadoCobertura.CUBIERTO_PARCIAL]
        assert dictamen.clausula is not None


class TestMotorCampoAusente:
    """Precondición: campo obligatorio ausente → REQUIERE_REVISION."""

    def test_campo_fecha_ausente(self):
        """Fecha ausente → REQUIERE_REVISION."""
        poliza = make_poliza()
        extraccion = make_extraccion(ausentes=["fecha_siniestro"])
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION

    def test_campo_monto_ausente(self):
        """Monto ausente → REQUIERE_REVISION."""
        poliza = make_poliza()
        extraccion = make_extraccion(ausentes=["monto_reclamado"])
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION


class TestMotorPolizaNoEncontrada:
    """Precondición: solo candidatas, sin póliza confirmada → REQUIERE_REVISION (P4)."""

    def test_poliza_candidatas_solo(self):
        """ResultadoPoliza.encontrada=False → REQUIERE_REVISION."""
        poliza = make_poliza()
        extraccion = make_extraccion()
        resultado_poliza = ResultadoPoliza(encontrada=False, poliza=None, candidatas=[poliza])

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION

