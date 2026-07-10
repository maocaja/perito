"""Tests Unit M — carta al asegurado (demo-scope).

Invariantes: P1 (draft ≠ send; envío exige firma, cero auto-envío), P2/P7 (resolución cita el dictamen
LITERAL con guardrail fail-closed), fail-safe (un fallo de SMTP no cambia el caso, no 500).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso
from app.api import cartas


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _caso_con_clausula():
    return next(c for c in get_caso_repository().list() if c.dictamen and c.dictamen.clausula)


def _terminal_con_clausula():
    base = _caso_con_clausula()
    return base.model_copy(update={"estado": EstadoCaso.APROBADO, "aprobado_por": "test.analista"})


def _caso_revision():
    return next(c for c in get_caso_repository().list() if c.estado == EstadoCaso.REQUIERE_REVISION)


# ---------- tipo de carta por estado ----------

def test_tipo_carta_por_estado(client):
    assert vista_caso.tipo_carta(_terminal_con_clausula()) == "resolucion"
    assert vista_caso.tipo_carta(_caso_revision()) == "datos"
    listo = next(c for c in get_caso_repository().list() if c.estado == EstadoCaso.LISTO_PARA_APROBAR)
    assert vista_caso.tipo_carta(listo) is None


# ---------- P2/P7: cobertura verbatim + guardrail ----------

def test_plantilla_resolucion_cita_dictamen_verbatim(client):
    caso = _terminal_con_clausula()
    texto = cartas.plantilla_carta(caso, "resolucion")
    assert caso.dictamen.regla_aplicada in texto
    assert caso.dictamen.clausula.id in texto


def test_guardrail_detecta_cita_removida(client):
    caso = _terminal_con_clausula()
    bueno = cartas.plantilla_carta(caso, "resolucion")
    assert cartas.cita_intacta(bueno, caso) is True
    # si el "pulido" borró el id de la cláusula → el guardrail lo detecta
    roto = bueno.replace(caso.dictamen.clausula.id, "XXX")
    assert cartas.cita_intacta(roto, caso) is False


def test_guardrail_detecta_veredicto_volteado(client):
    """El guardrail impide voltear el veredicto (ADMITIDA↔NO ADMITIDA) — cierra inyección por texto libre."""
    caso = _terminal_con_clausula()  # APROBADO → carta dice ADMITIDA
    bueno = cartas.plantilla_carta(caso, "resolucion")
    assert cartas.cita_intacta(bueno, caso) is True
    volteado = bueno.replace("ADMITIDA", "NO ADMITIDA")  # aprobado → negado
    assert cartas.cita_intacta(volteado, caso) is False


def test_guardrail_sin_dictamen_ok(client):
    """Sin dictamen que citar → el guardrail no bloquea (no hay cobertura que proteger)."""
    caso = _caso_revision().model_copy(update={"dictamen": None})
    assert cartas.cita_intacta("cualquier texto", caso) is True


def test_pulir_sin_key_devuelve_plantilla(client):
    """Hermético: sin key real (ANTHROPIC_API_KEY=test) el pulido devuelve la plantilla intacta."""
    caso = _terminal_con_clausula()
    texto = cartas.plantilla_carta(caso, "resolucion")
    assert cartas.pulir_prosa(texto, caso, "resolucion") == texto


# ---------- P1: draft ≠ send ----------

def test_enviar_sin_usuario_400(client):
    cid = _caso_revision().id
    assert client.post(f"/casos/{cid}/carta/enviar", data={"contenido": "hola"}).status_code == 400


def test_preparar_carta_no_aplica_en_listo_400(client):
    listo = next(c for c in get_caso_repository().list() if c.estado == EstadoCaso.LISTO_PARA_APROBAR)
    assert client.post(f"/casos/{listo.id}/carta").status_code == 400


def test_preparar_carta_muestra_borrador(client):
    """POST /carta genera el borrador on-demand y lo muestra (con la cita literal)."""
    caso = _caso_revision()  # pedir-datos aplica
    r = client.post(f"/casos/{caso.id}/carta", data={"rol": "analista"})
    assert r.status_code == 200
    assert "Enviar al asegurado" in r.text  # el textarea + botón de envío
    assert "asegurado" in r.text


def test_enviar_fail_safe_no_rompe_el_caso(client, monkeypatch):
    """Fail-safe: si el SMTP falla, se informa el error, el caso queda intacto y NO es 500 (P)."""
    class _FakeMailbox:
        @classmethod
        def from_settings(cls):
            return cls()
        def enviar(self, **kw):
            raise RuntimeError("smtp caído")
    monkeypatch.setattr(cartas, "Mailbox", _FakeMailbox)
    caso = _caso_revision()
    estado_antes = caso.estado
    r = client.post(f"/casos/{caso.id}/carta/enviar",
                    data={"usuario": "diana", "contenido": "hola"}, follow_redirects=False)
    assert r.status_code == 200  # no 500
    assert "No se pudo enviar" in r.text
    assert get_caso_repository().get(caso.id).estado == estado_antes  # caso intacto


def test_enviar_ok_con_firma(client, monkeypatch):
    """Con firma y SMTP ok → 303 (PRG) y el cuerpo se envió."""
    enviado = {}
    class _OkMailbox:
        @classmethod
        def from_settings(cls):
            return cls()
        def enviar(self, asunto, cuerpo, to=None):
            enviado["cuerpo"] = cuerpo
    monkeypatch.setattr(cartas, "Mailbox", _OkMailbox)
    caso = _caso_revision()
    r = client.post(f"/casos/{caso.id}/carta/enviar",
                    data={"usuario": "diana", "contenido": "Estimado asegurado, falta el monto."},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "enviado=1" in r.headers["location"]
    assert enviado.get("cuerpo")
