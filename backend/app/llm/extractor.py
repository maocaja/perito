"""
app/llm/extractor.py — C2 Extractor (Haiku)

Extraction from redacted aviso using claude-haiku-4-5.

GATE 2: Model ID from config (not hardcoded)
GATE 3: No effort parameter (Haiku 4.5 doesn't support it)
GATE 4: Input redacted via security/redaction before LLM call
GATE 1: Uses output_config.format with correct "schema" key (not "json_schema")
P3: Constructs CampoExtraido with origin (EvidenciaOrigen)
P4: ausente=True ⇒ valor=None (fail-closed)
"""

import json
import logging
from anthropic import Anthropic
from app.config import settings
from app.contracts.extraccion import ExtraccionValidada, CampoExtraido, EvidenciaOrigen
from app.contracts.enums import TipoOrigen

from app.security.redaction import build_extraction_prompt_u2

logger = logging.getLogger(__name__)


class ExtractorError(Exception):
    """Raised if extraction fails (fail-closed)."""
    pass


# Flat schema for LLM output (not nested ExtraccionValidada structure)
FLAT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "numero_poliza": {"type": ["string", "null"], "description": "Policy number"},
        "fecha_siniestro": {"type": ["string", "null"], "description": "Claim date (YYYY-MM-DD)"},
        "monto_siniestro": {"type": ["string", "number", "null"], "description": "Claim amount"},
        "tipo_siniestro": {"type": ["string", "null"], "description": "Claim type"},
        "ausentes": {"type": "array", "items": {"type": "string"}, "description": "Fields not found"},
        "numero_poliza_confianza": {"type": "number", "minimum": 0, "maximum": 1},
        "fecha_siniestro_confianza": {"type": "number", "minimum": 0, "maximum": 1},
        "monto_siniestro_confianza": {"type": "number", "minimum": 0, "maximum": 1},
        "tipo_siniestro_confianza": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["ausentes"],
    "additionalProperties": False,
}


def call_c2_extractor(texto_crudo: str) -> ExtraccionValidada:
    """
    C2 Extractor: Extract structured data from insurance claim.
    
    PASO 2 (NFR Design): C2 Haiku extraction from redacted aviso.
    
    Architecture:
    1. build_extraction_prompt_u2 redacts PII (P5 deny-by-default)
    2. client.messages.create with output_config.format (correct form: schema key)
    3. Parse flat JSON response
    4. Map flat JSON → CampoExtraido with origen (P3) and ausente⇒valor=None (P4)
    5. Construct ExtraccionValidada and validate
    
    Args:
        texto_crudo: Raw aviso text (potentially contains PII)
    
    Returns:
        ExtraccionValidada with campos: [CampoExtraido(...)]
    
    Raises:
        ExtractorError: If any step fails (fail-closed)
    """
    
    # Step 1: Redact PII (Gate 4, P5)
    try:
        prompt_redactado = build_extraction_prompt_u2(texto_crudo)
    except Exception as e:
        logger.error(f"Prompt building failed: {str(e)}")
        raise ExtractorError(f"Redaction failed (P5): {str(e)}") from e
    
    # Step 2: Call Haiku with output_config.format (GATE 1: correct form with "schema" key)
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        # GATE 2: Model ID from config
        # GATE 3: No effort parameter (Haiku 4.5 does NOT support it)
        response = client.messages.create(
            model=settings.extractor_model,
            max_tokens=settings.extractor_max_tokens,
            # NOTE: No effort parameter. Haiku 4.5 does NOT support it.
            # If passed, raises 400 Bad Request. Use defaults.
            messages=[
                {
                    "role": "user",
                    "content": prompt_redactado,  # Redacted (no PII)
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": FLAT_EXTRACTION_SCHEMA,  # Key is "schema", not "json_schema"
                }
            },
        )
        
        logger.info(
            f"C2 extraction: {response.usage.input_tokens} input, "
            f"{response.usage.output_tokens} output tokens"
        )
    
    except Exception as e:
        logger.error(f"C2 LLM call failed: {str(e)}")
        raise ExtractorError(f"LLM call failed: {str(e)}") from e
    
    # Step 3: Parse JSON from response
    try:
        text_content = next(
            (block.text for block in response.content if hasattr(block, "text")),
            None,
        )
        if not text_content:
            raise ValueError("No text in response")
        data = json.loads(text_content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {str(e)}")
        raise ExtractorError(f"JSON parse failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Response extraction failed: {str(e)}")
        raise ExtractorError(f"Response parsing failed: {str(e)}") from e
    
    # Step 4: Map flat JSON → CampoExtraido (P3: origin, P4: ausente⇒valor=None)
    try:
        ausentes = set(data.get("ausentes", []))
        campos = []
        
        for nombre in ("numero_poliza", "fecha_siniestro", "monto_siniestro", "tipo_siniestro"):
            valor_raw = data.get(nombre)
            esta_ausente = (nombre in ausentes) or (valor_raw is None)
            
            # P3: Populate origin
            if esta_ausente:
                origen = None
            else:
                origen = EvidenciaOrigen(
                    tipo=TipoOrigen.SPAN,
                    referencia=f"extracted from redacted_texto",
                )
            
            # P4: ausente=True ⇒ valor=None
            valor = None if esta_ausente else str(valor_raw)
            
            # Confianza per field
            confianza = data.get(f"{nombre}_confianza", 0.5 if esta_ausente else 0.8)
            
            campos.append(
                CampoExtraido(
                    nombre=nombre,
                    valor=valor,
                    origen=origen,
                    confianza=float(confianza),
                    ausente=esta_ausente,
                )
            )
        
        # Construct ExtraccionValidada (not validate from crudo, but from built campos)
        extraccion = ExtraccionValidada(campos=campos)
        logger.info(f"Extraction mapped: {len(campos)} campos with origin (P3) and ausente logic (P4)")
        
    except Exception as e:
        logger.error(f"Mapping failed: {str(e)}")
        raise ExtractorError(f"Cannot build CampoExtraido: {str(e)}") from e
    
    # Step 5: Final validation (fail-closed)
    try:
        extraccion = ExtraccionValidada.model_validate(extraccion.model_dump())
        logger.info(f"Extraction validated: {len(extraccion.campos)} campos")
        return extraccion
    except Exception as e:
        logger.error(f"Final validation failed: {str(e)}")
        raise ExtractorError(f"Validation failed: {str(e)}") from e
