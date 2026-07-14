"""Tests W10 — Flujo teclado-first (ENTER → siguiente).

Invariantes: P1 (los atajos NO bypasean el gate — Radicar sigue exigiendo firma y estado LISTO en el
servidor); "avanzar=1" carga el siguiente caso de la cola; ADR-001 (JS mínimo, sin decisión en cliente).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _cola_ordenada():
    return sorted(get_caso_repository().list(), key=lambda c: c.timestamp_actualizacion, reverse=True)


# ---------- avanzar → siguiente ----------

def test_avanzar_carga_el_siguiente(client):
    cola = _cola_ordenada()
    if len(cola) < 2:
        pytest.skip("se necesitan ≥2 casos")
    primero, segundo = cola[0], cola[1]
    r = client.get(f"/workbench?caso_id={primero.id}&avanzar=1")
    assert r.status_code == 200
    # el header del caso activo muestra el id corto del SIGUIENTE, no del primero
    assert segundo.id in r.text


def test_avanzar_en_el_ultimo_se_queda(client):
    cola = _cola_ordenada()
    ultimo = cola[-1]
    r = client.get(f"/workbench?caso_id={ultimo.id}&avanzar=1")
    assert r.status_code == 200
    assert ultimo.id in r.text  # no hay siguiente → se queda en el último


# ---------- teclado presente pero sin bypass ----------

def test_hints_de_teclado_presentes(client):
    r = client.get("/workbench")
    assert "wb-keys" in r.text
    assert "radicar" in r.text and "escalar" in r.text


def test_atajo_escalar_apunta_al_endpoint(client):
    """El atajo E hace requestSubmit del form /escalar; la escala redirige con avanzar=1 (siguiente)."""
    html = client.get(f"/workbench/caso/{_cola_ordenada()[0].id}").text
    assert 'action="/casos/' in html and '/escalar"' in html
    caso = _cola_ordenada()[0]
    r = client.post(f"/casos/{caso.id}/escalar", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 303 and "avanzar=1" in r.headers["location"]


def test_js_minimo_sin_logica_de_decision(client):
    """ADR-001/P1: el JS de teclado no decide cobertura/estado; solo navega y hace submit de forms del server."""
    html = client.get("/workbench").text
    # el keymap sólo hace requestSubmit / click / scrollIntoView — nada de fetch a endpoints de decisión
    assert "requestSubmit" in html
    for prohibido in ("aprobado", "motor_cobertura", "fetch("):
        assert prohibido not in html


def test_enter_no_bypasea_gate_radicar_desde_no_listo(client):
    """🔒 P1: aunque el teclado dispare Radicar, el servidor rechaza (409) un caso no-LISTO."""
    from app.contracts.enums import EstadoCaso
    caso = next((c for c in get_caso_repository().list() if c.estado != EstadoCaso.LISTO_PARA_APROBAR), None)
    if caso is None:
        pytest.skip("todos LISTO")
    # el atajo equivale a postear /radicar con la firma
    r = client.post(f"/casos/{caso.id}/radicar", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 409


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
