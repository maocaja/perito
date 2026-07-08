# U4 Functional Design Plan — Orchestration·HITL·Termination

**Unit:** U4 · Orquestación FNOL · HITL · Terminación acotada
**Design Focus:** P1 (HITL único mutador), P4 (caps duros terminación), end-to-end closure
**Components:** C7 Orquestador + C8 HITL + C1 Intake + C11 Dashboard (demo-grade)

---

## Part 1: Functional Design Assessment & Questions

### P1: HITL (Human-in-the-Loop)

**Q1.1 Único mutador de estado:**
¿Quién (qué componente/función) es el ÚNICO responsable de transicionar Caso.estado?
- ¿Es C8 HITL el único que ejecuta `caso.estado = APROBADO | RECHAZADO`?
- ¿Todos los demás componentes (C7 orquestador, C2/C3/C4 extraer, C5/C6 motor/fraude) retornan señales (REQUIERE_REVISION, dictamen, alerta) SIN mutar caso.estado?
- ¿Hay algún path donde C7 orquestador o C5 motor intente mutar estado directamente?

[Answer]:

---

**Q1.2 Aprobado_por obligatorio (P1):**
¿Cómo se garantiza que terminal (APROBADO/RECHAZADO) exige aprobado_por humano?
- ¿Caso.estado = APROBADO lanza ValidationError si aprobado_por is None?
- ¿El test fail-closed H-12 verifica: Caso(estado=APROBADO, aprobado_por=None) → raises?
- ¿Existe un guardian test que bloquea la transición sin firma humana?

[Answer]:

---

**Q1.3 Alertas de fraude NO mutan estado:**
¿Las alertas de fraude (U3-C6) solo recomiendan revisión pero NO cierran casos?
- ¿AlertaFraude es un field informativo (Caso.alerta_fraude)?
- ¿No hay path donde severidad=ALTA → estado=RECHAZADO automático?
- ¿Fraude siempre escala a humano (REQUIERE_REVISION), nunca decide terminal?

[Answer]:

---

### P4: Terminación Acotada

**Q2.1 Caps duros del orquestador:**
¿C7 orquestador implementa límites duros de terminación?
- ¿Max rondas (por defecto: cuántas)?
- ¿Presupuesto tokens (por defecto: cuántos)?
- ¿Detección de ciclos (mismo estado consecutivo)?
- ¿Dónde viven estos caps (backend/app/orchestrator/)?

[Answer]:

---

**Q2.2 Escalamiento en vez de invención:**
¿Qué ocurre cuando falta dato o no hay match exacto?
- ¿Campo ausente en extracción → REQUIERE_REVISION (C5 motor lo rechaza)?
- ¿Póliza no encontrada (solo candidatas) → REQUIERE_REVISION (C4 PolicyLookup lo rechaza)?
- ¿El orquestador consume estas señales y escala (no reintenta, no inventa)?

[Answer]:

---

**Q2.3 Transiciones de estado (diagrama):**
¿Cuál es el flujo de transiciones válidas?
- RECIBIDO → EN_PROCESO → LISTO_PARA_APROBAR → (APROBADO | RECHAZADO)?
- ¿O REQUIERE_REVISION es estado intermedio que interrumpe?
- ¿Existen ciclos (REQUIERE_REVISION → EN_PROCESO → ...)?
- ¿Cuántos retries máximo en REQUIERE_REVISION antes de escalar a humano?

[Answer]:

---

### C1: Intake (Crear Caso)

**Q3.1 Crear Caso desde aviso:**
¿Cómo C1 Intake construye Caso inicial?
- ¿Entrada: AvisoNormalizado (texto_crudo del FNOL)?
- ¿Salida: Caso(estado=RECIBIDO, aviso, extraccion=None, poliza_match=None, ...)?
- ¿Validaciones: AvisoNormalizado.calidad (LIMPIO/DEGRADADO/ILEGIBLE) afecta flujo?
- ¿Dónde vive: backend/app/intake/ o backend/app/orchestrator/?

[Answer]:

---

**Q3.2 Calidad del documento (ILEGIBLE):**
¿Qué pasa si AvisoNormalizado.calidad = ILEGIBLE?
- ¿Escala a REQUIERE_REVISION inmediatamente (sin intentar extracción)?
- ¿O intenta C2 extracción y acepta confianza baja?

[Answer]:

---

### C8: HITL (Mutador de Estado)

**Q4.1 Función signature:**
¿Cuál es la interfaz de C8 HITL?
- Firma: `hitl_approve(caso_id, aprobado_por: str, decision: APROBADO | RECHAZADO) -> Caso`?
- ¿hitl_approve() es el ÚNICO path que muta Caso.estado?
- ¿Valida que aprobado_por es usuario válido (RolUsuario.ANALISTA | CUMPLIMIENTO)?

[Answer]:

---

**Q4.2 Información que presenta HITL:**
¿Qué ve el humano en el dashboard/detail para decidir?
- Caso completo (aviso, extracción, poliza_match, dictamen, alerta_fraude)?
- ¿Score/confianza de extracción (C2)?
- ¿Razón de REQUIERE_REVISION (qué campo faltaba, por qué escala)?

[Answer]:

---

### C7: Orquestador

**Q5.1 Loop principal:**
¿Cuál es el flujo de C7 orquestador?
- Pseudocódigo:
  ```
  caso = intake(aviso)
  while not terminal(caso):
    if rondas_agotadas or tokens_agotados or ciclo_detectado:
      caso.estado = REQUIERE_REVISION
      break
    
    caso = c2_extraccion(caso)  // si no tiene
    if not caso.extraccion.completa:
      caso.estado = REQUIERE_REVISION
      break
    
    caso = c4_policy_lookup(caso)  // si no tiene
    if not caso.poliza_match.encontrada:
      caso.estado = REQUIERE_REVISION
      break
    
    caso = c5_motor_cobertura(caso)  // cita dicta
    caso = c6_fraude(caso)  // alerta (no muta estado)
    
    // Revisar si terminal o REQUIERE_REVISION
    if es_terminal_o_escalamiento(caso):
      break
  
  return caso
  ```
- ¿Es este el flujo? ¿Hay pasos adicionales?

[Answer]:

---

**Q5.2 Detección de ciclos:**
¿Cómo se detectan ciclos (infinitos retry)?
- ¿Hash del estado (extraccion, poliza, dictamen) comparado con ronda anterior?
- ¿Booleano "estado no cambió en la última ronda" → REQUIERE_REVISION?

[Answer]:

---

### C11: Dashboard (Demo-grade)

**Q6.1 Bandeja de casos:**
¿Qué campos mínimos muestra C11 en la lista de casos?
- Caso.id, Caso.estado, Caso.timestamp, resumen de razón de escalamiento?

[Answer]:

---

**Q6.2 Detalle de caso:**
¿Qué información se expone en el detalle (para HITL)?
- Caso completo (aviso redactado, extracción, póliza, dictamen, alerta)?
- ¿O una vista compacta (resumen + link a detalles)?

[Answer]:

---

## Part 2: Execution Plan (Pending Answers)

Once all [Answer]: tags are filled, U4 FD will generate:

- [ ] `aidlc-docs/construction/u4/functional-design/hitl-contract.md`
  - Caso.estado enum (RECIBIDO, EN_PROCESO, ..., APROBADO, RECHAZADO)
  - Aprobado_por obligatorio (validator)
  - HITL como único mutador

- [ ] `aidlc-docs/construction/u4/functional-design/orchestrator-flow.md`
  - Pseudocódigo orquestador (C7)
  - Caps duros (rondas, tokens, ciclos)
  - Escalamiento lógica

- [ ] `aidlc-docs/construction/u4/functional-design/intake-spec.md`
  - C1 Intake: Caso constructor
  - Calidad del documento (ILEGIBLE handling)

- [ ] `aidlc-docs/construction/u4/functional-design/hitl-interface.md`
  - C8 HITL: hitl_approve() signature
  - Dashboard/detail mínimos (C11)

---

## Approval Gate

**User Vigilance Points:**
- [ ] HITL (C8) es ÚNICO mutador de estado (P1)
- [ ] Aprobado_por obligatorio en terminal (P1)
- [ ] Alertas de fraude NO cierran casos (P1)
- [ ] Caps duros de terminación (rondas, tokens, ciclos) en C7 (P4)
- [ ] Escalamiento en vez de invención (REQUIERE_REVISION path claro) (P4)
- [ ] Transiciones de estado: diagrama sin ciclos infinitos
- [ ] Test fail-closed H-12: terminal sin aprobado_por → raises

