"""
tests/test_u2_c2_c4_integration.py — Integration: C2 Extraction → C4 PolicyLookup

Verify that ExtraccionValidada output from C2 flows correctly into PolicyLookup.
Tests .campos access of numero_poliza end-to-end.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.contracts.poliza import Poliza, RangoFechas, ResultadoPoliza
from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
from app.policy.lookup import call_c4_policy_lookup, set_poliza_store


@pytest.fixture
def sample_polizas():
    """Sample polizas for integration testing."""
    return {
        "POL-2026-001": Poliza(
            numero="POL-2026-001",
            vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2027, 12, 31)),
            suma_asegurada=Decimal("50000000"),
            deducible=Decimal("500000")
        ),
    }


@pytest.fixture(autouse=True)
def setup_repo(sample_polizas):
    """Setup and cleanup mock repo."""
    set_poliza_store(sample_polizas)
    yield
    set_poliza_store({})


def test_c2_c4_flow_exact_match():
    """C2 extraction output → C4 lookup → exact match found."""
    # Simulate C2 ExtraccionValidada output
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="numero_poliza",
                valor="POL-2026-001",
                ausente=False,
                confianza=0.95
            ),
            CampoExtraido(
                nombre="tipo_siniestro",
                valor="AUTO_COLISION",
                ausente=False,
                confianza=0.9
            ),
            CampoExtraido(
                nombre="fecha_siniestro",
                valor="2026-07-06",
                ausente=False,
                confianza=0.85
            ),
        ]
    )

    # Call C4 with C2 output
    resultado = call_c4_policy_lookup(extraccion)

    # Verify result
    assert resultado.encontrada is True
    assert resultado.poliza is not None
    assert resultado.poliza.numero == "POL-2026-001"


def test_c2_c4_flow_missing_numero_poliza():
    """C2 extraction with missing numero_poliza → C4 returns encontrada=False."""
    # Simulate C2 output with ausente=True for numero_poliza
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="numero_poliza",
                valor=None,
                ausente=True,
                confianza=0.0
            ),
            CampoExtraido(
                nombre="tipo_siniestro",
                valor="AUTO_COLISION",
                ausente=False,
                confianza=0.9
            ),
        ]
    )

    # Call C4 with missing numero_poliza
    resultado = call_c4_policy_lookup(extraccion)

    # Should not crash, should return encontrada=False
    assert resultado.encontrada is False
    assert resultado.poliza is None
    assert len(resultado.candidatas) == 0


def test_c2_c4_flow_candidates():
    """C2 extraction with typo numero_poliza → C4 returns candidatas."""
    # Simulate C2 output with slightly misspelled numero_poliza
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="numero_poliza",
                valor="POL-2026-001-typo",  # Similar to existing
                ausente=False,
                confianza=0.6  # Lower confidence due to extraction uncertainty
            ),
        ]
    )

    # Call C4
    resultado = call_c4_policy_lookup(extraccion)

    # Should find candidates
    assert resultado.encontrada is False
    assert resultado.poliza is None  # Never promoted (Trap 3)
    assert len(resultado.candidatas) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
