"""Tests del Bolt `summary-agent-robusto` — Summary Agent no-bloqueante (U-W19.1) + confianza legible (U-W17.x).

Gate de salida del spec `specs/aidlc/evolution/summary-agent-robusto.md`. Herméticos (sin red): el cliente
Anthropic se mockea. El caché/cooldown se limpia entre tests vía conftest (autouse).
"""

import pytest

from app.config import settings
from app.demo.scenarios import construir_caso_preset
from app.dashboard import vista_caso
from app.llm import summary


def _caso():
    return construir_caso_preset("feliz")


# ------------------------------------------------------------------ U-W19.1 · caché
def test_cache_no_re_llama_al_llm_en_render_repetido(monkeypatch):
    """Criterio #1: 2 renders del mismo caso ya resumido → el LLM se invoca UNA sola vez."""
    llamadas = {"n": 0}
    def _redacta(caso):
        llamadas["n"] += 1
        return "El asegurado reportó un choque. La póliza está vigente."
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", _redacta)

    caso = _caso()
    t1, o1 = summary.call_summary_agent(caso)
    t2, o2 = summary.call_summary_agent(caso)          # auto-refresh: mismo caso, sin cambios
    assert o1 == o2 == "agente"
    assert t1 == t2
    assert llamadas["n"] == 1                          # 0 llamadas nuevas en el 2º render


def test_cache_se_invalida_si_el_caso_cambia(monkeypatch):
    """El caché es por hash del prompt: si el caso cambia (nueva info), se vuelve a redactar (auto-cura)."""
    llamadas = {"n": 0}
    def _redacta(caso):
        llamadas["n"] += 1
        return f"Resumen {llamadas['n']}: choque, póliza vigente."
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", _redacta)

    caso = _caso()
    summary.call_summary_agent(caso)
    # cambia un campo que entra al prompt (el monto) → nueva clave de estado → re-llama (mismo id)
    campos = [c.model_copy(update={"valor": "99999999"}) if c.nombre == "monto_reclamado" else c
              for c in caso.extraccion.campos]
    caso2 = caso.model_copy(update={"extraccion": caso.extraccion.model_copy(update={"campos": campos})})
    summary.call_summary_agent(caso2)
    assert llamadas["n"] == 2


# ------------------------------------------------------------------ U-W19.1 · fail-fast + cooldown
def test_llm_redacta_construye_cliente_failfast(monkeypatch):
    """Criterio #2/D2: el cliente se crea con max_retries=0 y el timeout configurado (no backoff ante 529)."""
    capturado = {}
    class _Blk:
        text = "El asegurado reportó un choque; la póliza está vigente."
    class _Resp:
        content = [_Blk()]
    class _Msgs:
        def create(self, **kw): return _Resp()
    class _FakeClient:
        def __init__(self, **kwargs): capturado.update(kwargs); self.messages = _Msgs()
    monkeypatch.setattr("anthropic.Anthropic", _FakeClient)

    summary._llm_redacta(_caso())
    assert capturado["max_retries"] == settings.summary_max_retries == 0
    assert capturado["timeout"] == settings.summary_timeout_s


def test_cooldown_no_re_llama_tras_fallo(monkeypatch):
    """Criterio #2/D1: tras un fallo, el 2º render NO re-llama al LLM (cooldown) → corta el martilleo del refresh."""
    llamadas = {"n": 0}
    def _boom(caso):
        llamadas["n"] += 1
        raise RuntimeError("OverloadedError")
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", _boom)
    monkeypatch.setattr(settings, "summary_cooldown_s", 30.0)

    caso = _caso()
    _t1, o1 = summary.call_summary_agent(caso)
    _t2, o2 = summary.call_summary_agent(caso)         # dentro del cooldown
    assert o1 == o2 == "base"
    assert llamadas["n"] == 1                          # el 2º render NO tocó el LLM


def test_cache_lru_expulsa_el_mas_viejo(monkeypatch):
    """Cota LRU: con el caché lleno, un caso nuevo expulsa al menos usado → no crece sin fin (fix code-review)."""
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", lambda caso: "El asegurado reportó un choque. La póliza está vigente.")
    monkeypatch.setattr(summary, "_CACHE_MAX", 2)
    c1, c2, c3 = _caso(), _caso(), _caso()             # ids distintos (uuid por construcción)
    for c in (c1, c2, c3):
        summary.call_summary_agent(c)
    assert len(summary._AGENTE_CACHE) == 2             # acotado a _CACHE_MAX
    assert c1.id not in summary._AGENTE_CACHE          # el más viejo se expulsó
    assert c3.id in summary._AGENTE_CACHE              # el más nuevo sigue


def test_cooldown_expira_y_reintenta(monkeypatch):
    """Auto-cura: con el cooldown vencido, se vuelve a intentar el LLM."""
    llamadas = {"n": 0}
    def _boom(caso):
        llamadas["n"] += 1
        raise RuntimeError("OverloadedError")
    monkeypatch.setattr(summary, "_llm_disponible", lambda: True)
    monkeypatch.setattr(summary, "_llm_redacta", _boom)
    monkeypatch.setattr(settings, "summary_cooldown_s", 0.0)   # cooldown inmediato → siempre reintenta

    caso = _caso()
    summary.call_summary_agent(caso)
    summary.call_summary_agent(caso)
    assert llamadas["n"] == 2


# ------------------------------------------------------------------ U-W17.x · confianza legible
def test_conf_texto_baja_lidera_significado():
    """0.20 pelado → 'Sin confirmar · 20%' + tooltip con el % y el umbral (encode-not-hide)."""
    valor, ayuda = vista_caso._conf_texto(0.20)
    assert valor == "Sin confirmar · 20%"
    assert "20%" in ayuda and "umbral" in ayuda


def test_conf_texto_alta_y_media():
    assert vista_caso._conf_texto(0.95)[0] == "Verificado"
    assert vista_caso._conf_texto(0.75)[0] == "Revisar · 75%"


def test_conf_texto_clamp_fuera_de_rango():
    """Valores fuera de [0,1] no rompen el render: se acotan (fix code-review)."""
    assert vista_caso._conf_texto(1.5)[0] == "Verificado"           # clamp a 1.0
    assert vista_caso._conf_texto(-0.2)[0] == "Sin confirmar · 0%"  # clamp a 0.0


def test_strip_verificacion_es_legible():
    """Integración: con una traza C3 de confianza 0.20, el chip 'Verificación' del strip es legible + con ayuda."""
    caso = _caso()
    traza = {"trace_events": [{"nodo": "c3_verificador", "resultado": "confianza=0.20, señales=1"}]}
    strip = vista_caso.confianza_riesgo(caso, traza)
    verif = next(i for i in strip if i["label"] == "Verificación")
    assert verif["valor"] == "Sin confirmar · 20%"
    assert verif["nivel"] == "bad"
    assert verif["ayuda"]                              # tooltip presente (no un 0.20 pelado)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
