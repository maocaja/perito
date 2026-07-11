"""Tests W9 — Acciones ampliadas del operador. 🔒 P1.

Central: ninguna acción nueva alcanza estado terminal sin humano; Radicar exige firma; enviar-a-fraude es
routing (no cambia dictamen/estado); escalar → REQUIERE_REVISION (no terminal).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


def _listo():
    for c in get_caso_repository().list():
        if c.estado == EstadoCaso.LISTO_PARA_APROBAR:
            return c
    return None


# ---------- 🔒 P1: firma obligatoria ----------

@pytest.mark.parametrize("accion", ["radicar", "escalar", "enviar_fraude", "solicitar_docs", "guardar_borrador"])
def test_accion_sin_usuario_400(client, accion):
    """P1: toda acción exige firma (usuario) → 400 si falta."""
    caso = _un_caso()
    r = client.post(f"/casos/{caso.id}/{accion}", data={}, follow_redirects=False)
    assert r.status_code == 400


# ---------- Radicar (terminal solo con firma) ----------

def test_radicar_aprueba_con_firma(client):
    caso = _listo()
    if caso is None:
        pytest.skip("sin caso LISTO")
    r = client.post(f"/casos/{caso.id}/radicar", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 303 and "/workbench" in r.headers["location"]
    actualizado = get_caso_repository().get(caso.id)
    assert actualizado.estado == EstadoCaso.APROBADO and actualizado.aprobado_por == "ana"


def test_radicar_desde_no_listo_409(client):
    """🔒 P1: radicar desde un estado ≠ LISTO_PARA_APROBAR se rechaza server-side (409), no salta revisión."""
    caso = next((c for c in get_caso_repository().list() if c.estado != EstadoCaso.LISTO_PARA_APROBAR), None)
    if caso is None:
        pytest.skip("todos los casos están LISTO")
    r = client.post(f"/casos/{caso.id}/radicar", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 409
    assert get_caso_repository().get(caso.id).estado == caso.estado  # intacto


# ---------- Escalar (no terminal) ----------

def test_escalar_va_a_requiere_revision_no_terminal(client):
    caso = _listo() or _un_caso()
    r = client.post(f"/casos/{caso.id}/escalar", data={"usuario": "ana", "motivo": "revisar placa"},
                    follow_redirects=False)
    assert r.status_code == 303
    est = get_caso_repository().get(caso.id).estado
    assert est == EstadoCaso.REQUIERE_REVISION
    assert est not in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)


# ---------- Enviar a fraude (routing, P6) ----------

def test_enviar_fraude_es_routing_no_decide(client):
    """🔒 P6: anota derivado_siu_por; NO cambia estado ni dictamen."""
    caso = _un_caso()
    estado0, dict0 = caso.estado, caso.dictamen
    r = client.post(f"/casos/{caso.id}/enviar_fraude", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 303
    act = get_caso_repository().get(caso.id)
    assert act.derivado_siu_por == "ana"
    assert act.estado == estado0                     # estado intacto
    assert act.dictamen == dict0                      # dictamen intacto
    assert act.estado not in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)


# ---------- Solicitar docs / borrador (no terminal) ----------

def test_solicitar_docs_prepara_borrador_mock(client):
    caso = next((c for c in get_caso_repository().list() if vista_caso.faltantes(c)), None) or _un_caso()
    r = client.post(f"/casos/{caso.id}/solicitar_docs", data={"usuario": "ana"}, follow_redirects=False)
    assert r.status_code == 303
    act = get_caso_repository().get(caso.id)
    assert act.solicitud_docs is not None and "[demo · no enviado]" in act.solicitud_docs  # mock rotulado
    assert act.estado not in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)


def test_guardar_borrador_no_cambia_estado(client):
    caso = _un_caso()
    estado0 = caso.estado
    r = client.post(f"/casos/{caso.id}/guardar_borrador", data={"usuario": "ana", "nota": "pendiente placa"},
                    follow_redirects=False)
    assert r.status_code == 303
    act = get_caso_repository().get(caso.id)
    assert "pendiente placa" in act.nota_operador
    assert act.estado == estado0


# ---------- render ----------

def test_workbench_muestra_acciones(client):
    r = client.get(f"/workbench/caso/{_un_caso().id}")
    for accion in ("Radicar caso", "Escalar a fraude", "Escalar a revisión", "Solicitar documentos", "Guardar"):
        assert accion in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
