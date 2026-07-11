"""Tests W20 · Bolt-2b — recomposición de jerarquía (A2–A5). Solo re-presentación; los contratos e invariantes
no cambian. Fail-closed sobre lo que la fusión NO puede romper:

- **A2** (hero "Necesitas revisar"): caso bloqueado → bloque héroe con el campo editable EMBEBIDO; caso no
  bloqueado → banner calmo. 🔒P1: corregir exige firma; nunca alcanza terminal (reusa la vía de Fase 2).
- **A3** (visor de documento): click abre el drawer; fail-closed a "no encontrado" si el índice no existe (P7);
  P5: el visor muestra etiqueta/huella/mock, nunca la media cruda (ni el nombre de archivo).
- **A4** (confirmación): las acciones sensibles llevan `data-confirm`; el gate real sigue en el servidor (P1).
- **A5** (Estado operativo): un solo bloque fusiona preparación (barra "N de M") + cobertura + riesgos.
  🔒P6/P1: alerta ALTA + cobertura REQUIERE_REVISION + health bajo NO deshabilita la firma ni cambia el estado.
- **encode-not-hide** (bidireccional): todo campo muestra su `%` (incluso 100%) y el timeline no se colapsa.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.demo.scenarios import construir_caso_preset
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso, ResultadoCobertura
from app.contracts.dictamen import AlertaFraude
from app.contracts.extraccion import EvidenciaOrigen, TipoOrigen


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _caso_estado(estado: EstadoCaso):
    return next((c for c in get_caso_repository().list() if c.estado == estado), None)


def _alerta_alta():
    return AlertaFraude(
        severidad="ALTA", confianza=0.9, capa=1,
        inconsistencias=[EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="MONTO_EXCEDE_SUMA: 999 > 100")],
        explicacion="Inconsistencia de monto.")


# ───────────────────────── A2 · Bloque héroe "Necesitas revisar" ─────────────────────────

def test_a2_bloqueado_muestra_hero_con_campo_editable(client):
    """Caso REQUIERE_REVISION → bloque héroe 'Necesitas revisar' con el form de corrección EMBEBIDO (firma P1)."""
    caso = _caso_estado(EstadoCaso.REQUIERE_REVISION)
    if caso is None:
        pytest.skip("no hay caso REQUIERE_REVISION sembrado")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Necesitas revisar" in html
    assert f'hx-post="/workbench/corregir/{caso.id}"' in html   # el campo editable posta a la corrección
    assert 'name="usuario"' in html and "required" in html      # firma obligatoria embebida (P1)
    # mutuamente excluyente: el colapsable "Corregir datos" (vía de un caso LISTO) NO aparece aquí
    assert "Corregir datos" not in html


def test_a2_no_bloqueado_usa_banner_no_hero(client):
    """Caso LISTO_PARA_APROBAR → banner calmo (sin hero de revisión); la corrección vive en el colapsable."""
    caso = _caso_estado(EstadoCaso.LISTO_PARA_APROBAR)
    if caso is None:
        pytest.skip("no hay caso LISTO_PARA_APROBAR sembrado")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Necesitas revisar" not in html
    assert "Corregir datos" in html                              # colapsable disponible para el caso preparado
    assert f'hx-post="/workbench/corregir/{caso.id}"' in html    # sigue habiendo un form de corrección


# ───────────────────────── A3 · Visor de documento (drawer) ─────────────────────────

def test_a3_wb_doc_abre_visor(client):
    """El documento en la galería es un control que abre el visor (drawer) por HTMX."""
    caso = get_caso_repository().list()[0]
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert f'hx-get="/workbench/documento/{caso.id}?doc=0"' in html
    # V1·4: el documento es un <button> nativo (teclado-first: Enter/Espacio disparan el click sin role/tabindex).
    assert '<button class="wb-doc"' in html and 'hx-target="#wb-drawer"' in html


def test_a3_visor_muestra_etiqueta_y_no_media_cruda(client):
    """P5: el visor muestra etiqueta + huella/mock, NUNCA el nombre de archivo crudo ni media cruda."""
    from app.dashboard import documentos as _documentos
    caso = get_caso_repository().list()[0]
    doc0 = _documentos.documentos_de(caso)[0]
    html = client.get(f"/workbench/documento/{caso.id}?doc=0").text
    assert doc0.etiqueta in html                # se muestra la etiqueta legible
    assert doc0.nombre not in html              # NO se filtra el nombre de archivo crudo (P5)
    assert "wb-ev-page" in html                 # render mock (reusa el visor de W12), no la imagen real
    assert "Usar este valor" in html            # acción del visor (deshabilitada hasta M1, P7)


def test_a3_documento_fuera_de_rango_failclosed(client):
    """Fail-closed (P7): un índice inexistente NO inventa un visor → 'Documento no encontrado'."""
    caso = get_caso_repository().list()[0]
    html = client.get(f"/workbench/documento/{caso.id}?doc=9999").text
    assert "Documento no encontrado" in html
    assert "wb-ev-page" not in html


def test_a3_documento_caso_inexistente_404(client):
    assert client.get("/workbench/documento/no-existe?doc=0").status_code == 404


# ───────────────────────── A4 · Confirmación antes de acciones sensibles ─────────────────────────

def test_a4_acciones_sensibles_piden_confirmacion(client):
    """radicar/rechazar/enviar_fraude/escalar llevan `data-confirm` (diálogo nativo, ADR-001)."""
    caso = _caso_estado(EstadoCaso.LISTO_PARA_APROBAR) or get_caso_repository().list()[0]
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert html.count("data-confirm=") >= 3     # al menos radicar + fraude + escalar (rechazar si no terminal)
    assert 'action="/casos/%s/radicar"' % caso.id in html
    # el data-confirm acompaña al form de radicar (no lo sustituye)
    ini = html.find('action="/casos/%s/radicar"' % caso.id)
    assert "data-confirm=" in html[ini - 120:ini + 120]


def test_a4_confirmacion_no_reemplaza_el_gate_del_servidor(client):
    """🔒P1: la confirmación es fricción de UI; el servidor SIGUE exigiendo firma (radicar sin usuario → 400)."""
    caso = _caso_estado(EstadoCaso.LISTO_PARA_APROBAR)
    if caso is None:
        pytest.skip("no hay caso LISTO_PARA_APROBAR")
    assert client.post(f"/casos/{caso.id}/radicar", data={}, follow_redirects=False).status_code == 400


# ───────────────────────── A5 · "Estado operativo" (fusión) + fail-closed P6/P1 ─────────────────────────

def test_a5_un_solo_bloque_estado_operativo(client):
    """A5: preparación + cobertura + riesgos viven en UN bloque 'Estado operativo' (no 3 tarjetas sueltas)."""
    caso = next((c for c in get_caso_repository().list() if c.dictamen), get_caso_repository().list()[0])
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Estado operativo" in html
    assert 'data-slot="estado"' in html
    # las tarjetas separadas ya no existen (se fusionaron)
    assert 'data-slot="health"' not in html and 'data-slot="dictamen"' not in html
    assert "Cobertura · por qué" in html and "no el LLM (P2)" in html   # P2 intacto (presenta el motor)
    assert re.search(r"\d+ de \d+ verificaciones", html)               # barra "N de M" (health sin %)


def test_a5_p6_p1_combinacion_no_bloquea_la_firma(client):
    """🔒P6/P1 (code-review P-3): alerta ALTA + cobertura REQUIERE_REVISION + health bajo NO deshabilita la firma
    ni cambia el estado. La fusión de presentación no puede convertir un riesgo en un bloqueo."""
    reset_caso_repository()
    caso = construir_caso_preset("feliz")   # trae dictamen
    peor = caso.model_copy(update={
        "estado": EstadoCaso.LISTO_PARA_APROBAR,   # preparado → radicar habilitado
        "alerta_fraude": _alerta_alta(),            # riesgo ALTA
        "dictamen": caso.dictamen.model_copy(update={"resultado": ResultadoCobertura.REQUIERE_REVISION}),
    })
    get_caso_repository().save(peor)
    r = client.get(f"/workbench/caso/{peor.id}")
    assert r.status_code == 200
    html = r.text
    assert "Riesgos a revisar" in html and "sugerencia, no un veredicto" in html   # P6: solo sugiere
    # el botón Radicar NO trae disabled (el riesgo/cobertura NO lo bloquean; solo lo gatea el estado, que es LISTO)
    ini = html.find('action="/casos/%s/radicar"' % peor.id)
    assert ini != -1
    assert "disabled" not in html[ini:html.find("Radicar caso", ini) + 12]
    # el estado no cambió por presentar los 3 juntos (GET es passive, P1)
    assert get_caso_repository().get(peor.id).estado == EstadoCaso.LISTO_PARA_APROBAR


# ───────────────────────── encode-not-hide (bidireccional, code-review P-5) ─────────────────────────

def test_encode_not_hide_muestra_pct_incluso_al_100(client):
    """El `%` se muestra en TODOS los campos, aunque sea 100% (no se oculta la confianza alta)."""
    reset_caso_repository()
    caso = construir_caso_preset("feliz")
    campos_100 = [c.model_copy(update={"confianza": 1.0}) if (not c.ausente and c.valor is not None) else c
                  for c in caso.extraccion.campos]
    caso = caso.model_copy(update={"extraccion": caso.extraccion.model_copy(update={"campos": campos_100})})
    get_caso_repository().save(caso)
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "100%" in html                       # confianza alta VISIBLE, no oculta
    assert "wb-conf-pct" in html


def test_encode_not_hide_timeline_no_colapsa(client):
    """El timeline agent-native (W18) sigue VISIBLE (condensado, no colapsado a una línea)."""
    caso = get_caso_repository().list()[0]
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Actividad del caso" in html          # V1·6: la cronología (humana) sigue presente, no colapsada
    assert "wb-crono-step" in html               # renderiza sus pasos (no un resumen de una línea)
    assert "Ver actividad técnica" in html       # el rastro técnico REAL sigue accesible a un click (encode-not-hide)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
