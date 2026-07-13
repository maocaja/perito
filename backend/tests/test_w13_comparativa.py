"""Tests W13 — Cruce de fuentes del expediente (M3, real vía `comparativa_de`).

`comparativa_de(caso)` adapta el overlay REAL del Evidence Correlator (M3, `caso.correlaciones`) a la vista
(DIP). P7: LATENTE sin ≥2 fuentes reales (`disponible=False`, no fabrica). P6: una divergencia solo sugiere y
trae evidencia. P5: los valores citados ya vienen redactados de M3.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import comparativa
from app.contracts.correlacion import Correlacion


@pytest.fixture(autouse=True)
def _seed():
    seed_demo_casos()


@pytest.fixture
def client():
    return TestClient(app)


def _corr_coincide() -> Correlacion:
    return Correlacion(campo_nombre="placa", campo_label="Placa",
                       valores_por_fuente={"Correo": "FBC123", "Denuncia": "FBC123"},
                       fuentes=["Correo", "Denuncia"], coincide=True, confianza_ajustada=0.95,
                       inconsistencia=None)


def _corr_diverge() -> Correlacion:
    return Correlacion(campo_nombre="placa", campo_label="Placa",
                       valores_por_fuente={"Correo": "GHT456", "SOAT": "GHT457"},
                       fuentes=["Correo", "SOAT"], coincide=False, confianza_ajustada=0.4,
                       inconsistencia="Placa: las fuentes no concuerdan — Correo dice «GHT456»; SOAT dice «GHT457».")


def _caso_con(correlaciones):
    return get_caso_repository().list()[0].model_copy(update={"correlaciones": correlaciones})


# ---------- provider: real desde M3 ----------

def test_comparativa_real_desde_m3():
    c = comparativa.comparativa_de(_caso_con([_corr_coincide(), _corr_diverge()]))
    assert c["origen"] == "real" and c["disponible"] is True
    assert 2 <= len(c["fuentes"]) <= comparativa.MAX_FUENTES
    assert len(c["cambios"]) == 2
    assert all(isinstance(f, comparativa.FuenteCorreo) for f in c["fuentes"])
    assert all(isinstance(ch, comparativa.CambioDetectado) for ch in c["cambios"])
    assert all(f.etiqueta and f.resumen for f in c["fuentes"])  # etiqueta/resumen presentes


def test_comparativa_latente_sin_fuentes():
    """P7: un caso sin ≥2 fuentes reales (seed sin adjuntos) NO fabrica un cruce."""
    caso = get_caso_repository().list()[0]  # seed: sin adjuntos → sin correlaciones
    c = comparativa.comparativa_de(caso)
    assert c["disponible"] is False
    assert c["fuentes"] == [] and c["cambios"] == []


def test_divergencia_es_hallazgo_con_evidencia():
    """P6: una divergencia es un hallazgo '⚠️' que cita la inconsistencia (evidencia obligatoria)."""
    c = comparativa.comparativa_de(_caso_con([_corr_diverge()]))
    hallazgo = c["cambios"][0]
    assert hallazgo.icono == "⚠️"
    assert "no concuerdan" in hallazgo.texto


def test_coincidencia_es_hallazgo_positivo():
    c = comparativa.comparativa_de(_caso_con([_corr_coincide()]))
    hallazgo = c["cambios"][0]
    assert hallazgo.icono == "✅" and "concuerdan" in hallazgo.texto


# ---------- render ----------

def test_render_cruce_real(client):
    caso = _caso_con([_corr_diverge()])
    get_caso_repository().save(caso)
    drawer = client.get(f"/workbench/comparativa/{caso.id}").text
    assert "Cruce de fuentes" in drawer
    assert "Coincidencias y divergencias entre fuentes" in drawer
    assert 'class="wb-comp-f-res"' in drawer      # estructura del resumen redactado (P5)
    assert "badge-demo" not in drawer             # es real (M3), no demo (P7)


def test_render_trigger_en_caso(client):
    caso = _caso_con([_corr_coincide()])
    get_caso_repository().save(caso)
    caso_html = client.get(f"/workbench/caso/{caso.id}").text
    assert "Comparar fuentes" in caso_html
    assert 'hx-get="/workbench/comparativa/' in caso_html
    assert 'data-slot="comparativa"' in caso_html


def test_caso_sin_fuentes_no_muestra_cruce(client):
    """P7: sin correlaciones, la sección de cruce no aparece (no se fabrica)."""
    caso = get_caso_repository().list()[0]  # sin adjuntos
    html = client.get(f"/workbench/caso/{caso.id}").text
    assert 'data-slot="comparativa"' not in html


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
