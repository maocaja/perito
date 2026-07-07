# U3 NFR Requirements — Performance, Testability (PBT-03), Reliability, Security

**Unit:** U3 · Cobertura determinística · Fraude
**Approved Answers:** User-provided, 6 invariants enforced, P7 honest

---

## Performance Requirements

### Motor R1-R5 (Función Pura)

**Latency:**
- Sub-millisecond (no I/O, pure functions)
- **N/A SLA duro** (P7: se mide, no se promete; portafolio, una persona)

**Fraude (LLM):**
- Segundos (Sonnet call), acotado por MAX_TOKENS_BUDGET (P4, no SLA)

**Concurrency:**
- **N/A RPS de producción** (P7: motor stateless/paralelizable, pero no target prometido)
- Throughput dataset eval = build-time (U5), no RPS prod

---

## Testability Requirements — PBT-03 CORE 🔒

### Property-Based Testing (Hypothesis)

**Coverage Target:** 🔒 **100% del motor R1-R5 vía PBT**
- R1-R5 son funciones puras determinísticas = caso ideal para property-based (RNF-05)
- Invariantes deben sostenerse para TODO input generado, no solo happy path
- Propiedades universales cubierta por PBT:
  1. `resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}`
  2. `deducible_calculado ≥ 0`
  3. `deducible_calculado ≤ min(monto, suma_asegurada)`
  4. Si CUBIERTO/CUBIERTO_PARCIAL → `clausula ≠ None` (RULE-CTR-03, P3)
  5. Idempotencia: `f(x) = f(x)` siempre
  6. Orden invariante: permutar R1-R5 no cambia resultado
  7. R1 falla ⇒ `resultado = NO_CUBIERTO`, cita R1
  8. Campo ausente → `resultado = REQUIERE_REVISION`

**Unit Tests (Complementarias):**
- Casos de cita-regla específicos ("R1 expirada → NO_CUBIERTO R1", etc.)
- Edge cases determinísticos

### Fraude Testing

**LLM Mocking:** 🔒 Determinístico, sin Sonnet real en tests (como C2/C3)
**PBT Coverage:**
- Inconsistencias duras (código) → PBT de severidad mapping
- Partes determinísticas (severidad ∈ {BAJA, MEDIA, ALTA}) → property sobre mapeo fijo
**Unit Assertions:**
- AlertaFraude no muta `Caso.estado` (P1)
- `inconsistencias ≠ vacío` (P6, evidencia obligatoria)
- Redacción aplicada antes de Sonnet (P5)

---

## Reliability Requirements (P4 Fail-Closed)

### Escalamiento vs. Invención

**Campo Ausente / Cláusula No Encontrada:**
- → `REQUIERE_REVISION` (escalar, no inventar)
- **N/A umbral alerta operacional duro** (P7: ops de producción)
- Tasa escalamiento = métrica U5 evals (proxy calidad extracción/cobertura), reportada honesta

### LLM Fraude Error Handling 🔒

**Graceful Degradation:**
- Si Sonnet falla (timeout, API error):
  - Retorna `AlertaFraude` válida CON solo inconsistencias determinísticas (degradada)
  - Loguea fallo (no crashea el caso)
  - **NO bloquea cobertura** (P2 independiente, fraude no es gating)

---

## Security Requirements (P5)

### PII Redaction — LLM Input 🔒

**Redactado:**
- Nombres, cédulas, direcciones, teléfonos, emails

**NO redactado:**
- Montos (`monto_reclamado`, `suma_asegurada`)
- Rationale: operacionales, no PII; fraude necesita "monto > suma" para razonar

**Implementation:**
- LLMPayloadBuilder + `redact_pii_spans_es_co()` (mismo que C2/C3)

### Logging Policy

**Motor (Dictamen):**
- Loguea: resultado, regla_aplicada, clausula (sin PII)
- Montos permitidos en logs (no PII)

**PII en eventos:**
- Usa `PIIRedactingLogSerializer` para eventos estructurados con riesgo PII
- `texto_crudo` NUNCA al log crudo

---

## Validation Checklist (Pre-Code-Gen)

- [ ] Motor R1-R5 es función pura (cero I/O, cero BD)
- [ ] 100% PBT coverage via Hypothesis strategies
- [ ] Fraude mocks LLM, asserts P1/P6/P5
- [ ] Redacción: nombres/cedulas SI, montos NO
- [ ] Graceful LLM degradation
- [ ] Docstrings R1-R5 + tests documentados
- [ ] Cero deps nuevas (pytest + Hypothesis only)

