# U3 Functional Design Plan — Cobertura Determinística & Fraude

**Unit:** U3 · Cobertura determinística · Fraude
**Components:** C5 Motor de cobertura (P2), C6 Fraude (P6/P1)
**Stories:** H-07 (motor R1-R5, LLM no decide), H-08 (cobertura negativa + cita), H-09 (fraude explicable), H-10 (fraude solo sugiere)
**Invariants:** P2 (cobertura determinística), P6 (fraude explicable), P1 (fraude no decide)

---

## Part 1: Plan Analysis & Questions

### Context
- **Inputs:** ExtraccionValidada (from U2-C2), ResultadoPoliza + Poliza (from U2-C4)
- **Outputs:** Dictamen (regla_aplicada, cláusula, resultado_cobertura, deducible_calculado), AlertaFraude (severidad, inconsistencias, explicacion)
- **Boundary:** fraud/ ≠ rules/ (no imports between modules — already verified in grafo)

### Design Checkpoints

#### Checkpoint 1: Motor R1-R5 (C5, P2 Core)
- [ ] **Rule Order & Execution Flow**

  Reglas se aplican en cascada: R1 (Vigencia) → R2 (Cobertura contratada) → R3 (Exclusiones) → R4 (Límite) → R5 (Deducible).
  
  **Q1.1 Parada temprana vs. ejecutar todas:**
  Cuando R1 (vigencia) falla, ¿paramos y retornamos NO_CUBIERTO? ¿O ejecutamos R2-R5 de todas formas para obtener contexto completo?
  
  [Answer]: 

  **Q1.2 Orden de exclusiones:**
  ¿R3 (Exclusiones) se aplica DESPUÉS de R2 (cobertura contratada)?
  Ej: si cliente contrató AUTO_COLISION pero existe exclusión "conductores menores de 25", ¿primero confirmamos cobertura, luego aplicamos exclusión?
  
  [Answer]: 

  **Q1.3 CUBIERTO_PARCIAL (cuándo se retorna):**
  ¿Retorna CUBIERTO_PARCIAL en qué caso? Ej: cobertura parcialmente contratada, o límite alcanzado parcialmente, o deducible alto?
  
  [Answer]: 

- [ ] **Cláusula Citada (P3/RULE-CTR-03, no negociable)**

  Todo Dictamen DEBE incluir (regla_aplicada, clausula_texto, clausula_id). Sin estos, contrato lo rechaza.
  
  **Q1.4 Mapeo regla→cláusula:**
  ¿Cada póliza tiene cláusulas pre-cargadas (en RAG/BD) que mapean a R1-R5? Ej: R1 Vigencia → Cláusula ID "vigencia-2026"?
  
  [Answer]: 

  **Q1.5 Cláusula no encontrada (escalamiento):**
  Si un claim califica bajo R2 (cobertura contratada) pero NO hay cláusula en la póliza que lo justifique, ¿retornamos REQUIERE_REVISION (escalamiento P4)?
  
  [Answer]: 

- [ ] **Deducible Cálculo (R5)**

  **Q1.6 Múltiples deducibles:**
  ¿Una póliza puede tener deducible por tipo de siniestro (colisión $X, robo $Y)? O es único por póliza?
  
  [Answer]: 

  **Q1.7 Deducible vs. Límite:**
  ¿El deducible se resta del límite de cobertura, o son independientes?
  Ej: límite $50M, deducible $500K, siniestro $10M → paga $10M - $500K = $9.5M?
  
  [Answer]: 

#### Checkpoint 2: Fraude (C6, P6 & P1)

- [ ] **Qué es Fraude (criterios de detección)**

  **Q2.1 Fuente de inconsistencias:**
  ¿Fraude detecta inconsistencias entre campos extraídos (C2) y póliza (C4)?
  Ej: "fecha siniestro posterior a vigencia fin", "monto solicitud > suma asegurada"?
  
  [Answer]: 

  **Q2.2 LLM en detección:**
  ¿Fraude usa LLM para razonar inconsistencias (C6→LLM), o solo reglas determinísticas?
  
  [Answer]: 

  **Q2.3 Severidad (cómo se calcula):**
  ¿AlertaFraude.severidad ∈ {BAJA, MEDIA, ALTA}? ¿Basada en conteo de inconsistencias, o en tipo?
  
  [Answer]: 

- [ ] **Evidencia Obligatoria (P6, no negociable)**

  AlertaFraude.evidencia es lista de (tipo_inconsistencia, detalles). Sin evidencia, contrato rechaza AlertaFraude.
  
  **Q2.4 Formato de evidencia:**
  AlertaFraude{severidad, inconsistencias: list[str], explicacion: str, evidencia: list[{tipo, valor_esperado, valor_extraido}]}?
  
  [Answer]: 

- [ ] **"Solo sugiere, no decide" (P1 & P6, no negociable)**

  **Q2.5 Cómo se integra con Dictamen:**
  ¿Fraude emite AlertaFraude independiente de Dictamen? ¿Ambos coexisten en Caso.dictamen y Caso.alerta_fraude?
  
  [Answer]: 

  **Q2.6 Estado terminal:**
  ¿AlertaFraude cambia Caso.estado? Ej: ¿RECHAZADO si severidad=ALTA?
  Respuesta esperada: NO (solo sugiere; U4 y humano deciden).
  
  [Answer]: 

#### Checkpoint 3: Módulo Boundaries & Integration

- [ ] **Frontera fraud/ ↔ rules/ (ya verificado grafo, confirmar aquí)**

  **Q3.1 ¿fraud/ importa rules/?**
  ¿O fraude es independiente? Ej: ¿fraude consulta Dictamen.regla_aplicada para contexto, o no?
  
  [Answer]: 

- [ ] **Inputs (campos extraídos, póliza, deducible)**

  **Q3.2 Lectura de campos:**
  ¿Motor lee numero_poliza, tipo_siniestro, monto_siniestro, fecha_siniestro vía ExtraccionValidada.campos (no plano)?
  
  [Answer]: 

  **Q3.3 ¿Qué pasa si campo ausente?:**
  Si tipo_siniestro ausente, ¿R2 (cobertura) retorna REQUIERE_REVISION? ¿O NO_CUBIERTO (fail-closed)?
  
  [Answer]: 

#### Checkpoint 4: Testing & PBT-03

- [ ] **Property-Based Testing (Hypothesis)**

  **Q4.1 Propiedades invariantes del motor:**
  - P1: Resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}
  - P2: deducible_calculado ≥ 0
  - P3: Si CUBIERTO o CUBIERTO_PARCIAL, entonces Dictamen.cláusula ≠ None
  - P4: Resultado no cambia si se ejecuta 2 veces con misma entrada
  
  ¿Hay más propiedades a probar?
  
  [Answer]: 

- [ ] **Unit Tests (determinístico, mock pólizas)**

  **Q4.2 Test cases iniciales:**
  - Vigencia válida (R1 pasa)
  - Vigencia expirada (R1 falla)
  - Cobertura no contratada (R2 falla)
  - Exclusión aplicable (R3 falla)
  - Monto > límite (R4 falla)
  - Deducible > monto (R5 falla)
  - Happy path (todas las reglas pasan)
  
  ¿Hay casos adicionales? Ej: CUBIERTO_PARCIAL?
  
  [Answer]: 

---

## Part 2: Execution Plan (Pending Answers)

Once all [Answer]: tags are filled, Functional Design will generate:

- [ ] `aidlc-docs/construction/u3/functional-design/business-logic-model.md`
  - Motor R1-R5 flow (secuencia, parada, ejecución)
  - Fraude detection logic (inconsistencies, severidad)

- [ ] `aidlc-docs/construction/u3/functional-design/business-rules.md`
  - R1-R5 formal definitions (vigencia, cobertura, exclusiones, límite, deducible)
  - Fraude scoring rules
  - Validation constraints (deducible ≥ 0, resultado ∈ enum, etc.)

- [ ] `aidlc-docs/construction/u3/functional-design/domain-entities.md`
  - Dictamen contract review (regla_aplicada, cláusula, resultado_cobertura, deducible)
  - AlertaFraude contract review (severidad, inconsistencias, explicacion, evidencia)
  - RelatedPoliza, Clausula structures

---

## Approval Gate

**User Decision Point:** After answering all [Answer]: tags,
1. Verify answers align with P2 (deterministic, no LLM), P6 (fraude explicable), P1 (no state change)
2. Confirm business rules are unambiguous
3. Approve or request clarifications

