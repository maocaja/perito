# U4 NFR Requirements Plan — ANSWERED & LOCKED 🔒

**Status:** All 13 questions answered with 6 critical invariants marked 🔒

---

## Part 1: NFR Requirements Answers

### P1 Enforcement (HITL Validator)

**Q1.1 — 🔒 Frozen per-field, NOT model-wide:**
NO ConfigDict(frozen=True) en todo Caso (congelaría sub-objetos que orquestador adjunta).
Usar frozen=True solo en estado + aprobado_por + validate_assignment=True.
Test: caso.estado = APROBADO (asignación directa) → raises FrozenFieldError.
(Frozen bloquea asignación directa pero NO model_copy — por eso Q1.3.)

**Q1.2 — @field_validator aprobado_por enforces terminal:**
@field_validator('aprobado_por') exige no-nulo si estado ∈ {APROBADO, RECHAZADO}.
H-12a: Caso(estado=APROBADO, aprobado_por=None) → ValidationError ✅

**Q1.3 — 🔒 CRITICAL: Doble cierre (hitl lógica + model_validate):**
(a) hitl.aprobar/rechazar: if usuario is None: raise ANTES de cualquier construcción
(b) Construir terminal vía: Caso.model_validate({**caso.model_dump(), "estado": APROBADO, "aprobado_por": usuario.id})
    NO model_copy (que evade validadores)
    model_validate re-corre @field_validator = defensa en profundidad
H-12b: hitl.aprobar(caso, usuario=None) → raises ✅

### P4 Terminación

**Q2.1 — Cotas contract:**
Cotas(max_rondas: int = Field(gt=0), presupuesto_tokens: int = Field(gt=0)) ya existe en U1.
Defaults: max_rondas=1, presupuesto_tokens=20000.

**Q2.2 — 🔒 Token accumulation (REAL, not estimated):**
ronda += 1 al inicio del loop, comparar con max_rondas.
🔒 Tokens: acumula response.usage REAL de cada LLM call (C2/C3), NO hardcodeados ("~500"/"~1000" del plan son placeholders).
En tests: inyecta token usage vía mock de LLM.
Agotado antes de terminal → hitl.transicionar(REQUIERE_REVISION, motivo="cotas agotadas").

**Q2.3 — Cycle detection via snapshot/hash:**
snapshot_previo = hash(model_dump_json(extraccion, poliza_match, dictamen)) al inicio de ronda.
Si snapshot_previo == snapshot_actual (0 progreso en ronda) → REQUIERE_REVISION.
Con max_rondas=1 casi nunca dispara, pero es defensa (LangGraph 33.8% loops).

### Testabilidad & Reliability

**Q3.1 — 🔒 CORONA TEST: Orquestador nunca cierra:**
SÍ a todos los paths (happy, escalamiento C2/C4/C5, caps agotados, ciclos).
🔒 TEST CORONA: En TODOS los paths, assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}.
El orquestador NUNCA produce terminal (APROBADO/RECHAZADO). Esa es la garantía P1.

**Q3.2 — H-12 fail-closed tests (construction + hitl logic):**
H-12a: Caso(estado=APROBADO, aprobado_por=None) → ValidationError (construction validator)
H-12b: hitl.aprobar(caso, usuario=None) → raises (hitl lógica, antes de model_validate)
H-12c: hitl.aprobar(caso, usuario_válido) → aprobado_por == usuario (model_validate éxitoso)
H-12d: Documenta el gap — model_copy({estado:APROBADO, aprobado_por:None}) crudo SÍ colaría el validador.
Por eso hitl usa model_validate, no model_copy. (Es el "por qué" del enforcement.)

**Q3.3 — Dashboard passivity (no state mutation):**
GET retornan Caso read-only (sin cambios).
POST/PUT solo llaman hitl.* (nunca caso.estado = X).
Test: mockea hitl.aprobar, aprueba vía endpoint, assert hitl.aprobar fue llamado y endpoint no tocó caso.estado.
Dashboard delega (C11 de U1), no decide.

### Non-Functional

**Q4.1 — Performance (single-pass):**
Single-pass: max_rondas=1. Latencia dominada por LLM (C2 Haiku + C3 Sonnet) → segundos, aceptable.
Overhead orquestación (motor, lookup) sub-ms.
Sin SLA duro (P7 — portafolio honesto). Se mide, no se promete.

**Q4.2 — 🔒 Fail-closed error handling:**
Cada stage (C2/C4/C5) en try/except.
Si sub-componente lanza → orquestador captura → hitl.transicionar(REQUIERE_REVISION, motivo="fallo en Cx").
Nunca propaga excepción cruda como "decisión".
Siempre escala a humano.

**Q4.3 — Auditability (logging + PII redaction):**
Cada transición: timestamp_actualizacion, actor (SISTEMA|usuario), motivo.
Vía PIIRedactingLogSerializer (sin PII en logs, P5).
motivo_escalamiento documenta el por qué.

---

## Part 2: Execution Plan

4 artifacts generating now:
- [ ] hitl-validator-enforcement.md (frozen per-field, model_validate, H-12 tests)
- [ ] orchestrator-caps.md (Cotas, ronda counter, REAL tokens, cycle detection)
- [ ] test-strategy.md (path coverage, "orquestador nunca cierra" corona test, H-12)
- [ ] reliability-audit.md (SLA, fail-closed, audit trail P3)

---

## Approval Gate

**User Vigilance Points:**
- [x] Caso.estado frozen per-field (not model-wide) + validate_assignment=True
- [x] @field_validator aprobado_por enforces terminal invariant (H-12a)
- [x] 🔒 hitl.aprobar/rechazar use model_validate (not model_copy) to re-run validators (H-12b, H-12d documenta gap)
- [x] Orquestador respeta Cotas (max_rondas=1, presupuesto_tokens=20000)
- [x] 🔒 Token accounting REAL (response.usage from LLM, not hardcoded estimates)
- [x] Cycle detection prevents infinite loops (P4)
- [x] 🔒 CORONA TEST: Orquestador never produces terminal (APROBADO/RECHAZADO)
- [x] Dashboard is passive (delegates to hitl.*)
- [x] 🔒 Fail-closed: orquestador captures failures → escalates, never propagates

