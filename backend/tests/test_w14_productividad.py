"""Tests W14 — Panel de productividad del operador.

Honesto (P7): casos/pendientes son REALES (del repo); tiempo/SLA/errores/serie son mock rotulado. Passive (P1).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository
from app.dashboard import productividad
from app.contracts.enums import EstadoCaso


@pytest.fixture
def client():
    seed_demo_casos()
    return TestClient(app)


def test_casos_y_pendientes_son_reales():
    """Los conteos reales salen del repo (no inventados)."""
    p = productividad.productividad("ANALISTA")
    casos = get_caso_repository().list()
    assert p["casos"] == sum(1 for c in casos if c.estado in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO))
    assert p["pendientes"] == sum(1 for c in casos if c.estado in
                                  (EstadoCaso.REQUIERE_REVISION, EstadoCaso.LISTO_PARA_APROBAR))


def test_metricas_no_medidas_van_demo():
    """P7: tiempo/SLA/errores están rotulados como demo (aún no los medimos)."""
    p = productividad.productividad("ANALISTA")
    assert p["demo"] is True
    assert p["tiempo_prom"] and p["sla"] and "serie" in p


def test_render_productividad(client):
    # W20/A1: la productividad se movió de la Workbench a Reportes (`/panel`). La Workbench es la estación de
    # decisión, enfocada en el caso; la productividad es una vista de jornada, no de caso.
    html = client.get("/panel").text
    assert "Tu productividad hoy" in html
    assert "Casos procesados" in html
    assert "SLA cumplimiento" in html
    assert "wb-prod-chart" in html      # el gráfico
    assert "badge-demo" in html          # métricas mock rotuladas


def test_productividad_no_esta_en_workbench(client):
    # A1 fail-closed: la Workbench NO muestra la franja de productividad (declutter — estación de decisión).
    assert "wb-prod-chart" not in client.get("/workbench").text


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
