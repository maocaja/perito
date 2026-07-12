"""Tests W19 — Summary Agent (LLM mockeable). 🔒 P1.

Central: el agente DESCRIBE, no decide. Guard fail-closed (sin PALABRAS_PROHIBIDAS; no contradice al motor)
+ fallback determinístico a W4. P5: prompt de campos redactados, no del texto_crudo. Hermético: sin key real,
usa el fallback (no toca red).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.llm import summary
from app.contracts.enums import ResultadoCobertura


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _un_caso():
    return get_caso_repository().list()[0]


def _con_dictamen():
    return next((c for c in get_caso_repository().list() if c.dictamen is not None), None)


# ---------- hermético: sin LLM real → fallback (no red) ----------

def test_hermetico_usa_fallback_base():
    """Con key='test' (hermético) el agente NO llama al LLM → usa la plantilla W4 (origen='base')."""
    caso = _un_caso()
    texto, origen = summary.call_summary_agent(caso)
    assert origen == "base"
    assert texto == vista_caso.resumen_narrativo(caso)


# ---------- V1·2: la historia se rinde como prosa; la IA es invisible ----------

def test_v1_historia_se_rinde_sin_exponer_la_ia(client):
    """V1·2: el resumen aparece como HISTORIA (prosa), y la IA es INVISIBLE — sin badge 'Summary Agent'/'agente'
    gritón. El contenido (la explicación) sí se muestra: la IA aparece cuando explica, no como marketing."""
    caso = _un_caso()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "wb-narrativa" in html                       # la historia se rinde como prosa
    assert vista_caso.resumen_ejecutivo(caso)["texto"][:24] in html  # el contenido real está presente
    assert "wb-agente-tag" not in html                  # sin el badge de IA (invisible)
    assert "Summary Agent" not in html                  # sin exponer la orquestación (manifiesto V1)


# ---------- agente real (mock) ----------

def test_agente_redacta_cuando_llm_valido(monkeypatch):
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda caso: "El asegurado reportó un choque. La póliza está vigente.")
    texto, origen = summary.call_summary_agent(_un_caso())
    assert origen == "agente"
    assert "choque" in texto


# ---------- 🔒 guard fail-closed ----------

def test_guard_rechaza_palabra_de_decision(monkeypatch):
    """Si el LLM 'decide' (aprobado/rechazado) → guard falla → fallback base (P1)."""
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda caso: "El caso queda aprobado y cerrado.")
    _texto, origen = summary.call_summary_agent(_un_caso())
    assert origen == "base"


def test_guard_rechaza_cobertura_contradictoria(monkeypatch):
    """🔒 P2: si el LLM afirma una cobertura distinta a la del motor → guard falla → fallback."""
    caso = _con_dictamen()
    if caso is None:
        pytest.skip("sin caso con dictamen")
    contraria = "no cubierto" if caso.dictamen.resultado != ResultadoCobertura.NO_CUBIERTO else "cubierto"
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda c: f"El siniestro está {contraria} según el análisis.")
    _texto, origen = summary.call_summary_agent(caso)
    assert origen == "base"


def test_guard_acepta_cobertura_coincidente(monkeypatch):
    caso = _con_dictamen()
    if caso is None:
        pytest.skip("sin caso con dictamen")
    label = caso.dictamen.resultado.value.replace("_", " ").lower()
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda c: f"Ocurrió un siniestro; el motor lo marcó {label}.")
    _texto, origen = summary.call_summary_agent(caso)
    assert origen == "agente"  # coincide con el motor → válido


def test_guard_acepta_cubierto_parcial_especifico(monkeypatch):
    """🔒 P2 (regresión del bug de substring): 'cubierto parcial' con dictamen CUBIERTO_PARCIAL NO se rechaza."""
    caso = next((c for c in get_caso_repository().list()
                 if c.dictamen and c.dictamen.resultado == ResultadoCobertura.CUBIERTO_PARCIAL), None)
    if caso is None:
        pytest.skip("sin caso CUBIERTO_PARCIAL")
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda c: "El motor lo marcó cubierto parcial; revisa el sublímite.")
    _texto, origen = summary.call_summary_agent(caso)
    assert origen == "agente"  # antes del fix, "cubierto" matcheaba dentro de "cubierto parcial" → falso rechazo


def test_guard_rechaza_cobertura_sin_dictamen(monkeypatch):
    """Si no hay dictamen y la narrativa afirma cobertura → guard falla → fallback (no inventa veredicto)."""
    caso = next((c for c in get_caso_repository().list() if c.dictamen is None), None)
    if caso is None:
        pytest.skip("sin caso sin dictamen")
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda c: "El siniestro está cubierto por la póliza.")
    _texto, origen = summary.call_summary_agent(caso)
    assert origen == "base"


def test_excepcion_del_llm_cae_a_fallback(monkeypatch):
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda c: (_ for _ in ()).throw(RuntimeError("LLM down")))
    _texto, origen = summary.call_summary_agent(_un_caso())
    assert origen == "base"


# ---------- 🔒 P5 prompt ----------

def test_prompt_no_incluye_texto_crudo_y_redacta():
    """El prompt se arma de campos redactados, NO del texto_crudo del correo."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = _un_caso()
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="numero_poliza", valor="POL-1 C.C. 1.098.765.432",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    # el texto_crudo tiene PII que NO debe entrar al prompt
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(
        campos=[c for c in campos if c.nombre != "numero_poliza"] + [campos[-1]])})
    prompt = summary.construir_prompt(caso2)
    assert caso2.aviso.texto_crudo not in prompt          # no el correo crudo
    assert "1.098.765.432" not in prompt                   # cédula redactada


# ---------- render ----------

def test_render_muestra_la_historia(client):
    """V1·2: la historia aparece con su eyebrow calmo ('Resumen del caso'); ya NO hay badge de agente/origen
    (la IA es invisible — el origen LLM/base se comunica, si acaso, con una nota sutil, no un badge)."""
    html = client.get(f"/workbench/caso/{_un_caso().id}").text
    assert "wb-historia" in html
    assert "Resumen del caso" in html
    assert "wb-agente-tag" not in html and "Summary Agent" not in html


def test_resumen_no_llama_al_llm_fuera_de_modo_real(monkeypatch):
    """El Summary Agent (LLM) solo corre en modo `real`; en deterministic/off usa la historia W4 DIRECTO,
    sin tocar la API (respeta el modo: cero costo/latencia/ruido, no un fallback por error 400)."""
    from app.dashboard import vista_caso
    from app.demo.scenarios import construir_caso_preset
    from app.config import settings
    import app.llm.summary as summary

    llamado = {"n": 0}
    def _spy(caso):
        llamado["n"] += 1
        return ("historia del agente", "agente")
    monkeypatch.setattr(summary, "call_summary_agent", _spy)
    for modo in ("off", "deterministic"):
        monkeypatch.setattr(settings, "demo_live", modo)
        r = vista_caso.resumen_ejecutivo(construir_caso_preset("feliz"))
        assert r["origen"] == "base"
    assert llamado["n"] == 0   # nunca se invocó el agente LLM fuera de `real`


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
