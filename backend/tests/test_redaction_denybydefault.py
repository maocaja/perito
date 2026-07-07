"""Pytest: Redacción PII deny-by-default (PATTERN-U1-01, P5).

Los redactores deben redactar todos los campos marcados PII por defecto.
"""

from app.contracts.extraccion import AvisoNormalizado
from app.contracts.pii import pii_fields
from app.security.redaction import PIIRedactingLogSerializer


def test_pii_fields_detecta_texto_crudo():
    """pii_fields(AvisoNormalizado): encuentra 'texto_crudo' como PII."""
    pii = pii_fields(AvisoNormalizado)
    assert "texto_crudo" in pii


def test_redaction_serializer_redacta_pii_por_defecto():
    """PIIRedactingLogSerializer: redacta PII sin whitelist."""
    serializer = PIIRedactingLogSerializer()
    aviso = AvisoNormalizado(texto_crudo="Juan Pérez, cédula 12345678")
    
    redacted = serializer.redact(
        {"texto_crudo": aviso.texto_crudo},
        AvisoNormalizado,
        whitelist=set(),  # vacío = deny-by-default
    )
    
    assert redacted["texto_crudo"] == "[REDACTED]"


def test_redaction_serializer_permite_whitelist():
    """PIIRedactingLogSerializer: whitelist permite campos PII."""
    serializer = PIIRedactingLogSerializer()
    aviso = AvisoNormalizado(texto_crudo="Juan Pérez")
    
    redacted = serializer.redact(
        {"texto_crudo": aviso.texto_crudo},
        AvisoNormalizado,
        whitelist={"texto_crudo"},  # ← permitido
    )
    
    assert redacted["texto_crudo"] == "Juan Pérez"
