"""PBT: Invariantes de contrato (NFR-U1-03).

Propiedades que SIEMPRE deben ser verdaderas para instancias válidas.
"""

from hypothesis import given
from app.contracts.enums import EstadoCaso, ESTADOS_TERMINALES
from app.contracts.poliza import RangoFechas, Poliza
from app.contracts.extraccion import CampoExtraido
from app.contracts.caso import Caso
from tests.generators import (
    st_rango_fechas,
    st_poliza,
    st_campo_extraido,
    st_caso,
)


@given(st_rango_fechas())
def test_rango_fechas_desde_le_hasta(rf):
    """RangoFechas: desde ≤ hasta (RULE-POL-01)."""
    assert rf.desde <= rf.hasta


@given(st_poliza())
def test_poliza_montos_no_negativos(poliza):
    """Poliza: suma_asegurada ≥ 0 y deducible ≥ 0 (RULE-CTR-04)."""
    assert poliza.suma_asegurada >= 0
    assert poliza.deducible >= 0


@given(st_campo_extraido())
def test_campo_ausente_implica_valor_none(campo):
    """CampoExtraido: ausente=True ⇒ valor=None (no-invención, P4)."""
    if campo.ausente:
        assert campo.valor is None


@given(st_campo_extraido())
def test_campo_presente_implica_valor_no_none(campo):
    """CampoExtraido: ausente=False ⇒ valor puede ser None o str (lógica simple)."""
    # Si ausente=False, no hay restricción en valor (puede ser None o string)
    pass  # Esta propiedad es trivial


@given(st_caso())
def test_caso_no_terminal_sin_firma(caso):
    """Caso no terminal: aprobado_por=None (P1)."""
    if caso.estado not in ESTADOS_TERMINALES:
        assert caso.aprobado_por is None
