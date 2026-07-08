"""Tests Unit de Evolución B1 — sink de Langfuse (observabilidad real, Must #10).

Cubre los criterios §3 del spec: sink desactivado sin keys, fail-open si el sink lanza, y P5
(motivo redactado antes de enviar). El SDK va mockeado — el smoke real (Docker) es manual (D3).
"""

from app.observability import langfuse_sink
from app.observability.replay import ReplayStore
from app.observability.tracer import Tracer


def _tracer_demo():
    t = Tracer("caso-x")
    t.emit("intake", "Caso recibido")
    t.emit("extractor", "Extracción completada", tokens_in=100, tokens_out=50)
    return t


def test_sink_desactivado_sin_keys():
    """Sin keys configuradas → sink off, sin error (floor JSON sigue solo)."""
    assert langfuse_sink.is_enabled() is False   # env de test no tiene keys de Langfuse
    assert langfuse_sink.emit_trace("c", "LISTO_PARA_APROBAR", None, [], {"tokens_total": 0}) is False


def test_save_fail_open_si_sink_lanza(monkeypatch):
    """FAIL-OPEN: si el sink lanza, ReplayStore.save() termina y el floor JSON queda intacto."""
    def boom(**kwargs):
        raise ConnectionError("Langfuse caído")
    monkeypatch.setattr("app.observability.langfuse_sink.emit_trace", boom)
    store = ReplayStore()
    store.save(_tracer_demo(), "LISTO_PARA_APROBAR", motivo=None)
    assert store.load("caso-x") is not None   # el caso quedó en el floor pese al fallo del sink


def test_p5_motivo_redactado_antes_de_enviar(monkeypatch):
    """P5: un `motivo` con PII se redacta ANTES de mandarse a Langfuse."""
    captured = {}

    class _FakeSpan:
        def start_observation(self, **kwargs):
            return _FakeSpan()
        def end(self):
            pass

    class _FakeClient:
        def start_observation(self, **kwargs):
            captured.setdefault("roots", []).append(kwargs)
            return _FakeSpan()
        def flush(self):
            pass

    monkeypatch.setattr("app.observability.langfuse_sink.is_enabled", lambda: True)
    monkeypatch.setattr("app.observability.langfuse_sink._get_client", lambda: _FakeClient())

    ok = langfuse_sink.emit_trace(
        caso_id="c",
        caso_estado="REQUIERE_REVISION",
        motivo="Escala: reintentar contacto al 3115551234 del asegurado",
        trace_events=[],
        token_summary={"tokens_total": 0},
    )
    assert ok is True
    motivo_enviado = captured["roots"][0]["metadata"]["motivo_escalamiento"]
    assert "3115551234" not in motivo_enviado   # PII (teléfono) NO se filtra a Langfuse
    assert "[REDACTED]" in motivo_enviado         # el sink aplicó la redacción antes de enviar


def test_p5_eventos_ya_redactados_llegan_al_sink(monkeypatch):
    """Los eventos que recibe el sink vienen del get_trace_log() ya redactado (P5)."""
    captured = {}

    class _FakeSpan:
        def start_observation(self, **kwargs):
            captured.setdefault("children", []).append(kwargs)
            return _FakeSpan()
        def end(self):
            pass

    class _FakeClient:
        def start_observation(self, **kwargs):
            return _FakeSpan()
        def flush(self):
            pass

    monkeypatch.setattr("app.observability.langfuse_sink.is_enabled", lambda: True)
    monkeypatch.setattr("app.observability.langfuse_sink._get_client", lambda: _FakeClient())

    t = Tracer("caso-y")
    t.emit("extractor", "Reporta C.C. 1.098.765.432 celular 3115551234", tokens_in=10, tokens_out=5)
    langfuse_sink.emit_trace("caso-y", "LISTO_PARA_APROBAR", None, t.get_trace_log(), t.get_token_summary())

    salida = str(captured["children"])
    assert "1.098.765.432" not in salida and "3115551234" not in salida
