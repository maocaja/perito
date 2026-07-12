"""Tests W22 — content design + interacción del Workbench.

Blindaje de las correcciones de lenguaje/jerarquía/acción. Cadencia AI-DLC (spec w22-content-design.md).

- **L1** · un solo bloqueo + UNA acción primaria por estado (recomendación == acción). 🔒P1: solo Radicar
  alcanza terminal (LISTO); en estado bloqueado la primaria NO es terminal; sin repetición triple.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.scenarios import construir_caso_preset
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    return TestClient(app)


def _guardar(key, **update):
    reset_caso_repository()
    caso = construir_caso_preset(key)
    if update:
        caso = caso.model_copy(update=update)
    get_caso_repository().save(caso)
    return caso


# ───────────────────────── L1 · acción primaria única por estado ─────────────────────────

def test_accion_primaria_bloqueado_es_no_terminal():
    """REQUIERE_REVISION + faltantes → primaria 'Solicitar al asegurado' (NO terminal, P1)."""
    caso = construir_caso_preset("campos-faltantes")
    accion = vista_caso.recomendacion(caso)["accion"]
    assert accion["endpoint"] == "solicitar_docs" and accion["kind"] == "primary"
    assert accion["label"] == "Solicitar al asegurado"


def test_accion_primaria_listo_es_radicar():
    """LISTO_PARA_APROBAR → primaria 'Radicar caso' (terminal con firma, P1)."""
    accion = vista_caso.recomendacion(construir_caso_preset("feliz"))["accion"]
    assert accion["endpoint"] == "radicar" and accion["kind"] == "go" and accion["confirm"]


def test_accion_primaria_terminal_es_none():
    """Caso resuelto → sin primaria (None)."""
    caso = construir_caso_preset("feliz").model_copy(
        update={"estado": EstadoCaso.APROBADO, "aprobado_por": "ana"})
    assert vista_caso.recomendacion(caso)["accion"] is None


def test_render_primaria_por_estado(client):
    """El panel renderiza UNA primaria = la recomendación del estado."""
    bloq = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{bloq.id}").text
    assert "Solicitar al asegurado" in html and "Siguiente paso" in html
    assert "/radicar" not in html                       # Radicar no se ofrece en estado bloqueado (P1)

    listo = _guardar("feliz")
    html = client.get(f"/workbench/caso/{listo.id}").text
    assert 'action="/casos/%s/radicar"' % listo.id in html


def test_sin_repeticion_triple_del_bloqueo(client):
    """L1: el detalle del bloqueo aparece UNA vez (bloque central), no repetido en el panel derecho."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    # el texto largo de la recomendación (bloque central) NO se repite en el panel (wb-reco-text)
    texto = vista_caso.recomendacion(caso)["texto"]
    assert html.count(texto.split(".")[0]) == 1          # la 1ª frase del detalle aparece una sola vez


def test_boton_corregir_es_resultado_humano(client):
    """El botón de corrección dice el RESULTADO ('Guardar y verificar'), no la mecánica técnica."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Guardar y verificar" in html and "Corregir y recalcular" not in html


def test_recomendacion_degradada_anula_la_accion(monkeypatch):
    """🔒P1 fail-closed (code-review L1 2ª pasada): si la recomendación se degrada por una palabra de decisión,
    la acción primaria se ANULA (no queda un botón que no case con el texto neutro)."""
    # forzamos el fail-closed marcando como prohibida una palabra que SÍ aparece en la recomendación de un LISTO
    monkeypatch.setattr(vista_caso, "PALABRAS_PROHIBIDAS", vista_caso.PALABRAS_PROHIBIDAS | {"dictamen"})
    rec = vista_caso.recomendacion(construir_caso_preset("feliz"))
    assert rec["accion"] is None
    assert rec["titulo"] == "Decisión humana requerida"


@pytest.mark.parametrize("estado", [EstadoCaso.RECIBIDO, EstadoCaso.EN_PROCESO, EstadoCaso.EN_REVISION])
def test_accion_primaria_estado_no_mapeado_es_none(estado):
    """Robustez (code-review L1 2ª pasada): un estado NO mapeado no defaultea a Radicar → sin primaria."""
    caso = construir_caso_preset("feliz").model_copy(update={"estado": estado})
    assert vista_caso.recomendacion(caso)["accion"] is None


# ───────────────────────── L2 · lenguaje humano (de-jerga) ─────────────────────────

def test_tipo_siniestro_se_muestra_humano(client):
    """El tipo se muestra HUMANO ('Colisión vehicular'), no el enum; el dato/campo sigue siendo el enum (P2)."""
    caso = _guardar("feliz")
    assert vista_caso.clasificar(caso)["tipo_humano"] == "Colisión vehicular"
    assert vista_caso.clasificar(caso)["tipo"] == "AUTO_COLISION"       # el código canónico no cambia
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Colisión vehicular" in html


def test_labels_de_campo_humanos_y_consistentes(client):
    """Los labels son humanos y CONSISTENTES entre tabla, checklist y resumen (sin crudos)."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Valor de la reclamación" in html
    assert "Monto reclamado" not in html and "Numero poliza" not in html


def test_regla_tecnica_bajo_disclosure_no_en_superficie(client):
    """L2 + encode-not-hide: la superficie es humana ('no la IA'); la regla/motor técnicos viven a un click
    ('Ver regla aplicada'), NO borrados."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "no la IA" in html and "Ver regla aplicada" in html   # humano + disclosure
    assert "no el LLM" in html                                    # el técnico sigue en el DOM (P2, encode-not-hide)


def test_confianza_calma_pero_pct_en_el_dom(client):
    """L2: un campo verificado muestra 'Verificado' (sin % ruidoso); pero el % sigue en el DOM (title del campo)
    aunque sea alto — encode-not-hide (mover, no borrar)."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Verificado" in html
    assert "confianza 90%" in html   # el % vive en el title (presente + accesible), no se borró


def test_recomendacion_faltantes_sin_nombre_tecnico(client):
    """El bloqueo por dato faltante se nombra en HUMANO, sin el nombre técnico crudo del campo."""
    rec = vista_caso.recomendacion(construir_caso_preset("campos-faltantes"))
    assert "monto_reclamado" not in (rec["titulo"] + rec["texto"])
    assert "valor de la reclamación" in (rec["titulo"] + rec["texto"]).lower()


def test_labels_fuente_unica_entre_superficies():
    """L2 (code-review 2ª pasada): campo/estado/cobertura tienen FUENTE ÚNICA → el panel y la Workbench
    nombran igual cada cosa (sin mapas duplicados divergentes)."""
    assert vista_caso.label_campo("monto_reclamado") == "Valor de la reclamación"
    assert vista_caso.label_estado("REQUIERE_REVISION") == "Necesita revisión"   # antes el panel decía otro
    assert vista_caso.label_cobertura("CUBIERTO_PARCIAL") == "Cubierto parcial"


# ───────────────────────── L3 · densidad ─────────────────────────

def test_mas_acciones_agrupa_secundarias_sin_ocultarlas(client):
    """Las secundarias (rechazar/fraude/escalar/carta/guardar) viven bajo 'Más acciones' (disclosure) —
    presentes en el DOM, sin competir con la primaria."""
    caso = _guardar("feliz")   # LISTO → primaria Radicar
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'class="wb-mas"' in html and "Más acciones" in html
    # toda la funcionalidad sigue accesible (dentro del disclosure)
    assert "Rechazar siniestro" in html and "Guardar" in html
    # la primaria NO está dentro del disclosure (aparece antes que 'Más acciones')
    assert html.index('/casos/%s/radicar' % caso.id) < html.index('Más acciones')


def test_checklist_pendiente_visible_resto_a_un_click(client):
    """El checklist muestra 'Pendiente' a la vista y el resto bajo 'Ver todas' — encode-not-hide: la lista
    completa sigue en el DOM."""
    caso = _guardar("campos-faltantes")   # tiene al menos un check pendiente (warn)
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Pendiente" in html
    assert 'class="wb-hc-more"' in html and "Ver todas las verificaciones" in html


def test_campo_faltante_dice_no_encontrado(client):
    """La fila de un campo faltante dice 'No encontrado' (claro), no un críptico 'Falta'."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "No encontrado" in html


# ───────────────────────── L4 · cola con razón operativa ─────────────────────────

def test_razon_operativa_por_estado():
    """Cada caso trae una razón operativa (por qué está en la cola) — para elegir sin abrir. Passive (P1)."""
    assert "falta" in vista_caso.razon_cola(construir_caso_preset("campos-faltantes")).lower()
    assert vista_caso.razon_cola(construir_caso_preset("cobertura-negativa")) == "Cobertura no aplica"
    assert vista_caso.razon_cola(construir_caso_preset("feliz")) == "Listo para revisar"


def test_razon_no_contiene_palabras_prohibidas():
    """🔒P1: la razón de la cola nunca decide (no contiene aprobar/rechazar/…)."""
    from app.demo.seed import seed_demo_casos
    seed_demo_casos()
    for c in get_caso_repository().list():
        razon = vista_caso.razon_cola(c).lower()
        assert not any(p in razon for p in vista_caso.PALABRAS_PROHIBIDAS)


def test_cola_renderiza_razon_y_tipo_humano(client):
    """La tarjeta de la cola muestra la razón operativa y el tipo HUMANO (no 'Auto Colision' crudo)."""
    from app.demo.seed import seed_demo_casos
    seed_demo_casos()
    html = client.get("/workbench").text
    assert "wb-card-razon" in html
    assert "Colisión vehicular" in html and "Auto Colision" not in html


# ───────────────────────── L5 · confirmaciones fuertes post-acción ─────────────────────────

def test_confirmacion_fuerte_solo_en_terminal(client):
    """Tras una acción terminal (APROBADO) → confirmación INEQUÍVOCA con referencia del expediente y siguiente
    paso, anunciable a lector de pantalla (role=status). Un caso NO terminal no la muestra."""
    aprobado = _guardar("feliz", estado=EstadoCaso.APROBADO, aprobado_por="ana")
    html = client.get(f"/workbench/caso/{aprobado.id}").text
    assert "Caso radicado" in html
    assert ("#" + aprobado.id[:8].upper()) in html          # referencia del expediente
    assert 'role="status"' in html and "Continuar" in html   # anuncio + siguiente paso

    bloqueado = _guardar("campos-faltantes")
    assert 'data-slot="confirmacion"' not in client.get(f"/workbench/caso/{bloqueado.id}").text


def test_confirmacion_redacta_firmante(client):
    """🔒P5: el firmante en la confirmación se redacta (no PII cruda); la referencia es el id opaco, no PII."""
    aprobado = _guardar("feliz", estado=EstadoCaso.APROBADO, aprobado_por="Juan C.C. 1.098.765.432")
    html = client.get(f"/workbench/caso/{aprobado.id}").text
    assert "1.098.765.432" not in html   # el redactor de spans enmascara la cédula del firmante


def test_indicador_carga_en_recalculo(client):
    """El recálculo inline muestra un estado de CARGA ('Guardando…') mientras el servidor re-evalúa (HTMX)."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "htmx-indicator" in html and "Guardando" in html


def test_referencia_honesta_no_finge_radicado_oficial(client):
    """🔒P7 (code-review L5): la referencia es el id interno del caso ('Referencia del caso #…'), no un
    'Expediente #…' que finja un número de radicado oficial."""
    aprobado = _guardar("feliz", estado=EstadoCaso.APROBADO, aprobado_por="ana")
    html = client.get(f"/workbench/caso/{aprobado.id}").text
    assert "Referencia del caso" in html and "Expediente #" not in html


# ───────────────────────── L6 · accesibilidad + evidencia al click ─────────────────────────

def test_evidencia_se_abre_al_click_en_un_campo(client):
    """Un campo presente es un control que abre su EVIDENCIA (drawer) al click — salto a la fuente, sin fricción."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'hx-get="/workbench/evidencia/' in html and 'hx-target="#wb-drawer"' in html
    # el endpoint responde con el visor de evidencia
    assert client.get(f"/workbench/evidencia/{caso.id}?campo=Póliza").status_code == 200


def test_banner_estado_es_region_viva(client):
    """🔒 a11y: el banner de estado es una región viva (role=status/aria-live) → el cambio tras recalcular se
    anuncia a lector de pantalla."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    ini = html.find('data-slot="status"')
    assert 'role="status"' in html[ini - 120:ini + 120] and 'aria-live="polite"' in html[ini - 120:ini + 120]


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
