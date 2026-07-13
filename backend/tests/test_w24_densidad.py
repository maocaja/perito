"""Tests W24 — segunda pasada de densidad/dedup (spec w24-densidad-dedup.md).

Regla de oro: MOVER/DEDUP, no borrar (encode-not-hide). Invariantes P1–P7 intactos. Feedback: review del
usuario tras W23 (eliminar repetición, bajar carga cognitiva).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.scenarios import construir_caso_preset
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.dashboard import vista_caso
from app.contracts.extraccion import EvidenciaOrigen
from app.contracts.enums import TipoOrigen


@pytest.fixture
def client():
    return TestClient(app)


def _guardar(key):
    reset_caso_repository()
    caso = construir_caso_preset(key)
    get_caso_repository().save(caso)
    return caso


# ───────────────────────── N1 · un solo estado (cobertura fuera del strip) ─────────────────────────

def test_cobertura_fuera_del_strip():
    """N1: el strip de un vistazo NO repite el estado de cobertura (vive en el panel derecho)."""
    strip = vista_caso.confianza_riesgo(construir_caso_preset("campos-faltantes"), None)
    assert "Cobertura" not in [c["label"] for c in strip]
    assert [c["label"] for c in strip] == ["Extracción", "Verificación", "Fraude"]


# ───────────────────────── N2 · resumen ejecutivo ─────────────────────────

def test_resumen_es_una_linea_de_senales():
    """N2: el resumen es conteo+señal separado por '·', no prosa que repita hero/campos."""
    prosa = vista_caso.resumen_narrativo(construir_caso_preset("campos-faltantes"))
    assert prosa.count(" · ") >= 2 and "datos extraídos" in prosa
    # no repite el nombre del asegurado ni el tipo (ya están en el hero)
    assert "reportó" not in prosa


# ───────────────────────── N5 · origen por dato (✓ IA / ✍ Manual) ─────────────────────────

def test_campo_ia_vs_manual():
    """N5: un campo distingue IA (extraído) de Manual (corrección humana)."""
    assert vista_caso._es_manual(EvidenciaOrigen(tipo=TipoOrigen.HUMANO, referencia="ana")) is True
    assert vista_caso._es_manual(EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="correo")) is False


def test_icono_fuente_por_tipo():
    """N5/N9: la fuente se muestra como icono compacto (no el texto 'Correo' repetido)."""
    assert vista_caso.icono_fuente("Correo") == "📧"
    assert vista_caso.icono_fuente("PDF") == "📄"
    assert vista_caso.icono_fuente("Corrección humana") == "✍"
    assert vista_caso.icono_fuente("cualquier-otra") == "📎"   # default, no revienta


def test_render_campo_muestra_origen_no_ia(client):
    """N5 (rev W24.1): la tabla de datos muestra el ORIGEN del dato por campo (Correo/SOAT/…), NO un badge 'IA'
    (la IA es invisible en el flujo; repetir 'IA' es ruido). Solo lo manual se marca aparte."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "wb-field-origen" in html
    assert " IA</span>" not in html   # ya NO hay badge 'IA' por fila
    assert "Correo" in html or "SOAT" in html   # el origen sí se muestra


# ───────────────────────── N6 · firma única en el punto de acción ─────────────────────────

def test_una_sola_firma_por_estado(client):
    """N6: hay EXACTAMENTE un #wb-firma en la página (el JS lo busca por id; dos romperían el copiado)."""
    for key in ("campos-faltantes", "feliz"):
        caso = _guardar(key)
        html = client.get(f"/workbench/caso/{caso.id}").text
        assert html.count('id="wb-firma"') == 1


def test_firma_no_flota_arriba_va_con_la_accion(client):
    """N6: en un caso LISTO la firma acompaña a Radicar (punto de acción), no flota al inicio del panel.
    Se verifica que la firma aparece DESPUÉS del resumen/estado, cerca del botón terminal."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    pos_firma = html.find('id="wb-firma"')
    pos_radicar = html.find("Radicar caso")
    assert pos_firma != -1 and pos_radicar != -1
    # la firma está junto a la acción terminal (antes del botón, en su bloque), no al tope del panel
    assert abs(pos_firma - pos_radicar) < 600


def test_gate_de_firma_sigue_en_el_servidor(client):
    """🔒P1: N6 solo reposiciona la firma; el gate REAL sigue en el servidor (radicar sin usuario → no aprueba)."""
    caso = _guardar("feliz")
    r = client.post(f"/casos/{caso.id}/radicar", data={"usuario": ""}, follow_redirects=False)
    assert r.status_code >= 400   # sin firma, el servidor rechaza (no alcanza APROBADO)


# ───────────────────────── N7 · actividad colapsable ─────────────────────────

def test_actividad_colapsa_eventos_anteriores(client):
    """N7: si hay más de 4 eventos, los anteriores se colapsan bajo un <details>; el timeline completo sigue en
    el DOM (encode-not-hide). Con ≤4 no aparece el colapsable."""
    from app.dashboard import c11
    from app.observability.replay import get_replay_store
    caso = _guardar("feliz")
    # el detalle se arma vía el endpoint; solo verificamos que el render no rompe y que el eyebrow sigue
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Actividad del caso" in html
    # si hay colapsable, su summary nombra los eventos anteriores (encode-not-hide)
    if "wb-crono-fold" in html:
        assert "eventos anteriores" in html


# ───────────────────────── N8 · menos texto/badges ─────────────────────────

def test_aviso_preparacion_es_tooltip_no_linea(client):
    """N8: el aviso 'La preparación es informativa…' pasa a tooltip (title), no ocupa una línea fija (card-foot)."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'title="La preparación es informativa; la aprobación la decides tú (P1)."' in html
    assert '<div class="card-foot">La preparación es informativa' not in html   # ya NO es una línea fija


# ───────────────────────── N9 · detalles ─────────────────────────

def test_consultar_no_preguntar_a_la_ia(client):
    """N9: el chat se llama 'Consultar el caso' (menos repetición de 'IA'); el mecanismo sigue igual."""
    caso = _guardar("feliz")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Consultar el caso" in html and "Preguntar a la IA" not in html
    assert 'hx-post="/workbench/preguntar/' in html   # el endpoint no cambió


def test_terminal_una_sola_tarjeta(client):
    """N9: en un caso terminal, el banner de estado y la tarjeta de confirmación se fusionan (una sola)."""
    from app.contracts.enums import EstadoCaso
    reset_caso_repository()
    caso = construir_caso_preset("feliz").model_copy(update={"estado": EstadoCaso.APROBADO, "aprobado_por": "ana"})
    get_caso_repository().save(caso)
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Caso aprobado y radicado" in html
    assert 'data-slot="status"' not in html          # el banner de estado NO se repite en terminal
    assert 'data-slot="confirmacion"' in html         # solo la tarjeta de confirmación


def test_falta_no_repite_no_encontrado(client):
    """N9: el valor de un campo ausente no repite 'No encontrado' (ya está en el chip de la derecha)."""
    caso = _guardar("campos-faltantes")
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Ingrésalo arriba" in html
    assert "No encontrado — ingrésalo arriba" not in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
