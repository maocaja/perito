"""Tests W23 — última pasada de precisión (content + microcopy + flujo).

Blindaje de los refinamientos finales (spec w23-precision-pass.md). Regla de oro (W22): MOVER lo técnico,
no borrar; label ≠ valor. Invariantes P1–P7 + encode-not-hide intactos.

- **M1** · el panel enfoca la ACCIÓN (no re-enuncia el problema); Estado operativo = conteo, detalle a un click.
"""

import re

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


# ───────────────────────── M1 · panel enfoca la acción + estado operativo colapsado ─────────────────────────

def test_accion_trae_titulo_orientado_a_la_accion():
    """La acción primaria trae un `titulo` que es la ACCIÓN (imperativo), no el enunciado del problema."""
    acc_falta = vista_caso.recomendacion(construir_caso_preset("campos-faltantes"))["accion"]
    assert "solicitar" in acc_falta["titulo"].lower() and "asegurado" in acc_falta["titulo"].lower()
    acc_listo = vista_caso.recomendacion(construir_caso_preset("feliz"))["accion"]
    assert "firma" in acc_listo["titulo"].lower()


def test_accion_titulo_sin_palabras_prohibidas():
    """🔒P1: el título de acción nunca decide (aprobar/rechazar/…)."""
    for key in ("campos-faltantes", "feliz", "cobertura-negativa", "no-encontrada"):
        acc = vista_caso.recomendacion(construir_caso_preset(key))["accion"]
        if acc:
            assert not any(p in acc["titulo"].lower() for p in vista_caso.PALABRAS_PROHIBIDAS)


def test_panel_enfoca_accion(client):
    """El panel 'Siguiente paso' muestra la ACCIÓN a realizar (no re-enuncia 'Falta un dato', que ya está en el
    banner + el bloque central de resolución)."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    # el título de acción del panel está presente
    acc = vista_caso.recomendacion(caso)["accion"]
    assert acc["titulo"] in html


def test_estado_operativo_conteo_pendientes_colapsado(client):
    """M1: el Estado operativo muestra el CONTEO de pendientes; el detalle se despliega a un click (colapsado
    por defecto). encode-not-hide: la lista completa sigue en el DOM."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert re.search(r"\d+ pendiente", html)                        # conteo visible
    assert 'class="wb-hc-more"' in html and "y el resto" in html     # detalle a un click
    assert "<summary>Ver" in html                                    # colapsable (no lista suelta)


# ───────────────────────── M2 · resumen sin jerga interna ─────────────────────────

def test_resumen_operativo_sin_jerga_de_regla():
    """El resumen NO expone el IDENTIFICADOR técnico de la regla ni el enum interno. (W24: 'cobertura pendiente
    de regla' en humano SÍ se permite —es lo que el usuario pidió—; lo prohibido es el id de la regla del motor
    y el enum crudo.)"""
    for key in ("feliz", "campos-faltantes", "cobertura-negativa", "no-encontrada"):
        caso = construir_caso_preset(key)
        prosa = vista_caso.resumen_narrativo(caso)
        assert "PRE_MOTOR" not in prosa
        if caso.dictamen and caso.dictamen.regla_aplicada:
            assert caso.dictamen.regla_aplicada not in prosa   # el id técnico de la regla no se filtra
        assert "AUTO_COLISION" not in prosa and "HOGAR_AGUA" not in prosa


def test_resumen_escalado_explica_por_que():
    """Cuando el motor no puede dictaminar (falta un dato), el resumen ejecutivo nombra el faltante en humano."""
    prosa = vista_caso.resumen_narrativo(construir_caso_preset("campos-faltantes")).lower()
    assert "falta" in prosa and "obligatorio" in prosa
    assert "valor de la reclamación" in prosa
    assert "cobertura pendiente de regla" in prosa


def test_resumen_terminal_dice_el_resultado_humano():
    """Con dictamen terminal, el resumen dice el resultado humano ('cubierto'/'no cubierto'), sin enum ni id de regla."""
    assert "cobertura: cubierto" in vista_caso.resumen_narrativo(construir_caso_preset("feliz")).lower()
    assert "cobertura: no cubierto" in vista_caso.resumen_narrativo(construir_caso_preset("cobertura-negativa")).lower()


def test_p2_regla_no_desaparece_solo_se_mueve():
    """🔒P2 (MOVER, no borrar): la cita de la regla del motor SIGUE existiendo (en el resumen del copiloto /
    'Ver regla aplicada'), aunque salga de la prosa del operador."""
    r = vista_caso.resumen_copiloto(construir_caso_preset("feliz"))
    cob = " ".join(l["texto"] for l in r["lineas"])
    caso = construir_caso_preset("feliz")
    assert caso.dictamen.regla_aplicada in cob   # la regla se cita (P2), solo que no en la prosa


# ───────────────────────── M3 · enums fuera del formulario ─────────────────────────

def test_tipo_corregible_es_dropdown_humano():
    """El campo editable 'tipo_siniestro' es un dropdown con etiquetas HUMANAS y valores ENUM (label ≠ valor)."""
    tipo = next(c for c in vista_caso.campos_corregibles(construir_caso_preset("feliz"))
                if c["nombre"] == "tipo_siniestro")
    assert tipo["tipo"] == "select"
    labels = {o["label"] for o in tipo["opciones"]}
    valores = {o["valor"] for o in tipo["opciones"]}
    assert "Colisión vehicular" in labels and "AUTO_COLISION" in valores   # humano en la vista, enum en el value


def test_render_form_tipo_es_select_con_enum_en_value(client):
    """El HTML del form muestra <select> con la etiqueta humana visible y el ENUM como value (lo que se envía)."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert '<select name="tipo_siniestro">' in html
    assert 'value="AUTO_COLISION"' in html and "Colisión vehicular</option>" in html
    assert 'name="tipo_siniestro" value=' not in html   # ya NO es un <input> de texto con el enum crudo


def test_correccion_con_enum_del_dropdown_redictamina(client):
    """🔒P2: el form envía el ENUM (valor del select); el servidor re-dictamina con él (no se rompe el motor)."""
    caso = _guardar("campos-faltantes")
    r = client.post(f"/workbench/corregir/{caso.id}", data={
        "usuario": "ana", "rol": "ANALISTA", "numero_poliza": "POL-DEMO-1001",
        "fecha_siniestro": "2026-06-10", "tipo_siniestro": "AUTO_COLISION", "monto_reclamado": "5000000",
    }, follow_redirects=False)
    assert r.status_code == 200   # re-render del partial (el motor re-dictaminó con el enum)


# ───────────────────────── M4 · microcopy (firma, verificación, tooltips) ─────────────────────────

def test_firma_sin_p1_en_la_superficie(client):
    """Firma de estación (D): la identidad viene de la SESIÓN, no por acción → el detalle del caso ya no tiene
    campo de firma inline ('Firma del analista' / '#wb-firma'). El gate P1 sigue en el servidor."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'id="wb-firma"' not in html
    assert "Firma del analista" not in html


def test_verificacion_no_realizada_en_humano(client):
    """M4: cuando la verificación C3 no corrió (modo determinístico), la tira dice 'No realizada', no el
    técnico 'No disponible'."""
    caso = _guardar("campos-faltantes")
    verif = next(c for c in vista_caso.confianza_riesgo(caso, {}) if c["label"] == "Verificación")
    # sin traza C3, la verificación no está disponible → etiqueta humana, no el técnico "No disponible"
    assert verif["valor"] == "No realizada"
    assert "No disponible" not in verif["valor"]


def test_acciones_traen_tooltip_explicativo(client):
    """M4: Radicar y 'revisión especializada' llevan un tooltip que dice QUÉ hacen (autoexplicativo)."""
    listo = _guardar("feliz")
    html_listo = client.get(f"/workbench/caso/{listo.id}").text
    assert "Crear formalmente el expediente y enviarlo al siguiente equipo" in html_listo
    falta = _guardar("campos-faltantes")
    html_falta = client.get(f"/workbench/caso/{falta.id}").text
    assert "Enviar el caso a un especialista para evaluación manual" in html_falta


# ───────────────────────── M5 · "Preparar solicitud" + flujo conectado ─────────────────────────

def test_primaria_falta_prepara_borrador_no_envia():
    """M5: la primaria de un caso con falta es 'Preparar solicitud' y ABRE un borrador (drawer), no un POST a
    ciegas. 🔒P1 draft≠send: prepara, el humano revisa y envía."""
    acc = vista_caso.recomendacion(construir_caso_preset("campos-faltantes"))["accion"]
    assert acc["label"] == "Preparar solicitud"
    assert acc["endpoint"] == "carta" and acc["drawer"] is True
    assert acc["titulo"]   # el título conecta con el dato faltante (imperativo)


def test_render_primaria_falta_abre_drawer_sin_firma_previa(client):
    """M5: el botón primario de 'Preparar solicitud' abre el drawer (hx-post → #wb-drawer); abrir el borrador
    no exige firma (la firma va al ENVIAR desde el drawer). No es el form de firma directo."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Preparar solicitud" in html
    assert 'hx-post="/casos/' in html and 'hx-target="#wb-drawer"' in html
    # dedup (M5): la carta secundaria "✍ Preparar carta" no se repite cuando la primaria ya es el borrador
    assert "✍ Preparar carta" not in html


def test_borrador_solicitud_nombra_el_dato_faltante(client):
    """M5: el borrador que abre la primaria nombra el DATO faltante (conecta la acción con el problema)."""
    caso = _guardar("campos-faltantes")
    r = client.post(f"/casos/{caso.id}/carta", data={"rol": "ANALISTA"})
    assert r.status_code == 200
    assert "necesitamos el siguiente dato" in r.text.lower()
    # el label del dato en la carta coincide con el del workbench (W23·M5), no el técnico "monto reclamado"
    assert "valor de la reclamación" in r.text.lower() and "monto reclamado" not in r.text.lower()


def test_solicitar_documentos_sigue_como_secundaria(client):
    """M5: 'Solicitar documentos' (envío rápido) permanece como acción SECUNDARIA aunque la primaria pase a
    'Preparar solicitud' — no se pierde la vía directa."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Solicitar documentos" in html
    assert "/solicitar_docs" in html   # el endpoint secundario sigue ofreciéndose


# ───────────────────────── M6 · refinamiento del bloque de excepción ─────────────────────────

def test_datos_verificados_colapsados_en_caso_bloqueado(client):
    """M6 'primero la excepción': en un caso BLOQUEADO los datos extraídos se colapsan bajo 'Ver información
    extraída' (<details>), dejando manda la excepción. encode-not-hide: los campos siguen en el DOM."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'class="wb-datos-fold"' in html                     # los datos van en un <details>
    assert "Ver información extraída" in html                   # summary a un click
    assert "numero_poliza" in html or "Póliza" in html         # los campos SIGUEN en el DOM (no borrados)


def test_datos_expandidos_en_caso_listo(client):
    """M6: en un caso LISTO (no bloqueado) los datos se ven expandidos (son el objeto de la firma), sin colapsar."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'class="wb-datos-fold"' not in html                 # sin colapsar
    assert "Datos del siniestro" in html                       # encabezado normal


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
