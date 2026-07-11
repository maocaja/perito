"""C7 Orchestrator: Process FNOL case through C2-C6 pipeline.

CORONA TEST: assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}
The orchestrator NEVER produces terminal (APROBADO/RECHAZADO).

C9 OBSERVABILITY INJECTION: Optional Tracer for per-node tracing (no logic mutation).
"""

import hashlib
import json
from datetime import datetime
from typing import Optional

from app.contracts.caso import Caso
from app.contracts.enums import EstadoCaso, ResultadoCobertura
from app.contracts.dictamen import Cotas
from app.observability.tracer import Tracer
from app.config import settings
from app.security.redaction import redact_pii_spans_es_co
from app.llm.extractor import call_c2_extractor
from app.llm.verifier import call_c3_verifier_capa1, call_c3_verifier_capa2
from app.policy.lookup import call_c4_policy_lookup
from app.rules.motor_r1_r5 import motor_cobertura
from app.fraud.fraude import construir_alerta_fraude
from app.fraud.cross_claim import combinar_alertas

# U9 — Umbral de baja fidelidad para disparar la re-extracción reflexiva C2↔C3 (P4-owned, explícito).
# El loop re-extrae SOLO si confianza < este umbral Y hay ≥1 inconsistencia de campo. Configurable.
UMBRAL_REEXTRACCION = 0.7


def orquestar_fnol(
    caso: Caso,
    hitl_service,
    cotas: Cotas,
    tracer: Optional[Tracer] = None  # C9 injection: optional
) -> Caso:
    """Main FNOL case processing orchestrator.
    
    CRITICAL INVARIANTS:
    - Never mutates caso.estado directly (hitl.transicionar only)
    - Never produces terminal (APROBADO/RECHAZADO)
    - Respects Cotas (max_rondas, presupuesto_tokens, cycle detection)
    - Exception capture → escalate, never propagate
    - C9 Observability: optional Tracer for instrumentation (no logic mutation)
    
    Args:
        caso: Caso in RECIBIDO state
        hitl_service: HITL service for state transitions
        cotas: Cotas contract with max_rondas and presupuesto_tokens
        tracer: Optional Tracer for per-node tracing (C9)
    
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
        
        if tracer:
            tracer.emit("orquestador_inicio", "Transición a EN_PROCESO")
        
        # --- Phase 2: Process loop with caps ---
        ronda = 0
        tokens_usados = 0
        snapshot_previo = None
        reextraido = False  # U9: cap DURO — a lo sumo UNA re-extracción reflexiva por caso (P4)
        
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
                if tracer:
                    tracer.emit("orquestador_cap_rondas", f"Rondas agotadas (max={cotas.max_rondas})")
                break
            
            # Cap 2: Token budget
            if tokens_usados > cotas.presupuesto_tokens:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    actor="SISTEMA",
                    motivo=f"Presupuesto de tokens ({cotas.presupuesto_tokens}) agotado"
                )
                if tracer:
                    tracer.emit("orquestador_cap_tokens", f"Tokens agotados (presupuesto={cotas.presupuesto_tokens})", tokens_in=tokens_usados)
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
                if tracer:
                    tracer.emit("orquestador_ciclo", "Ciclo detectado")
                break
            snapshot_previo = snapshot_actual
            
            # --- C2: Extracción (real, Haiku) ---
            if caso.extraccion is None:
                try:
                    extraccion, usage = call_c2_extractor(caso.aviso.texto_crudo)
                    caso = caso.model_copy(update={"extraccion": extraccion})
                    tokens_usados += usage["tokens_in"] + usage["tokens_out"]
                    if tracer:
                        tracer.emit("c2_extraccion", "Extracción completada",
                                    tokens_in=usage["tokens_in"], tokens_out=usage["tokens_out"])
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                        motivo=f"Extracción falló: {str(e)}"
                    )
                    if tracer:
                        tracer.emit("c2_extraccion", "Extracción falló", error=str(e))
                    break

                # --- C3: Verificación adversarial (Sonnet) + consistencia (determinística) ---
                try:
                    texto_red = redact_pii_spans_es_co(caso.aviso.texto_crudo)
                    verif, usage = call_c3_verifier_capa1(caso.extraccion, texto_red)
                    # Capa 2 agrega señales determinísticas (confianza baja, inconsistencias, campos)
                    _consistencia, señales = call_c3_verifier_capa2(caso.extraccion, verif)
                    tokens_usados += usage["tokens_in"] + usage["tokens_out"]
                    if tracer:
                        tracer.emit("c3_verificador", f"confianza={verif.confianza}, señales={len(señales)}",
                                    tokens_in=usage["tokens_in"], tokens_out=usage["tokens_out"])
                    # --- U9: Loop reflexivo C2↔C3 (evaluator-optimizer). Cap DURO por encima del framework ---
                    # Si C3 marca BAJA FIDELIDAD (confianza < umbral Y ≥1 inconsistencia de campo), el cap lo
                    # permite (max_rondas ≥ 2) y aún NO se ha re-extraído → C2 re-extrae UNA vez con la crítica
                    # de C3 como feedback. `reextraido` es el bound estructural: es imposible re-extraer dos veces.
                    # 🔒 P2: la re-extracción actualiza SOLO `extraccion` (campos); jamás toca cobertura ni
                    # `dictamen` (aquí es None; el motor R1-R5 dictamina DESPUÉS y sigue siendo el único).
                    if (señales and not reextraido and cotas.max_rondas >= 2
                            and verif.confianza < UMBRAL_REEXTRACCION and verif.inconsistencias):
                        reextraido = True
                        señalados = list(verif.inconsistencias)
                        critica = _critica_c3(verif)
                        antes = _valores_campos(caso.extraccion, señalados)
                        try:
                            reextr, usage_r = call_c2_extractor(caso.aviso.texto_crudo, feedback=critica)
                            caso = caso.model_copy(update={"extraccion": reextr})  # 🔒 P2: solo extraccion
                            tokens_usados += usage_r["tokens_in"] + usage_r["tokens_out"]
                            texto_red2 = redact_pii_spans_es_co(caso.aviso.texto_crudo)
                            verif, usage_v = call_c3_verifier_capa1(caso.extraccion, texto_red2)
                            _consistencia, señales = call_c3_verifier_capa2(caso.extraccion, verif)
                            tokens_usados += usage_v["tokens_in"] + usage_v["tokens_out"]
                            if tracer:
                                despues = _valores_campos(caso.extraccion, señalados)
                                tracer.emit("c2_reextraccion",
                                            f"Extractor re-extrajo tras crítica del Verificador: {antes} → {despues}",
                                            tokens_in=usage_r["tokens_in"], tokens_out=usage_r["tokens_out"])
                                tracer.emit("c3_reverificacion",
                                            f"confianza={verif.confianza}, señales={len(señales)}",
                                            tokens_in=usage_v["tokens_in"], tokens_out=usage_v["tokens_out"])
                        except Exception as e:
                            caso = hitl_service.transicionar(
                                caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                                motivo=f"Re-extracción reflexiva falló: {str(e)}"
                            )
                            if tracer:
                                tracer.emit("c2_reextraccion", "Re-extracción falló", error=str(e))
                            break

                    # Tras la posible re-extracción: si SIGUE habiendo señales → escala (como hoy). No loopea.
                    if señales:
                        caso = hitl_service.transicionar(
                            caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                            motivo=f"Verificación escaló: {señales[0].motivo}"
                        )
                        break
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                        motivo=f"Verificación falló: {str(e)}"
                    )
                    if tracer:
                        tracer.emit("c3_verificador", "Verificación falló", error=str(e))
                    break
            
            # --- C4: Policy Lookup (real, determinístico) ---
            if caso.poliza_match is None:
                try:
                    resultado_poliza = call_c4_policy_lookup(caso.extraccion)
                    caso = caso.model_copy(update={"poliza_match": resultado_poliza})
                    if tracer:
                        tracer.emit("c4_policy_lookup", f"encontrada={resultado_poliza.encontrada}")
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                        motivo=f"Póliza lookup falló: {str(e)}"
                    )
                    if tracer:
                        tracer.emit("c4_policy_lookup", "Policy lookup falló", error=str(e))
                    break
            
            # --- C5: Motor Cobertura (real, determinístico R1-R5) ---
            if caso.dictamen is None:
                try:
                    dictamen = motor_cobertura(caso.extraccion, caso.poliza_match)
                    caso = caso.model_copy(update={"dictamen": dictamen})
                    if tracer:
                        tracer.emit("c5_motor_cobertura", f"dictamen={dictamen.resultado.value}")
                    if dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION:
                        caso = hitl_service.transicionar(
                            caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                            motivo="Motor escaló (dato faltante o póliza no encontrada)"
                        )
                        break
                except Exception as e:
                    caso = hitl_service.transicionar(
                        caso, EstadoCaso.REQUIERE_REVISION, actor="SISTEMA",
                        motivo=f"Motor falló: {str(e)}"
                    )
                    if tracer:
                        tracer.emit("c5_motor_cobertura", "Motor falló", error=str(e))
                    break
            
            # --- C6: Fraude (real; informativo, NO escala — P1/P6) ---
            # Capas 1-2 intra-caso + capa 4 cross-claim (U10). Ambas SOLO sugieren: jamás cambian estado ni
            # deshabilitan la firma (P6). Fail-open: cualquier fallo aquí se registra y NO rompe el pipeline.
            if caso.alerta_fraude is None and caso.poliza_match and caso.poliza_match.poliza:
                try:
                    intra = construir_alerta_fraude(caso.extraccion, caso.poliza_match.poliza)
                    cross = _alerta_cross_claim(caso)  # U10: capa 4 (frecuencia hoy; foto/co-ocurrencia latentes)
                    alerta = combinar_alertas(intra, cross)
                    caso = caso.model_copy(update={"alerta_fraude": alerta})
                    if tracer:
                        capas = "+".join(c for c, a in (("intra", intra), ("cross-claim", cross)) if a)
                        tracer.emit("c6_fraude", f"Alerta emitida ({capas})" if alerta else "Sin inconsistencias")
                except Exception:
                    # Fraude no escala (informativo); solo se registra
                    if tracer:
                        tracer.emit("c6_fraude", "Fraude falló (no escala)")
            
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
                if tracer:
                    tracer.emit("orquestador_decision", "LISTO_PARA_APROBAR")
                break
        
        # --- CORONA TEST: Verify orchestrator never produces terminal ---
        assert caso.estado in {
            EstadoCaso.LISTO_PARA_APROBAR,
            EstadoCaso.REQUIERE_REVISION
        }, f"CORONA TEST FAILED: orquestador produce {caso.estado}, nunca debe ser terminal"
        
        return caso
    
    except Exception as e:
        # Fail-closed: unexpected error → escalate
        if tracer:
            tracer.emit("orquestador", "Excepción no capturada", error=str(e))
        raise RuntimeError(f"Orquestador failed: {str(e)}") from e


def _alerta_cross_claim(caso):
    """U10: alerta cross-claim (capa 4). Frecuencia por póliza + foto reutilizada (M1: huella de adjunto real).
    Informativa (P6): nunca cambia estado. Fail-open: None si no hay señal o algo falla.

    Consultas acotadas (P4): `casos_por_poliza` y `HuellaStore.buscar` heredan sus cotas duras.
    """
    try:
        from app.dashboard.store import get_caso_repository
        from app.fraud.cross_claim import construir_alerta_cross_claim
        from app.fraud.historia import get_huella_store
        from app.intake.document_ai import hash_media_de

        numero = None
        if caso.extraccion:
            numero = next((c.valor for c in caso.extraccion.campos
                           if c.nombre == "numero_poliza" and not c.ausente), None)
        # M1: huella de un adjunto real (foto) → activa la detección de foto reutilizada (antes latente).
        hash_media = hash_media_de(getattr(caso, "adjuntos", None) or [])
        return construir_alerta_cross_claim(
            caso_id=caso.id, numero_poliza=numero, hash_media=hash_media,
            repo=get_caso_repository(), huella_store=get_huella_store(),
        )
    except Exception:
        return None  # fail-open: el fraude cross-claim nunca rompe el pipeline (P6/P4)


def _critica_c3(verif) -> str:
    """U9: arma la crítica textual C3→C2 para la re-extracción. Solo NOMBRES DE CAMPO (sin PII).

    Reusa lo que C3 ya produce (`confianza` + `inconsistencias`); no inventa un contrato nuevo.
    """
    # Defensivo: los nombres vienen de C3 (confiable) pero se sanean igual antes de entrar al prompt —
    # una sola línea, sin caracteres de control, acotados (evita inyección por un nombre malformado).
    limpios = [" ".join(str(n).split())[:60] for n in (verif.inconsistencias or []) if str(n).strip()]
    campos = ", ".join(limpios[:10]) if limpios else "algunos campos"
    return (
        f"REVISIÓN DEL VERIFICADOR (C3): la confianza fue baja ({verif.confianza:.2f}) y se señalaron "
        f"posibles inconsistencias en: {campos}. Vuelve a leer el aviso con cuidado y corrige SOLO esos "
        f"campos si el texto los respalda. No inventes valores; si no están, márcalos ausentes."
    )


def _valores_campos(extraccion, nombres) -> dict:
    """Valores actuales de los campos señalados (para el 'antes → después' del feed, U9). Sin PII externa."""
    if extraccion is None:
        return {}
    quiere = set(nombres or [])
    return {c.nombre: c.valor for c in extraccion.campos if c.nombre in quiere}


def _es_terminal(estado: EstadoCaso) -> bool:
    """¿El caso alcanzó estado terminal?"""
    return estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def _snapshot_caso(caso: Caso) -> str:
    """Hash determinístico del CONTENIDO de (extraccion, poliza, dictamen) para detección de ciclos (P4).

    Usa el contenido (`model_dump_json`), NO `id()` del objeto: `id()` cambia en cada `model_copy`, así que
    el snapshot nunca coincidía y el ciclo NUNCA se detectaba (bug). Ahora si el estado se repite → se detecta.
    """
    def _contenido(m):
        return m.model_dump_json() if m is not None else None
    snapshot_dict = {
        "extraccion": _contenido(caso.extraccion),
        "poliza": _contenido(caso.poliza_match),
        "dictamen": _contenido(caso.dictamen),
    }
    snapshot_json = json.dumps(snapshot_dict, sort_keys=True)
    return hashlib.sha256(snapshot_json.encode()).hexdigest()
