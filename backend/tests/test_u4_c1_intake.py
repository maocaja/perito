"""Tests para C1 Intake (crear Caso desde AvisoNormalizado)."""

import pytest
from datetime import date

from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso


class TestIntakeCrearCaso:
    """C1 Intake: Crear Caso inicial."""

    def test_crear_caso_happy_path(self):
        """Happy path: LIMPIO → Caso(RECIBIDO)."""
        aviso = AvisoNormalizado(
            texto_crudo="Siniestro reportado...",
            calidad=CalidadDoc.LIMPIO
        )

        caso = intake_crear_caso(aviso)

        assert caso.estado == EstadoCaso.RECIBIDO
        assert caso.aviso == aviso
        assert caso.extraccion is None
        assert caso.poliza_match is None
        assert caso.dictamen is None
        assert caso.alerta_fraude is None
        assert caso.aprobado_por is None
        assert caso.id is not None
        assert caso.timestamp_creacion is not None

    def test_crear_caso_degradado(self):
        """DEGRADADO → Caso(RECIBIDO) (procesa pero monitorea confianza)."""
        aviso = AvisoNormalizado(
            texto_crudo="Aviso parcialmente legible...",
            calidad=CalidadDoc.DEGRADADO
        )

        caso = intake_crear_caso(aviso)

        assert caso.estado == EstadoCaso.RECIBIDO
        assert caso.aviso == aviso

    def test_crear_caso_ilegible_raises(self):
        """ILEGIBLE → raises ValueError (no procesar)."""
        aviso = AvisoNormalizado(
            texto_crudo="[texto ilegible]",
            calidad=CalidadDoc.ILEGIBLE
        )

        with pytest.raises(ValueError) as exc_info:
            intake_crear_caso(aviso)

        assert "ILEGIBLE" in str(exc_info.value)

