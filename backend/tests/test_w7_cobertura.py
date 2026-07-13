"""Tests W7 — Explicación "por qué" de la cobertura. 🔒 P2: PRESENTA la decisión del motor, no re-decide.

Invariante: lo que muestra la explicación == lo que dice `caso.dictamen` (no diverge del motor).
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


def _caso_con_dictamen():
    for c in get_caso_repository().list():
        if c.dictamen is not None:
            return c
    return None


def test_explicacion_cita_el_mismo_dictamen():
    """🔒 P2: la explicación NO diverge del motor — resultado/regla/deducible salen del Dictamen."""
    caso = _caso_con_dictamen()
    if caso is None:
        pytest.skip("no hay caso con dictamen sembrado")
    cob = vista_caso.explicacion_cobertura(caso)
    assert cob["disponible"] is True
    assert cob["resultado"] == caso.dictamen.resultado.value
    assert cob["regla"] == caso.dictamen.regla_aplicada
    assert cob["deducible"] == str(caso.dictamen.deducible_calculado)


def test_explicacion_clausula_coincide():
    caso = _caso_con_dictamen()
    if caso is None or caso.dictamen.clausula is None:
        pytest.skip("no hay caso con cláusula")
    cob = vista_caso.explicacion_cobertura(caso)
    assert cob["clausula"]["referencia"] == caso.dictamen.clausula.referencia


def test_sin_dictamen_no_inventa():
    caso = get_caso_repository().list()[0].model_copy(update={"dictamen": None})
    assert vista_caso.explicacion_cobertura(caso) == {"disponible": False}


def test_frase_sin_palabras_prohibidas():
    """P1: la frase describe, no decide."""
    for c in get_caso_repository().list():
        cob = vista_caso.explicacion_cobertura(c)
        if cob["disponible"]:
            assert not any(p in cob["frase"].lower() for p in vista_caso.PALABRAS_PROHIBIDAS)


def test_render_cobertura(client):
    caso = _caso_con_dictamen()
    if caso is None:
        pytest.skip("no hay caso con dictamen")
    r = client.get(f"/workbench/caso/{caso.id}")
    assert "Cobertura · por qué" in r.text
    assert "no el LLM" in r.text   # el motor sigue citado (en "Ver regla aplicada")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
