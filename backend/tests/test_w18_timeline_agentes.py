"""Tests W18 — Timeline agent-native.

🔴 Blindaje agéntico: los pasos de AGENTES salen SOLO de la traza real (nunca fabricados); un agente que no
corrió no aparece; un agente NUEVO aparece sin tocar la vista (mapa extensible). Los conteos de docs (mock)
van rotulados y visualmente distintos.
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


def _traza(*nodos):
    return {"trace_events": [{"nodo": n, "resultado": "ok", "timestamp": "2026-07-10T10:00:0%d" % i,
                              "tokens_in": 200, "tokens_out": 50} for i, n in enumerate(nodos)]}


# ---------- 🔴 pasos de agentes SOLO de la traza ----------

_NOMBRES_AGENTE = ("Extractor", "Verificador", "Grounding", "Motor", "Fraude", "Document AI",
                   "Correlación", "Resumen")


def test_sin_traza_no_hay_pasos_de_agente():
    """Sin traza → ningún paso de agente fabricado (solo correo + docs demo + estado)."""
    pasos = vista_caso.timeline(_un_caso(), traza=None)
    agentes = [p for p in pasos if any(n in p["texto"] for n in _NOMBRES_AGENTE)]
    assert agentes == []  # no se inventa ningún agente si no corrió


def test_agente_que_no_corrio_no_aparece():
    """Traza con solo el Extractor → NO aparecen Verificador/Motor (no fabricados)."""
    pasos = vista_caso.timeline(_un_caso(), _traza("c2_extraccion"))
    textos = " ".join(p["texto"] for p in pasos)
    assert "Extractor" in textos
    assert "Verificador" not in textos and "Motor" not in textos


def test_agente_nuevo_aparece_sin_tocar_la_vista():
    """Un agente NUEVO (M1 Document AI / M3 Correlator / W19 Summary) que emite traza → se renderiza."""
    pasos = vista_caso.timeline(_un_caso(), _traza("document_ai", "evidence_correlator", "summary_agent"))
    textos = " ".join(p["texto"] for p in pasos)
    assert "Document AI" in textos
    assert "Correlación de evidencia" in textos
    assert "Resumen" in textos


def test_nodo_desconocido_no_crashea():
    """Un nodo sin mapear cae al nombre técnico (fallback), no rompe (P7)."""
    pasos = vista_caso.timeline(_un_caso(), _traza("agente_del_futuro_xyz"))
    assert any("agente_del_futuro_xyz" in p["texto"] for p in pasos)


# ---------- separación demo vs real ----------

def test_conteos_demo_distintos_de_los_agentes():
    pasos = vista_caso.timeline(_un_caso(), _traza("c2_extraccion"))
    docs = [p for p in pasos if p.get("demo")]
    agentes = [p for p in pasos if not p.get("demo") and "Extractor" in p["texto"]]
    assert docs and all("PDF" in p["texto"] or "fotografía" in p["texto"] for p in docs)
    assert agentes and all(p["demo"] is False for p in agentes)


def test_tokens_en_pasos_de_agente():
    pasos = vista_caso.timeline(_un_caso(), _traza("c2_extraccion"))
    extractor = next(p for p in pasos if "Extractor" in p["texto"])
    assert extractor["tokens"] == 250  # 200 in + 50 out (real de la traza)


# ---------- render ----------

def test_render_horizontal_y_demo_distinto(client):
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "wb-tl-h" in html            # timeline horizontal
    assert "is-demo" in html            # los pasos demo llevan la clase distintiva
    assert "rastro real" in html         # el encabezado nombra la orquesta


# ---------- Fase 1 · drawer de actividad (encode-not-hide: timeline condensado + detalle a un click) ----------

def test_workbench_tiene_drawer_raiz(client):
    """El <dialog id="wb-drawer"> raíz existe (fuera de la cola y el caso → inmune al poll)."""
    html = client.get("/workbench").text
    assert 'id="wb-drawer"' in html


def test_timeline_tiene_trigger_ver_actividad(client):
    """El timeline condensado ofrece 'Ver actividad' que abre el detalle en el drawer (no se ocultó, W18)."""
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "Ver actividad" in html
    assert 'hx-get="/workbench/actividad/' in html and 'hx-target="#wb-drawer"' in html


def test_endpoint_actividad_detalle_real(client):
    """El drawer de actividad sirve el rastro REAL por agente (tokens/hora), passive (P7)."""
    html = client.get(f"/workbench/actividad/{_un_caso().id}").text
    assert "wb-drawer-inner" in html and "Actividad de la orquesta" in html
    assert "wb-act" in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
