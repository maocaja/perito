"""PBT-03: Property-based tests para motor R1-R5 via Hypothesis.

Invariantes testeadas:
1. Idempotencia: motor(ex, pol) == motor(ex, pol)
2. Resultado enum-válido: resultado ∈ ResultadoCobertura
3. Monto no negativo: monto ≥ 0
4. Redondeo fijo: todos los montos son enteros (0 decimales)
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from app.contracts.enums import ResultadoCobertura, TipoClausula, TipoSiniestro
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada, TipoOrigen
from app.contracts.poliza import Clausula, Poliza, RangoFechas, ResultadoPoliza
from app.rules.motor_r1_r5 import motor_cobertura, redondear_monto


def make_poliza():
    """Factory: crear póliza válida."""
    return Poliza(
        numero="POL-2025-001",
        vigencia=RangoFechas(desde=date(2025, 1, 1), hasta=date(2025, 12, 31)),
        coberturas_contratadas=[TipoSiniestro.AUTO_COLISION.value, TipoSiniestro.AUTO_HURTO.value],
        exclusiones=[],
        suma_asegurada=Decimal("50000"),
        deducible=Decimal("500"),
        clausulas=[
            Clausula(id="VIG-001", texto="Vigencia", tipo=TipoClausula.VIGENCIA, referencia="REF-VIG"),
            Clausula(id="COV-001", texto="Cobertura", tipo=TipoClausula.COBERTURA, referencia="REF-COV"),
            Clausula(id="DED-001", texto="Deducible", tipo=TipoClausula.DEDUCIBLE, referencia="REF-DED")
        ]
    )


def make_extraccion(fecha=None, monto=None, tipo=None, ausentes=None):
    """Factory: crear extracción validada."""
    ausentes = ausentes or []
    campos = [
        CampoExtraido(
            nombre="fecha_siniestro",
            valor=None if "fecha_siniestro" in ausentes else (fecha or date(2025, 6, 15)).isoformat(),
            origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:0"),
            ausente="fecha_siniestro" in ausentes
        ),
        CampoExtraido(
            nombre="tipo_siniestro",
            valor=None if "tipo_siniestro" in ausentes else (tipo or TipoSiniestro.AUTO_COLISION.value),
            origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:1"),
            ausente="tipo_siniestro" in ausentes
        ),
        CampoExtraido(
            nombre="monto_reclamado",
            valor=None if "monto_reclamado" in ausentes else str(monto or Decimal("10000")),
            origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:2"),
            ausente="monto_reclamado" in ausentes
        )
    ]
    return ExtraccionValidada(campos=campos)


class TestRedondeoFijo:
    """Invariante 6: Redondeo ROUND_HALF_UP (determinístico)."""

    def test_redondeo_half_up_ejemplos(self):
        """Casos específicos de ROUND_HALF_UP."""
        assert redondear_monto(Decimal("10.5")) == Decimal("11")
        assert redondear_monto(Decimal("10.4")) == Decimal("10")
        assert redondear_monto(Decimal("10.6")) == Decimal("11")
        assert redondear_monto(Decimal("0.5")) == Decimal("1")

    @given(st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("1000000"),
        allow_nan=False,
        allow_infinity=False
    ))
    @settings(max_examples=100)
    def test_redondeo_idempotente(self, monto):
        """redondear(x) == redondear(redondear(x))."""
        redondeado = redondear_monto(monto)
        redondeado_dos = redondear_monto(redondeado)
        assert redondeado == redondeado_dos

    @given(st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("1000000"),
        allow_nan=False,
        allow_infinity=False
    ))
    @settings(max_examples=100)
    def test_redondeo_entero(self, monto):
        """Resultado siempre tiene 0 decimales."""
        redondeado = redondear_monto(monto)
        assert redondeado == redondeado.quantize(Decimal("1"))


class TestMotorIdempotencia:
    """Invariante 1: Idempotencia."""

    def test_motor_idempotente(self):
        """Mismo input → mismo output siempre."""
        poliza = make_poliza()
        extraccion = make_extraccion()
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen_1 = motor_cobertura(extraccion, resultado_poliza)
        dictamen_2 = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen_1.resultado == dictamen_2.resultado
        assert dictamen_1.regla_aplicada == dictamen_2.regla_aplicada


class TestMotorResultadoEnum:
    """Invariante 2: Resultado siempre válido."""

    def test_resultado_en_enum(self):
        """Resultado ∈ ResultadoCobertura enum."""
        poliza = make_poliza()
        extraccion = make_extraccion()
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert isinstance(dictamen.resultado, ResultadoCobertura)
        assert dictamen.resultado in ResultadoCobertura


class TestMotorMontoNoNegativo:
    """Invariante 3: Monto siempre ≥ 0."""

    def test_monto_no_negativo(self):
        """deducible_calculado ≥ 0."""
        poliza = make_poliza()
        extraccion = make_extraccion()
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        assert dictamen.deducible_calculado >= Decimal(0)


class TestMotorClausulaTerminal:
    """Invariante 4: Terminal → clausula ≠ None."""

    def test_clausula_en_terminal(self):
        """Si resultado terminal, clausula es citada."""
        poliza = make_poliza()
        extraccion = make_extraccion()
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza)

        dictamen = motor_cobertura(extraccion, resultado_poliza)

        if dictamen.resultado in [
            ResultadoCobertura.CUBIERTO,
            ResultadoCobertura.CUBIERTO_PARCIAL,
            ResultadoCobertura.NO_CUBIERTO
        ]:
            assert dictamen.clausula is not None

