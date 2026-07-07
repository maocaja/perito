# AI-DLC State Tracking — Perito

## Project Information
- **Project Type**: Greenfield
- **Start Date**: 2026-07-06
- **Current Phase**: CONSTRUCTION
- **Current Stage**: U2 — Extracción/Verificación/Grounding (C2/C3/C4 ✅ APROBADOS)
- **Unidad en curso**: U2 parcial (C2/C3/C4 completos; C1 Intake pendiente)
- **Loop por-unidad**: Functional Design → NFR Requirements → NFR Design → Infrastructure Design → Code Generation (por unidad); Build & Test tras todas las unidades.

## Workspace State
- **Existing Code**: No (greenfield)
- **Programming Languages**: Python 3.14 + Pydantic v2
- **Build System**: pytest + FastAPI (scaffold)
- **Project Structure**: backend/ (app, tests); aidlc-docs/
- **Reverse Engineering Needed**: No
- **Workspace Root**: /Users/mauricio/dev/perito

## Domain Inputs
- `PRD.md` — Product Requirements Document (Estación 2)
- `AGENTS.md` — contexto de negocio/arquitectura y principios no negociables P1-P7
- `.claude/rules/` — hitl (P1), coverage-determinism (P2), termination (P4), testing

## Code Location Rules
- **Application Code**: Workspace root (NUNCA en aidlc-docs/)
- **Documentation / Artefactos AI-DLC**: aidlc-docs/ únicamente
- **Cosecha final**: a `specs/aidlc/` (NO se mergea CLAUDE.md de esta rama a main)

## Extension Configuration
| Extension | Enabled | Mode | Decided At |
|---|---|---|---|
| Security Baseline | Yes | Blocking (todas las reglas SECURITY-01..15) | Requirements Analysis |
| Property-Based Testing | Yes | **Partial** — enforced: PBT-02, PBT-03, PBT-07, PBT-08, PBT-09; resto advisory | Requirements Analysis |

## Decisiones de alcance (Requirements Analysis)
- **Q1 Alcance**: B — Must completo (13 items → módulos M1-M10). Should/SOAT fuera de esta Inception.
- **Q2 Depth**: A — Comprehensive (con matriz de trazabilidad a P1-P7).
- **Q3 Idioma**: A — Español (es-CO).
- **Q4 User Stories**: A — Sí, con Gherkin (Given/When/Then reutilizables como escenarios de eval por estrato).

## Execution Plan Summary
- **Stages to Execute (Inception)**: Application Design, Units Generation — ✅ COMPLETO
- **Stages to Execute (Construction, en curso)**: Functional Design, NFR Requirements, NFR Design, Code Generation, Build & Test — EN CURSO
- **Stages to Skip**: Reverse Engineering (greenfield), Infrastructure Design (portafolio — nada se despliega, RES-02/P7; Won't)
- **Alcance activo de esta sesión**: U1 + U2-C2/C3/C4; siguiente U3 o (C1 + U4)

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [x] Reverse Engineering (SKIPPED — greenfield)
- [x] Requirements Analysis (aprobado 2026-07-06; ajuste RF-27.1 SOAT diferido)
- [x] User Stories (Gherkin) — aprobado 2026-07-06 (18 historias, 14 fail-closed; ESPERANDO_INFO diferido declarado)
- [x] Workflow Planning — aprobado 2026-07-06 (Infra Design SKIP firme; docker-compose local = entregable de Code Gen)
- [x] Application Design — aprobado 2026-07-06 (A/A/A; P2 probado en grafo; 2 notas de endurecimiento anotadas)
- [x] Units Generation — aprobado 2026-07-06 (5 unidades, DAG verificado, P1/P2 preservados a nivel de import)

**✅ FASE INCEPTION COMPLETA (2026-07-06).**

### 🟢 CONSTRUCTION PHASE — EN CURSO (loop por-unidad)

**U1 · Fundaciones & Contratos:** ✅ COMPLETO
- [x] Functional Design, NFR Requirements, NFR Design, Infrastructure Design (SKIP), Code Generation (Tanda A-C)
- [x] Build and Test — posterior

**U2 · Extracción · Verificación · Grounding:** 🟠 PARCIAL (3 de 4 componentes)
- [x] C2 Extractor (Haiku) — aprobado 2026-07-06 (36/36 tests, P3/P4)
- [x] C3 Verifier (Sonnet) — aprobado 2026-07-06 (adversarial P5/P7 limpio)
- [x] C4 Policy Lookup — **aprobado 2026-07-07** (deterministic, 44/44 suite, cero LLM, .campos, no forzar match)
- [ ] C1 Intake (H-01) — ⏳ PENDIENTE (crear Caso desde aviso, duplicados)
- **Nota:** Persistencia de políticas stubbeada (dict en memoria). SQL real diferido a integración U4/Postgres.

**U3-U5:** ⏳ BLOQUEADOS (esperan U2-C4 + decisión de orden siguiente)

### 🟡 OPERATIONS PHASE
- [ ] Operations — PLACEHOLDER

---

## Summary: What's Done, What's Left

### ✅ DONE (Verified Real, Not Assumed)
- **U1 Foundations:** 100% (contratos Pydantic, RAG schema, synthetic data, FastAPI scaffolding)
- **U2-C2 Extractor:** 100% (flat JSON schema, CampoExtraido with EvidenciaOrigen, ausente⇒valor=None, P3/P4 verified)
- **U2-C3 Verifier:** 100% (adversarial re-read, SeñalEscalamiento, VerificacionConsistencia, P5 redaction complete)
- **U2-C4 Policy Lookup:** 100% (deterministic SQL sim., .campos access, no forced match, RULE-CTR-07, 8 new tests green)
- **Full Test Suite:** 44/44 passing (zero failures, zero warnings)

### ⏳ PENDING
- **U2-C1 Intake:** Crear Caso desde aviso, marcar duplicados (H-01). Puede plegarse con U4 (orquestador crea de todos modos).
- **U3 Cobertura & Fraude:** Motor R1-R5 determinístico (P2), alertas P6 explicables. Depende de U2-C4 ✅ (desbloqueado).
- **U4 Orquestación & HITL:** Terminación acotada (P4), único mutador Caso.estado (P1), bandeja HITL. Depende de U3.
- **U5 Observabilidad & Evals:** Trazas, evals por estrato, red-team. Transversal, evals finales requieren U2-U4.

---

## Ruta Crítica (Núcleo irrenunciable)
```
U1 ✅
  ↓
U2-C2 ✅
  ↓
U2-C3 ✅
  ↓
U2-C4 ✅  ← DESBLOQUEÓ U3
  ↓
U3 ⏳ (siguiente recomendado)
  ↓
U4 ⏳
  ↓
U5 ⏳ (transversal, evals finales)
```

---

## Próximos Pasos: Dos Caminos Válidos

### Opción A: U3 (Ruta Crítica, Recomendado)
- **Por qué:** Máximo valor, depende de U2-C4 ✅
- **Qué:** Motor de cobertura R1-R5 (P2 determinístico), alertas de fraude (P6 explicables)
- **Estimado:** ~1 día
- **Nota:** Cierra la lógica de decisión antes de orquestación

### Opción B: C1 Intake + U4 (Cerrar U2 primero)
- **Por qué:** U2 "completo", menos threads abiertos
- **Qué:** C1 (crear Caso desde aviso) plegado con U4 (orquestador lo necesita de todos modos)
- **Estimado:** ~0.5 día C1 + 1 día U4

### Recomendación del Usuario
**U3 primero** (ruta crítica). C1 Intake → U4 después.

---

## Verificación de Invariantes (P1-P7)

| Principio | U1 | U2 | U3 | U4 | U5 | Status |
|---|---|---|---|---|---|---|
| P1 HITL | — | Señales ✅ | Señales ✅ | **Decide** | Mide | En U4 |
| P2 Cobertura Det. | Contrato | — | **Motor** | Orquesta | Mide | En U3 |
| P3 Trazabilidad | Contrato | ✅ Origen | Cita | Traza | Audit | End-to-end en U4 |
| P4 Terminación | — | Señales | — | **Caps** | Mide | En U4 |
| P5 PII | — | Redactor ✅ | — | — | Export | ✅ |
| P6 Explicabilidad | — | — | Fraude ✅ | — | Mide | En U3 |
| P7 Honestidad | Gap P7 ✅ | Gap P7 ✅ | — | — | Gap ✅ | Mantenida |

