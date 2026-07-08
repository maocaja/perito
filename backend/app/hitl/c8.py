"""C8 HITL Service: State transitions and approvals with model_validate enforcement.

RULE-CTR-08 (P1 HITL):
- transicionar: moves between non-terminal states
- aprobar: terminal state (APROBADO) with usuario signature
- rechazar: terminal state (RECHAZADO) with usuario signature
- ALL use model_validate(dict) to re-run @field_validators (Pydantic v2)
- Never model_copy (bypasses validators)

H-12 Dual Gates:
- H-12a (construction): Caso.__init__ rejects APROBADO/RECHAZADO without aprobado_por
- H-12b (hitl logic): aprobar/rechazar require usuario ≠ None
"""

from datetime import datetime, timezone
from typing import Optional

from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso


class HITLService:
    """HITL state machine for Caso."""
    
    @staticmethod
    def transicionar(
        caso: Caso,
        nuevo_estado: EstadoCaso,
        actor: str,
        motivo: Optional[str] = None
    ) -> Caso:
        """Transition between non-terminal states.
        
        Args:
            caso: Current Caso
            nuevo_estado: Target state (non-terminal)
            actor: Who initiated (e.g., "SISTEMA", "USUARIO")
            motivo: Reason for transition
        
        Returns:
            Updated Caso with new estado
        
        Raises:
            ValueError: If nuevo_estado is terminal
            ValueError: Pydantic validation error (from model_validate)
        """
        
        if nuevo_estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}:
            raise ValueError(
                f"RULE-CTR-08: transicionar({nuevo_estado}) es prohibido; "
                "usa aprobar() o rechazar() para estados terminales"
            )
        
        # Use model_validate to re-run @field_validators (Pydantic v2)
        caso_dict = caso.model_dump()
        caso_dict["estado"] = nuevo_estado
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        if motivo:
            caso_dict["motivo_escalamiento"] = motivo
        
        caso_actualizado = Caso.model_validate(caso_dict)
        return caso_actualizado
    
    @staticmethod
    def aprobar(
        caso: Caso,
        usuario: str
    ) -> Caso:
        """Approve claim (move to APROBADO).
        
        CRITICAL (H-12b): usuario must not be None.
        This is the hitl logic dual gate (construction has H-12a).
        
        Args:
            caso: Caso in non-terminal state
            usuario: Human approvee (required)
        
        Returns:
            Caso in APROBADO state with aprobado_por set
        
        Raises:
            ValueError: If usuario is None (H-12b gate)
            ValueError: Pydantic validation error (H-12a via model_validate)
        """
        
        # H-12b gate: usuario ≠ None
        if usuario is None:
            raise ValueError(
                "RULE-CTR-08 (H-12b): aprobar(usuario=None) es prohibido; "
                "aprobación sin firma humana viola P1 HITL"
            )
        
        # Use model_validate to enforce H-12a (aprobado_por ≠ None for terminal)
        caso_dict = caso.model_dump()
        caso_dict["estado"] = EstadoCaso.APROBADO
        caso_dict["aprobado_por"] = usuario
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        
        caso_aprobado = Caso.model_validate(caso_dict)
        return caso_aprobado
    
    @staticmethod
    def rechazar(
        caso: Caso,
        usuario: str,
        motivo: str
    ) -> Caso:
        """Reject claim (move to RECHAZADO).
        
        CRITICAL (H-12b): usuario must not be None.
        
        Args:
            caso: Caso in non-terminal state
            usuario: Human rejectee (required)
            motivo: Rejection reason
        
        Returns:
            Caso in RECHAZADO state with aprobado_por and motivo_escalamiento set
        
        Raises:
            ValueError: If usuario is None (H-12b gate)
            ValueError: Pydantic validation error (H-12a via model_validate)
        """
        
        # H-12b gate: usuario ≠ None
        if usuario is None:
            raise ValueError(
                "RULE-CTR-08 (H-12b): rechazar(usuario=None) es prohibido; "
                "rechazo sin firma humana viola P1 HITL"
            )
        
        # Use model_validate to enforce H-12a (aprobado_por ≠ None for terminal)
        caso_dict = caso.model_dump()
        caso_dict["estado"] = EstadoCaso.RECHAZADO
        caso_dict["aprobado_por"] = usuario
        caso_dict["motivo_escalamiento"] = motivo
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        
        caso_rechazado = Caso.model_validate(caso_dict)
        return caso_rechazado


# Module-level convenience functions
def transicionar(caso: Caso, nuevo_estado: EstadoCaso, actor: str, motivo: Optional[str] = None) -> Caso:
    """Module-level wrapper for HITLService.transicionar."""
    return HITLService.transicionar(caso, nuevo_estado, actor, motivo)


def aprobar(caso: Caso, usuario: str) -> Caso:
    """Module-level wrapper for HITLService.aprobar."""
    return HITLService.aprobar(caso, usuario)


def rechazar(caso: Caso, usuario: str, motivo: str) -> Caso:
    """Module-level wrapper for HITLService.rechazar."""
    return HITLService.rechazar(caso, usuario, motivo)
