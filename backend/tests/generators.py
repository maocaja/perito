"""Generadores Hypothesis para Property-Based Testing (PBT-07).

Produc strategies tipadas que generan instancias válidas de contratos.
Se usan en test_contracts_* para ejercer propiedades invariantes.
"""

from datetime import date, timedelta
from decimal import Decimal
from hypothesis import strategies as st
from typing import Any

from app.contracts.enums import (
    EstadoCaso,
    ResultadoCobertura,
    CalidadDoc,
    RolUsuario,
    TipoClausula,
    TipoOrigen,
)
from app.contracts.poliza import RangoFechas, Clausula, Poliza
from app.contracts.extraccion import EvidenciaOrigen, CampoExtraido, ExtraccionValidada, AvisoNormalizado
from app.contracts.dictamen import Dictamen, AlertaFraude, Cotas
from app.contracts.dataset import FilaEntrada, GroundTruth
from app.contracts.caso import Usuario, Caso


@st.composite
def st_rango_fechas(draw) -> RangoFechas:
    """Estrategia: RangoFechas válido."""
    today = date.today()
    desde = draw(st.dates(min_value=today - timedelta(days=365), max_value=today))
    hasta = draw(st.dates(min_value=desde, max_value=today + timedelta(days=365)))
    return RangoFechas(desde=desde, hasta=hasta)


@st.composite
def st_clausula(draw) -> Clausula:
    """Estrategia: Clausula válida."""
    return Clausula(
        id=draw(st.text(min_size=1, max_size=20)),
        texto=draw(st.text(min_size=1, max_size=500)),
        tipo=draw(st.sampled_from(list(TipoClausula))),
        referencia=draw(st.text(min_size=1, max_size=100)),
    )


@st.composite
def st_poliza(draw) -> Poliza:
    """Estrategia: Poliza válida."""
    return Poliza(
        numero=draw(st.text(min_size=1, max_size=20)),
        vigencia=draw(st_rango_fechas()),
        coberturas_contratadas=draw(st.lists(st.text(min_size=1, max_size=20))),
        exclusiones=draw(st.lists(st.text(min_size=1, max_size=20))),
        suma_asegurada=draw(st.decimals(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False)),
        deducible=draw(st.decimals(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False)),
        clausulas=draw(st.lists(st_clausula(), max_size=5)),
    )


@st.composite
def st_campo_extraido(draw) -> CampoExtraido:
    """Estrategia: CampoExtraido válido (ausente=True ⇒ valor=None)."""
    ausente = draw(st.booleans())
    return CampoExtraido(
        nombre=draw(st.text(min_size=1, max_size=50)),
        valor=None if ausente else draw(st.text(min_size=1, max_size=100)),
        origen=None,  # simplificado
        confianza=None,
        ausente=ausente,
    )


@st.composite
def st_aviso_normalizado(draw) -> AvisoNormalizado:
    """Estrategia: AvisoNormalizado válido."""
    return AvisoNormalizado(
        texto_crudo=draw(st.text(min_size=1, max_size=500)),
        calidad=draw(st.sampled_from(list(CalidadDoc))),
    )


@st.composite
def st_usuario(draw) -> Usuario:
    """Estrategia: Usuario válido."""
    return Usuario(
        usuario_id=draw(st.uuids()).hex,
        rol=draw(st.sampled_from(list(RolUsuario))),
    )


@st.composite
def st_caso(draw) -> Caso:
    """Estrategia: Caso válido (estado no terminal, sin firma)."""
    return Caso(
        aviso=draw(st_aviso_normalizado()),
        estado=draw(st.sampled_from([EstadoCaso.RECIBIDO, EstadoCaso.EN_PROCESO])),
        extraccion=None,
    )
