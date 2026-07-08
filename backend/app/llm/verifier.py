"""
app/llm/verifier.py — C3 Verifier (Capa 1: Sonnet Adversarial + Capa 2: Deterministic Code)

Two-layer verification:
- Capa 1: Sonnet re-reads source, confirms extraction is faithful (anti-hallucination H-03)
- Capa 2: Deterministic code validates consistency (no LLM)

GATE 4: Both pass through security/redaction before any LLM call
GATE 1: Capa 1 uses output_config.format with correct "schema" key
"""

import json
import logging
from datetime import datetime
from anthropic import Anthropic
from app.config import settings
from app.contracts.extraccion import ExtraccionValidada
from app.contracts.verificacion import (
    VerificacionAdversarial,
    VerificacionConsistencia,
    SeñalEscalamiento,
    TipoSenal,
)
from app.contracts.extraccion import EvidenciaOrigen
from app.contracts.enums import TipoSiniestro

logger = logging.getLogger(__name__)


class VerifierError(Exception):
    """Raised if verification fails (fail-closed)."""
    pass


# Flat schema for C3 Capa 1 output
FLAT_VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "confianza": {"type": "number", "description": "Confianza 0..1"},
        "inconsistencias": {"type": "array", "items": {"type": "string"}},
        "recomendacion": {"type": "string", "enum": ["ACEPTA", "REVISA", "RECHAZA"]},
    },
    "required": ["confianza", "recomendacion"],
    "additionalProperties": False,
}


def call_c3_verifier_capa1(
    extraccion: ExtraccionValidada,
    texto_redactado: str,
) -> tuple[VerificacionAdversarial, dict]:
    """
    C3 Capa 1: Adversarial Verification (Sonnet)
    
    Re-read redacted aviso and confirm extraction is faithful to source.
    Detect hallucinations (H-03).
    
    PASO 3 (NFR Design): C3 Capa 1 adversarial re-read.
    """
    
    # Step 1: Build verification prompt with .campos data
    try:
        campos_str = "\n".join(
            [f"- {c.nombre}: {c.valor}" for c in extraccion.campos if not c.ausente]
        )
        prompt_ver = f"""
You are an adversarial verifier. Re-read the claim notice below and confirm each 
extracted field comes from the source OR is marked as absent.

--- BEGIN REDACTED NOTICE ---
{texto_redactado}
--- END NOTICE ---

Here is what was extracted:
{campos_str}

For each field in the extraction:
1. Confirm it appears in the source document, OR
2. Confirm it is marked as absent=true, OR
3. Flag it as potentially invented/inconsistent

Return JSON with: confianza (0-1), inconsistencias (list of field names), recomendacion (ACEPTA/REVISA/RECHAZA).
"""
    except Exception as e:
        logger.error(f"Verification prompt building failed: {str(e)}")
        raise VerifierError(f"Prompt failed: {str(e)}") from e
    
    # Step 2: Call Sonnet with output_config.format (GATE 1: correct form with "schema" key)
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model=settings.verifier_model,
            max_tokens=settings.verifier_max_tokens,
            messages=[{"role": "user", "content": prompt_ver}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": FLAT_VERIFICATION_SCHEMA,  # Key is "schema", not "json_schema"
                }
            },
        )
        
        logger.info(
            f"C3 Capa 1 verification: {response.usage.input_tokens} input, "
            f"{response.usage.output_tokens} output tokens"
        )
    
    except Exception as e:
        logger.error(f"C3 Capa 1 LLM call failed: {str(e)}")
        raise VerifierError(f"LLM call failed: {str(e)}") from e
    
    # Step 3: Parse JSON
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
        raise VerifierError(f"JSON parse failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Response extraction failed: {str(e)}")
        raise VerifierError(f"Response parsing failed: {str(e)}") from e
    
    # Step 4: Map to VerificacionAdversarial
    try:
        verificacion = VerificacionAdversarial(
            confianza=float(data.get("confianza", 0.5)),
            inconsistencias=data.get("inconsistencias", []),
            recomendacion=data.get("recomendacion", "REVISA"),
        )
        logger.info(
            f"Verification mapped: confianza={verificacion.confianza}, "
            f"inconsistencias={len(verificacion.inconsistencias)}"
        )
        usage = {"tokens_in": response.usage.input_tokens, "tokens_out": response.usage.output_tokens}
        return verificacion, usage
    
    except Exception as e:
        logger.error(f"Verification mapping failed: {str(e)}")
        raise VerifierError(f"Mapping failed: {str(e)}") from e


def call_c3_verifier_capa2(
    extraccion: ExtraccionValidada,
    verificacion_capa1: VerificacionAdversarial,
) -> tuple[VerificacionConsistencia, list[SeñalEscalamiento]]:
    """
    C3 Capa 2: Deterministic Consistency Validation (No LLM)
    
    Validate extraction via .campos (iterate CampoExtraido by nombre).
    Checks: fecha ≤ hoy, monto > 0, tipo ∈ TipoSiniestro, numero_poliza present.
    
    Emits SeñalEscalamiento if confianza < threshold or inconsistency found.
    NO decide cobertura (P2) ni muta estado (P1).
    
    Returns:
        (VerificacionConsistencia, list[SeñalEscalamiento])
    """
    
    signals = []
    
    # Check 1: confianza threshold (P4)
    if verificacion_capa1.confianza < settings.confidence_threshold:
        signals.append(
            SeñalEscalamiento(
                motivo=f"Confianza baja: {verificacion_capa1.confianza:.2f} < {settings.confidence_threshold}",
                tipo=TipoSenal.CONFIANZA_BAJA,
                datos_contexto={"confianza": verificacion_capa1.confianza},
            )
        )
    
    # Check 2: inconsistencias from adversarial (P1)
    if verificacion_capa1.inconsistencias:
        signals.append(
            SeñalEscalamiento(
                motivo=f"Inconsistencias detectadas: {', '.join(verificacion_capa1.inconsistencias)}",
                tipo=TipoSenal.VERIFIER_RECHAZA,
                datos_contexto={"inconsistencias": verificacion_capa1.inconsistencias},
            )
        )
    
    # Check 3: Deterministic validation (read via .campos)
    checks = {}
    
    try:
        # Field: numero_poliza (grounding critical)
        campo_poliza = next((c for c in extraccion.campos if c.nombre == "numero_poliza"), None)
        checks["numero_poliza_present"] = campo_poliza is not None and not campo_poliza.ausente and campo_poliza.valor is not None
        
        # Field: tipo_siniestro (P2 cobertura decision input)
        campo_tipo = next((c for c in extraccion.campos if c.nombre == "tipo_siniestro"), None)
        if campo_tipo and not campo_tipo.ausente and campo_tipo.valor:
            try:
                TipoSiniestro(campo_tipo.valor)
                checks["tipo_siniestro_valid"] = True
            except (ValueError, KeyError):
                checks["tipo_siniestro_valid"] = False
        else:
            checks["tipo_siniestro_valid"] = False
        
        # Field: fecha_siniestro (P4 consistency)
        campo_fecha = next((c for c in extraccion.campos if c.nombre == "fecha_siniestro"), None)
        if campo_fecha and not campo_fecha.ausente and campo_fecha.valor:
            try:
                fecha = datetime.fromisoformat(str(campo_fecha.valor))
                checks["fecha_siniestro_valid"] = fecha <= datetime.now()
            except Exception:
                checks["fecha_siniestro_valid"] = False
        else:
            checks["fecha_siniestro_valid"] = False
        
        # Field: monto_reclamado (P4 consistency)
        campo_monto = next((c for c in extraccion.campos if c.nombre == "monto_reclamado"), None)
        checks["monto_reclamado_positive"] = (
            campo_monto is not None 
            and not campo_monto.ausente
            and campo_monto.valor is not None 
            and float(campo_monto.valor) > 0
        )
    
    except Exception as e:
        logger.error(f"Consistency check failed: {str(e)}")
        raise VerifierError(f"Consistency check error: {str(e)}") from e
    
    # If any check failed, emit signal
    if not all(checks.values()):
        signals.append(
            SeñalEscalamiento(
                motivo=f"Validación de consistencia falló: {[k for k,v in checks.items() if not v]}",
                tipo=TipoSenal.DOCUMENTO_SUCIO,
                datos_contexto={"checks": checks},
            )
        )
    
    logger.info(f"Consistency checks: {checks}")
    
    return (
        VerificacionConsistencia(checks=checks, aprobado=all(checks.values())),
        signals,
    )
