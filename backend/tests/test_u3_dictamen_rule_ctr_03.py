"""Test guardián: RULE-CTR-03 validación condicional de clausula.

Invariante: Resultados terminales (CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO)
exigen clausula no-nula. REQUIERE_REVISION permite clausula=None.

Este test es el centinela de auditabilidad P2/P3: si cae, RULE-CTR-03 está roto.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.contracts.dictamen import Dictamen
from app.contracts.enums import ResultadoCobertura
from app.contracts.poliza import Clausula
from app.contracts.enums import TipoClausula


class TestRuleCtr03Guardian:
    """Guardián: clausula obligatoria en terminales."""

    def test_no_cubierto_sin_clausula_raises(self):
        """NO_CUBIERTO sin clausula → raises (RULE-CTR-03)."""
        with pytest.raises(ValidationError) as exc_info:
            Dictamen(
                resultado=ResultadoCobertura.NO_CUBIERTO,
                regla_aplicada="R1_VIGENCIA",
                clausula=None,  # ← VIOLACIÓN
                deducible_calculado=Decimal(0)
            )
        
        assert "RULE-CTR-03" in str(exc_info.value)
        assert "terminal" in str(exc_info.value).lower()

    def test_cubierto_sin_clausula_raises(self):
        """CUBIERTO sin clausula → raises (RULE-CTR-03)."""
        with pytest.raises(ValidationError) as exc_info:
            Dictamen(
                resultado=ResultadoCobertura.CUBIERTO,
                regla_aplicada="R5_DEDUCIBLE",
                clausula=None,  # ← VIOLACIÓN
                deducible_calculado=Decimal(0)
            )
        
        assert "RULE-CTR-03" in str(exc_info.value)

    def test_cubierto_parcial_sin_clausula_raises(self):
        """CUBIERTO_PARCIAL sin clausula → raises (RULE-CTR-03)."""
        with pytest.raises(ValidationError) as exc_info:
            Dictamen(
                resultado=ResultadoCobertura.CUBIERTO_PARCIAL,
                regla_aplicada="R5_DEDUCIBLE",
                clausula=None,  # ← VIOLACIÓN
                deducible_calculado=Decimal(500)
            )
        
        assert "RULE-CTR-03" in str(exc_info.value)

    def test_requiere_revision_sin_clausula_ok(self):
        """REQUIERE_REVISION sin clausula → OK (escalamiento, no dictamen terminal)."""
        dictamen = Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,  # ← PERMITIDO
            deducible_calculado=Decimal(0)
        )
        
        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION
        assert dictamen.clausula is None

    def test_terminal_con_clausula_ok(self):
        """NO_CUBIERTO con clausula → OK (RULE-CTR-03 satisfecho)."""
        clausula = Clausula(
            id="VIG-001",
            texto="Vigencia",
            tipo=TipoClausula.VIGENCIA,
            referencia="REF-VIG"
        )
        
        dictamen = Dictamen(
            resultado=ResultadoCobertura.NO_CUBIERTO,
            regla_aplicada="R1_VIGENCIA",
            clausula=clausula,  # ← PRESENTE
            deducible_calculado=Decimal(0)
        )
        
        assert dictamen.resultado == ResultadoCobertura.NO_CUBIERTO
        assert dictamen.clausula is not None
        assert dictamen.clausula.id == "VIG-001"

