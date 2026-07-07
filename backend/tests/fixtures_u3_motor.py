"""Fixtures y factories para tests del motor U3 (PBT-03)."""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from app.contracts.enums import ResultadoCobertura, TipoClausula, TipoSiniestro
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada, TipoOrigen
from app.contracts.poliza import Clausula, Poliza, RangoFechas, ResultadoPoliza


@pytest.fixture
def poliza_builder():
    """Factory para construir pólizas de prueba (MVP)."""

    class PolizaBuilder:
        def __init__(self):
            self.numero = "POL-2025-001"
            self.vigencia = RangoFechas(
                desde=date(2025, 1, 1),
                hasta=date(2025, 12, 31)
            )
            self.coberturas_contratadas = [
                TipoSiniestro.AUTO_COLISION.value,
                TipoSiniestro.AUTO_HURTO.value
            ]
            self.exclusiones = []
            self.suma_asegurada = Decimal("50000")
            self.deducible = Decimal("500")
            self.clausulas = [
                Clausula(
                    id="CLU-2025-VIGENCIA-001",
                    texto="Vigencia del 1 enero al 31 diciembre 2025",
                    tipo=TipoClausula.VIGENCIA,
                    referencia="REF-VIG-001"
                ),
                Clausula(
                    id="CLU-2025-COBERTURA-001",
                    texto="Cobertura: AUTO_COLISION, AUTO_HURTO",
                    tipo=TipoClausula.COBERTURA,
                    referencia="REF-COV-001"
                ),
                Clausula(
                    id="CLU-2025-DEDUCIBLE-001",
                    texto="Deducible: COP 500",
                    tipo=TipoClausula.DEDUCIBLE,
                    referencia="REF-DED-001"
                )
            ]

        def build(self) -> Poliza:
            return Poliza(
                numero=self.numero,
                vigencia=self.vigencia,
                coberturas_contratadas=self.coberturas_contratadas,
                exclusiones=self.exclusiones,
                suma_asegurada=self.suma_asegurada,
                deducible=self.deducible,
                clausulas=self.clausulas
            )

    return PolizaBuilder()


@pytest.fixture
def extraccion_builder():
    """Factory para construir extracciones validadas de prueba."""

    class ExtraccionBuilder:
        def __init__(self):
            self.campos = [
                CampoExtraido(
                    nombre="fecha_siniestro",
                    valor="2025-06-15",
                    origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="doc:page1:span2"),
                    ausente=False
                ),
                CampoExtraido(
                    nombre="tipo_siniestro",
                    valor=TipoSiniestro.AUTO_COLISION.value,
                    origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="doc:page1:span3"),
                    ausente=False
                ),
                CampoExtraido(
                    nombre="monto_reclamado",
                    valor="25000",
                    origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="doc:page1:span4"),
                    ausente=False
                )
            ]

        def con_fecha(self, fecha: date) -> "ExtraccionBuilder":
            for campo in self.campos:
                if campo.nombre == "fecha_siniestro":
                    campo.valor = fecha.isoformat()
            return self

        def con_monto(self, monto: Decimal) -> "ExtraccionBuilder":
            for campo in self.campos:
                if campo.nombre == "monto_reclamado":
                    campo.valor = str(monto)
            return self

        def marcar_ausente(self, nombre: str) -> "ExtraccionBuilder":
            for campo in self.campos:
                if campo.nombre == nombre:
                    campo.ausente = True
                    campo.valor = None
            return self

        def build(self) -> ExtraccionValidada:
            return ExtraccionValidada(campos=self.campos)

    return ExtraccionBuilder()


# Hypothesis strategies para PBT-03

def st_fecha_valida() -> st.SearchStrategy[date]:
    """Genera fechas válidas dentro de vigencia 2025."""
    return st.dates(
        min_value=date(2025, 1, 1),
        max_value=date(2025, 12, 31)
    )


def st_monto_valido() -> st.SearchStrategy[Decimal]:
    """Genera montos válidos (0 a 100000 COP, enteros)."""
    return st.integers(min_value=0, max_value=100000).map(Decimal)


def st_tipo_siniestro() -> st.SearchStrategy[str]:
    """Genera tipos de siniestro válidos."""
    return st.sampled_from([
        TipoSiniestro.AUTO_COLISION.value,
        TipoSiniestro.AUTO_HURTO.value,
        TipoSiniestro.HOGAR_AGUA.value
    ])


def st_extraccion_valida(
    fecha: date = None,
    monto: Decimal = None,
    tipo: str = None
) -> st.SearchStrategy[ExtraccionValidada]:
    """Genera ExtraccionValidada válida con valores específicos o generados."""
    return st.just(ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="fecha_siniestro",
                valor=(fecha or date(2025, 6, 15)).isoformat(),
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:0"),
                ausente=False
            ),
            CampoExtraido(
                nombre="tipo_siniestro",
                valor=tipo or TipoSiniestro.AUTO_COLISION.value,
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:1"),
                ausente=False
            ),
            CampoExtraido(
                nombre="monto_reclamado",
                valor=str(monto or Decimal("10000")),
                origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="test:2"),
                ausente=False
            )
        ]
    ))

