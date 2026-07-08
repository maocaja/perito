"""Tests C11 Dashboard — bandeja, detalle, acciones HITL, panel.

Invariantes verificados: P1 (usuario obligatorio, delega en HITL, terminal solo
con firma), P5 (aviso redactado en el detalle), estructural (dashboard/ no importa
rules/orchestrator, no muta caso.estado).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.dashboard as dashboard_pkg
from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.contracts.enums import EstadoCaso, ResultadoCobertura


@pytest.fixture
def client():
    """Re-siembra limpio (store + replay) antes de cada test → aislamiento."""
    seed_demo_casos()
    return TestClient(app)


def _caso_pendiente():
    for c in get_caso_repository().list():
        if c.estado == EstadoCaso.LISTO_PARA_APROBAR:
            return c
    raise AssertionError("no hay caso LISTO_PARA_APROBAR sembrado")


def _caso_con_pii():
    for c in get_caso_repository().list():
        if "1.098.765.432" in c.aviso.texto_crudo:
            return c
    raise AssertionError("no hay caso con PII sembrado")


# ---------- H-19 Bandeja ----------

def test_bandeja_lista_casos(client):
    r = client.get("/casos")
    assert r.status_code == 200
    assert r.text.count("/casos/") >= 4  # un enlace de detalle por caso

def test_bandeja_filtro_por_estado(client):
    r = client.get("/casos", params={"estado": "REQUIERE_REVISION"})
    assert r.status_code == 200
    assert "REQUIERE_REVISION" in r.text


# ---------- H-20 Detalle ----------

def test_detalle_200(client):
    cid = get_caso_repository().list()[0].id
    assert client.get(f"/casos/{cid}").status_code == 200

def test_detalle_404_caso_inexistente(client):
    assert client.get("/casos/no-existe").status_code == 404

def test_detalle_muestra_dictamen_con_clausula(client):
    """P3: el detalle cita la cláusula del dictamen."""
    pendiente = _caso_pendiente()
    html = client.get(f"/casos/{pendiente.id}").text
    if pendiente.dictamen and pendiente.dictamen.clausula:
        assert pendiente.dictamen.clausula.id in html


# ---------- P5: aviso redactado ----------

def test_p5_aviso_redactado_en_detalle(client):
    """P5 fail-closed: la cédula cruda NO aparece en el HTML; sí el marcador [REDACTED]."""
    caso = _caso_con_pii()
    html = client.get(f"/casos/{caso.id}").text
    assert "1.098.765.432" not in html   # cédula cruda NO se filtra
    assert "3115551234" not in html      # celular crudo NO se filtra
    assert "[REDACTED]" in html          # sí hay redacción


# ---------- P1: HITL (usuario obligatorio, delega, terminal con firma) ----------

def test_p1_aprobar_sin_usuario_400(client):
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/aprobar", data={}).status_code == 400

def test_p1_aprobar_usuario_solo_espacios_400(client):
    """Firma inválida: usuario='   ' (solo espacios) debe rechazarse (P1)."""
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/aprobar", data={"usuario": "   "}).status_code == 400

def test_p1_aprobar_con_usuario_alcanza_terminal(client):
    cid = _caso_pendiente().id
    r = client.post(f"/casos/{cid}/aprobar", data={"usuario": "diana.analista"})
    assert r.status_code == 200
    caso = get_caso_repository().get(cid)
    assert caso.estado == EstadoCaso.APROBADO
    assert caso.aprobado_por == "diana.analista"   # firma humana registrada (P1)

def test_p1_rechazar_sin_usuario_400(client):
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/rechazar", data={"motivo": "x"}).status_code == 400

def test_p1_rechazar_sin_motivo_400(client):
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/rechazar", data={"usuario": "u"}).status_code == 400

def test_p1_rechazar_ok(client):
    cid = _caso_pendiente().id
    r = client.post(f"/casos/{cid}/rechazar", data={"usuario": "andres", "motivo": "documentación insuficiente"})
    assert r.status_code == 200
    caso = get_caso_repository().get(cid)
    assert caso.estado == EstadoCaso.RECHAZADO
    assert caso.aprobado_por == "andres"


# ---------- H-21 Panel + export ----------

def test_panel_200_con_trazas(client):
    r = client.get("/panel")
    assert r.status_code == 200
    assert r.text.count("/panel/export/") >= 4   # un enlace de export por caso sembrado

def test_export_pia_json(client):
    cid = get_caso_repository().list()[0].id
    r = client.get(f"/panel/export/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body["caso_id"] == cid
    assert "trace_events" in body and "token_summary" in body


# ---------- F2 Métricas del panel (H-21) ----------

def test_panel_metricas_render(client):
    """El panel muestra las métricas de operación + las garantías (separadas, P7)."""
    r = client.get("/panel")
    assert r.status_code == 200
    assert "Métricas de operación" in r.text
    assert "Garantías" in r.text and "RULE-CTR-03" in r.text
    assert "estimado" in r.text  # costo rotulado como estimado (no facturable)
    total = len(get_caso_repository().list())
    assert str(total) in r.text  # el KPI de casos totales


def test_panel_metricas_cero_casos_no_rompe(client):
    """H-21 robustez: con 0 casos el panel NO rompe (sin ZeroDivisionError)."""
    get_caso_repository().clear()
    r = client.get("/panel")
    assert r.status_code == 200
    assert "0%" in r.text  # pct_escalado con 0 casos, sin crash


# ---------- F1 HITL Corregir (H-20) ----------

def _caso_no_cubierto():
    for c in get_caso_repository().list():
        if c.dictamen and c.dictamen.resultado == ResultadoCobertura.NO_CUBIERTO:
            return c
    raise AssertionError("no hay caso NO_CUBIERTO sembrado")


def test_corregir_cambia_dictamen_y_marca_origen_humano(client):
    """Corregir tipo mal (HOGAR_AGUA→AUTO_COLISION) → re-dictamen ≠ NO_CUBIERTO, no terminal, origen HUMANO (P3)."""
    caso = _caso_no_cubierto()
    r = client.post(f"/casos/{caso.id}/corregir",
                    data={"usuario": "diana.analista", "tipo_siniestro": "AUTO_COLISION"},
                    follow_redirects=False)
    assert r.status_code == 303
    act = get_caso_repository().get(caso.id)
    assert act.dictamen.resultado != ResultadoCobertura.NO_CUBIERTO   # el dictamen cambió (P2, motor re-decide)
    assert act.estado not in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}  # nunca terminal (P1)
    tipo = next(c for c in act.extraccion.campos if c.nombre == "tipo_siniestro")
    assert tipo.valor == "AUTO_COLISION"
    assert tipo.origen.tipo.value == "HUMANO"   # auditable (P3)


def test_corregir_sin_usuario_400(client):
    cid = _caso_no_cubierto().id
    r = client.post(f"/casos/{cid}/corregir", data={"tipo_siniestro": "AUTO_COLISION"}, follow_redirects=False)
    assert r.status_code == 400   # firma obligatoria (P1)


def test_corregir_caso_terminal_409(client):
    """P1 integridad: un caso ya decidido (APROBADO) NO se puede corregir → 409."""
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/aprobar", data={"usuario": "diana"}).status_code == 200
    assert get_caso_repository().get(cid).estado == EstadoCaso.APROBADO  # pre-condición verificada
    r = client.post(f"/casos/{cid}/corregir", data={"usuario": "diana", "tipo_siniestro": "AUTO_COLISION"}, follow_redirects=False)
    assert r.status_code == 409


# ---------- Estructural (P1/P2): dashboard passive ----------

def test_dashboard_no_importa_rules_ni_orchestrator():
    dash_dir = Path(dashboard_pkg.__file__).parent
    for py in dash_dir.glob("*.py"):
        src = py.read_text()
        assert "app.rules" not in src, f"{py.name} importa rules/"
        assert "app.orchestrator" not in src, f"{py.name} importa orchestrator/"

def test_dashboard_no_muta_estado_directo():
    dash_dir = Path(dashboard_pkg.__file__).parent
    for py in dash_dir.glob("*.py"):
        assert "caso.estado =" not in py.read_text(), f"{py.name} muta caso.estado directo"
