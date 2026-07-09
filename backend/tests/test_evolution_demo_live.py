"""Tests de la demo en vivo (Unit H) — mailbox, poller, gating. IMAP mockeado (sin Gmail real).

Cubre los invariantes: P5 (el remitente se omite), P4 (idempotencia: marca leído SIEMPRE),
P1 (el poller nunca alcanza terminal), y el gating por DEMO_LIVE (fail-safe).
"""

import pytest

from app.config import settings
from app.contracts.enums import EstadoCaso
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.intake import poller
from app.intake.mailbox import Mailbox, _extraer_cuerpo
from tests.imap_mock import FakeIMAP, build_raw


def _mailbox_con(mensajes) -> Mailbox:
    mb = Mailbox("demo@x.com", "pwd", "imap", "smtp")
    mb._imap = FakeIMAP(mensajes)
    return mb


# ---------------- Mailbox / parser (P5) ----------------

def test_fetch_unseen_extrae_cuerpo_y_omite_remitente_when_correo_llega():
    raw = build_raw("[DEMO:feliz] Reporte #1", "Siniestro AUTO_COLISION, monto 5000000.",
                    sender="juan.perez@personal.com")
    mb = _mailbox_con([(b"1", raw)])
    correos = mb.fetch_unseen()
    assert len(correos) == 1
    c = correos[0]
    # el cuerpo (aviso) llega; el asunto conserva el marcador
    assert "AUTO_COLISION" in c.cuerpo
    assert "[DEMO:feliz]" in c.asunto
    # P5: el remitente NO se captura en ningún campo del CorreoEntrante
    assert "juan.perez@personal.com" not in (c.asunto + c.cuerpo)
    assert not hasattr(c, "remitente") and not hasattr(c, "from_")


def test_extraer_cuerpo_multipart_toma_texto_plano():
    raw = build_raw("asunto", "cuerpo de texto plano")
    from email import message_from_bytes
    assert "cuerpo de texto plano" in _extraer_cuerpo(message_from_bytes(raw))


# ---------------- Poller: mapeo de escenario ----------------

@pytest.mark.parametrize("asunto,esperado", [
    ("[DEMO:fraude] x", "fraude"),
    ("[DEMO:cobertura-negativa] x", "cobertura-negativa"),
    ("sin marcador", "feliz"),
])
def test_escenario_de_asunto_when_marcador(asunto, esperado):
    assert poller._escenario_de_asunto(asunto) == esperado


# ---------------- Poller: idempotencia (P4) ----------------

def test_procesar_lote_marca_leido_siempre_when_procesar_falla(monkeypatch):
    """Un correo que falla al procesar TAMBIÉN se marca leído → no se reprocesa, no loopea (P4)."""
    monkeypatch.setattr(poller, "_procesar", lambda correo: (_ for _ in ()).throw(RuntimeError("boom")))
    mb = _mailbox_con([(b"1", build_raw("a", "x")), (b"2", build_raw("b", "y"))])
    n = poller._procesar_lote(mb)
    assert n == 2
    assert mb._imap.seen == ["1", "2"]  # ambos marcados leídos pese al fallo


# ---------------- Poller: procesa y NUNCA cierra (P1) ----------------

def test_procesar_deterministic_guarda_caso_no_terminal_when_correo(monkeypatch):
    monkeypatch.setattr(settings, "demo_live", "deterministic")
    reset_caso_repository()
    get_caso_repository().clear()
    correo = type("C", (), {"uid": "1", "asunto": "[DEMO:cobertura-negativa] x", "cuerpo": "irrelevante"})()
    poller._procesar(correo)
    casos = get_caso_repository().list()
    assert len(casos) == 1
    # P1: el poller PREPARA, nunca alcanza terminal
    assert casos[0].estado not in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


# ---------------- Gating por DEMO_LIVE (fail-safe) ----------------

def test_iniciar_poller_no_arranca_when_off(monkeypatch):
    monkeypatch.setattr(settings, "demo_live", "off")
    monkeypatch.setattr(poller, "_started", False)
    assert poller.iniciar_poller() is False


def test_iniciar_poller_no_arranca_when_faltan_credenciales(monkeypatch):
    monkeypatch.setattr(settings, "demo_live", "real")
    monkeypatch.setattr(settings, "demo_gmail_address", "")
    monkeypatch.setattr(settings, "demo_gmail_app_password", "")
    monkeypatch.setattr(poller, "_started", False)
    assert poller.iniciar_poller() is False  # fail-safe: no arranca sin creds
