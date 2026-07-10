"""Tests W5 — Riesgos ("míralo"). 🔒 P6: reencuadre de alerta_fraude que SOLO sugiere.

Invariante central: ninguna señal cambia el estado ni deshabilita la firma; copy sin veredicto.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso
from app.contracts.dictamen import AlertaFraude
from app.contracts.extraccion import EvidenciaOrigen, TipoOrigen


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _caso_con_riesgo():
    for c in get_caso_repository().list():
        if c.alerta_fraude is not None:
            return c
    return None


def _inyectar_riesgo(caso):
    alerta = AlertaFraude(
        severidad="ALTA", confianza=0.9, capa=1,
        inconsistencias=[EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="MONTO_EXCEDE_SUMA: 999 > 100")],
        explicacion="Inconsistencia de monto.")
    return caso.model_copy(update={"alerta_fraude": alerta})


# ---------- view-model ----------

def test_riesgos_traduce_a_frase_humana():
    caso = _inyectar_riesgo(get_caso_repository().list()[0])
    r = vista_caso.riesgos(caso)
    assert r["hay"] is True
    assert r["lista"][0]["texto"] == "El monto reclamado supera la suma asegurada."
    assert 0.0 <= r["confianza"] < 1.0


def test_riesgos_sin_alerta():
    caso = get_caso_repository().list()[0].model_copy(update={"alerta_fraude": None})
    assert vista_caso.riesgos(caso) == {"hay": False, "lista": []}


def test_riesgo_legible_referencia_desconocida_no_expone_cruda():
    """P5: una referencia no mapeada cae a una frase genérica, no filtra el detalle crudo."""
    assert vista_caso._riesgo_legible("ALGO_RARO: cédula 1.098.765.432") == "Inconsistencia detectada — revísala."


def test_riesgos_guard_inconsistencias_vacias():
    """Defensivo: si (por lo que sea) una alerta no tiene inconsistencias, no se dice que 'hay' riesgos."""
    from types import SimpleNamespace
    caso = SimpleNamespace(alerta_fraude=SimpleNamespace(inconsistencias=[], severidad="MEDIA",
                                                         confianza=0.8, explicacion="x"))
    assert vista_caso.riesgos(caso) == {"hay": False, "lista": []}


# ---------- 🔒 P6 fail-closed ----------

def test_p6_riesgo_no_cambia_estado_ni_firma(client):
    """🔒 P6: un caso LISTO_PARA_APROBAR con riesgo sigue LISTO y firmable (la señal no decide)."""
    caso = get_caso_repository().list()[0]
    caso = caso.model_copy(update={"estado": EstadoCaso.LISTO_PARA_APROBAR})
    caso = _inyectar_riesgo(caso)
    get_caso_repository().save(caso)
    r = client.get(f"/workbench/caso/{caso.id}")
    assert r.status_code == 200
    assert "Riesgos a revisar" in r.text
    # el estado NO cambió y la firma (Radicar) NO está deshabilitada por el riesgo
    assert get_caso_repository().get(caso.id).estado == EstadoCaso.LISTO_PARA_APROBAR
    # Aísla el form de Radicar (action de aprobar → botón Radicar) y verifica que su botón no trae disabled.
    ini = r.text.find('action="/casos/%s/aprobar"' % caso.id)
    form_radicar = r.text[ini:r.text.find("Radicar", ini) + 10]
    assert 'disabled' not in form_radicar


def test_p6_panel_sin_lenguaje_de_veredicto(client):
    """El panel invita a mirar, no dictamina fraude ni decisión."""
    caso = _inyectar_riesgo(get_caso_repository().list()[0])
    get_caso_repository().save(caso)
    texto = client.get(f"/workbench/caso/{caso.id}").text.lower()
    for prohibida in ("fraude confirmado", "rechazar por fraude", "bloquear"):
        assert prohibida not in texto
    assert "sugerencia, no un veredicto" in texto


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
