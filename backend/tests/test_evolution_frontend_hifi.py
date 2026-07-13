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

# W20/A6+A7: la decisión vive en el panel de la Workbench. 'Radicar caso' (→APROBADO) está deshabilitado salvo
# LISTO_PARA_APROBAR; 'Rechazar siniestro' (→RECHAZADO) está disponible mientras el caso no sea terminal (P1).

def test_radicar_no_ofrecido_si_no_listo(client):
    """REQUIERE_REVISION → 'Radicar caso' NO se ofrece (L1: la primaria es otra acción NO terminal)."""
    html = client.get(f"/workbench/caso/{_caso_revision().id}").text
    assert "Radicar caso" not in html


def test_radicar_habilitado_si_listo(client):
    """LISTO_PARA_APROBAR → 'Radicar caso' SIN `disabled`."""
    html = client.get(f"/workbench/caso/{_caso_listo().id}").text
    assert "disabled>Radicar caso" not in html
    assert ">Radicar caso" in html


def test_rechazar_disponible_si_no_terminal(client):
    """'Rechazar siniestro' se ofrece mientras el caso no sea terminal (P1: el humano puede negar)."""
    for caso in (_caso_listo(), _caso_revision()):
        html = client.get(f"/workbench/caso/{caso.id}").text
        assert "Rechazar siniestro" in html


# ---------- Pseudo-filtros de los KPIs clicables ----------

# W20/A6: el board `bandeja.html` se retiró; el filtrado (`_filtrar_bandeja`) que alimentaba sus KPIs sigue
# vivo (lo usa la cola de la Workbench por estado). Se verifica directo sobre la función (sin la UI del board).

def test_filtro_fraude_alta_igual_agregado(client):
    """`_filtrar_bandeja(..., 'FRAUDE_ALTA')` == EXACTAMENTE los casos con alerta severidad ALTA.

    Se inyecta una alerta ALTA (el seed trae MEDIA) para ejercitar el caso positivo, no solo la exclusión.
    """
    repo = get_caso_repository()
    con_alerta = next(c for c in repo.list() if c.alerta_fraude)
    alta_caso = con_alerta.model_copy(
        update={"alerta_fraude": con_alerta.alerta_fraude.model_copy(update={"severidad": "ALTA"})}
    )
    repo.save(alta_caso)
    todos = repo.list()
    esperado = {c.id for c in todos if c.alerta_fraude and c.alerta_fraude.severidad == "ALTA"}
    assert alta_caso.id in esperado  # el positivo existe (test no vacuo)
    assert {c.id for c in c11._filtrar_bandeja(todos, "FRAUDE_ALTA")} == esperado


def test_filtro_resueltos_igual_terminales(client):
    """`_filtrar_bandeja(..., 'RESUELTOS')` == APROBADO+RECHAZADO. Se radica uno para tener un terminal real."""
    listo = _caso_listo()
    assert client.post(f"/casos/{listo.id}/radicar", data={"usuario": "diana"},
                       follow_redirects=False).status_code == 303
    todos = get_caso_repository().list()
    esperado = {c.id for c in todos if c.estado in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)}
    assert listo.id in esperado
    assert {c.id for c in c11._filtrar_bandeja(todos, "RESUELTOS")} == esperado


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
    assert items["Resultado de cobertura"]["ok"] is True


# ---------- P7: sin datos del prototipo ----------

def test_detalle_sin_literales_del_prototipo(client):
    """P7: el detalle se arma del Caso real; nada de los datos fabricados del handoff."""
    html = client.get(f"/workbench/caso/{_caso_revision().id}").text
    for literal in ("María Restrepo", "FNOL-2026-0142", "#1e91208b", "1.976 tokens"):
        assert literal not in html


# ---------- Alineamiento visual con el prototipo ----------

def test_banner_titulo_refleja_conteo_faltantes(client):
    """El banner titula 'Falta(n) N dato(s)…' (copy del prototipo, con el conteo real)."""
    caso = _caso_revision()
    rec = vista_caso.recomendacion(caso)
    falt = vista_caso.faltantes(caso)
    # L2: el banner nombra el dato faltante en HUMANO (sin "dictaminar" ni el nombre técnico crudo)
    label_humano = vista_caso._LABEL_CAMPO.get(falt[0], falt[0]).lower()
    assert label_humano in rec["titulo"].lower()
    assert "dictaminar" not in rec["titulo"].lower() and falt[0] not in rec["titulo"]
    assert rec["tono"] == "warn"


def test_caso_usa_etiquetas_humanas(client):
    """La tabla de datos del caso muestra etiquetas humanas ('Póliza', 'Monto reclamado'), no el nombre técnico."""
    html = client.get(f"/workbench/caso/{_caso_revision().id}").text
    assert "Póliza" in html
    assert "Valor de la reclamación" in html   # L2: label humano y consistente (antes "Monto reclamado")


def test_strip_extraccion_muestra_completitud(client):
    """La tira de estado muestra la completitud de campos ('N / 4 campos'), estilo prototipo."""
    strip = vista_caso.confianza_riesgo(_caso_revision(), None)
    ext = next(c for c in strip if c["label"] == "Extracción")
    assert "/ 4 campos" in ext["valor"]


# ---------- Batch de pulido UX (honestidad) ----------

def test_hint_aprobar_honesto_sin_faltantes(client):
    """P7: si el bloqueo NO es por faltantes, la recomendación NO dice 'completa los datos' (unit sobre la fuente).

    Se prueba `recomendacion()` directamente (el banner de la Workbench la renderiza); robusto al markup.
    """
    listo = _caso_listo()  # todos los campos presentes
    escalado = listo.model_copy(update={"estado": EstadoCaso.REQUIERE_REVISION})
    assert not vista_caso.faltantes(escalado)  # sin faltantes, pero no aprobable
    rec = vista_caso.recomendacion(escalado)
    blob = f"{rec['titulo']} {rec.get('subtitulo', '')} {rec.get('detalle', '')}".lower()
    assert "completa los datos faltantes" not in blob  # no miente sobre el bloqueo


def test_deducible_oculto_sin_cobertura(client):
    """El deducible solo se muestra con cobertura real; no en un caso escalado/sin cobertura."""
    revision = _caso_revision()
    if revision.dictamen:
        assert revision.dictamen.resultado.value not in ("CUBIERTO", "CUBIERTO_PARCIAL")
    assert "Deducible calculado" not in client.get(f"/workbench/caso/{revision.id}").text


def test_cobertura_humanizada_en_health(client):
    """La cobertura se muestra humanizada ('Requiere revisión'), no el enum crudo. W24·N1: ya no vive en el
    strip (salió por dedup); su hogar autoritativo es el Estado operativo / panel derecho."""
    checks = vista_caso.health_check(_caso_revision(), None)["checks"]
    cob = next(c for c in checks if c["label"] == "Resultado de cobertura")
    assert cob["detalle"] == "Requiere revisión"


def test_checklist_verificacion_na_no_bloquea(client):
    """En modo determinístico la verificación es 'no aplica' (na), no un pendiente que nunca llega."""
    items = {i["label"]: i for i in vista_caso.checklist_aprobacion(_caso_listo(), None)}
    verif = items["Coincidencia entre fuentes"]
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


# W20/A6: los tests de markup del board (columnas Póliza/Ramo, filas uniformes, id sin FNOL) se retiraron con
# `bandeja.html`. La cola de la Workbench tiene su propia estructura (W8) y cobertura (test_w8/test_w16).


# ---------- Unit L: coherencia de estados + fraude visible ----------

def test_estado_listo_se_muestra_neutral(client):
    """P1/coherencia: LISTO_PARA_APROBAR se muestra 'Listo p/ aprobar' nunca (etiqueta neutral en el detalle)."""
    html_detalle = client.get(f"/workbench/caso/{_caso_listo().id}").text
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


# W20/A6: 'test_p7_detalle_no_finge_score_de_juez_por_caso' se retiró — probaba la sección "Verificación de la
# trayectoria" de la página `detalle` (eliminada). El P7 del juez-como-eval-de-CI se verifica en el panel de
# cumplimiento (test_panel_auditoria_eu_ai_act) y la lógica en test_verificacion_trayectoria_*.


def test_panel_auditoria_eu_ai_act(client):
    """El panel se reencuadra como trazabilidad de cumplimiento (EU AI Act / NAIC) + sello del juez Claude."""
    html = client.get("/panel").text
    assert "EU AI Act" in html
    assert "juez Claude" in html


# ---------- U1: clasificación + prioridad + routing ----------

def test_prioridad_cita_regla(client):
    """La prioridad devuelve nivel + motivo (regla citada), passive."""
    for c in get_caso_repository().list():
        p = vista_caso.prioridad(c)
        assert p["nivel"] in ("ALTA", "MEDIA", "BAJA")
        assert p["motivo"]  # siempre cita el porqué


def test_prioridad_fraude_alta_es_alta(client):
    """Fraude ALTA → prioridad ALTA (regla)."""
    base = next(c for c in get_caso_repository().list() if c.alerta_fraude)
    alta = base.model_copy(update={"alerta_fraude": base.alerta_fraude.model_copy(update={"severidad": "ALTA"})})
    assert vista_caso.prioridad(alta)["nivel"] == "ALTA"


def test_prioridad_no_muta_estado(client):
    """P1: prioridad/routing son passive — no tocan el estado."""
    c = _caso_listo()
    antes = c.estado
    vista_caso.prioridad(c); vista_caso.equipo(c); vista_caso.clasificar(c)
    assert c.estado == antes


def test_equipo_por_producto_y_siu(client):
    """Routing: producto → equipo; fraude → sugiere SIU (P6, sin cambiar estado)."""
    con_fraude = next((c for c in get_caso_repository().list() if c.alerta_fraude), None)
    sin_fraude = next((c for c in get_caso_repository().list() if not c.alerta_fraude), None)
    assert con_fraude and sin_fraude, "el seed debe traer casos con y sin fraude"
    e = vista_caso.equipo(con_fraude)
    assert e["equipo"] and e["siu"] is True
    assert vista_caso.equipo(sin_fraude)["siu"] is False


def test_clasificar_no_inventa_tipo(client):
    """P7: clasificar() devuelve '—' si tipo_siniestro está ausente; no inventa."""
    from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
    base = _caso_listo()
    sin_tipo = base.model_copy(update={"extraccion": ExtraccionValidada(
        campos=[CampoExtraido(nombre="tipo_siniestro", valor=None, ausente=True)])})
    assert vista_caso.clasificar(sin_tipo)["tipo"] == "—"


# W20/A6: 'test_detalle_muestra_prioridad_y_equipo' se retiró (render de la página `detalle`). La lógica de
# prioridad/routing se prueba en test_prioridad_cita_regla / test_prioridad_fraude_alta_es_alta / test_equipo_*.


# ---------- U2: documentos requeridos por producto ----------

def test_docs_por_producto_distintos(client):
    """Cada producto exige documentos distintos (catálogo determinístico)."""
    autos = vista_caso.documentos_requeridos("Autos")
    hogar = vista_caso.documentos_requeridos("Hogar")
    assert autos and hogar and autos != hogar


def test_docs_producto_no_modelado_no_inventa(client):
    """P7: producto sin catálogo → disponible=False, sin lista inventada."""
    assert vista_caso.documentos_requeridos("Vida") == []
    ck = vista_caso.checklist_documentos(_caso_listo())  # ramo Autos/Hogar/— según el caso
    assert isinstance(ck["disponible"], bool)
    if not ck["disponible"]:
        assert ck["docs"] == []


# W20/A6: 'test_detalle_muestra_documentos' se retiró (render de la sección de docs de la página `detalle`). El
# catálogo de documentos por producto se prueba en test_docs_por_producto_distintos / test_docs_producto_no_modelado.


# W20/A6: la no-regresión del auto-refresh en vivo ahora aplica a la cola de la Workbench (auto-poll cada 3s),
# no al board retirado. Cubierto por los tests de la Workbench (test_w1/test_w8).
