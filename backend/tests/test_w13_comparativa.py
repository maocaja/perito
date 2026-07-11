"""Tests W13 — Vista comparativa multi-correo.

Provider (DIP): interfaz que U7/U8/M1 volverán real (clustering de correos del mismo expediente). P7: mock
rotulado. P5: fuentes/cambios redactados, sin PII cruda.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import comparativa


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


_MIN_FUENTES = 2  # una comparativa tiene sentido con ≥2 correos


def test_comparativa_devuelve_fuentes_y_cambios():
    c = comparativa.comparativa_de(_un_caso())
    assert c["origen"] == "demo"          # P7: rotulado
    assert _MIN_FUENTES <= len(c["fuentes"]) <= comparativa.MAX_FUENTES  # varios, pero acotado (P4)
    assert 1 <= len(c["cambios"]) <= comparativa.MAX_CAMBIOS
    assert all(isinstance(f, comparativa.FuenteCorreo) for f in c["fuentes"])
    assert all(isinstance(ch, comparativa.CambioDetectado) for ch in c["cambios"])
    assert all(f.etiqueta and f.fecha for f in c["fuentes"])  # campos presentes, no None


def test_comparativa_redacta_en_el_render(client):
    """P5: fuentes/cambios pasan por |redact (estructura presente, sin PII cruda). Fase 1: en el drawer."""
    html = client.get(f"/workbench/comparativa/{_un_caso().id}").text
    assert 'class="wb-comp-f-res"' in html  # la estructura del resumen redactado
    assert "Cambios detectados por la IA" in html


def test_render_comparativa(client):
    caso = _un_caso()
    # Fase 1: el caso muestra un AVISO con el trigger; la comparativa completa vive en el drawer (endpoint).
    caso_html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Comparar correos" in caso_html
    assert 'hx-get="/workbench/comparativa/' in caso_html
    # el contenido completo lo sirve el endpoint del drawer
    drawer = client.get(f"/workbench/comparativa/{caso.id}").text
    assert "Vista comparativa" in drawer
    assert "Cambios detectados por la IA" in drawer
    assert "Se adjuntó la factura de reparación." in drawer
    assert "wb-comp" in drawer


def test_comparativa_rotulada_demo(client):
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    # la sección comparativa lleva el badge demo
    assert 'data-slot="comparativa"' in html and "badge-demo" in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
