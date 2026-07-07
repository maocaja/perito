"""
tests/test_u2_extractor_mapping.py — Test C2 flat JSON → CampoExtraido mapping

Verify that flat JSON from LLM is correctly mapped to CampoExtraido with:
- origen populated (P3)
- ausente=True ⇒ valor=None (P4)
"""

import pytest
from app.llm.extractor import call_c2_extractor, FLAT_EXTRACTION_SCHEMA
from app.contracts.extraccion import ExtraccionValidada
from unittest.mock import patch, MagicMock
import json


def mock_flat_response_happy():
    """Mock LLM response: flat JSON (what real Haiku returns)"""
    return {
        "numero_poliza": "POL-2026-001",
        "fecha_siniestro": "2026-07-05",
        "monto_siniestro": "5000000",
        "tipo_siniestro": "AUTO_COLISION",
        "ausentes": [],
        "numero_poliza_confianza": 0.95,
        "fecha_siniestro_confianza": 0.9,
        "monto_siniestro_confianza": 0.85,
        "tipo_siniestro_confianza": 0.8,
    }


def mock_flat_response_with_ausentes():
    """Mock LLM response: some fields absent"""
    return {
        "numero_poliza": "POL-2026-001",
        "fecha_siniestro": None,
        "monto_siniestro": "5000000",
        "tipo_siniestro": "AUTO_COLISION",
        "ausentes": ["fecha_siniestro"],
        "numero_poliza_confianza": 0.95,
        "monto_siniestro_confianza": 0.85,
        "tipo_siniestro_confianza": 0.8,
    }


@patch('app.llm.extractor.Anthropic')
def test_extractor_maps_flat_json_to_campos(mock_anthropic_class):
    """Flat JSON from LLM → CampoExtraido with origen (P3) and ausente logic (P4)"""
    
    # Setup mock LLM
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    response_data = mock_flat_response_happy()
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = [
        MagicMock(text=json.dumps(response_data), type="text")
    ]
    mock_client.messages.create.return_value = mock_response
    
    # Call extractor
    extraccion = call_c2_extractor("test aviso with POL-2026-001")
    
    # Verify campos structure
    assert len(extraccion.campos) == 4
    
    # Verify each campo has origen (P3)
    for campo in extraccion.campos:
        if not campo.ausente:
            assert campo.origen is not None, f"Campo {campo.nombre} missing origen (P3)"
            assert campo.origen.tipo == "SPAN"
            assert campo.valor is not None
    
    # Verify ausente logic (P4)
    poliza_campo = next((c for c in extraccion.campos if c.nombre == "numero_poliza"), None)
    assert poliza_campo is not None
    assert not poliza_campo.ausente
    assert poliza_campo.valor == "POL-2026-001"
    assert poliza_campo.origen is not None


@patch('app.llm.extractor.Anthropic')
def test_extractor_ausente_implies_valor_none(mock_anthropic_class):
    """P4: ausente=True ⇒ valor=None"""
    
    # Setup mock LLM
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    response_data = mock_flat_response_with_ausentes()
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = [
        MagicMock(text=json.dumps(response_data), type="text")
    ]
    mock_client.messages.create.return_value = mock_response
    
    # Call extractor
    extraccion = call_c2_extractor("test aviso")
    
    # Verify ausente=True ⇒ valor=None (fail-closed)
    fecha_campo = next((c for c in extraccion.campos if c.nombre == "fecha_siniestro"), None)
    assert fecha_campo is not None
    assert fecha_campo.ausente == True
    assert fecha_campo.valor is None, "P4 violation: ausente=True but valor is not None"
    assert fecha_campo.origen is None, "ausente fields should have origen=None"


@patch('app.llm.extractor.Anthropic')
def test_extractor_preserves_confianza_per_field(mock_anthropic_class):
    """Each CampoExtraido has confianza from LLM response"""
    
    # Setup mock LLM
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    response_data = mock_flat_response_happy()
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = [
        MagicMock(text=json.dumps(response_data), type="text")
    ]
    mock_client.messages.create.return_value = mock_response
    
    # Call extractor
    extraccion = call_c2_extractor("test aviso")
    
    # Verify confianza per field
    poliza = next((c for c in extraccion.campos if c.nombre == "numero_poliza"), None)
    assert poliza.confianza == 0.95
    
    fecha = next((c for c in extraccion.campos if c.nombre == "fecha_siniestro"), None)
    assert fecha.confianza == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
