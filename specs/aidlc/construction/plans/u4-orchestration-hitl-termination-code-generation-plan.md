# U4 Code Generation Plan — Orchestration·HITL·Termination

**Components:** C7 Orchestrator + C8 HITL + C1 Intake + C11 Dashboard
**Locked Spec:** 6 critical invariants from U4 NFR Requirements (no docs generated; spec embedded in plan)
**Protected Routes:** `backend/app/orchestrator/` (hook: requires explicit approval)

---

## Locked Invariants (From NFR Answers)

🔒 **1. Frozen per-field:** Caso.estado + aprobado_por only (validate_assignment=True), NOT model-wide
🔒 **2. CRITICAL hitl enforcement:** hitl.aprobar/rechazar use `Caso.model_validate({...})` NOT `model_copy()` 
🔒 **3. Token accounting REAL:** response.usage from LLM (C2/C3), not hardcoded placeholders
🔒 **4. CORONA TEST:** Assert `caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}` on ALL paths
🔒 **5. Fail-closed:** orquestador captures exceptions → hitl.transicionar(REQUIERE_REVISION), never propagates
🔒 **6. H-12 dual gates:** H-12a (construction validator) + H-12b (hitl.aprobar(usuario=None) raises)

---

## Components to Generate

### C7 Orchestrator (`backend/app/orchestrator/c7.py`)

**Responsibilities:**
- Main loop: intake → C2/C3/C4/C5/C6 → hitl.transicionar
- Respect Cotas (max_rondas=1, presupuesto_tokens=20000)
- Accumulate REAL token usage (invariant 🔒 3)
- Cycle detection via snapshot/hash
- Capture exceptions → escalate (invariant 🔒 5)
- NEVER `caso.estado = X` (hitl.transicionar only)
- NEVER produce terminal (invariant 🔒 4 CORONA TEST)

**Pseudo-code already locked in FD:**
- Intake → EN_PROCESO
- Loop while not terminal && cotas.ok()
- Each stage: try/except, capture → escape
- Final: LISTO_PARA_APROBAR or REQUIERE_REVISION
- Return to HITL for terminal decision

**Tests:**
- Happy path → LISTO_PARA_APROBAR
- C2 fails → REQUIERE_REVISION
- C4 no match → REQUIERE_REVISION
- Motor REQUIERE_REVISION → escalate
- Max_rondas agotado → REQUIERE_REVISION
- Cycle detected → REQUIERE_REVISION
- All paths: assert estado ∈ {LISTO_PARA_APROBAR, REQUIERE_REVISION} (CORONA TEST)

### C8 HITL (`backend/app/hitl/c8.py`)

**Responsibilities:**
- UNIQUE state mutator for Caso.estado
- hitl.transicionar(caso, nuevo_estado, actor, motivo) → Caso
- hitl.aprobar(caso, usuario) → Caso (terminal APROBADO, with aprobado_por)
- hitl.rechazar(caso, usuario, motivo) → Caso (terminal RECHAZADO, with aprobado_por)
- hitl.corregir(caso, cambios, usuario) → Caso (update sub-objects, state stays REQUIERE_REVISION)

**CRITICAL Implementation Detail (invariant 🔒 2):**
```
def aprobar(caso: Caso, usuario: str) -> Caso:
    if usuario is None:
        raise ValueError("RULE-CTR-05: usuario requerido para terminal")
    
    # Never use model_copy for terminal — it bypasses validators
    caso_dict = caso.model_dump()
    caso_dict.update({
        "estado": EstadoCaso.APROBADO,
        "aprobado_por": usuario,
        "timestamp_actualizacion": datetime.utcnow()
    })
    
    # model_validate re-runs @field_validator
    return Caso.model_validate(caso_dict)
```

**Tests:**
- H-12a: Caso(estado=APROBADO, aprobado_por=None) → raises
- H-12b: hitl.aprobar(caso, usuario=None) → raises
- H-12c: hitl.aprobar(caso, usuario_válido) → aprobado_por == usuario
- H-12d: direct model_copy(update={estado:APROBADO, aprobado_por:None}) would bypass validator (document why hitl uses model_validate)

### C1 Intake (`backend/app/intake/c1.py`)

**Responsibilities:**
- intake_crear_caso(aviso: AvisoNormalizado) → Caso(estado=RECIBIDO, ...)
- CalidadDoc=ILEGIBLE → raise (no processing)
- CalidadDoc=LIMPIO/DEGRADADO → create Caso

**Tests:**
- Happy path → Caso.estado == RECIBIDO
- ILEGIBLE → raises

### C11 Dashboard (demo-grade, `backend/app/dashboard/c11.py`)

**Responsibilities:**
- GET /casos → list of Caso (read-only)
- GET /casos/{id} → Caso detail (aviso redacted, P5)
- POST /casos/{id}/aprobar → hitl.aprobar() (delegates, not decides)
- POST /casos/{id}/rechazar → hitl.rechazar() (delegates)

**Tests:**
- Mock hitl.aprobar, call endpoint, assert hitl.aprobar was invoked
- Endpoint does NOT directly assign caso.estado

---

## Code Generation Gates

### Phase 1: C1 Intake (non-protected)
- [ ] intake_crear_caso() implemented
- [ ] CalidadDoc.ILEGIBLE handling
- [ ] 2 tests pass

### Phase 2: C7 Orchestrator (PROTECTED — requires hook approval)
- [ ] Main loop without `caso.estado = X`
- [ ] Cotas enforcement (max_rondas=1, presupuesto_tokens=20000)
- [ ] Exception capture → escalate
- [ ] Snapshot/hash cycle detection
- [ ] CORONA TEST on all paths: estado ∈ {LISTO_PARA_APROBAR, REQUIERE_REVISION}
- [ ] 6+ path tests GREEN
- [ ] User verifies by execution before hook approval

### Phase 3: C8 HITL (PROTECTED — requires hook approval)
- [ ] aprobar/rechazar use model_validate (not model_copy) 
- [ ] H-12a + H-12b + H-12c + H-12d tests pass
- [ ] frozen per-field validation (caso.estado = X raises)
- [ ] User verifies H-12 by execution before hook approval

### Phase 4: C11 Dashboard (non-protected)
- [ ] GET /casos, GET /casos/{id}
- [ ] POST /casos/{id}/aprobar delegates to hitl
- [ ] Tests: mockea hitl.*, verifies delegation

---

## User Verification Protocol

**Before each protected route (C7/C8) merge:**
- User runs `pytest backend/tests/test_u4_*.py -v`
- Verifies CORONA TEST passes (all paths: estado never terminal)
- Verifies H-12 passes (hitl model_validate enforcement)
- Confirms 6 locked invariants present in code
- Approves hook via `git push` (hook will ask for explicit approval)

---

## Execution Order

1. C1 Intake (quick, non-protected)
2. C7 Orchestrator (core loop, protected, CORONA TEST)
3. C8 HITL (validator enforcement, protected, H-12)
4. C11 Dashboard (UI delegation, non-protected)

---

## Success Criteria

✅ All 6 locked invariants implemented and verified by execution
✅ CORONA TEST: `assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}` passes on all paths
✅ H-12 dual gates: construction validator + hitl logic both fail-closed
✅ Orchestrator never produces terminal (P1 enforced)
✅ Tokens accumulated from REAL response.usage (not hardcoded)
✅ Suite 100% green, run by user

