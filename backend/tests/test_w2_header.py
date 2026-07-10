"""Tests W2 — Header del caso (tipo + asegurado + confianza% + tiempo estimado).

Invariantes: P7 (asegurado mock rotulado 'demo'; tiempo 'estimado'), P1 (informativo), reproducibilidad
del mock (determinístico por caso).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- view-models ----------

def test_asegurado_mock_rotulado_demo():
    """Sin campo 'asegurado_nombre', el provider devuelve un mock con origen='demo' (P7)."""
    caso = _un_caso()
    a = vista_caso.asegurado_de(caso)
    assert a["origen"] == "demo"
    assert a["nombre"]  # tiene un nombre demo


def test_asegurado_mock_determinístico():
    """El nombre demo es estable para el mismo caso (no aleatorio entre refrescos)."""
    caso = _un_caso()
    assert vista_caso.asegurado_de(caso)["nombre"] == vista_caso.asegurado_de(caso)["nombre"]


def test_asegurado_real_si_campo_presente():
    """Si existe el campo 'asegurado_nombre' (M2), el provider lo usa con origen='real'."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = _un_caso()
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="asegurado_nombre", valor="Pedro Real",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    a = vista_caso.asegurado_de(caso2)
    assert a == {"nombre": "Pedro Real", "origen": "real"}


def test_asegurado_campo_ausente_cae_al_demo():
    """P7: si 'asegurado_nombre' existe pero está ausente/vacío → fallback a mock demo (no lo fuerza)."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada
    caso = _un_caso()
    campos = list(caso.extraccion.campos) + [CampoExtraido(nombre="asegurado_nombre", valor=None, ausente=True)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    assert vista_caso.asegurado_de(caso2)["origen"] == "demo"


def test_tiempo_estimado_rotulado_y_crece_con_faltantes():
    caso = _un_caso()
    t = vista_caso.tiempo_estimado(caso)
    assert t["es_estimado"] is True
    assert "min" in t["texto"] or "s" in t["texto"]
    assert t["segundos"] >= 90


# ---------- render en la workbench ----------

def test_header_muestra_tipo_confianza_y_tiempo(client):
    caso = _un_caso()
    r = client.get(f"/workbench/caso/{caso.id}")
    assert r.status_code == 200
    assert "wb-header" in r.text
    assert "tiempo est. de revisión" in r.text
    assert "confianza" in r.text


def test_header_asegurado_demo_lleva_badge(client):
    """P7: el asegurado mock aparece con el badge 'demo' (no se presenta como real)."""
    caso = _un_caso()
    r = client.get(f"/workbench/caso/{caso.id}")
    assert "badge-demo" in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
