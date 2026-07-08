"""
tests/test_u2_verifier_signal.py — Test C3 Capa 2 signals (P1/P4)

Verify SeñalEscalamiento is emitted correctly:
- confianza < 0.70 → CONFIANZA_BAJA signal
- confianza >= 0.70 + no inconsistencias → no signal
- Signals are typed, NOT Caso.estado (P1)
"""

import pytest
from datetime import datetime
from app.contracts.verificacion import (
    VerificacionAdversarial,
    SeñalEscalamiento,
    TipoSenal,
)
from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
from app.contracts.enums import TipoSiniestro
from app.llm.verifier import call_c3_verifier_capa2


def mock_extraccion():
    """Helper: mock valid ExtraccionValidada"""
    return ExtraccionValidada(
        campos=[
            CampoExtraido(nombre="numero_poliza", valor="POL-2026-001", confianza=0.95, ausente=False),
            CampoExtraido(nombre="tipo_siniestro", valor="AUTO_COLISION", confianza=0.9, ausente=False),
            CampoExtraido(nombre="fecha_siniestro", valor="2026-07-05", confianza=0.85, ausente=False),
            CampoExtraido(nombre="monto_siniestro", valor="5000000", confianza=0.8, ausente=False),
        ]
    )


def test_signal_confianza_baja():
    """If confianza < 0.70, emit CONFIANZA_BAJA signal"""
    extraccion = mock_extraccion()
    verificacion = VerificacionAdversarial(
        confianza=0.5,  # < 0.70
        inconsistencias=[],
        recomendacion="REVISA"
    )
    
    consistency, signals = call_c3_verifier_capa2(extraccion, verificacion)
    
    # Signal must be emitted
    assert len(signals) > 0
    confianza_signal = next((s for s in signals if s.tipo == TipoSenal.CONFIANZA_BAJA), None)
    assert confianza_signal is not None
    
    # CRITICAL: SeñalEscalamiento is NOT Caso.estado (P1)
    assert confianza_signal.tipo != "APROBADO"  # Not a state
    assert confianza_signal.tipo != "RECHAZADO"  # Not a state


def test_no_signal_confianza_alta():
    """If confianza >= 0.70 + no inconsistencias, NO CONFIANZA_BAJA signal"""
    extraccion = mock_extraccion()
    verificacion = VerificacionAdversarial(
        confianza=0.95,  # >= 0.70
        inconsistencias=[],
        recomendacion="ACEPTA"
    )
    
    consistency, signals = call_c3_verifier_capa2(extraccion, verificacion)
    
    # No CONFIANZA_BAJA signal if high confidence
    confianza_signals = [s for s in signals if s.tipo == TipoSenal.CONFIANZA_BAJA]
    assert len(confianza_signals) == 0


def test_signal_inconsistencias():
    """If inconsistencias found, emit VERIFIER_RECHAZA signal"""
    extraccion = mock_extraccion()
    verificacion = VerificacionAdversarial(
        confianza=0.95,
        inconsistencias=["numero_poliza seems invented"],
        recomendacion="RECHAZA"
    )
    
    consistency, signals = call_c3_verifier_capa2(extraccion, verificacion)
    
    # Signal must be emitted
    assert len(signals) > 0
    rechazo_signal = next((s for s in signals if s.tipo == TipoSenal.VERIFIER_RECHAZA), None)
    assert rechazo_signal is not None


def test_consistency_checks_fail():
    """If consistency checks fail (e.g., tipo_siniestro invalid), emit DOCUMENTO_SUCIO"""
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(nombre="numero_poliza", valor="POL-001", confianza=0.95, ausente=False),
            CampoExtraido(nombre="tipo_siniestro", valor="INVALID_TYPE", confianza=0.5, ausente=False),  # Invalid enum
            CampoExtraido(nombre="fecha_siniestro", valor="2026-07-05", confianza=0.85, ausente=False),
            CampoExtraido(nombre="monto_siniestro", valor="1000", confianza=0.8, ausente=False),
        ]
    )
    verificacion = VerificacionAdversarial(confianza=0.9, inconsistencias=[], recomendacion="ACEPTA")
    
    consistency, signals = call_c3_verifier_capa2(extraccion, verificacion)
    
    # Consistency check should fail
    assert not consistency.aprobado
    
    # DOCUMENTO_SUCIO signal emitted
    assert any(s.tipo == TipoSenal.DOCUMENTO_SUCIO for s in signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
