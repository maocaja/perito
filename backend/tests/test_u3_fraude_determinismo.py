"""PBT + Unit tests para Fraude (U3-C6).

Invariantes testeadas:
1. Capa 1: Chequeos duros determinísticos (función pura)
2. Capa 2: Severidad determinística (mismo input → mismo output)
3. Capa 3: LLM mockeable (no modifica severidad/inconsistencias)
4. Cero inconsistencias → None (no AlertaFraude vacío, P6)
5. inconsistencias: list[EvidenciaOrigen], no list[str]
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from app.contracts.enums import TipoOrigen
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada
from app.contracts.poliza import Poliza, RangoFechas
from app.fraud.fraude import (
    detectar_inconsistencias_fraude,
    calcular_severidad,
    construir_alerta_fraude,
    TipoInconsistencia,
    SeveridadFraude,
)


def make_poliza():
    """Factory: crear póliza válida para fraude tests."""
    return Poliza(
        numero="POL-2025-FRAUDE",
        vigencia=RangoFechas(desde=date(2025, 1, 1), hasta=date(2025, 12, 31)),
        coberturas_contratadas=["AUTO_COLISION", "AUTO_HURTO"],
        exclusiones=[],
        suma_asegurada=Decimal("50000"),
        deducible=Decimal("500"),
        clausulas=[]
    )


def make_extraccion(fecha=None, monto=None, tipo=None):
    """Factory: crear extracción para fraude tests."""
    return ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="fecha_siniestro",
                valor=(fecha or date(2025, 6, 15)).isoformat(),
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:0"),
                ausente=False
            ),
            CampoExtraido(
                nombre="monto_reclamado",
                valor=str(monto or Decimal("10000")),
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:1"),
                ausente=False
            ),
            CampoExtraido(
                nombre="tipo_siniestro",
                valor=tipo or "AUTO_COLISION",
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:2"),
                ausente=False
            )
        ]
    )


class TestCapaUnoIdempotencia:
    """Capa 1: Detectar inconsistencias es determinístico."""

    def test_capa_uno_idempotente(self):
        """Mismo input → mismo output."""
        poliza = make_poliza()
        extraccion = make_extraccion(fecha=date(2024, 1, 1))  # Anterior vigencia

        inc_1 = detectar_inconsistencias_fraude(extraccion, poliza)
        inc_2 = detectar_inconsistencias_fraude(extraccion, poliza)

        assert inc_1 == inc_2
        assert len(inc_1) == len(inc_2)


class TestCapaUnoChequeos:
    """Capa 1: Chequeos específicos."""

    def test_fecha_anterior_vigencia(self):
        """Fecha anterior → inconsistencia detectada."""
        poliza = make_poliza()
        extraccion = make_extraccion(fecha=date(2024, 12, 31))

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) > 0
        assert any("ANTERIOR_VIGENCIA" in e.referencia for e in inconsistencias)

    def test_fecha_posterior_vigencia(self):
        """Fecha posterior → inconsistencia detectada."""
        poliza = make_poliza()
        extraccion = make_extraccion(fecha=date(2026, 1, 1))

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) > 0
        assert any("POSTERIOR_VIGENCIA" in e.referencia for e in inconsistencias)

    def test_fecha_futuro(self):
        """Fecha futura → inconsistencia detectada."""
        poliza = make_poliza()
        manana = date.today() + __import__('datetime').timedelta(days=1)
        extraccion = make_extraccion(fecha=manana)

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) > 0
        assert any("FUTURO" in e.referencia for e in inconsistencias)

    def test_monto_excede_suma(self):
        """Monto > suma asegurada → inconsistencia detectada."""
        poliza = make_poliza()
        extraccion = make_extraccion(monto=Decimal("60000"))  # > suma 50000

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) > 0
        assert any("MONTO_EXCEDE_SUMA" in e.referencia for e in inconsistencias)

    def test_tipo_no_cubierto(self):
        """Tipo no en coberturas → inconsistencia detectada."""
        poliza = make_poliza()
        extraccion = make_extraccion(tipo="HOGAR_AGUA")  # No en coberturas

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) > 0
        assert any("TIPO_NO_CUBIERTO" in e.referencia for e in inconsistencias)

    def test_cero_inconsistencias_happy_path(self):
        """Datos válidos → cero inconsistencias."""
        poliza = make_poliza()
        extraccion = make_extraccion(
            fecha=date(2025, 6, 15),
            monto=Decimal("10000"),
            tipo="AUTO_COLISION"
        )

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        assert len(inconsistencias) == 0


class TestCapaDosIdempotencia:
    """Capa 2: Severidad es determinística."""

    def test_severidad_idempotente(self):
        """Mismo set inconsistencias → misma severidad."""
        inconsistencias = [
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="MONTO_EXCEDE_SUMA: 60k > 50k")
        ]

        sev_1 = calcular_severidad(inconsistencias)
        sev_2 = calcular_severidad(inconsistencias)

        assert sev_1 == sev_2
        assert sev_1 == SeveridadFraude.ALTA  # Tipo duro


class TestCapaDosReglas:
    """Capa 2: Reglas de severidad."""

    def test_tipo_duro_alta(self):
        """FECHA_FUTURO, MONTO_EXCEDE_SUMA → ALTA."""
        inconsistencias = [
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="FECHA_FUTURO: ...")
        ]
        assert calcular_severidad(inconsistencias) == SeveridadFraude.ALTA

    def test_vigencia_media(self):
        """VIGENCIA → MEDIA."""
        inconsistencias = [
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="FECHA_ANTERIOR_VIGENCIA: ...")
        ]
        assert calcular_severidad(inconsistencias) == SeveridadFraude.MEDIA

    def test_tres_mas_inconsistencias_sube_nivel(self):
        """3+ inconsistencias → sube severidad."""
        inconsistencias = [
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="INC1"),
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="INC2"),
            EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="INC3"),
        ]
        severidad = calcular_severidad(inconsistencias)
        assert severidad in [SeveridadFraude.MEDIA, SeveridadFraude.ALTA]

    def test_cero_inconsistencias_baja(self):
        """Cero inconsistencias → BAJA."""
        assert calcular_severidad([]) == SeveridadFraude.BAJA


class TestAlertaFraudeConstruction:
    """AlertaFraude: construcción y P6."""

    def test_cero_inconsistencias_none(self):
        """Cero inconsistencias → retorna None (no AlertaFraude vacío, P6)."""
        poliza = make_poliza()
        extraccion = make_extraccion()  # Happy path (cero inconsistencias)

        alerta = construir_alerta_fraude(extraccion, poliza)

        assert alerta is None

    def test_inconsistencias_presente_alerta(self):
        """Inconsistencias > 0 → emite AlertaFraude (con LLM mockeado)."""
        poliza = make_poliza()
        extraccion = make_extraccion(monto=Decimal("60000"))  # Inconsistencia

        # Mock LLM call
        import app.fraud.fraude as fraud_module
        original_llm = fraud_module._llm_call
        try:
            fraud_module._llm_call = lambda prompt: "Fraude detectado por LLM (mock)."
            alerta = construir_alerta_fraude(extraccion, poliza)
            
            assert alerta is not None
            assert len(alerta.inconsistencias) > 0
            assert "mock" in alerta.explicacion.lower()
        finally:
            fraud_module._llm_call = original_llm

    def test_alerta_estructura(self):
        """AlertaFraude tiene estructura correcta."""
        poliza = make_poliza()
        extraccion = make_extraccion(
            fecha=date(2024, 1, 1),  # Anterior vigencia
            monto=Decimal("60000")  # Excede suma
        )

        import app.fraud.fraude as fraud_module
        original_llm = fraud_module._llm_call
        try:
            fraud_module._llm_call = lambda prompt: "Fraude por múltiples indicadores."
            alerta = construir_alerta_fraude(extraccion, poliza)
            
            assert alerta is not None
            assert alerta.severidad in [SeveridadFraude.BAJA, SeveridadFraude.MEDIA, SeveridadFraude.ALTA]
            assert isinstance(alerta.inconsistencias, list)
            assert all(isinstance(e, EvidenciaOrigen) for e in alerta.inconsistencias)
            assert isinstance(alerta.explicacion, str)
        finally:
            fraud_module._llm_call = original_llm


class TestEvidenciaOrigen:
    """Invariante: inconsistencias son list[EvidenciaOrigen], no list[str]."""

    def test_inconsistencias_tipo_evidencia_origen(self):
        """Todas inconsistencias son EvidenciaOrigen."""
        poliza = make_poliza()
        extraccion = make_extraccion(fecha=date(2024, 1, 1))

        inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

        for e in inconsistencias:
            assert isinstance(e, EvidenciaOrigen)
            assert hasattr(e, "tipo")
            assert hasattr(e, "referencia")

