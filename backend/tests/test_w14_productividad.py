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
    html = client.get("/workbench").text
    assert "Tu productividad hoy" in html
    assert "Casos procesados" in html
    assert "SLA cumplimiento" in html
    assert "wb-prod-chart" in html      # el gráfico
    assert "badge-demo" in html          # métricas mock rotuladas


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
