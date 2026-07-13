"""Tests Fase 2 — Corrección inline en la Workbench (server-authoritative).

El endpoint HTMX `/workbench/corregir/{id}` reusa `aplicar_correccion`: el SERVIDOR re-corre C4 + motor
determinístico (P2, la cobertura NO la decide el cliente), exige firma (P1), nunca alcanza terminal, 409 si
el caso ya fue decidido. Devuelve el partial `#wb-caso` (sin recarga).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.contracts.enums import EstadoCaso
from app.dashboard import vista_caso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _con_extraccion():
    for c in get_caso_repository().list():
        if c.extraccion and c.estado not in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO):
            return c
    return get_caso_repository().list()[0]


# ---------- P1: firma obligatoria ----------

def test_correccion_sin_firma_400(client):
    caso = _con_extraccion()
    r = client.post(f"/workbench/corregir/{caso.id}", data={"numero_poliza": "POL-X"})
    assert r.status_code == 400  # 🔒 P1: sin firma no hay corrección


def test_correccion_404_si_no_existe(client):
    r = client.post("/workbench/corregir/no-existe", data={"usuario": "Ana", "numero_poliza": "X"})
    assert r.status_code == 404


# ---------- happy: devuelve el partial + el servidor re-dictamina ----------

def test_correccion_devuelve_partial_y_reejecuta_motor(client):
    caso = _con_extraccion()
    poliza = next((c.valor for c in caso.extraccion.campos if c.nombre == "numero_poliza" and not c.ausente), "POL-DEMO-0002")
    r = client.post(f"/workbench/corregir/{caso.id}",
                    data={"usuario": "Ana Ríos", "rol": "CUMPLIMIENTO",
                          "numero_poliza": poliza or "POL-DEMO-0002",
                          "monto_reclamado": "12345"})
    assert r.status_code == 200
    assert "wb-centro" in r.text            # devolvió el partial del caso (no un redirect)
    # el servidor aplicó la corrección y re-dictaminó (motor determinístico, P2)
    actualizado = get_caso_repository().get(caso.id)
    monto = next((c for c in actualizado.extraccion.campos if c.nombre == "monto_reclamado"), None)
    assert monto and monto.valor == "12345"
    assert monto.origen.tipo.value == "HUMANO"   # P3: corrección humana auditable
    assert actualizado.estado not in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)  # 🔒 P1: nunca terminal


def test_correccion_no_alcanza_terminal(client):
    """🔒 P1: por más que se corrija, el caso queda en LISTO_PARA_APROBAR / REQUIERE_REVISION, nunca terminal."""
    caso = _con_extraccion()
    r = client.post(f"/workbench/corregir/{caso.id}",
                    data={"usuario": "Ana", "numero_poliza": "POL-DEMO-0002"})
    assert r.status_code == 200
    est = get_caso_repository().get(caso.id).estado
    assert est in (EstadoCaso.LISTO_PARA_APROBAR, EstadoCaso.REQUIERE_REVISION)


# ---------- 🔒 P1: 409 si el caso ya fue decidido ----------

def test_correccion_terminal_409(client):
    """Un caso ya APROBADO no se puede corregir (409) — la decisión firmada no se re-abre por inline-edit."""
    from app.hitl.c8 import aprobar
    caso = _con_extraccion()
    caso = caso.model_copy(update={"estado": EstadoCaso.LISTO_PARA_APROBAR})
    get_caso_repository().save(caso)
    aprobado = aprobar(caso, "Firmante")   # → APROBADO con aprobado_por
    get_caso_repository().save(aprobado)
    r = client.post(f"/workbench/corregir/{aprobado.id}", data={"usuario": "Ana", "numero_poliza": "X"})
    assert r.status_code == 409


# ---------- UI: el form de corrección está presente y pre-llenado ----------

def test_form_corregir_presente_y_prellenado(client):
    caso = _con_extraccion()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'hx-post="/workbench/corregir/' in html and 'hx-target="#wb-caso"' in html
    assert "Guardar y verificar" in html   # L1: acción con resultado humano (antes "Corregir y recalcular")
    # campos_corregibles pre-llena con los valores actuales
    corregibles = vista_caso.campos_corregibles(caso)
    assert len(corregibles) == len(vista_caso.CAMPOS)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
