"""Tests W18 — Timeline agent-native.

🔴 Blindaje agéntico: los pasos de AGENTES salen SOLO de la traza real (nunca fabricados); un agente que no
corrió no aparece; un agente NUEVO aparece sin tocar la vista (mapa extensible). Los conteos de docs son
REALES (los adjuntos del correo) y visualmente distintos de los pasos de agentes.
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


def _caso_con_adjuntos():
    """Caso sembrado con adjuntos reales (auto); robusto al orden de `list()` (el de vivienda no trae)."""
    return next(c for c in get_caso_repository().list() if c.adjuntos)


def _traza(*nodos):
    return {"trace_events": [{"nodo": n, "resultado": "ok", "timestamp": "2026-07-10T10:00:0%d" % i,
                              "tokens_in": 200, "tokens_out": 50} for i, n in enumerate(nodos)]}


# ---------- 🔴 pasos de agentes SOLO de la traza ----------

# Frases (en lenguaje de operador) que identifican un paso de AGENTE en el timeline. Distintas de los
# pasos no-agente ("Correo recibido", "Leyó N fotografía(s)", estado final) para no dar falso positivo.
_NOMBRES_AGENTE = ("Leí los datos", "Verifiqué", "Busqué la póliza", "Evalué la cobertura",
                   "sospechoso", "documentos adjuntos", "Crucé las fuentes", "Analicé el caso")


def test_sin_traza_no_hay_pasos_de_agente():
    """Sin traza → ningún paso de agente fabricado (solo correo + docs reales si los hubo + estado)."""
    pasos = vista_caso.timeline(_un_caso(), traza=None)
    agentes = [p for p in pasos if any(n in p["texto"] for n in _NOMBRES_AGENTE)]
    assert agentes == []  # no se inventa ningún agente si no corrió


def test_agente_que_no_corrio_no_aparece():
    """Traza con solo la lectura de datos → NO aparecen la verificación ni la evaluación (no fabricados)."""
    pasos = vista_caso.timeline(_un_caso(), _traza("c2_extraccion"))
    textos = " ".join(p["texto"] for p in pasos)
    assert "Leí los datos" in textos
    assert "Verifiqué" not in textos and "Evalué la cobertura" not in textos


def test_agente_nuevo_aparece_sin_tocar_la_vista():
    """Un paso NUEVO (M1 documentos / M3 cruce de fuentes / W19 análisis) que emite traza → se renderiza."""
    pasos = vista_caso.timeline(_un_caso(), _traza("document_ai", "evidence_correlator", "summary_agent"))
    textos = " ".join(p["texto"] for p in pasos)
    assert "Leí los documentos adjuntos" in textos
    assert "Crucé las fuentes" in textos
    assert "Analicé el caso" in textos


def test_nodo_desconocido_no_crashea():
    """Un nodo sin mapear cae al nombre técnico (fallback), no rompe (P7)."""
    pasos = vista_caso.timeline(_un_caso(), _traza("agente_del_futuro_xyz"))
    assert any("agente_del_futuro_xyz" in p["texto"] for p in pasos)


# ---------- separación docs reales vs agentes ----------

def test_conteos_de_docs_distintos_de_los_agentes():
    """Los pasos de lectura de documentos (conteos REALES del correo) son distintos de los pasos de
    agentes de la traza; ninguno va rotulado demo (ya no se fabrican conteos)."""
    pasos = vista_caso.timeline(_caso_con_adjuntos(), _traza("c2_extraccion"))
    docs = [p for p in pasos if "PDF" in p["texto"] or "fotografía" in p["texto"]]
    agentes = [p for p in pasos if "Leí los datos" in p["texto"]]
    assert docs and all(p["demo"] is False for p in docs)      # docs reales, no fabricados
    assert agentes and all(p["demo"] is False for p in agentes)


def test_tokens_en_pasos_de_agente():
    pasos = vista_caso.timeline(_un_caso(), _traza("c2_extraccion"))
    lectura = next(p for p in pasos if "Leí los datos" in p["texto"])
    assert lectura["tokens"] == 250  # 200 in + 50 out (real de la traza)


# ---------- render ----------

def test_render_cronologia_humana(client):
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "wb-crono" in html            # V1·6: cronología HUMANA (vertical), no un strip técnico horizontal
    assert "Ver actividad técnica" in html  # el rastro técnico real sigue a un click (drawer, encode-not-hide)


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
