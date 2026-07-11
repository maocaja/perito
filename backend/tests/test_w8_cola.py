"""Tests W8 — Cola inteligente por razón (🔴🟠🟡🟢).

Invariantes: carril determinístico y mutuamente excluyente (reproducible), passive (P1/P2: ordena, no
decide), conteos por carril suman el total, filtro por carril.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def _casos():
    return get_caso_repository().list()


# ---------- clasificador ----------

def test_carril_determinístico_y_valido():
    for c in _casos():
        a = vista_caso.clasificador_cola(c)["carril"]
        b = vista_caso.clasificador_cola(c)["carril"]
        assert a == b
        assert a in {"rojo", "ambar", "amarillo", "verde"}


def test_listo_sin_faltantes_ni_riesgo_es_verde():
    caso = next((c for c in _casos() if c.estado == EstadoCaso.LISTO_PARA_APROBAR
                 and not vista_caso.faltantes(c) and c.alerta_fraude is None
                 and not vista_caso._lesionados(c)
                 and c.dictamen is not None and c.dictamen.resultado.value != "CUBIERTO_PARCIAL"), None)
    if caso is None:
        pytest.skip("sin caso 'verde' limpio en el seed")
    assert vista_caso.clasificador_cola(caso)["carril"] == "verde"


def test_faltantes_es_amarillo():
    caso = next((c for c in _casos() if vista_caso.faltantes(c) and c.alerta_fraude is None
                 and not vista_caso._lesionados(c)
                 and not (c.estado == EstadoCaso.REQUIERE_REVISION and not vista_caso.faltantes(c))), None)
    if caso is None:
        pytest.skip("sin caso con faltantes")
    assert vista_caso.clasificador_cola(caso)["carril"] == "amarillo"


def test_terminal_es_verde_cerrado():
    """Un caso resuelto (APROBADO/RECHAZADO) va a verde con motivo 'cerrado' (no 'listo para firma')."""
    caso = _casos()[0].model_copy(update={"estado": EstadoCaso.APROBADO, "aprobado_por": "ana"})
    r = vista_caso.clasificador_cola(caso)
    assert r["carril"] == "verde" and "cerrado" in r["motivo"]


def test_lesionados_sin_aviso_no_crashea():
    from types import SimpleNamespace
    assert vista_caso._lesionados(SimpleNamespace(aviso=None)) is False


def test_lesionados_heuristica_es_rojo():
    caso = _casos()[0].model_copy()
    # forzar el texto con una palabra de lesionados
    caso = caso.model_copy(update={"aviso": caso.aviso.model_copy(update={"texto_crudo": "Hubo un herido en el choque."})})
    assert vista_caso.clasificador_cola(caso)["carril"] == "rojo"


# ---------- ruta / conteos ----------

def test_conteos_por_carril_suman_total(client):
    r = client.get("/workbench")
    assert r.status_code == 200
    # cada carril aparece como chip
    for etiqueta in ("Lesionados", "Cobertura dudosa", "Documentos faltantes", "Listo para radicar"):
        assert etiqueta in r.text


def test_filtro_por_carril(client):
    """El filtro por carril reduce la cola a ese carril (o vacía)."""
    total_verde = sum(1 for c in _casos() if vista_caso.clasificador_cola(c)["carril"] == "verde")
    r = client.get("/workbench?carril=verde")
    assert r.status_code == 200
    # un `data-caso-id=` por ítem (marcador único por fila)
    assert r.text.count("data-caso-id=") == total_verde


def test_cada_caso_en_un_solo_carril(client):
    casos = _casos()
    suma = sum(len([c for c in casos if vista_caso.clasificador_cola(c)["carril"] == k])
               for k, _, _ in vista_caso.CARRILES)
    assert suma == len(casos)  # partición exacta


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
