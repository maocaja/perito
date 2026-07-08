"""Tests C1 — persistencia SQL (round-trip + factory + P1).

El round-trip se prueba contra SQLite in-memory (SQLAlchemy) — sin Postgres real; el smoke Neon
es manual (D3). Verifica: factory por config, round-trip save/get/list, y que reconstruir con
model_validate_json preserva la firma y rechaza un terminal sin firma (P1).
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.dashboard import store
from app.dashboard.store import InMemoryCasoRepository, SqlCasoRepository, get_caso_repository
from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso
from app.demo.scenarios import construir_caso_preset
from app.hitl.c8 import aprobar


@pytest.fixture
def sqlite_engine():
    # in-memory compartida entre conexiones (StaticPool) — imita Postgres para el round-trip.
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_factory_memory_por_default():
    store.reset_caso_repository()
    assert isinstance(get_caso_repository(), InMemoryCasoRepository)


def test_factory_postgres_por_config(monkeypatch, sqlite_engine):
    monkeypatch.setattr("app.dashboard.store.settings.persistence", "postgres")
    monkeypatch.setattr("app.persistence.db.get_engine", lambda: sqlite_engine)
    store.reset_caso_repository()
    try:
        assert isinstance(get_caso_repository(), SqlCasoRepository)
    finally:
        store.reset_caso_repository()


def test_sql_roundtrip(sqlite_engine):
    repo = SqlCasoRepository(sqlite_engine)
    repo.clear()
    caso = construir_caso_preset("feliz")  # LISTO_PARA_APROBAR, CUBIERTO_PARCIAL
    repo.save(caso)

    got = repo.get(caso.id)
    assert got is not None
    assert got.id == caso.id
    assert got.estado == caso.estado
    assert got.dictamen.resultado == caso.dictamen.resultado
    # list filtra por estado (en SQL)
    assert len(repo.list()) == 1
    assert len(repo.list(estado=EstadoCaso.LISTO_PARA_APROBAR)) == 1
    assert len(repo.list(estado=EstadoCaso.APROBADO)) == 0


def test_sql_persiste_terminal_con_firma(sqlite_engine):
    """P1: un caso terminal (APROBADO) se persiste y reconstruye con su firma (aprobado_por)."""
    repo = SqlCasoRepository(sqlite_engine)
    repo.clear()
    aprobado = aprobar(construir_caso_preset("feliz"), "diana.analista")
    repo.save(aprobado)
    got = repo.get(aprobado.id)
    assert got.estado == EstadoCaso.APROBADO
    assert got.aprobado_por == "diana.analista"   # firma preservada por model_validate_json


def test_p1_model_validate_json_rechaza_terminal_sin_firma():
    """P1 fail-closed: JSON de caso terminal SIN aprobado_por → model_validate_json rompe."""
    d = json.loads(construir_caso_preset("feliz").model_dump_json())
    d["estado"] = "APROBADO"
    d["aprobado_por"] = None
    with pytest.raises(Exception):
        Caso.model_validate_json(json.dumps(d))
