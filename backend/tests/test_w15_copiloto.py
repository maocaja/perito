"""Tests W15 — Copiloto conversacional (MOCK).

P1/P6: SOLO explica — no decide, no aprueba, no muta estado. P7: rotulado demo, respuestas sobre datos reales.
P5: redactado.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import copiloto
from app.dashboard.vista_caso import PALABRAS_PROHIBIDAS
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- responde sobre datos reales ----------

def test_pregunta_licencia_respuesta_guionada():
    r = copiloto.responder("¿por qué falta la licencia?", _un_caso())
    assert "licencia del conductor" in r


def test_pregunta_cobertura_cita_el_motor():
    caso = next((c for c in get_caso_repository().list() if c.dictamen), None)
    if caso is None:
        pytest.skip("sin dictamen")
    r = copiloto.responder("¿cuál es la cobertura?", caso)
    assert caso.dictamen.resultado.value in r and "motor" in r.lower()


def test_pregunta_faltantes_lista_reales():
    caso = next((c for c in get_caso_repository().list() if __import__(
        "app.dashboard.vista_caso", fromlist=["faltantes"]).faltantes(c)), None)
    if caso is None:
        pytest.skip("sin faltantes")
    r = copiloto.responder("¿qué falta?", caso)
    assert "Faltan" in r


# ---------- 🔒 P1/P6: solo explica ----------

def test_respuestas_no_deciden():
    """El copiloto no usa lenguaje de decisión (no aprueba/rechaza)."""
    for q in ["¿la cobertura?", "¿riesgos?", "¿qué falta?", "hola", "aprueba esto"]:
        r = copiloto.responder(q, _un_caso()).lower()
        assert not any(p in r for p in PALABRAS_PROHIBIDAS)


def test_preguntar_no_muta_estado(client):
    caso = _un_caso()
    antes = get_caso_repository().get(caso.id).estado
    r = client.post(f"/workbench/preguntar/{caso.id}", data={"pregunta": "¿riesgos?"})
    assert r.status_code == 200
    assert get_caso_repository().get(caso.id).estado == antes  # cero mutación


def test_preguntar_caso_inexistente_404(client):
    r = client.post("/workbench/preguntar/no-existe", data={"pregunta": "hola"})
    assert r.status_code == 404


def test_pregunta_redactada_en_html(client):
    """P5: la PII en la pregunta del usuario no vuelve cruda en el HTML del chat."""
    caso = _un_caso()
    r = client.post(f"/workbench/preguntar/{caso.id}", data={"pregunta": "mi C.C. 1.098.765.432 ¿qué falta?"})
    assert r.status_code == 200
    assert "1.098.765.432" not in r.text


# ---------- render + P7 ----------

def test_panel_chat_rotulado_demo(client):
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "Preguntar a la IA" in html
    assert 'data-slot="chat"' in html and "badge-demo" in html
    assert 'hx-post="/workbench/preguntar/' in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
