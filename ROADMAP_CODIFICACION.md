# 🗺️ ROADMAP COMPLETO DE CODIFICACIÓN — Perito

**Proyecto:** Perito (copiloto agéntico de admisión de siniestros)  
**Estación actual:** 5 (CONSTRUCTION)  
**Estado:** U1 ✅ VERDE  

---

## 📋 ÍNDICE DEL ROADMAP

1. **U1 — Fundaciones & Contratos** (✅ COMPLETADA)
2. **U2 — Extracción·Verificación·Grounding** (PRÓXIMA — con LLM + P5 redaction + P4 verificación)
3. **U3 — Cobertura·Fraude** (DESPUÉS de U2 — **AQUÍ está R1-R5 motor determinístico** + fraude signals)
4. **U4 — Orquestación·Terminación·HITL** (DESPUÉS de U3 — máquina de estados + P1 cierre)
5. **U5 — Observabilidad·Evals·Red-team** (PARALELO con U2-U4 — **CRÍTICO para Must #11/#13**)
6. **Estación 6** (DESPUÉS de U1 verde)
7. **Estación 7** (DESPUÉS de Estación 6)
8. **Estación 8** (DESPUÉS de todas las unidades)

---

## ✅ U1 — FUNDACIONES & CONTRATOS (Estación 5 / Code Generation) — COMPLETADA

**Historias:** H-16, H-17  
**Objetivo:** Contratos Pydantic + generador sintético + RAG estructura  

### ✅ TANDA A (Steps 1-3) — COMPLETADA

```
Step 1: Project Structure Setup
  ├─ Crear backend/ árbol
  ├─ pyproject.toml (deps aprobadas: pydantic, pytest, hypothesis, faker, psycopg)
  └─ .env.example (sin secrets reales)
  Salida: √ pyproject.toml, √ backend/__init__.py

Step 2: Config & Secrets
  ├─ app/config.py (Settings strict, EMBEDDING_DIM param, DATABASE_URL sin default)
  └─ Sin pydantic-settings (una sola dep nueva = NO)
  Salida: √ app/config.py (strict=True, frozen=True)

Step 3: Business Logic — Contracts
  ├─ app/contracts/__init__.py (Contract base: strict=True, extra="forbid")
  ├─ app/contracts/enums.py (EstadoCaso, ResultadoCobertura, RolUsuario, etc)
  ├─ app/contracts/pii.py (Marcador PII + pii_fields() introspectable)
  ├─ app/contracts/poliza.py (RangoFechas, Clausula, Poliza, ResultadoPoliza)
  ├─ app/contracts/extraccion.py (CampoExtraido, ExtraccionValidada, AvisoNormalizado)
  ├─ app/contracts/dictamen.py (Dictamen, AlertaFraude, Cotas)
  ├─ app/contracts/dataset.py (FilaEntrada, GroundTruth)
  ├─ app/contracts/money.py (Tipo monetario Decimal, sin float)
  └─ app/contracts/caso.py (Caso, Usuario — P1 HITL, frozen, validador)
  Salida: √ 9 contratos con validadores, P1-P6 implementados
```

**Commit:** 77333c6 (fix P1)

### ✅ TANDA B (Steps 4-6) — COMPLETADA + BUGS ARREGLADOS

```
Step 4: Business Logic — Security/Redaction
  ├─ app/security/__init__.py
  └─ app/security/redaction.py
      ├─ PIIRedactingLogSerializer (redacta logs, deny-by-default)
      └─ LLMPayloadBuilder (construye prompts al LLM sin PII) ← P5 PATTERN-U1-01
  Salida: √ PATTERN-U1-01 (P5) realizado, type hints + isinstance() validation

Step 5: Business Logic — Synthetic Generator
  ├─ app/synthetic/__init__.py
  ├─ app/synthetic/adapters.py (KaggleAdapter: FilaEntrada abstracto, validación fail-closed)
  └─ app/synthetic/generator.py
      ├─ SyntheticCaseGenerator (genera casos + fraude encodado)
      ├─ _generate_inconsistency() (diversifica 4 tipos: SPAN/AMOUNT/COVERAGE/EXCLUSION)
      └─ ASSERTION FAIL-CLOSED (fraude sin inconsistencia → rompe, RULE-GEN-02 🔒)
  Salida: √ RULE-GEN-02 + RULE-GEN-03 realizados, inconsistencias diversificadas

Step 6: Repository — RAG Schema
  ├─ app/rag/__init__.py
  └─ app/rag/schema.py
      ├─ RAGSchema.build_metadata(embedding_dim)  ← PATTERN-U1-03 (NO hardcodeada)
      ├─ get_rag_connection_string()
      └─ init_rag_schema()  ← SQLAlchemy 2.0+ compatible (sin append_column deprecated)
  Salida: √ PATTERN-U1-03 (dimensión parametrizada)
```

**Commits:** 0d46cf7 (Tanda B), 47d65c8 (fixes Tanda B)

### ✅ TANDA C (Steps 7-10) — COMPLETADA

```
Step 7: API Scaffold
  └─ app/main.py (FastAPI mínimo, health check)
  Salida: √ app/main.py (HTTP endpoint básico)

Step 8: Unit Tests
  ├─ tests/__init__.py
  ├─ tests/generators.py (generadores Hypothesis por tipo)
  ├─ tests/test_contracts_roundtrip.py (PBT round-trip, NFR-U1-01)
  ├─ tests/test_contracts_invariants.py (PBT invariantes, NFR-U1-03)
  ├─ tests/test_validation_failclosed.py (pytest, validación fail-closed, NFR-U1-02)
  ├─ tests/test_generator_failclosed.py (pytest, generador fail-closed, RULE-GEN-02)
  └─ tests/test_redaction_denybydefault.py (pytest, PII redactada, PATTERN-U1-01)
  Salida: √ tests/ con cobertura 100% de reglas (pytest + hypothesis)
  Exit criteria: 21/21 tests pasan, 0 malformados aceptados ✅

Step 9: Deployment Artifacts (dev-env)
  ├─ docker-compose.yml (postgres/pgvector + langfuse local)
  ├─ .github/workflows/test.yml (CI básico: pytest + lint) ← en scratchpad, pendiente permiso
  ├─ .env.example (actualizar con envs de docker-compose)
  └─ .gitignore (actualizar: venv/, .pytest_cache/, .coverage)
  Salida: √ docker-compose up → postgres + langfuse + app en localhost

Step 10: Documentation
  └─ aidlc-docs/construction/u1-fundaciones-contratos/code/code-summary.md
      ├─ Resumen de archivos creados
      ├─ Cómo correr tests (`pytest tests/`)
      ├─ Cómo levantar docker-compose
      └─ Notas sobre U2 (extracción): qué espera
  Salida: √ code-summary.md (HOW_TO_TEST.md)

Artefactos de diseño (commit f33d44b):
  ├─ plans/ (5 planes de actividades por unidad)
  ├─ functional-design/ (domain-entities, business-rules, business-logic-model)
  ├─ nfr-requirements/ (8 NFRs aplicables, tech-stack-decisions)
  ├─ nfr-design/ (componentes lógicos, patrones)
  └─ infrastructure-design/ (arquitectura deployment)
  Salida: √ artefactos de AI-DLC preservados para cosecha a specs/aidlc/
```

**Commits:** dfaf304 (Tanda C), 31b910a (fix U1 fundación), f33d44b (docs), 47d65c8 (fixes), 0e0edf1 (revert app/llm)

**Condiciones de salida (U1 VERDE):** ✅
- ✅ Todos los tests pasan (21/21 pytest + hypothesis)
- ✅ Cobertura: 100% de reglas en business-rules.md
- ✅ Fail-closed: 0 malformados aceptados
- ✅ Docker-compose levanta sin errores
- ✅ Invariantes P1-P6 verificadas por tests
- ✅ Rama consistente (contratos trackeados, mensajes honestos)

---

## 🔵 U2 — EXTRACCIÓN·VERIFICACIÓN·GROUNDING (PRÓXIMA — Estación 5, después de U1 verde)

**Historias:** H-02 (extractor + campo faltante)  
**Dependencias:** Requiere U1 (contratos, redactores, generador)  
**Objetivo:** LLM extrae campos del aviso, redactado (P5), verificación (P4), grounding en póliza

**Invariantes críticas:**
- **P1:** Extractor NO decide siniestro, solo sugiere (no muta estado terminal)
- **P4:** NO inventar campos (ausente=True ⇒ valor=None)
- **P5:** PII redactada deny-by-default ANTES de enviar al LLM

### Flujo previo a Code Generation:

```
GATE: Functional Design (como U1)
  ├─ domain-entities.md (Extractor agent, ExtractorResult, VerificationResult)
  ├─ business-rules.md (RULE-EXT-01..05 sobre campos + confianza + verificación)
  ├─ business-logic-model.md (flujos E2E + decisiones)
  └─ NFR Requirements (accuracy, speed, recall, campos inventados ≈0)
  
APROBACIÓN REQUERIDA antes de Code Gen
```

### Code Generation Steps (10 Tandas):

```
Actividad 5: Code Generation
  Step 1: Project Structure (reusa backend/, solo tests/extraction/)
  Step 2: Config (heredado de U1)
  Step 3: Domain Models (Extractor, ExtractorResult, VerificationResult)
  Step 4: LLM Client + Redaction
      └─ Usa LLMPayloadBuilder de U1 (redacta PII)
      └─ Construye prompt con campos esperados (P4 validación)
  Step 5: Extraction Logic
      └─ Llama Claude Haiku (model económico)
      └─ Genera EvidenciaOrigen para cada campo
      └─ Marca ausentes explícitamente (no inventar)
  Step 6: Verification & Grounding
      └─ Valida extracción contra póliza buscada
      └─ Prepara para U3
  Step 7: Repository (almacena extractos)
  Step 8: API (POST /cases/{id}/extract)
  Step 9: Unit Tests
      ├─ Mock LLM con respuestas tipadas
      ├─ Round-trip (aviso → extracción → aviso)
      ├─ P4: campos inventados rechazados
      └─ P5: PII redactada en entrada
  Step 10: Documentation

Salida: √ Extractor LLM + tests + API
        √ Caso.extraccion populado + listo para U3
```

**Ruta crítica:** U1 ✅ → U2 → U3

---

## 🟡 U3 — COBERTURA·FRAUDE (Estación 5, después de U2 verde)

**Historias:** H-03 (cobertura), H-09 (fraude)  
**Dependencias:** U1 (contratos, pólizas) + U2 (campos extraídos)  
**Objetivo:** Motor de reglas determinístico (R1-R5) + detección de fraude con evidencia

**REGLAS AQUÍ (NO en U4):**
- **R1:** Vigencia (fecha siniestro ∈ RangoFechas póliza)
- **R2:** Cobertura (tipo siniestro ∈ coberturas_contratadas)
- **R3:** Exclusiones (¿aplica alguna exclusión?)
- **R4:** Límite (monto_reclamado ≤ suma_asegurada)
- **R5:** Deducible (calculado correctamente)

**Invariante crítica:**
- **P2:** R1-R5 son determinísticos, CERO aristas LLM (rules engine puro)

### Flujo previo a Code Generation:

```
GATE: Functional Design
  ├─ domain-entities.md (RulesEngine, CoberturaDictamen, FraudDetector)
  ├─ business-rules.md (RULE-COV-R1..R5, RULE-FRAUD-01..03)
  ├─ business-logic-model.md (decisiones por estrato)
  └─ NFR Requirements (accuracy cobertura vs etiqueta, precision/recall fraude)
  
APROBACIÓN REQUERIDA antes de Code Gen
```

### Code Generation Steps (10 Tandas):

```
Actividad 5: Code Generation
  Step 1-2: Project Structure + Config (heredados)
  Step 3: Domain Models (RuleEngine, FraudDetector, CoberturaDictamen)
  Step 4-5: Rules Implementation
      ├─ backend/app/rules/r1_vigencia.py (fecha_siniestro ∈ vigencia)
      ├─ backend/app/rules/r2_cobertura.py (tipo siniestro contratado)
      ├─ backend/app/rules/r3_exclusiones.py (¿exclusión aplica?)
      ├─ backend/app/rules/r4_limite.py (monto ≤ suma_asegurada)
      └─ backend/app/rules/r5_deducible.py (deducible aplicado)
      └─ TODAS las reglas DETERMINÍSTICAS, sin LLM
  Step 6: Fraud Detection
      ├─ backend/app/fraud/detector.py (identifica inconsistencias)
      └─ backend/app/fraud/scoring.py (severidad de alerta)
  Step 7: Repository
  Step 8: API (POST /cases/{id}/evaluate-coverage, POST /cases/{id}/detect-fraud)
  Step 9: Unit Tests
      ├─ Reglas con datos sintéticos variados
      ├─ Fraude scoring con inconsistencias diversas
      └─ Cobertura vs etiqueta ground truth
  Step 10: Documentation

Salida: √ Rules engine (R1-R5) determinístico
        √ Fraud detector + scoring
        √ Caso.dictamen + Caso.alerta_fraude populados
```

**Protección:** backend/app/rules/ está protegido por hook (no se toca salvo autorización P2)

**Ruta crítica:** U1 ✅ → U2 → U3 → U4

---

## 🟠 U4 — ORQUESTACIÓN·TERMINACIÓN·HITL (Estación 5, después de U3 verde)

**Historias:** H-11 (HITL), H-12 (P1 test), H-18 (orquestación)  
**Dependencias:** U1 (Caso, validadores) + U2 (Extractor) + U3 (Rules, Fraud)  
**Objetivo:** Máquina de estados LangGraph + aprobación humana + P1 Capa 2

**Invariante crítica:**
- **P1 Capa 2:** transition_to_terminal(caso, aprobado_por) valida aprobado_por ANTES de model_copy

### Flujo previo a Code Generation:

```
GATE: Functional Design
  ├─ domain-entities.md (CaseOrchestrator, StateMachine, ApprovalRequest)
  ├─ business-rules.md (transiciones de estado, P1 en capas)
  ├─ business-logic-model.md (decisiones de escalamiento)
  └─ NFR Requirements (latencia orquestación, loops detectados)
  
APROBACIÓN REQUERIDA antes de Code Gen
```

### Code Generation Steps (10 Tandas):

```
Actividad 5: Code Generation
  Step 1-2: Project Structure + Config (heredados)
  Step 3: Domain Models (CaseOrchestrator, StateMachine, ApprovalRequest)
  Step 4: State Transitions
      └─ backend/app/hitl/transition.py
          ├─ transition_to_terminal(caso, estado, aprobado_por) ← P1 Capa 2
          ├─ Valida aprobado_por ≠ None ANTES de model_copy
          └─ Lanza ValueError si no cumple
  Step 5: Approval Service
      └─ backend/app/hitl/approval.py
          ├─ Usuario firma → genera aprobación
          └─ AuditLog registra decisión + timestamp
  Step 6: Orchestrator (LangGraph)
      └─ backend/app/orchestrator/orchestrator.py
          ├─ Nodo 1: Extractor (U2)
          ├─ Nodo 2: Rules + Fraud (U3)
          ├─ Nodo 3: Verificación (¿terminal?)
          ├─ Nodo 4: Escalamiento (REQUIERE_REVISION)
          ├─ Respeta max_rondas + presupuesto_tokens (P4)
          └─ Ciclo detectado: lanza error (sin loop infinito)
  Step 7: API (POST /cases, GET /cases/{id}, POST /cases/{id}/approve)
  Step 8: Unit Tests
      ├─ Transiciones de estado válidas
      ├─ P1 cierre: aprobado_por requerido para terminal
      ├─ P4: max_rondas respetadas
      └─ Orquestación E2E con casos sintéticos
  Step 9: Deployment Artifacts
  Step 10: Documentation

Salida: √ Orquestador LangGraph
        √ HITL machine + P1 Capa 2 cerrada
        √ Caso.estado = APROBADO/RECHAZADO/REQUIERE_REVISION + aprobado_por
```

**Invariante P1:** transition_to_terminal() valida aprobado_por ANTES de tocar Caso (Capa 2, cierre)

**Ruta crítica:** U1 ✅ → U2 → U3 → U4 (CRÍTICA, lineal)

---

## 🟣 U5 — OBSERVABILIDAD·EVALS·RED-TEAM (Paralelo con U2-U4, final — CRÍTICO PARA MUST #11/#13)

**Historias:** H-13 (logging), H-14 (audit), H-15 (RAG), H-31 (evals)  
**Dependencias:** U1 (contratos) + todas las demás (produce artefactos de test)  
**Objetivo:** Logging sin PII + evals framework por estrato + golden datasets + red-team

**ESTO NO ES OPCIONAL:** Must #11 (automedible) y Must #13 (dataset consistent) dependen de U5

### Flujo previo a Code Generation:

```
GATE: Functional Design
  ├─ domain-entities.md (Logger, Evaluator, EvalResult, RedTeamTest)
  ├─ business-rules.md (RULE-LOG-01..03, RULE-EVAL-01..07, RULE-REDTEAM-01..02)
  ├─ business-logic-model.md (evals por estrato, scoring de riesgos)
  └─ NFR Requirements (cobertura de estratos, precision de métricas)
  
APROBACIÓN REQUERIDA antes de Code Gen
```

### Code Generation Steps (10 Tandas):

```
Actividad 5: Code Generation
  Step 1-2: Project Structure + Config (heredados)
  Step 3: Domain Models (AuditEvent, EvalResult, EvalMetric, RedTeamCase)
  Step 4: Logging & Audit
      └─ backend/app/logging/audit_logger.py
          ├─ Eventos JSON estructurados
          ├─ Redacción automática de PII (usa redactores de U1)
          ├─ Almacenamiento en PostgreSQL (audit_log table)
          └─ Trazabilidad completa: Caso → decisión → usuario
  Step 5: RAG Indexing
      └─ backend/app/rag/indexer.py
          ├─ Indexa cláusulas de pólizas
          ├─ Embeddings locales (sentence-transformers, sin API)
          └─ Búsqueda vectorial en PostgreSQL+pgvector
  Step 6: Evaluation Framework
      └─ backend/app/evals/evaluator.py
          ├─ 7 estratos de evaluación (de spec/prd.md Segmento 11):
          │   1. happy: caso sin fraude, cobertura clara
          │   2. campos-faltantes: debe escalar a REQUIERE_REVISION
          │   3. poliza-no-encontrada: grounding falla, escala
          │   4. cobertura-negativa: R1-R5 rechaza, decide motor
          │   5. fraude: AlertaFraude disparada, escala
          │   6. SOAT: regla especial, excluida de cobertura
          │   7. documento-sucio: CalidadDoc.SUCIO, verifica verificación
          ├─ Métricas por estrato:
          │   - Accuracy (coincide resultado vs ground truth)
          │   - Precision/Recall (fraude detection)
          │   - Campos inventados ≈ 0 (P4 verificación)
          │   - Trazabilidad (cada decisión cita regla + cláusula)
          └─ Golden datasets: casos etiquetados con inconsistencias encodadas
  Step 7: Red-Team (adversarial testing)
      └─ backend/app/redteam/generator.py
          ├─ Genera casos límite (borderline cobertura)
          ├─ Casos de adversarios (tratar de engañar extractor/rules)
          └─ Casos de estrés (max montos, múltiples exclusiones)
  Step 8: Unit Tests + Integration Tests
      ├─ tests/evals/test_happy_path.py
      ├─ tests/evals/test_campos_faltantes.py
      ├─ tests/evals/test_poliza_no_encontrada.py
      ├─ tests/evals/test_cobertura_negativa.py
      ├─ tests/evals/test_fraude.py
      ├─ tests/evals/test_soat.py
      ├─ tests/evals/test_documento_sucio.py
      └─ tests/redteam/ (casos adversarios)
      Salida: √ 7 estratos testados, golden datasets con inconsistencias encodadas
  Step 9: Deployment Artifacts
      └─ Langfuse configurado (ya en docker-compose de U1)
      └─ Dashboard de métricas (POST /metrics)
  Step 10: Documentation
      └─ Guía de evals (cómo añadir casos, cómo interpretar métricas)

Salida: √ Logging fail-closed (sin PII)
        √ Evals framework (7 estratos + métricas)
        √ Golden datasets (casos etiquetados, inconsistencias encodadas)
        √ Red-team cases (adversarial)
        √ Dashboard de métricas
        ✓ MUST #11 satisfecho: sistema automedible
        ✓ MUST #13 satisfecho: dataset consistente
```

**Parallelizable:** U5 no depende de U2/U3/U4 en código, solo en artefactos generados (pueden correr en paralelo)

---

## 📊 ORDEN GLOBAL DE EJECUCIÓN

```
FASE 1: Fundación (U1) ✅ COMPLETADA
  Tanda A (P1 fix)        → Commit 77333c6
  Tanda B (Security+Gen)  → Commit 0d46cf7 + fixes 47d65c8
  Tanda C (Tests+Docker)  → Commit dfaf304 + recovery 31b910a + docs f33d44b
  Revert app/llm          → Commit 0e0edf1
  [U1 VERDE] ✅ Gate PASSED

FASE 2: Ruta crítica en secuencia (U2 → U3 → U4)
  U2 Extracción·Verificación·Grounding
      Functional Design → Code Gen Steps 1-10
      [U2 VERDE] ← Gate
      Entrega: Caso.extraccion populado
  
  U3 Cobertura·Fraude (R1-R5 AQUÍ, NO en U4)
      Functional Design → Code Gen Steps 1-10
      [U3 VERDE] ← Gate
      Entrega: Caso.dictamen + Caso.alerta_fraude populados
  
  U4 Orquestación·Terminación·HITL
      Functional Design → Code Gen Steps 1-10
      [U4 VERDE] ← Gate (SISTEMA INTEGRADO)
      Entrega: Caso.estado (APROBADO/RECHAZADO/REQUIERE_REVISION) + aprobado_por

FASE 3: Observabilidad (paralelo con FASE 2, final)
  U5 Observabilidad·Evals·Red-team
      Functional Design → Code Gen Steps 1-10
      [U5 VERDE]
      Entrega: Logging + Evals framework (7 estratos) + Red-team
      ✓ MUST #11 y #13 satisfechos

FASE 4: Estación 6 (DESPUÉS de U1 verde ✅)
  Setup arnés, AGENTS.md, orquestación conceptual
  
FASE 5: Estación 7 (DESPUÉS de todas las unidades)
  OpenSymphony/Linear, orquestación de trabajo, code review

FASE 6: Estación 8 (FINAL)
  Testing exhaustivo (Playwright E2E, Persona+Juez, golden datasets)
```

---

## 📈 RESUMEN DE ARCHIVOS POR UNIDAD

### U1 (✅ COMPLETADA)
```
app/contracts/       9 archivos (enums, pii, poliza, extraccion, dictamen, dataset, caso, money)
app/security/        redaction.py (2 clases, type hints + isinstance)
app/synthetic/       adapters.py (validación fail-closed), generator.py (4 inconsistencies)
app/rag/             schema.py (SQLAlchemy 2.0+ compatible)
app/config.py        Settings strict
pyproject.toml       Deps (NO anthropic)
tests/               6 archivos (round-trip, invariantes, fail-closed, redaction, generator)
docker-compose.yml   postgres/pgvector + langfuse
.github/workflows/   test.yml (CI, en scratchpad)
aidlc-docs/          construction/ con planes + diseño
```
Total U1: ~30 archivos (TERMINADO)

### U2 (Próxima — Extracción·Verificación·Grounding)
```
app/extraction/      extractor.py, verification.py, client.py (~4 archivos)
app/llm/             __init__.py (get_anthropic_client factory) ← AQUÍ va, NO en U1
tests/extraction/    ~6 tests (redaction, P4 verification, grounding)
```
Total U2: ~10 archivos

### U3 (Cobertura·Fraude — R1-R5 AQUÍ)
```
app/rules/           r1_vigencia.py, r2_cobertura.py, r3_exclusiones.py, r4_limite.py, r5_deducible.py (~5)
app/fraud/           detector.py, scoring.py (~2)
tests/coverage/      ~5 tests
tests/fraud/         ~5 tests
```
Total U3: ~12 archivos

### U4 (Orquestación·Terminación·HITL)
```
app/hitl/            transition.py (P1 Capa 2), approval.py (~2)
app/orchestrator/    orchestrator.py (LangGraph) (~1)
tests/hitl/          ~5 tests
tests/orchestrator/  ~5 tests
```
Total U4: ~8 archivos

### U5 (Observabilidad·Evals·Red-team — CRÍTICO)
```
app/logging/         audit_logger.py (~1)
app/evals/           evaluator.py (~1)
app/rag/             indexer.py (~1)
app/redteam/         generator.py (~1)
tests/evals/         ~7 tests (7 estratos)
tests/redteam/       ~3 tests
tests/integration/   ~3 tests
```
Total U5: ~17 archivos

---

## 🎯 Próximas Acciones

**Ahora (después de U1 ✅):**
1. ✅ Revertir app/llm/ de U1 (commit 0e0edf1) → mover a U2
2. ✅ Corregir roadmap (este archivo) → alineado con unit-of-work.md
3. Esperar aprobación de usuario

**Cuando arranque U2:**
1. Functional Design gate (como U1)
2. Mi review + aprobación
3. Code Gen Tandas A/B/C

---

**CRÍTICO:** Sin U5 (Observabilidad·Evals·Red-team), los Musts #11 (automedible) y #13 (dataset) se pierden.
