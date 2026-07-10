"""Tests W12 — Evidencia clickable → salto a la fuente (visor). 🔒 P5.

Fail-closed: campo sin ancla → "sin fuente localizada" (nunca salto falso, P7). P5: el visor sirve
contenido mock/redactado, cita el documento por su etiqueta (no nombre crudo), nunca PII.
"""

import pytest
from urllib.parse import quote
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import evidencia


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- provider ----------

def test_ancla_de_campo_conocido():
    a = evidencia.ancla_de(_un_caso(), "Fecha del evento")
    assert isinstance(a, evidencia.Ancla)
    assert a.documento == "Denuncia Policía" and a.pagina == 2 and a.origen == "demo"


def test_ancla_de_campo_desconocido_es_none():
    """Fail-closed: un campo sin fuente localizada → None (no se inventa un ancla)."""
    assert evidencia.ancla_de(_un_caso(), "Campo Inexistente XYZ") is None


def test_zona_determinística():
    a = evidencia.ancla_de(_un_caso(), "Placa")
    b = evidencia.ancla_de(_un_caso(), "Placa")
    assert a.zona_top == b.zona_top  # estable, no aleatorio


# ---------- ruta / visor ----------

def test_visor_muestra_la_fuente(client):
    caso = _un_caso()
    r = client.get(f"/workbench/evidencia/{caso.id}?campo={quote('Fecha del evento')}")
    assert r.status_code == 200
    assert "Denuncia Policía" in r.text
    assert "Campo extraído" in r.text
    assert "wb-ev-hl" in r.text        # el resaltado
    assert "badge-demo" in r.text       # rotulado


def test_visor_sin_ancla_avisa_no_salta(client):
    """Fail-closed en la UI: campo sin ancla → aviso 'sin fuente localizada', no un visor falso."""
    caso = _un_caso()
    r = client.get(f"/workbench/evidencia/{caso.id}?campo={quote('Campo Inexistente')}")
    assert r.status_code == 200
    assert "Sin fuente localizada" in r.text
    assert "wb-ev-hl" not in r.text     # no hay visor falso


def test_campos_son_clickables_al_visor(client):
    """Los campos de Información extraída disparan el visor por HTMX (salto a la fuente)."""
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert 'hx-get="/workbench/evidencia/' in html
    assert 'hx-target="#wb-evidencia"' in html


@pytest.mark.parametrize("campo", ["Vehículo", "Lugar", "Teléfono", "Fecha del evento"])
def test_campos_con_ancla_renderizan_visor(client, campo):
    """Los campos con fuente (incl. ricos con acentos, urlencode roundtrip) abren el visor."""
    caso = _un_caso()
    r = client.get(f"/workbench/evidencia/{caso.id}?campo={quote(campo)}")
    assert r.status_code == 200
    assert "Sin fuente localizada" not in r.text
    assert "wb-ev-hl" in r.text


def test_visor_no_expone_pii_ni_nombre_crudo(client):
    """P5: el visor cita el documento por etiqueta; ningún nombre de archivo crudo aparece."""
    caso = _un_caso()
    from app.dashboard import documentos
    r = client.get(f"/workbench/evidencia/{caso.id}?campo={quote('Vehículo')}")
    for d in documentos.documentos_de(caso):
        assert d.nombre not in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
