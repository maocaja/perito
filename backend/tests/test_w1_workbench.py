"""Tests W1 — Workbench shell 3-columnas.

Invariantes: server-rendered (ADR-001), passive (P1: cero decisión en cliente), retro-compat (bandeja/
detalle siguen vivos), swap HTMX del caso sin recargar el shell.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- shell ----------

def test_workbench_200_y_tres_columnas(client):
    r = client.get("/workbench")
    assert r.status_code == 200
    # las 3 regiones del shell
    assert 'class="wb"' in r.text
    assert 'wb-cola' in r.text        # izquierda
    assert 'id="wb-caso"' in r.text   # centro+derecha


def test_workbench_lista_casos_en_cola(client):
    r = client.get("/workbench")
    total = len(get_caso_repository().list())
    assert r.text.count("wb-cola-item") >= total  # una fila por caso (clase por ítem)


def test_workbench_arranca_con_primer_caso_en_centro(client):
    """La estación no arranca vacía: el primer caso ya se ve en el centro."""
    r = client.get("/workbench")
    assert 'wb-centro' in r.text
    assert 'Datos del siniestro' in r.text  # panel del caso presente


def test_workbench_caso_explicito_por_query(client):
    caso = _un_caso()
    r = client.get(f"/workbench?caso_id={caso.id}")
    assert r.status_code == 200
    assert caso.id[:8] in r.text  # el header muestra el id corto del caso pedido


# ---------- swap HTMX del caso ----------

def test_workbench_caso_parcial_200(client):
    caso = _un_caso()
    r = client.get(f"/workbench/caso/{caso.id}")
    assert r.status_code == 200
    assert 'wb-centro' in r.text and 'wb-derecha' in r.text
    # es un PARCIAL: no trae el shell completo (sin <html>/sidebar)
    assert "<html" not in r.text and 'class="sidebar"' not in r.text


def test_workbench_caso_inexistente_404(client):
    assert client.get("/workbench/caso/no-existe").status_code == 404


def test_workbench_caso_sin_extraccion_renderiza(client):
    """Edge case: un caso con extraccion=None NO revienta el render (guard Jinja)."""
    repo = get_caso_repository()
    caso = repo.list()[0]
    repo.save(caso.model_copy(update={"extraccion": None}))
    r = client.get(f"/workbench/caso/{caso.id}")
    assert r.status_code == 200
    assert "Datos del siniestro" in r.text
    # Fase 0: sin extracción la tabla fusionada no revienta; muestra los requeridos como REQUERIDO (no crash).
    assert "REQUERIDO" in r.text


def test_cola_item_apunta_al_parcial_via_htmx(client):
    """Cada ítem de la cola hace hx-get del parcial al #wb-caso (swap sin recargar el shell)."""
    r = client.get("/workbench")
    assert 'hx-get="/workbench/caso/' in r.text
    assert 'hx-target="#wb-caso"' in r.text


# ---------- P1 / passive ----------

def test_radicar_deshabilitado_si_no_listo(client):
    """P1: 'Radicar' (aprobar) deshabilitado salvo LISTO_PARA_APROBAR — el gate real es HITL."""
    caso = next((c for c in get_caso_repository().list() if c.estado != EstadoCaso.LISTO_PARA_APROBAR), None)
    if caso is None:
        pytest.skip("todos los casos sembrados están LISTO_PARA_APROBAR")
    r = client.get(f"/workbench/caso/{caso.id}")
    assert "disabled" in r.text  # el botón Radicar viene deshabilitado


def test_workbench_no_muta_estado(client):
    """GET a la workbench nunca cambia el estado de un caso (passive)."""
    antes = {c.id: c.estado for c in get_caso_repository().list()}
    client.get("/workbench")
    client.get(f"/workbench/caso/{_un_caso().id}")
    despues = {c.id: c.estado for c in get_caso_repository().list()}
    assert antes == despues


# ---------- retro-compat ----------

def test_workbench_es_la_unica_superficie_del_operador(client):
    # W20/A6+A7: el board `/casos` y la página `detalle` `/casos/{id}` se retiraron; `/` redirige a la Workbench.
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and "/workbench" in r.headers["location"]
    assert client.get("/casos").status_code == 404
    assert client.get(f"/casos/{_un_caso().id}").status_code == 404


def test_nav_incluye_workbench(client):
    assert 'href="/workbench' in client.get("/workbench").text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
