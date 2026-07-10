"""Tests U8 — Entity resolution (fallback lookup por placa/cédula/nombre).

Cubre el paso 3 del operador: sin número de póliza, buscar por claves alternativas. Determinístico.
Invariantes: P4 (no forzar match; ambigüedad → escala), passive respecto a cobertura (solo resuelve póliza).
"""

from datetime import date
from decimal import Decimal

import pytest

from app.contracts.extraccion import CampoExtraido, ExtraccionValidada
from app.contracts.poliza import Poliza, RangoFechas
from app.policy.lookup import call_c4_policy_lookup, set_poliza_store


def _poliza(numero, *, placa=None, cedula=None, nombre=None):
    return Poliza(
        numero=numero,
        vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2027, 12, 31)),
        coberturas_contratadas=["AUTO_COLISION"],
        suma_asegurada=Decimal("50000000"),
        deducible=Decimal("500000"),
        placa=placa,
        asegurado_cedula=cedula,
        asegurado_nombre=nombre,
    )


@pytest.fixture(autouse=True)
def _repo():
    set_poliza_store({
        "POL-1": _poliza("POL-1", placa="ABC123", cedula="1.020.304", nombre="Ana María Gómez"),
        "POL-2": _poliza("POL-2", placa="XYZ789", cedula="9.999.999", nombre="Ana María Gómez"),
        "POL-3": _poliza("POL-3", placa="ABC123", cedula="5.555.555", nombre="Carlos Ruiz"),
    })
    yield
    set_poliza_store({})


def _extraccion(**claves):
    """Campos alternativos sin número de póliza (numero_poliza ausente)."""
    campos = [CampoExtraido(nombre="numero_poliza", valor=None, ausente=True)]
    for nombre, valor in claves.items():
        campos.append(CampoExtraido(nombre=nombre, valor=valor, ausente=False, confianza=0.9))
    return ExtraccionValidada(campos=campos)


# ---------------------------------------------------- resolución por clave fuerte única

def test_sin_numero_placa_unica_resuelve():
    """Sin número pero con placa que hace UN match → resuelve la póliza (paso 3 del operador)."""
    res = call_c4_policy_lookup(_extraccion(placa="XYZ789"))  # única
    assert res.encontrada is True
    assert res.poliza.numero == "POL-2"


def test_cedula_normalizada_resuelve():
    """La cédula normaliza puntos/espacios: '10 20 304' == '1.020.304'."""
    res = call_c4_policy_lookup(_extraccion(cedula="10 20 304"))  # == 1.020.304 → POL-1
    assert res.encontrada is True
    assert res.poliza.numero == "POL-1"


def test_placa_normaliza_guiones_y_mayusculas():
    res = call_c4_policy_lookup(_extraccion(placa="xyz-789"))
    assert res.encontrada is True and res.poliza.numero == "POL-2"


# ---------------------------------------------------- ambigüedad → escala (P4)

def test_placa_ambigua_no_fuerza_match():
    """Placa que aparece en 2 pólizas → NO resuelve; devuelve candidatas (escala, P4)."""
    res = call_c4_policy_lookup(_extraccion(placa="ABC123"))  # POL-1 y POL-3
    assert res.encontrada is False
    assert res.poliza is None
    assert {p.numero for p in res.candidatas} == {"POL-1", "POL-3"}


def test_nombre_nunca_autoresuelve_aunque_sea_unico():
    """Nombre = identificador débil: aunque haya 1 match, NO resuelve → candidatas (escala)."""
    res = call_c4_policy_lookup(_extraccion(nombre="Carlos Ruiz"))  # único (POL-3)
    assert res.encontrada is False          # no fuerza por nombre
    assert res.poliza is None
    assert [p.numero for p in res.candidatas] == ["POL-3"]


def test_nombre_multiple_es_candidatas():
    res = call_c4_policy_lookup(_extraccion(nombre="ana maría gómez"))  # POL-1 y POL-2 (normalizado)
    assert res.encontrada is False
    assert {p.numero for p in res.candidatas} == {"POL-1", "POL-2"}


# ---------------------------------------------------- ninguna → escala, no inventa

def test_ninguna_clave_hace_match_escala():
    res = call_c4_policy_lookup(_extraccion(placa="NOEXISTE"))
    assert res.encontrada is False
    assert res.poliza is None
    assert res.candidatas == []


def test_sin_numero_ni_claves_escala():
    """Retro-compat: sin número y sin claves alternativas → encontrada=False (comportamiento previo)."""
    res = call_c4_policy_lookup(_extraccion())
    assert res.encontrada is False
    assert res.candidatas == []


@pytest.mark.parametrize("valor", ["", "   ", "----", "...."])
def test_clave_vacia_o_solo_simbolos_no_resuelve(valor):
    """Placa vacía / solo símbolos → normaliza a '' → no busca, no fuerza (escala)."""
    res = call_c4_policy_lookup(_extraccion(placa=valor))
    assert res.encontrada is False
    assert res.poliza is None


def test_clave_presente_pero_ausente_no_busca():
    """Un campo 'placa' marcado ausente no dispara el fallback (no-invención)."""
    campos = [
        CampoExtraido(nombre="numero_poliza", valor=None, ausente=True),
        CampoExtraido(nombre="placa", valor=None, ausente=True),
    ]
    res = call_c4_policy_lookup(ExtraccionValidada(campos=campos))
    assert res.encontrada is False and res.candidatas == []


# ---------------------------------------------------- prioridad y precedencia del número

def test_numero_exacto_tiene_precedencia_sobre_claves():
    """Si el número hace match exacto, NO se usa el fallback (camino principal intacto)."""
    campos = [
        CampoExtraido(nombre="numero_poliza", valor="POL-1", ausente=False, confianza=0.95),
        CampoExtraido(nombre="placa", valor="XYZ789", ausente=False, confianza=0.9),  # apuntaría a POL-2
    ]
    res = call_c4_policy_lookup(ExtraccionValidada(campos=campos))
    assert res.encontrada is True
    assert res.poliza.numero == "POL-1"  # ganó el número, no la placa


def test_placa_prioritaria_sobre_cedula():
    """Orden placa → cédula: una placa única resuelve antes de mirar la cédula."""
    res = call_c4_policy_lookup(_extraccion(placa="XYZ789", cedula="1.020.304"))
    assert res.encontrada is True and res.poliza.numero == "POL-2"  # por placa, no cédula (POL-1)


def test_resolucion_no_toca_cobertura():
    """Passive (P2/P1): C4 solo resuelve la póliza; no emite dictamen ni estado."""
    res = call_c4_policy_lookup(_extraccion(placa="XYZ789"))
    assert not hasattr(res, "dictamen") and not hasattr(res, "estado")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
