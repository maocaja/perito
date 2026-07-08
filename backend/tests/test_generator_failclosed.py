"""Pytest: Generador fail-closed (RULE-GEN-02, P4).

Fraude etiquetado SIN inconsistencia encodada → excepción.
"""

import pytest
from app.contracts.dataset import GroundTruth
from app.contracts.enums import ResultadoCobertura


def test_ground_truth_fraude_sin_inconsistencia():
    """GroundTruth: etiqueta_fraude=True sin inconsistencia_esperada → ValueError."""
    with pytest.raises(ValueError, match="inconsistencia_esperada"):
        GroundTruth(
            campos_esperados={},
            resultado_cobertura_esperado=ResultadoCobertura.CUBIERTO,
            etiqueta_fraude=True,
            inconsistencia_esperada=None,  # ← Falta, fraude requiere inconsistencia
        )


def test_ground_truth_fraude_con_inconsistencia():
    """GroundTruth: etiqueta_fraude=True + inconsistencia_esperada → OK."""
    from app.contracts.extraccion import EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    
    gt = GroundTruth(
        campos_esperados={},
        resultado_cobertura_esperado=ResultadoCobertura.CUBIERTO,
        etiqueta_fraude=True,
        inconsistencia_esperada=EvidenciaOrigen(
            tipo=TipoOrigen.SPAN,
            referencia="Fecha inconsistente",
        ),
    )
    assert gt.etiqueta_fraude is True
    assert gt.inconsistencia_esperada is not None
