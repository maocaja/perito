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

def test_workbench_lista_casos(client):
    # W20/A6: la cola del operador vive en la Workbench (el board `/casos` se retiró).
    r = client.get("/workbench")
    assert r.status_code == 200
    assert r.text.count("/workbench/caso/") >= 4  # un enlace por caso en la cola

def test_workbench_filtro_por_estado(client):
    # El filtro por estado (Inbox/En Proceso/Radicados/Escalados) ocurre DENTRO de la Workbench (W8).
    r = client.get("/workbench", params={"estado": "REQUIERE_REVISION"})
    assert r.status_code == 200


# ---------- Caso (partial de la Workbench; W20/A6 retiró la página `detalle`) ----------

def test_caso_partial_200(client):
    cid = get_caso_repository().list()[0].id
    assert client.get(f"/workbench/caso/{cid}").status_code == 200

def test_caso_partial_404_caso_inexistente(client):
    assert client.get("/workbench/caso/no-existe").status_code == 404

def test_caso_muestra_dictamen_con_clausula(client):
    """P3/P2: el panel del caso cita la regla y la cláusula del dictamen ('por qué' de la cobertura)."""
    pendiente = _caso_pendiente()
    html = client.get(f"/workbench/caso/{pendiente.id}").text
    if pendiente.dictamen:
        assert pendiente.dictamen.regla_aplicada in html   # el motor R1-R5 se cita (P2)
        cl = pendiente.dictamen.clausula
        if cl:
            assert (cl.id in html) or (cl.referencia in html) or (cl.texto in html)


# ---------- P5: aviso redactado ----------

def test_p5_operador_ve_el_correo_original(client):
    """P5 (dos niveles): el OPERADOR —encargado autorizado con finalidad legítima (Ley 1581)— ve el correo
    ORIGINAL con los datos reales. La minimización P5 es hacia el LLM (el prompt va redactado,
    `build_extraction_prompt_u2` — verificado en test_u2/test_demo_cierre), no hacia el operador legítimo."""
    caso = _caso_con_pii()
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "1.098.765.432" in html   # el operador ve la cédula real (es su trabajo verificar identidad)


# ---------- P1: HITL (usuario obligatorio, delega, terminal con firma) ----------

# W20/A6+A7: la vía a APROBADO es 'radicar' (Workbench); el legacy '/casos/{id}/aprobar' (que renderizaba
# detalle) se retiró. 'radicar' exige firma (P1) y solo procede desde LISTO_PARA_APROBAR; redirige a /workbench.

def test_p1_radicar_sin_usuario_400(client):
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/radicar", data={}, follow_redirects=False).status_code == 400

def test_p1_radicar_usuario_solo_espacios_400(client):
    """Firma inválida: usuario='   ' (solo espacios) debe rechazarse (P1)."""
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/radicar", data={"usuario": "   "}, follow_redirects=False).status_code == 400

def test_p1_radicar_con_usuario_alcanza_terminal(client):
    cid = _caso_pendiente().id   # LISTO_PARA_APROBAR
    r = client.post(f"/casos/{cid}/radicar", data={"usuario": "diana.analista"}, follow_redirects=False)
    assert r.status_code == 303 and "/workbench" in r.headers["location"]  # PRG a la Workbench
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
    r = client.post(f"/casos/{cid}/rechazar", data={"usuario": "andres", "motivo": "documentación insuficiente"},
                    follow_redirects=False)
    assert r.status_code == 303 and "/workbench" in r.headers["location"]  # PRG a la Workbench (W20/A7)
    caso = get_caso_repository().get(cid)
    assert caso.estado == EstadoCaso.RECHAZADO
    assert caso.aprobado_por == "andres"   # firma humana registrada (P1)


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
    assert "Qué está pasando" in r.text                       # W24·N3: sección de métricas de operación
    assert "Ver controles" in r.text and "RULE-CTR-03" in r.text  # garantías colapsadas, controles siguen en el DOM
    assert "estimado" in r.text  # costo rotulado como estimado (no facturable), ahora en Detalle técnico
    total = len(get_caso_repository().list())
    assert str(total) in r.text  # el KPI de backlog total


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


# W20/A6: la corrección vive en `/workbench/corregir` (HTMX, re-pinta el partial; el legacy `/casos/{id}/corregir`
# se retiró con detalle). Mismos invariantes (P1/P2/P3), verificados sobre la ruta real.

def test_corregir_cambia_dictamen_y_marca_origen_humano(client):
    """Corregir tipo mal (HOGAR_AGUA→AUTO_COLISION) → re-dictamen ≠ NO_CUBIERTO, no terminal, origen HUMANO (P3)."""
    caso = _caso_no_cubierto()
    r = client.post(f"/workbench/corregir/{caso.id}",
                    data={"usuario": "diana.analista", "tipo_siniestro": "AUTO_COLISION"})
    assert r.status_code == 200   # partial #wb-caso re-pintado (sin recarga)
    act = get_caso_repository().get(caso.id)
    assert act.dictamen.resultado != ResultadoCobertura.NO_CUBIERTO   # el dictamen cambió (P2, motor re-decide)
    assert act.estado not in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}  # nunca terminal (P1)
    tipo = next(c for c in act.extraccion.campos if c.nombre == "tipo_siniestro")
    assert tipo.valor == "AUTO_COLISION"
    assert tipo.origen.tipo.value == "HUMANO"   # auditable (P3)


def test_corregir_sin_usuario_400(client):
    cid = _caso_no_cubierto().id
    r = client.post(f"/workbench/corregir/{cid}", data={"tipo_siniestro": "AUTO_COLISION"})
    assert r.status_code == 400   # firma obligatoria (P1)


def test_corregir_caso_terminal_409(client):
    """P1 integridad: un caso ya decidido (APROBADO vía radicar) NO se puede corregir → 409."""
    cid = _caso_pendiente().id
    assert client.post(f"/casos/{cid}/radicar", data={"usuario": "diana"},
                       follow_redirects=False).status_code == 303
    assert get_caso_repository().get(cid).estado == EstadoCaso.APROBADO  # pre-condición verificada
    r = client.post(f"/workbench/corregir/{cid}", data={"usuario": "diana", "tipo_siniestro": "AUTO_COLISION"})
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
