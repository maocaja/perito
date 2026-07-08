# U4 Functional Design — Orchestrator Flow (P4: Bounded Termination)

**Invariant Lock:** C7 Orquestador NUNCA muta Caso.estado; TODAS las transiciones vía HITL

---

## 1. Pseudocódigo CORRECTO (P1 Enforced)

```python
def orquestar_fnol(aviso: AvisoNormalizado, cotas: Cotas) -> Caso:
    """Orquestador C7: ensambla U2+U3, pero NUNCA muta estado.
    
    Invariante (P1): Todas las transiciones de Caso.estado van via hitl_service.
    El orquestador NUNCA hace caso.estado = X.
    
    Invariante (P4): Respeta caps duros (rondas, tokens, ciclos).
    Al agotar → solicita REQUIERE_REVISION via hitl, no inventa.
    """
    
    # --- C1 INTAKE: Crear Caso inicial ---
    caso = intake_crear_caso(aviso)  # estado=RECIBIDO
    
    # --- HITL: transicionar a EN_PROCESO ---
    caso = hitl_service.transicionar(
        caso,
        EstadoCaso.EN_PROCESO,
        actor="SISTEMA",
        motivo="Inicio orquestación"
    )
    
    # --- P4: CAPS DUROS ---
    ronda = 0
    tokens_usados = 0
    snapshot_previo = None
    
    # --- MAIN LOOP: U2+U3 Processing ---
    while not es_terminal(caso.estado) and cotas.ok():
        ronda += 1
        
        # P4: Chequear caps antes de continuar
        if ronda > cotas.max_rondas:
            caso = hitl_service.transicionar(
                caso,
                EstadoCaso.REQUIERE_REVISION,
                actor="SISTEMA",
                motivo=f"Máximo de rondas ({cotas.max_rondas}) agotado"
            )
            break
        
        if tokens_usados > cotas.presupuesto_tokens:
            caso = hitl_service.transicionar(
                caso,
                EstadoCaso.REQUIERE_REVISION,
                actor="SISTEMA",
                motivo=f"Presupuesto de tokens ({cotas.presupuesto_tokens}) agotado"
            )
            break
        
        # P4: Detección de ciclos (mismo estado 2 rondas seguidas)
        snapshot_actual = (caso.extraccion, caso.poliza_match, caso.dictamen)
        if snapshot_previo == snapshot_actual:
            caso = hitl_service.transicionar(
                caso,
                EstadoCaso.REQUIERE_REVISION,
                actor="SISTEMA",
                motivo="Ciclo detectado: estado no avanzó en esta ronda"
            )
            break
        snapshot_previo = snapshot_actual
        
        # --- C2 EXTRACCIÓN (si falta) ---
        if caso.extraccion is None:
            extraccion_resultado = c2_extraccion(caso.aviso)
            if extraccion_resultado.es_error():
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    motivo=f"Extracción falló: {extraccion_resultado.error}"
                )
                break
            caso = caso.model_copy(update={"extraccion": extraccion_resultado.valor})
        
        # --- C3 VERIFICACIÓN (si falta) ---
        # (Opcional MVP: skip si confianza alta)
        
        # --- C4 POLICY LOOKUP (si falta) ---
        if caso.poliza_match is None:
            poliza_resultado = c4_policy_lookup(caso.extraccion)
            if not poliza_resultado.encontrada:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    motivo="Póliza no encontrada (solo candidatas)"
                )
                break
            caso = caso.model_copy(update={"poliza_match": poliza_resultado})
        
        # --- C5 MOTOR COBERTURA (si falta) ---
        if caso.dictamen is None:
            dictamen = c5_motor_cobertura(caso.extraccion, caso.poliza_match)
            if dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION:
                caso = hitl_service.transicionar(
                    caso,
                    EstadoCaso.REQUIERE_REVISION,
                    motivo=f"Motor escaló: {dictamen.regla_aplicada}"
                )
                break
            caso = caso.model_copy(update={"dictamen": dictamen})
        
        # --- C6 FRAUDE (siempre, informa sin mutar estado) ---
        alerta_fraude = c6_fraude(caso.extraccion, caso.poliza_match)
        caso = caso.model_copy(update={"alerta_fraude": alerta_fraude})
        # Nota: c6 NUNCA muta estado; alerta es informativa
        
        # --- DECISIÓN: ¿Listo para aprobación o escalamiento? ---
        if caso.dictamen and caso.dictamen.resultado in {
            ResultadoCobertura.CUBIERTO,
            ResultadoCobertura.CUBIERTO_PARCIAL,
            ResultadoCobertura.NO_CUBIERTO
        }:
            # Motor produjo dictamen terminal → listo para HITL
            caso = hitl_service.transicionar(
                caso,
                EstadoCaso.LISTO_PARA_APROBAR,
                actor="SISTEMA",
                motivo="Extracción+Póliza+Motor completados, listo para revisión"
            )
        
        # Contabilizar tokens aproximados (para P4)
        tokens_usados += 500  # Stub: depende de modelo LLM real
    
    # --- Resultado final ---
    # El orquestador retorna Caso en:
    # - LISTO_PARA_APROBAR: humano vía hitl.aprobar/rechazar
    # - REQUIERE_REVISION: humano ingresa datos faltantes, orquestador vuelve a intentar
    # - Nunca APROBADO/RECHAZADO (esos solo via hitl.aprobar/rechazar)
    
    return caso


def es_terminal(estado: EstadoCaso) -> bool:
    """¿El caso alcanzó un estado terminal?"""
    return estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}
```

---

## 2. Invariantes Enforced (P4)

✅ **No state mutation by orchestrator:**
- Todas las transiciones pasan por `hitl_service.transicionar()`
- Sub-objetos (extraccion, poliza_match, dictamen, alerta_fraude) se actualizan via `modelo_copy()`
- **NUNCA:** `caso.estado = REQUIERE_REVISION` ← VIOLACIÓN P1

✅ **Caps duros:**
- `max_rondas`: límite de intentos (default: 1 = single-pass)
- `presupuesto_tokens`: ~10-20k (depende de modelo LLM real)
- **Detección de ciclos:** snapshot(extraccion, poliza, dictamen) sin cambios entre rondas → REQUIERE_REVISION

✅ **Escalamiento vs. Invención:**
- Campo ausente en extracción → C5 rechaza (REQUIERE_REVISION)
- Póliza sin match exacto → C4 rechaza (REQUIERE_REVISION)
- Orquestador **consume la señal** y escala; **NO reintenta, NO inventa**

✅ **Fraude nunca cierra:**
- C6 retorna `AlertaFraude | None` (informativo)
- **Nunca** muta `caso.estado`
- **Nunca** causa transición a terminal automática

✅ **Terminal is human-only:**
- Orquestador retorna caso en `LISTO_PARA_APROBAR` o `REQUIERE_REVISION`
- **APROBADO/RECHAZADO** solo via `hitl_service.aprobar()` / `hitl_service.rechazar()`
- Usuario (ANALISTA/CUMPLIMIENTO) es quien firma (aprobado_por)

---

## 3. Flow Summary

```
[RECIBIDO] → hitl.transicionar → [EN_PROCESO]
  ↓
  ├─ C2 (extracción)  ─→  falla? → hitl.transicionar → [REQUIERE_REVISION]
  ├─ C4 (póliza)      ─→  no match? → hitl.transicionar → [REQUIERE_REVISION]
  ├─ C5 (motor)       ─→  escala? → hitl.transicionar → [REQUIERE_REVISION]
  ├─ C6 (fraude)      ─→  alerta (no muta estado)
  ↓
  [LISTO_PARA_APROBAR] → hitl.transicionar → [EN_REVISION]
  ↓
  (HUMANO decide)
  ├─ hitl.aprobar  → [APROBADO] (con aprobado_por)
  ├─ hitl.rechazar → [RECHAZADO] (con aprobado_por)
  └─ hitl.transicionar → [REQUIERE_REVISION]
  
[REQUIERE_REVISION] → humano aporta dato → hitl.transicionar → [EN_PROCESO]
  ↓
  (loop de nuevo, acotado por max_rondas)
```

