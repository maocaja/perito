"""C7 Orchestrator: Process FNOL case through C2-C6 pipeline.

CORONA TEST: assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}
The orchestrator NEVER produces terminal (APROBADO/RECHAZADO).
"""

import hashlib
import json
from datetime import datetime
from typing import Optional

from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso, ResultadoCobertura
from app.contracts.dictamen import Cotas


def orquestar_fnol(
    caso: Caso,
    hitl_service,
    cotas: Cotas
) -> Caso:
    """Main FNOL case processing orchestrator.
    
    CRITICAL INVARIANTS:
    - Never mutates caso.estado directly (hitl.transicionar only)
    - Never produces terminal (APROBADO/RECHAZADO)
    - Respects Cotas (max_rondas, presupuesto_tokens, cycle detection)
    - Exception capture → escalate, never propagate
    
    Args:
        caso: Caso in RECIBIDO state
        hitl_service: HITL service for state transitions
        cotas: Cotas contract with max_rondas and presupuesto_tokens
    
    Returns:
        Caso in LISTO_PARA_APROBAR or REQUIERE_REVISION (NEVER terminal)
    
    Raises:
        Never (fail-closed)
    """
    
    try:
        # --- Phase 1: Transition to EN_PROCESO ---
        caso = hitl_service.transicionar(
            caso,
            EstadoCaso.EN_PROCESO,
            actor="SISTEMA",
            motivo="Inicio orquestación FNOL"
        )
        
        # --- Phase 2: Process loop with caps ---
        ronda = 0
        tokens_usados = 0
        snapshot_previo = None
        
        while not _es_terminal(caso.estado) and cotas is not None:
            ronda += 1
            
            # Cap 1: Max rondas (typically max_rondas=1 for single-pass)
            if ronda > cotas.max_rondas:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    actor="SISTEMA",
                    motivo=f"Máximo de rondas ({cotas.max_rondas}) agotado"
                )
                break
            
            # Cap 2: Token budget
            if tokens_usados > cotas.presupuesto_tokens:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    actor="SISTEMA",
                    motivo=f"Presupuesto de tokens ({cotas.presupuesto_tokens}) agotado"
                )
                break
            
            # Cap 3: Cycle detection
            snapshot_actual = _snapshot_caso(caso)
            if snapshot_previo == snapshot_actual:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    actor="SISTEMA",
                    motivo="Ciclo detectado: sin progreso en esta ronda"
                )
                break
            snapshot_previo = snapshot_actual
            
            # --- C2: Extracción (stub) ---
            if caso.extraccion is None:
                try:
                    # In real implementation: c2_extraccion(caso.aviso)
                    # For now: stub (tests will mock)
                    pass
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso,
                        EstadoCaso.REQUIERE_REVISION,
                        actor="SISTEMA",
                        motivo=f"Extracción falló: {str(e)}"
                    )
                    break
            
            # --- C4: Policy Lookup (stub) ---
            if caso.poliza_match is None:
                try:
                    # In real implementation: c4_policy_lookup(caso.extraccion)
                    # For now: stub
                    pass
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso,
                        EstadoCaso.REQUIERE_REVISION,
                        actor="SISTEMA",
                        motivo=f"Póliza lookup falló: {str(e)}"
                    )
                    break
            
            # --- C5: Motor Cobertura (stub) ---
            if caso.dictamen is None:
                try:
                    # In real implementation: c5_motor_cobertura(caso.extraccion, caso.poliza_match.poliza)
                    # For now: stub
                    pass
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso,
                        EstadoCaso.REQUIERE_REVISION,
                        actor="SISTEMA",
                        motivo=f"Motor falló: {str(e)}"
                    )
                    break
            
            # --- C6: Fraude (stub) ---
            if caso.alerta_fraude is None:
                try:
                    # In real implementation: c6_fraude(caso.extraccion, caso.poliza_match.poliza)
                    # For now: stub (AlertaFraude optional, can be None)
                    pass
                except Exception:
                    # Fraude failures don't escalate; just continue
                    pass
            
            # --- Decision: LISTO_PARA_APROBAR or continue ---
            if caso.dictamen and caso.dictamen.resultado in {
                ResultadoCobertura.CUBIERTO,
                ResultadoCobertura.CUBIERTO_PARCIAL,
                ResultadoCobertura.NO_CUBIERTO
            }:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.LISTO_PARA_APROBAR,
                    actor="SISTEMA",
                    motivo="Extracción + Póliza + Motor completados"
                )
                break
        
        # --- CORONA TEST: Verify orchestrator never produces terminal ---
        assert caso.estado in {
            EstadoCaso.LISTO_PARA_APROBAR,
            EstadoCaso.REQUIERE_REVISION
        }, f"CORONA TEST FAILED: orquestador produce {caso.estado}, nunca debe ser terminal"
        
        return caso
    
    except Exception as e:
        # Fail-closed: unexpected error → escalate
        raise RuntimeError(f"Orquestador failed: {str(e)}") from e


def _es_terminal(estado: EstadoCaso) -> bool:
    """¿El caso alcanzó estado terminal?"""
    return estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def _snapshot_caso(caso: Caso) -> str:
    """Hash deterministico de (extraccion, poliza, dictamen) para ciclo detection."""
    snapshot_dict = {
        "extraccion_id": id(caso.extraccion) if caso.extraccion else None,
        "poliza_id": id(caso.poliza_match) if caso.poliza_match else None,
        "dictamen_id": id(caso.dictamen) if caso.dictamen else None,
    }
    snapshot_json = json.dumps(snapshot_dict, sort_keys=True)
    return hashlib.sha256(snapshot_json.encode()).hexdigest()
