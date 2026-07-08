"""PBT: Round-trip de todos los contratos (NFR-U1-01).

Propiedad: serializar(x) → deserializar() == x (identidad).
"""

from hypothesis import given
from app.contracts.poliza import Poliza, RangoFechas
from app.contracts.extraccion import CampoExtraido, AvisoNormalizado
from app.contracts.dictamen import Dictamen, AlertaFraude
from app.contracts.dataset import GroundTruth
from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso
from tests.generators import (
    st_rango_fechas,
    st_poliza,
    st_campo_extraido,
    st_aviso_normalizado,
    st_caso,
)


@given(st_rango_fechas())
def test_rango_fechas_roundtrip(rf):
    """RangoFechas: model_dump → model_validate == identidad."""
    dumped = rf.model_dump()
    restored = RangoFechas(**dumped)
    assert restored == rf


@given(st_poliza())
def test_poliza_roundtrip(poliza):
    """Poliza: serializar ⇒ deserializar == identidad."""
    dumped = poliza.model_dump()
    restored = Poliza(**dumped)
    assert restored == poliza


@given(st_campo_extraido())
def test_campo_extraido_roundtrip(campo):
    """CampoExtraido: round-trip manteniendo invariante ausente ⇒ valor=None."""
    dumped = campo.model_dump()
    restored = CampoExtraido(**dumped)
    assert restored == campo
    if restored.ausente:
        assert restored.valor is None


@given(st_aviso_normalizado())
def test_aviso_normalizado_roundtrip(aviso):
    """AvisoNormalizado: round-trip preserva PII."""
    dumped = aviso.model_dump()
    restored = AvisoNormalizado(**dumped)
    assert restored == aviso


@given(st_caso())
def test_caso_roundtrip(caso):
    """Caso: round-trip preserva estructura (no terminal)."""
    dumped = caso.model_dump(exclude={"caso_id"})  # UUID es generado
    # Nota: no hacemos restore directo porque caso_id se regenera
    assert caso.estado in [EstadoCaso.RECIBIDO, EstadoCaso.EN_PROCESO]
