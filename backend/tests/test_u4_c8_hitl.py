"""C8 HITL Tests (U4).

CRITICAL: model_validate enforcement + H-12 dual gates (construction + hitl logic)
"""

import pytest
from datetime import datetime

from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso, CalidadDoc
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.hitl.c8 import HITLService, transicionar, aprobar, rechazar


@pytest.fixture
def aviso_limpio():
    """Clean aviso (LIMPIO)."""
    return AvisoNormalizado(
        texto_crudo="Reclamo de siniestro total.",
        calidad=CalidadDoc.LIMPIO
    )


@pytest.fixture
def caso_recibido(aviso_limpio):
    """Caso in RECIBIDO state."""
    return intake_crear_caso(aviso_limpio)


class TestTransicionar:
    """HITLService.transicionar tests."""
    
    def test_transicionar_recibido_to_en_proceso(self, caso_recibido):
        """Happy path: RECIBIDO → EN_PROCESO."""
        resultado = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA",
            motivo="Test transition"
        )
        
        assert resultado.estado == EstadoCaso.EN_PROCESO
        assert resultado.motivo_escalamiento == "Test transition"
    
    def test_transicionar_en_proceso_to_listo_para_aprobar(self, caso_recibido):
        """Non-terminal transition: EN_PROCESO → LISTO_PARA_APROBAR."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = HITLService.transicionar(
            caso_en_proceso,
            EstadoCaso.LISTO_PARA_APROBAR,
            actor="SISTEMA"
        )
        
        assert resultado.estado == EstadoCaso.LISTO_PARA_APROBAR
    
    def test_transicionar_prohibido_aprobado(self, caso_recibido):
        """transicionar(APROBADO) is prohibited (use aprobar() instead)."""
        with pytest.raises(ValueError) as exc_info:
            HITLService.transicionar(
                caso_recibido,
                EstadoCaso.APROBADO,
                actor="SISTEMA"
            )
        
        assert "RULE-CTR-08" in str(exc_info.value)
        assert "prohibido" in str(exc_info.value).lower()
    
    def test_transicionar_prohibido_rechazado(self, caso_recibido):
        """transicionar(RECHAZADO) is prohibited (use rechazar() instead)."""
        with pytest.raises(ValueError) as exc_info:
            HITLService.transicionar(
                caso_recibido,
                EstadoCaso.RECHAZADO,
                actor="SISTEMA"
            )
        
        assert "RULE-CTR-08" in str(exc_info.value)


class TestAprobar:
    """HITLService.aprobar tests (H-12 dual gates)."""
    
    def test_aprobar_happy_path(self, caso_recibido):
        """Happy path: EN_PROCESO → APROBADO with usuario signature."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = HITLService.aprobar(caso_en_proceso, usuario="jose@seguros.com")
        
        assert resultado.estado == EstadoCaso.APROBADO
        assert resultado.aprobado_por == "jose@seguros.com"
    
    def test_aprobar_h12b_gate_usuario_none(self, caso_recibido):
        """H-12b gate: aprobar(usuario=None) raises ValueError (P1 HITL)."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        with pytest.raises(ValueError) as exc_info:
            HITLService.aprobar(caso_en_proceso, usuario=None)
        
        assert "H-12b" in str(exc_info.value)
        assert "P1 HITL" in str(exc_info.value)
    
    def test_aprobar_h12a_via_model_validate(self, caso_recibido):
        """H-12a enforced: model_validate re-runs validators."""
        # aprobar constructs dict and calls model_validate
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = HITLService.aprobar(caso_en_proceso, usuario="maria@seguros.com")
        
        # Verify model_validate ran validators (aprobado_por is set for terminal)
        assert resultado.aprobado_por is not None
        assert resultado.estado == EstadoCaso.APROBADO


class TestRechazar:
    """HITLService.rechazar tests (H-12 dual gates)."""
    
    def test_rechazar_happy_path(self, caso_recibido):
        """Happy path: EN_PROCESO → RECHAZADO with usuario signature."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = HITLService.rechazar(
            caso_en_proceso,
            usuario="paula@seguros.com",
            motivo="Póliza no encontrada"
        )
        
        assert resultado.estado == EstadoCaso.RECHAZADO
        assert resultado.aprobado_por == "paula@seguros.com"
        assert resultado.motivo_escalamiento == "Póliza no encontrada"
    
    def test_rechazar_h12b_gate_usuario_none(self, caso_recibido):
        """H-12b gate: rechazar(usuario=None) raises ValueError (P1 HITL)."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        with pytest.raises(ValueError) as exc_info:
            HITLService.rechazar(
                caso_en_proceso,
                usuario=None,
                motivo="Test"
            )
        
        assert "H-12b" in str(exc_info.value)
    
    def test_rechazar_h12a_via_model_validate(self, caso_recibido):
        """H-12a enforced: model_validate re-runs validators."""
        caso_en_proceso = HITLService.transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = HITLService.rechazar(
            caso_en_proceso,
            usuario="carlos@seguros.com",
            motivo="Fraude sospechoso"
        )
        
        # Verify model_validate ran validators
        assert resultado.aprobado_por is not None
        assert resultado.estado == EstadoCaso.RECHAZADO


class TestModuleLevel:
    """Module-level convenience functions."""
    
    def test_module_level_transicionar(self, caso_recibido):
        """Module-level transicionar wrapper."""
        resultado = transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        assert resultado.estado == EstadoCaso.EN_PROCESO
    
    def test_module_level_aprobar(self, caso_recibido):
        """Module-level aprobar wrapper."""
        caso_en_proceso = transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = aprobar(caso_en_proceso, usuario="test@seguros.com")
        
        assert resultado.estado == EstadoCaso.APROBADO
    
    def test_module_level_rechazar(self, caso_recibido):
        """Module-level rechazar wrapper."""
        caso_en_proceso = transicionar(
            caso_recibido,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA"
        )
        
        resultado = rechazar(
            caso_en_proceso,
            usuario="test@seguros.com",
            motivo="Test"
        )
        
        assert resultado.estado == EstadoCaso.RECHAZADO
