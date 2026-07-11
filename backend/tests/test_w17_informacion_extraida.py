"""Tests W17 — Panel "Información Extraída" (dato · confianza · fuente).

🔴 Blindaje agéntico: los campos del extractor REAL van origen='real' con su confianza/fuente VERDADERAS;
los ricos que aún no producimos van origen='demo' rotulado (P7). P5: valores redactados. P3: cita la fuente.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _con_extraccion():
    for c in get_caso_repository().list():
        if c.extraccion and any(not x.ausente for x in c.extraccion.campos):
            return c
    return None


# ---------- Fase 0 · tabla fusionada `datos_principales` ----------

def test_datos_principales_fusiona_presentes_y_faltantes(client):
    """La tabla única lista los campos presentes (con confianza/fuente) + los faltantes como REQUERIDO,
    sin duplicar labels (fusión de 'Datos del siniestro' + 'Información extraída')."""
    caso = _con_extraccion() or get_caso_repository().list()[0]
    datos = vista_caso.datos_principales(caso)
    labels = [d.label for d in datos]
    assert len(labels) == len(set(labels)), "no debe duplicar labels"
    assert any(not d.ausente for d in datos)  # hay presentes


def test_datos_principales_sin_extraccion_no_revienta(client):
    """Edge: con extraccion=None la tabla no crashea; marca todos los campos base como REQUERIDO (ausente)."""
    caso = get_caso_repository().list()[0].model_copy(update={"extraccion": None})
    datos = vista_caso.datos_principales(caso)
    requeridos = {d.label for d in datos if d.ausente}
    esperados = {vista_caso._LABEL_CAMPO[n] for n in vista_caso.CAMPOS}
    assert esperados <= requeridos  # los 4 campos base salen como REQUERIDO


# ---------- reales vs demo ----------

def test_campos_reales_marcados_real_con_confianza_verdadera():
    """Un campo del extractor real → origen='real' y su confianza es la del contrato (no inventada)."""
    caso = _con_extraccion()
    if caso is None:
        pytest.skip("sin extracción")
    campos = vista_caso.campos_extraidos(caso)
    poliza_real = next((x for x in caso.extraccion.campos if x.nombre == "numero_poliza" and not x.ausente), None)
    if poliza_real is None:
        pytest.skip("sin numero_poliza")
    ui = next(c for c in campos if c.label == "Póliza")
    assert ui.origen == "real"
    assert ui.confianza == poliza_real.confianza   # confianza VERDADERA, no demo


def test_campos_ricos_van_demo_rotulados():
    """Asegurado/vehículo/placa (aún no producidos) → origen='demo'."""
    caso = _con_extraccion() or get_caso_repository().list()[0]
    campos = vista_caso.campos_extraidos(caso)
    demos = [c for c in campos if c.origen == "demo"]
    assert any(c.label == "Placa" for c in demos)
    assert all(c.origen == "demo" for c in demos)


def test_real_desplaza_al_demo_del_mismo_label():
    """Si el extractor real emite 'asegurado_nombre', ese real desplaza al demo 'Asegurado' (sin dedup doble)."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = get_caso_repository().list()[0]
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="asegurado_nombre", valor="Pedro Real",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    ui = vista_caso.campos_extraidos(caso2)
    asegurados = [c for c in ui if c.label == "Asegurado"]
    assert len(asegurados) == 1 and asegurados[0].origen == "real"  # el real ganó, sin duplicado demo


# ---------- P3 fuente / P5 PII ----------

def test_cada_campo_cita_su_fuente():
    caso = _con_extraccion() or get_caso_repository().list()[0]
    for c in vista_caso.campos_extraidos(caso):
        assert c.fuente and c.fuente != ""


def test_valores_redactados():
    """P5: un asegurado real con cédula no aparece crudo."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = get_caso_repository().list()[0]
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="asegurado_nombre", valor="Juan C.C. 1.098.765.432",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    ui = next(c for c in vista_caso.campos_extraidos(caso2) if c.label == "Asegurado")
    assert "1.098.765.432" not in (ui.valor or "")


def test_valores_redactados_email_y_telefono():
    """P5 (defensa en profundidad, varios tipos): email/teléfono en un campo real no aparecen crudos."""
    from app.contracts.extraccion import CampoExtraido, ExtraccionValidada, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    caso = get_caso_repository().list()[0]
    campos = list(caso.extraccion.campos) + [CampoExtraido(
        nombre="asegurado_nombre", valor="Ana escribe a ana@correo.com, cel 310 555 8899",
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)]
    caso2 = caso.model_copy(update={"extraccion": ExtraccionValidada(campos=campos)})
    ui = next(c for c in vista_caso.campos_extraidos(caso2) if c.label == "Asegurado")
    assert "ana@correo.com" not in (ui.valor or "")
    assert "310 555 8899" not in (ui.valor or "")


# ---------- render ----------

def test_render_panel(client):
    caso = _con_extraccion() or get_caso_repository().list()[0]
    html = client.get(f"/workbench/caso/{caso.id}").text
    # Fase 0: la tabla se fusionó en 'Datos del siniestro' (antes duplicada con 'Información extraída').
    assert "Datos del siniestro" in html
    assert "wb-campo-conf" in html          # columna de confianza (codificada)
    assert "wb-campo-fuente" in html        # columna de fuente (P3: dato·confianza·fuente)
    assert "badge-demo" in html             # los ricos rotulados


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
