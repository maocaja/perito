"""Tests del Bolt `firma-unica-sesion` — identidad de sesión ligera (D).

La firma sale de la SESIÓN (la UI se identifica una vez); `usuario` (form) queda como fallback de compat.
Gate: sin firma → 400; con sesión → aprobado_por = firmante; el detalle del caso no tiene campo de firma.
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


def _un_listo():
    return next((c for c in get_caso_repository().list() if c.estado == EstadoCaso.LISTO_PARA_APROBAR), None)


def test_identificar_guarda_firmante_y_muestra_chip(client):
    """Sin identidad → overlay '¿Quién eres?'; tras identificarse → chip 'Firmando como' y sin overlay."""
    html = client.get("/workbench?rol=ANALISTA").text
    assert "¿Quién eres?" in html                      # captura única al entrar
    r = client.post("/workbench/identificar",
                    data={"firmante": "Ana Pérez", "next": "/workbench?rol=ANALISTA"}, follow_redirects=False)
    assert r.status_code == 303
    html = client.get("/workbench?rol=ANALISTA").text
    assert "Firmando como" in html and "Ana Pérez" in html
    assert "¿Quién eres?" not in html                  # ya no vuelve a pedir identidad


def test_accion_usa_firma_de_sesion(client):
    """Tras identificarse, radicar SIN enviar `usuario` firma con la identidad de sesión (aprobado_por)."""
    caso = _un_listo()
    assert caso is not None
    client.post("/workbench/identificar", data={"firmante": "Ana Pérez"})
    r = client.post(f"/casos/{caso.id}/radicar", data={}, follow_redirects=False)   # sin usuario
    assert r.status_code == 303
    actualizado = get_caso_repository().get(caso.id)
    assert actualizado.estado == EstadoCaso.APROBADO
    assert actualizado.aprobado_por == "Ana Pérez"     # firmó la identidad de sesión


def test_accion_sin_firma_ni_sesion_400(client):
    """🔒 P1 fail-closed: sin identidad de sesión NI `usuario` → 400; el caso queda intacto."""
    caso = _un_listo()
    r = client.post(f"/casos/{caso.id}/radicar", data={}, follow_redirects=False)
    assert r.status_code == 400
    assert get_caso_repository().get(caso.id).estado == EstadoCaso.LISTO_PARA_APROBAR


def test_fallback_usuario_sigue_funcionando(client):
    """Compat (P7): sin sesión, `usuario` (form) sigue firmando — para callers programáticos/tests."""
    caso = _un_listo()
    r = client.post(f"/casos/{caso.id}/radicar", data={"usuario": "Bob"}, follow_redirects=False)
    assert r.status_code == 303
    assert get_caso_repository().get(caso.id).aprobado_por == "Bob"


def test_detalle_sin_campo_de_firma(client):
    """El detalle del caso ya no tiene campo de firma inline (identidad de sesión, no por acción)."""
    caso = _un_listo()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'id="wb-firma"' not in html
    assert "Firma del analista" not in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
