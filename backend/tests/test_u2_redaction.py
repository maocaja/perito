"""
tests/test_u2_redaction.py — Test PII redaction (P5)

Verify that redact_pii_spans_es_co works correctly:
- Redacts: cédula, teléfono, email
- Preserves: póliza, fecha, monto, tipo
- Declares gap: nombres/direcciones (P7)
"""

import pytest
from app.security.redaction import redact_pii_spans_es_co


def test_redaction_cedula():
    """Cédula variants → [REDACTED]"""
    assert redact_pii_spans_es_co("C.C. 1098765432 es cliente") == "[REDACTED] es cliente"
    assert redact_pii_spans_es_co("cedula 80123456 registrada") == "[REDACTED] registrada"
    assert redact_pii_spans_es_co("Cédula No. 52.987.654 aplica") == "[REDACTED] aplica"


def test_redaction_celular():
    """Teléfono móvil variants → [REDACTED]"""
    assert redact_pii_spans_es_co("celular 3115551234 activo") == "celular [REDACTED] activo"
    assert "[REDACTED]" in redact_pii_spans_es_co("call +57 9 3115551234 now")
    assert "[REDACTED]" in redact_pii_spans_es_co("311 555 1234 fijo")


def test_redaction_email():
    """Email → [REDACTED]"""
    assert redact_pii_spans_es_co("juanp@gmail.com es correo") == "[REDACTED] es correo"
    assert "[REDACTED]" in redact_pii_spans_es_co("contact.person@company.co for info")


def test_preservation_operational():
    """Operacional fields preserved: póliza, fecha, monto, tipo"""
    texto = "POL-2026-00187, 2026-07-05, AUTO_COLISION, $5.000.000"
    result = redact_pii_spans_es_co(texto)
    assert "POL-2026-00187" in result
    assert "2026-07-05" in result
    assert "AUTO_COLISION" in result
    assert "$5.000.000" in result


def test_gap_nombres_no_redactados():
    """Nombres y direcciones NOT redacted (P7 gap declared)"""
    texto = "Juan Pérez, Calle 5 #10-23"
    result = redact_pii_spans_es_co(texto)
    assert "Juan Pérez" in result  # NOT redacted
    assert "Calle 5" in result  # NOT redacted (gap P7)


def test_adversarial_cedula_variants():
    """Adversarial test: cedula with dots/hyphens"""
    assert "[REDACTED]" in redact_pii_spans_es_co("C.C. 52.987.654")
    assert "[REDACTED]" in redact_pii_spans_es_co("cedula 52-987-654")


def test_adversarial_email_edge():
    """Adversarial test: email with unusual format"""
    result = redact_pii_spans_es_co("contact+tag@domain.co.uk")
    assert "[REDACTED]" in result


def test_empty_input():
    """Empty input returns empty"""
    assert redact_pii_spans_es_co("") == ""
    assert redact_pii_spans_es_co(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
