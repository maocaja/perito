"""Tests W6 — Health Check (% completo + checklist unificado).

Invariantes: P1 (informativo, no decide), P7 (docs 'na' rotulados demo, no cuentan al %; % reproducible).
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


def _un_caso():
    return get_caso_repository().list()[0]


def test_health_check_pct_reproducible():
    caso = _un_caso()
    a = vista_caso.health_check(caso, traza=None)
    b = vista_caso.health_check(caso, traza=None)
    assert a["pct"] == b["pct"]
    assert 0 <= a["pct"] <= 100


def test_campos_presentes_ok_ausentes_warn():
    caso = _un_caso()
    checks = vista_caso.health_check(caso, traza=None)["checks"]
    labels = {c["label"]: c for c in checks}
    # numero_poliza suele estar presente en el seed → ok (L2: label humano "Póliza")
    assert labels["Póliza"]["estado"] in ("ok", "warn")
    # coherencia: un campo presente es ok, uno ausente es warn
    for n in vista_caso._presentes(caso):
        assert labels[vista_caso._LABEL_CAMPO.get(n, n.replace("_", " ").capitalize())]["estado"] == "ok"


def test_docs_rotulados_demo_y_no_cuentan_al_pct():
    """P7: los ítems de documentos van 'na' + demo (adjuntos no fluyen aún) → no inflan/deflactan el %."""
    caso = _un_caso()
    hc = vista_caso.health_check(caso, traza=None)
    doc_checks = [c for c in hc["checks"] if c["demo"]]
    if doc_checks:
        assert all(c["estado"] == "na" for c in doc_checks)
    # el % se calcula solo sobre evaluables (no-'na')
    evaluables = [c for c in hc["checks"] if c["estado"] != "na"]
    oks = sum(1 for c in evaluables if c["estado"] == "ok")
    assert hc["pct"] == (round(100 * oks / len(evaluables)) if evaluables else 0)


def test_cobertura_parcial_es_warn_no_ok():
    """P7: CUBIERTO_PARCIAL se muestra ⚠, no ✔ (no un falso 'todo bien')."""
    from app.contracts.enums import ResultadoCobertura
    lst = get_caso_repository().list()
    caso = next((c for c in lst if c.dictamen and c.dictamen.resultado == ResultadoCobertura.CUBIERTO_PARCIAL), None)
    if caso is None:
        base = next((c for c in lst if c.dictamen and c.dictamen.clausula), None)
        if base is None:
            pytest.skip("sin dictamen con cláusula para construir el caso")
        caso = base.model_copy(update={"dictamen": base.dictamen.model_copy(
            update={"resultado": ResultadoCobertura.CUBIERTO_PARCIAL})})
    cob = next(c for c in vista_caso.health_check(caso, None)["checks"] if c["label"] == "Resultado de cobertura")
    assert cob["estado"] == "warn"


def test_verificacion_na_sin_traza():
    checks = vista_caso.health_check(_un_caso(), traza=None)["checks"]
    verif = next(c for c in checks if c["label"] == "Coincidencia entre fuentes")
    assert verif["estado"] in ("ok", "na")


def test_render_health(client):
    # W20·A5: el Health Check se fusionó en el bloque "Estado operativo"; el % dio paso a la barra "N de M
    # verificaciones" (encode-not-hide). El checklist y el copy P1 informativo se conservan.
    r = client.get(f"/workbench/caso/{_un_caso().id}")
    assert "Estado operativo" in r.text
    assert "verificaciones" in r.text               # barra "N de M verificaciones" (reemplaza el %)
    assert "la aprobación la decides tú" in r.text  # P1 informativo


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
