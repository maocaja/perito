"""
tests/test_u2_policy_lookup.py — C4 PolicyLookup unit tests

Mock Poliza repository (no real Postgres).
Test cases: exact match, no match → candidates, missing numero_poliza, Trap 3 (no force).
"""

import pytest
from datetime import date
from decimal import Decimal

from app.contracts.poliza import Poliza, RangoFechas, Clausula, ResultadoPoliza
from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
from app.contracts.enums import TipoClausula
from app.policy.lookup import call_c4_policy_lookup, set_poliza_store


@pytest.fixture
def mock_poliza_repo():
    """Mock Poliza repository — dict-based, not real Postgres."""
    return {
        "POL-2026-001": Poliza(
            numero="POL-2026-001",
            vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2027, 12, 31)),
            coberturas_contratadas=["AUTO_COLISION"],
            suma_asegurada=Decimal("50000000"),  # Money accepts Decimal directly
            deducible=Decimal("500000"),
            clausulas=[
                Clausula(
                    id="C1",
                    texto="Cubre colisión con terceros",
                    tipo=TipoClausula.COBERTURA,
                    referencia="Póliza Art. 3"
                )
            ]
        ),
        "POL-2026-002": Poliza(
            numero="POL-2026-002",
            vigencia=RangoFechas(desde=date(2026, 6, 1), hasta=date(2027, 5, 31)),
            coberturas_contratadas=["HOGAR_AGUA"],
            suma_asegurada=Decimal("30000000"),
            deducible=Decimal("300000"),
            clausulas=[]
        ),
        "POL-2025-999": Poliza(
            numero="POL-2025-999",
            vigencia=RangoFechas(desde=date(2025, 1, 1), hasta=date(2025, 12, 31)),
            coberturas_contratadas=["AUTO_HURTO"],
            suma_asegurada=Decimal("40000000"),
            deducible=Decimal("400000"),
            clausulas=[]
        ),
    }


@pytest.fixture(autouse=True)
def setup_repo(mock_poliza_repo):
    """Auto-setup mock repo for each test."""
    set_poliza_store(mock_poliza_repo)
    yield
    set_poliza_store({})  # cleanup


def _make_extraccion(numero_poliza_valor: str | None) -> ExtraccionValidada:
    """Helper to build ExtraccionValidada with numero_poliza campo."""
    campos = [
        CampoExtraido(
            nombre="numero_poliza",
            valor=numero_poliza_valor,
            ausente=(numero_poliza_valor is None),
            confianza=0.9
        ),
        CampoExtraido(
            nombre="tipo_siniestro",
            valor="AUTO_COLISION",
            ausente=False,
            confianza=0.85
        ),
    ]
    return ExtraccionValidada(campos=campos)


# ============================================================================
# TEST CASE 1: Exact match returns poliza
# ============================================================================

def test_exact_match_returns_poliza():
    """Exact match by numero_poliza → encontrada=True, poliza=<obj>."""
    extraccion = _make_extraccion("POL-2026-001")
    resultado = call_c4_policy_lookup(extraccion)

    assert resultado.encontrada is True
    assert resultado.poliza is not None
    assert resultado.poliza.numero == "POL-2026-001"
    assert len(resultado.candidatas) == 0  # No candidates when exact match


# ============================================================================
# TEST CASE 2: No match returns candidatas (Trap 3: no force)
# ============================================================================

def test_no_match_returns_candidatas():
    """No exact match → encontrada=False, poliza=None, candidatas=[...]."""
    # Query for "POL-2026-003" which doesn't exist
    extraccion = _make_extraccion("POL-2026-003")
    resultado = call_c4_policy_lookup(extraccion)

    assert resultado.encontrada is False
    assert resultado.poliza is None  # NEVER promote candidate to poliza (Trap 3)
    # Should find similar policies (POL-2026-001, POL-2026-002 start similarly)
    assert len(resultado.candidatas) > 0
    # All candidates should be from the store
    assert all(c.numero in ["POL-2026-001", "POL-2026-002", "POL-2025-999"] 
               for c in resultado.candidatas)


# ============================================================================
# TEST CASE 3: Missing numero_poliza (watch-item 2) → encontrada=False
# ============================================================================

def test_missing_numero_poliza_returns_false():
    """Missing numero_poliza → encontrada=False, poliza=None, candidatas=[].
    
    Does NOT crash (watch-item 2: numero_poliza ausente/None → encontrada=False).
    """
    extraccion = _make_extraccion(None)  # ausente=True
    resultado = call_c4_policy_lookup(extraccion)

    assert resultado.encontrada is False
    assert resultado.poliza is None
    assert len(resultado.candidatas) == 0  # No candidates without numero_poliza


# ============================================================================
# TEST CASE 4: Candidata NOT promoted to poliza (Trap 3)
# ============================================================================

def test_candidata_not_promoted_to_poliza():
    """Even if only 1 candidate matches, poliza=None (no forcing match, Trap 3).
    
    RULE-CTR-07 validator enforces encontrada=False ⇒ poliza=None.
    """
    # Use a typo that still has candidates
    extraccion = _make_extraccion("POL-2026-001-typo")
    resultado = call_c4_policy_lookup(extraccion)

    assert resultado.encontrada is False
    assert resultado.poliza is None  # NEVER promoted (Trap 3)
    # Candidates exist but poliza stays None
    if len(resultado.candidatas) > 0:
        # Verify Pydantic contract: this is valid (candidatas allowed when encontrada=False)
        pass


# ============================================================================
# TEST CASE 5: ResultadoPoliza contract validation (RULE-CTR-07)
# ============================================================================

def test_resultadopoliza_contract_validation():
    """ResultadoPoliza validator RULE-CTR-07 enforces encontrada=False ⇒ poliza=None."""
    # Valid: encontrada=True with poliza
    valid_true = ResultadoPoliza(
        encontrada=True,
        poliza=Poliza(
            numero="POL-X",
            vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2027, 1, 1)),
            suma_asegurada=Decimal("1000000"),
            deducible=Decimal("100000")
        )
    )
    assert valid_true.encontrada is True
    assert valid_true.poliza is not None

    # Valid: encontrada=False with poliza=None (Trap 3 honored)
    valid_false = ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])
    assert valid_false.encontrada is False
    assert valid_false.poliza is None

    # Invalid: encontrada=True without poliza → ValidationError
    with pytest.raises(ValueError, match="encontrada=True exige 'poliza' no nula"):
        ResultadoPoliza(encontrada=True, poliza=None)

    # Invalid: encontrada=False WITH poliza → ValidationError (no forzar match)
    with pytest.raises(ValueError, match="encontrada=False no admite 'poliza'"):
        ResultadoPoliza(
            encontrada=False,
            poliza=Poliza(
                numero="POL-X",
                vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2027, 1, 1)),
                suma_asegurada=Decimal("1000000"),
                deducible=Decimal("100000")
            )
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
