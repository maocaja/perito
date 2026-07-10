"""Tests del rediseño hi-fi (Unit J) — Bandeja + Detalle.

Verifican, fail-closed, los criterios del spec `frontend-hifi-redesign.md`:
- Regla de habilitación (P1 azúcar de UI): "Aprobar" deshabilitado salvo LISTO_PARA_APROBAR;
  "Rechazar" siempre disponible. El gate real sigue en `hitl` (probado en test_u5_c11_dashboard).
- Pseudo-filtros de los KPIs clicables (RESUELTOS, FRAUDE_ALTA) == agregado equivalente del repo.
- Checklist de aprobación: passive, nunca contiene PALABRAS_PROHIBIDAS (P1), refleja faltantes.
- P7: el detalle no filtra literales del prototipo de diseño (datos demo fabricados).
- No regresión: la bandeja en vivo conserva sus atributos HTMX cuando `en_vivo`.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso, c11
from app.observability.replay import get_replay_store
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _por_estado(estado):
    return [c for c in get_caso_repository().list() if c.estado == estado]


def _caso_listo():
    return _por_estado(EstadoCaso.LISTO_PARA_APROBAR)[0]


def _caso_revision():
    return _por_estado(EstadoCaso.REQUIERE_REVISION)[0]


# ---------- Regla de habilitación (P1 azúcar de UI) ----------

def test_aprobar_deshabilitado_si_no_listo(client):
    """REQUIERE_REVISION → el botón 'Aprobar dictamen' trae `disabled`."""
    html = client.get(f"/casos/{_caso_revision().id}").text
    assert "disabled>Aprobar dictamen" in html
    assert "Completa los datos faltantes y re-dictamina" in html  # lock-hint visible


def test_aprobar_habilitado_si_listo(client):
    """LISTO_PARA_APROBAR → 'Aprobar dictamen' SIN `disabled`."""
    html = client.get(f"/casos/{_caso_listo().id}").text
    assert "disabled>Aprobar dictamen" not in html
    assert ">Aprobar dictamen" in html


def test_rechazar_siempre_disponible(client):
    """'Rechazar' nunca se deshabilita, ni siquiera en REQUIERE_REVISION (P1)."""
    for caso in (_caso_listo(), _caso_revision()):
        html = client.get(f"/casos/{caso.id}").text
        assert 'type="submit">Rechazar</button>' in html


# ---------- Pseudo-filtros de los KPIs clicables ----------

def test_kpi_filtro_fraude_alta_igual_agregado(client):
    """`?estado=FRAUDE_ALTA` lista EXACTAMENTE los casos con alerta severidad ALTA.

    Se inyecta una alerta ALTA (el seed trae MEDIA) para ejercitar el caso positivo, no solo la exclusión.
    """
    repo = get_caso_repository()
    con_alerta = next(c for c in repo.list() if c.alerta_fraude)
    alta_caso = con_alerta.model_copy(
        update={"alerta_fraude": con_alerta.alerta_fraude.model_copy(update={"severidad": "ALTA"})}
    )
    repo.save(alta_caso)

    alta = {c.id for c in repo.list() if c.alerta_fraude and c.alerta_fraude.severidad == "ALTA"}
    otros = {c.id for c in repo.list()} - alta
    assert alta_caso.id in alta  # el positivo existe (test no vacuo)
    html = client.get("/casos", params={"estado": "FRAUDE_ALTA"}).text
    for cid in alta:
        assert f"/casos/{cid}" in html
    for cid in otros:
        assert f"/casos/{cid}?" not in html


def test_kpi_filtro_resueltos_igual_terminales(client):
    """`?estado=RESUELTOS` == APROBADO+RECHAZADO. Se aprueba uno para tener un terminal real."""
    listo = _caso_listo()
    assert client.post(f"/casos/{listo.id}/aprobar", data={"usuario": "diana"}).status_code == 200
    repo = get_caso_repository()
    terminales = {c.id for c in repo.list() if c.estado in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)}
    no_term = {c.id for c in repo.list()} - terminales
    html = client.get("/casos", params={"estado": "RESUELTOS"}).text
    assert listo.id in terminales
    for cid in terminales:
        assert f"/casos/{cid}" in html
    for cid in no_term:
        assert f"/casos/{cid}?" not in html


def test_kpi_activo_marca_aria_pressed(client):
    """El KPI del filtro activo se marca (toggle) — apoyo de accesibilidad."""
    html = client.get("/casos", params={"estado": "REQUIERE_REVISION"}).text
    assert 'aria-pressed="true"' in html


# ---------- Checklist de aprobación (passive, P1/P7) ----------

def test_checklist_nunca_contiene_palabras_prohibidas(client):
    """P1 fail-closed: ningún label/detalle del checklist decide (aprobar/rechazar/…)."""
    for caso in get_caso_repository().list():
        traza = get_replay_store().load(caso.id)
        for item in vista_caso.checklist_aprobacion(caso, traza):
            blob = f"{item['label']} {item['detalle']}".lower()
            for prohibida in vista_caso.PALABRAS_PROHIBIDAS:
                assert prohibida not in blob, f"checklist filtró '{prohibida}' en {caso.id}"


def test_checklist_refleja_faltantes(client):
    """El ítem 'Datos completos' es False y detalla los faltantes en un caso con campo ausente."""
    caso = _caso_revision()
    assert vista_caso.faltantes(caso)  # hay al menos un faltante
    items = {i["label"]: i for i in vista_caso.checklist_aprobacion(caso, get_replay_store().load(caso.id))}
    datos = items["Datos del siniestro completos"]
    assert datos["ok"] is False
    assert "faltan" in datos["detalle"]


def test_checklist_completo_en_caso_listo(client):
    """En un caso LISTO, 'Datos completos' y 'Cobertura dictaminada' están en ok."""
    caso = _caso_listo()
    items = {i["label"]: i for i in vista_caso.checklist_aprobacion(caso, get_replay_store().load(caso.id))}
    assert items["Datos del siniestro completos"]["ok"] is True
    assert items["Cobertura dictaminada"]["ok"] is True


# ---------- P7: sin datos del prototipo ----------

def test_detalle_sin_literales_del_prototipo(client):
    """P7: el detalle se arma del Caso real; nada de los datos fabricados del handoff."""
    html = client.get(f"/casos/{_caso_revision().id}").text
    for literal in ("María Restrepo", "FNOL-2026-0142", "#1e91208b", "1.976 tokens"):
        assert literal not in html


# ---------- Alineamiento visual con el prototipo ----------

def test_banner_titulo_refleja_conteo_faltantes(client):
    """El banner titula 'Falta(n) N dato(s)…' (copy del prototipo, con el conteo real)."""
    rec = vista_caso.recomendacion(_caso_revision())
    assert "dato" in rec["titulo"].lower() and "dictaminar" in rec["titulo"].lower()
    assert rec["tono"] == "warn"


def test_detalle_usa_etiquetas_humanas(client):
    """La tabla de datos muestra etiquetas humanas ('N.º de póliza'), no el nombre técnico."""
    html = client.get(f"/casos/{_caso_revision().id}").text
    assert "N.º de póliza" in html
    assert "Monto reclamado" in html


def test_strip_extraccion_muestra_completitud(client):
    """La tira de estado muestra la completitud de campos ('N / 4 campos'), estilo prototipo."""
    strip = vista_caso.confianza_riesgo(_caso_revision(), None)
    ext = next(c for c in strip if c["label"] == "Extracción")
    assert "/ 4 campos" in ext["valor"]


# ---------- Batch de pulido UX (honestidad) ----------

def test_hint_aprobar_honesto_sin_faltantes(client):
    """P7: si el bloqueo NO es por faltantes (póliza/cobertura), el hint NO dice 'completa los datos'."""
    repo = get_caso_repository()
    listo = _caso_listo()  # todos los campos presentes
    escalado = listo.model_copy(update={"estado": EstadoCaso.REQUIERE_REVISION})
    repo.save(escalado)
    assert not vista_caso.faltantes(escalado)  # sin faltantes, pero no aprobable
    html = client.get(f"/casos/{escalado.id}").text
    assert "Completa los datos faltantes" not in html  # no miente
    assert "resuelve lo indicado" in html


def test_evidencia_placeholder_se_limpia(client):
    """La evidencia técnica del extractor/preset ('span:…', 'extracted from…') se muestra legible."""
    html = client.get(f"/casos/{_caso_listo().id}").text
    assert "extraído del aviso" in html
    assert "span:numero_poliza" not in html
    assert "extracted from redacted_texto" not in html


def test_deducible_oculto_sin_cobertura(client):
    """El deducible solo se muestra con cobertura real; no en un caso escalado/sin cobertura."""
    revision = _caso_revision()
    if revision.dictamen:
        assert revision.dictamen.resultado.value not in ("CUBIERTO", "CUBIERTO_PARCIAL")
    assert "Deducible calculado" not in client.get(f"/casos/{revision.id}").text


def test_cobertura_humanizada_en_tira(client):
    """La tira de estado muestra la cobertura humanizada ('Requiere revisión'), no el enum crudo."""
    strip = vista_caso.confianza_riesgo(_caso_revision(), None)
    cob = next(c for c in strip if c["label"] == "Cobertura")
    assert cob["valor"] == "Requiere revisión"


def test_checklist_verificacion_na_no_bloquea(client):
    """En modo determinístico la verificación es 'no aplica' (na), no un pendiente que nunca llega."""
    items = {i["label"]: i for i in vista_caso.checklist_aprobacion(_caso_listo(), None)}
    verif = items["Verificación de fidelidad"]
    assert verif["na"] is True and verif["ok"] is False
    assert "no aplica" in verif["detalle"]


# ---------- Unit K: alineación de la bandeja con el prototipo ----------

def test_ramo_derivado_de_tipo_siniestro(client):
    """Ramo honesto: AUTO_*→Autos, HOGAR_*→Hogar, sin match→'—'. Nunca 'Vida' (P7)."""
    for c in get_caso_repository().list():
        tipo = next((x.valor for x in c.extraccion.campos if x.nombre == "tipo_siniestro" and not x.ausente), None)
        ramo = vista_caso.ramo_de(c)
        assert ramo != "Vida"  # no existe en el dominio, nunca se inventa
        if tipo and tipo.upper().startswith("AUTO"):
            assert ramo == "Autos"
        elif tipo and tipo.upper().startswith("HOGAR"):
            assert ramo == "Hogar"
        else:
            assert ramo == "—"


def test_ramo_ausente_es_guion(client):
    """tipo_siniestro ausente → '—' (no adivina)."""
    from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
    base = get_caso_repository().list()[0]
    sin_tipo = base.model_copy(update={"extraccion": ExtraccionValidada(
        campos=[CampoExtraido(nombre="tipo_siniestro", valor=None, ausente=True)])})
    assert vista_caso.ramo_de(sin_tipo) == "—"


def test_bandeja_columnas_nuevas(client):
    """La bandeja muestra las columnas Póliza + Ramo (espejo del prototipo, con dato real)."""
    html = client.get("/casos").text
    assert "<div>Póliza</div>" in html and "<div>Ramo</div>" in html
    assert "<div>Siniestro</div>" not in html  # la columna vieja se reemplazó


def test_bandeja_filas_uniformes(client):
    """Look uniforme como el prototipo: sin acento izquierdo ni atenuado (se quitó la jerarquía)."""
    html = client.get("/casos").text
    assert "row-accent" not in html and "row-muted" not in html


def test_p7_bandeja_sin_id_fabricado(client):
    """P7: el id del caso es el uuid real, no un 'FNOL-YYYY-NNNN' fabricado como el prototipo."""
    assert "FNOL-" not in client.get("/casos").text


# ---------- Unit L: coherencia de estados + fraude visible ----------

def test_estado_listo_se_muestra_neutral(client):
    """P1/coherencia: LISTO_PARA_APROBAR se muestra 'Listo para decisión', nunca 'Listo p/ aprobar'."""
    html_bandeja = client.get("/casos").text
    assert "Listo para decisión" in html_bandeja
    assert "Listo p/ aprobar" not in html_bandeja
    assert "Listos para decisión" in html_bandeja  # KPI reetiquetado
    html_detalle = client.get(f"/casos/{_caso_listo().id}").text
    assert "Listo p/ aprobar" not in html_detalle


def test_fraude_no_cambia_estado(client):
    """P6: un caso con fraude NO se fuerza a REQUIERE_REVISION — el fraude es ortogonal al estado."""
    con_fraude = [c for c in get_caso_repository().list() if c.alerta_fraude]
    assert con_fraude, "el seed debe traer al menos un caso con alerta de fraude"
    # el fraude coexiste con LISTO_PARA_APROBAR (no lo escala): P6 puro
    assert any(c.estado == EstadoCaso.LISTO_PARA_APROBAR for c in con_fraude)


def test_senal_fraude_legible(client):
    """La señal de fraude se resume en lenguaje plano; no expone el `referencia` crudo (P5)."""
    con_fraude = next(c for c in get_caso_repository().list() if c.alerta_fraude)
    senal = vista_caso.senal_fraude(con_fraude)
    assert senal and senal in vista_caso._SENAL_FRAUDE.values()
    # no filtra el texto técnico crudo (ej. 'MONTO_EXCEDE_SUMA: 15000000 > ...')
    assert ">" not in senal and "_" not in senal


def test_senal_fraude_none_sin_alerta(client):
    """Sin alerta → None (no inventa señal)."""
    sin = next(c for c in get_caso_repository().list() if not c.alerta_fraude)
    assert vista_caso.senal_fraude(sin) is None


# ---------- Unit N: visibilidad Tier-1 ----------

def test_verificacion_trayectoria_cita_clausula(client):
    """El check 'cita cláusula' es True en un caso cuyo dictamen cita cláusula (determinístico)."""
    con_clausula = next(c for c in get_caso_repository().list() if c.dictamen and c.dictamen.clausula)
    checks = {c["label"]: c for c in vista_caso.verificacion_trayectoria(con_clausula, get_replay_store().load(con_clausula.id))}
    assert checks["El dictamen cita cláusula"]["ok"] is True


def test_verificacion_trayectoria_sin_campos_inventados(client):
    """El check de campos verifica que todo campo presente tiene origen (P7, sin fabricación)."""
    caso = _caso_listo()
    checks = {c["label"]: c for c in vista_caso.verificacion_trayectoria(caso, get_replay_store().load(caso.id))}
    item = checks["Sin campos inventados (todos con origen)"]
    presentes = [c for c in caso.extraccion.campos if not c.ausente and c.valor is not None]
    esperado = all(c.origen is not None for c in presentes) and bool(presentes)
    assert item["ok"] is esperado


def test_latencia_de_traza(client):
    """La latencia sale de la traza (suma de latencia_ms); None si no hay traza."""
    caso = _caso_listo()
    lat = vista_caso.latencia_caso(get_replay_store().load(caso.id))
    assert lat is None or lat.endswith("s") or lat.endswith("ms")
    assert vista_caso.latencia_caso(None) is None  # sin traza → None (no inventa)


def test_razon_escalamiento_solo_en_revision(client):
    """La razón de escalamiento aparece solo en REQUIERE_REVISION; None en otros estados."""
    assert vista_caso.razon_escalamiento(_caso_revision()) is not None
    assert vista_caso.razon_escalamiento(_caso_listo()) is None


def test_p7_detalle_no_finge_score_de_juez_por_caso(client):
    """P7: el detalle referencia el juez Claude como eval de CI, no como score por-caso en vivo."""
    html = client.get(f"/casos/{_caso_listo().id}").text
    assert "pytest -m agentic" in html  # referencia honesta a CI
    assert "Verificación de la trayectoria" in html


def test_panel_auditoria_eu_ai_act(client):
    """El panel se reencuadra como trazabilidad de cumplimiento (EU AI Act / NAIC) + sello del juez Claude."""
    html = client.get("/panel").text
    assert "EU AI Act" in html
    assert "juez Claude" in html


# ---------- No regresión: bandeja en vivo (HTMX) ----------

def test_bandeja_live_htmx_preservado(client, monkeypatch):
    """Con `en_vivo` (demo_live != off) el bloque #bandeja-live conserva sus atributos HTMX."""
    monkeypatch.setattr(c11.settings, "demo_live", "deterministic")
    html = client.get("/casos").text
    assert 'id="bandeja-live"' in html
    assert 'hx-get="/casos' in html
    assert 'hx-select="#bandeja-live"' in html
    assert 'hx-swap="outerHTML"' in html
