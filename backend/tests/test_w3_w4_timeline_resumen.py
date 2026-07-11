"""Tests W3 (timeline visual) + W4 (resumen narrativo).

W3: pasos reales de la traza + conteos de docs (mock rotulado). W4: prosa determinística, P1 fail-closed.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.dashboard.vista_caso import PALABRAS_PROHIBIDAS


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


# ---------- W3 timeline ----------

def test_conteo_adjuntos_mock_rotulado():
    d = vista_caso.conteo_adjuntos(_un_caso())
    assert d["origen"] == "demo"
    assert d["pdfs"] >= 1 and d["fotos"] >= 1


def test_timeline_arranca_en_correo_y_lee_docs():
    pasos = vista_caso.timeline(_un_caso(), traza=None)
    textos = [p["texto"] for p in pasos]
    assert textos[0] == "Correo recibido"
    assert any("PDF" in t for t in textos)
    assert any("fotografía" in t for t in textos)
    # los pasos de docs van rotulados demo
    assert any(p["demo"] for p in pasos if "PDF" in p["texto"])


def test_timeline_incluye_estado_final():
    pasos = vista_caso.timeline(_un_caso(), traza=None)
    assert any(p["texto"] in ("Caso listo", "Escalado a revisión humana") for p in pasos)


@pytest.mark.parametrize("estado,esperado", [
    ("APROBADO", "Caso aprobado por humano"),
    ("RECHAZADO", "Caso rechazado por humano"),
])
def test_timeline_estados_terminales(estado, esperado):
    """P7: un caso resuelto muestra su estado terminal real, no termina abrupto."""
    from app.contracts.enums import EstadoCaso
    caso = _un_caso().model_copy(update={"estado": EstadoCaso(estado), "aprobado_por": "ana",
                                         "motivo_escalamiento": None})
    textos = [p["texto"] for p in vista_caso.timeline(caso, traza=None)]
    assert esperado in textos


def test_timeline_usa_pasos_reales_de_traza():
    """Los pasos de agentes salen de la traza (no se inventan): con eventos, aparecen."""
    traza = {"trace_events": [{"nodo": "c2_extraccion", "resultado": "ok", "timestamp": "2026-07-10T10:00:00"}]}
    pasos = vista_caso.timeline(_un_caso(), traza)
    assert len(pasos) >= 4  # correo + 2 docs + al menos 1 agente


def test_render_timeline(client):
    r = client.get(f"/workbench/caso/{_un_caso().id}")
    assert "Actividad del caso" in r.text   # V1·6: cronología humana (antes "Lo que hizo la IA")
    assert "wb-crono" in r.text
    assert "badge-demo" in r.text  # los conteos van rotulados


# ---------- W4 resumen narrativo ----------

def test_resumen_narrativo_es_prosa():
    caso = _un_caso()
    texto = vista_caso.resumen_narrativo(caso)
    assert vista_caso.asegurado_de(caso)["nombre"] in texto
    assert texto.endswith(".")


def test_resumen_narrativo_menciona_faltantes():
    """Si hay faltantes, el resumen los nombra (P7: no los inventa, los declara)."""
    caso = next((c for c in get_caso_repository().list() if vista_caso.faltantes(c)), None)
    if caso is None:
        pytest.skip("no hay caso con faltantes sembrado")
    assert "Falta:" in vista_caso.resumen_narrativo(caso)


def test_resumen_narrativo_sin_palabras_prohibidas():
    """P1: la narrativa nunca contiene lenguaje de decisión."""
    for c in get_caso_repository().list():
        texto = vista_caso.resumen_narrativo(c).lower()
        assert not any(p in texto for p in PALABRAS_PROHIBIDAS)


def test_resumen_narrativo_redacta_pii():
    """P5: si el asegurado real (M2) trae una cédula, no aparece cruda en la prosa (redacción en el view-model)."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = _un_caso()
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="asegurado_nombre", valor="Juan C.C. 1.098.765.432",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    assert "1.098.765.432" not in vista_caso.resumen_narrativo(caso2)


def test_render_resumen_narrativo(client):
    r = client.get(f"/workbench/caso/{_un_caso().id}")
    assert "Resumen del caso" in r.text   # V1·2: eyebrow de la historia (antes "Resumen ejecutivo")
    assert "wb-narrativa" in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
