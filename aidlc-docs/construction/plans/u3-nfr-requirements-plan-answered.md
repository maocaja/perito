# U3 NFR Requirements Plan — ANSWERED

**Unit:** U3 · Cobertura determinística · Fraude
**Answers:** User provided, 6 invariants marked 🔒, N/A honest (P7)

---

## Performance — ANSWERED

**Q1.1 Latencia del motor:**
[Answer]: Motor R1-R5 es función pura sin I/O → sub-milisegundo, trivial. Sin SLA duro (P7, se mide no se promete). Fraude llama LLM → segundos, acotado por MAX_TOKENS_BUDGET (cap P4), no SLA.

**Q1.2 Concurrencia de claims:**
[Answer]: N/A honesto (P7). Portafolio, una persona — no hay target RPS de producción. Motor es puro/stateless (paralelizable trivial), pero no se promete RPS. Throughput dataset de eval = build-time (U5), no RPS prod.

---

## Testability (PBT-03 Core) — ANSWERED

**Q2.1 Coverage de Hypothesis:** 🔒 INVARIANTE
[Answer]: 100% del motor R1-R5 vía PBT. Función pura determinística = caso ideal PBT (RNF-05 "100% por construcción"). No solo happy — invariantes deben sostenerse para todo input generado. Unit tests para casos de cita-regla específicos.

**Q2.2 Estrategia de generadores:** 🔒 INVARIANTE
[Answer]: Estrategias Hypothesis (st.dates, st.decimals, st.sampled_from) para PBT — NO Faker en @given (rompe shrinking/seed, PBT-08). Faker U1 = dataset eval, NO property tests. Sepáralos.

**Q2.3 Propiedades invariantes (PBT-03):**
[Answer]: Invariantes universales (resultado∈enum, deducible≥0, cláusula≠None, determinismo, orden-invariante) → PBT. Comportamientos de cita específicos ("sin cláusula → REQUIERE_REVISION", "R1 expirada → NO_CUBIERTO R1") → unit. Ambos.

**Q2.4 Fraude testing (LLM):** 🔒 INVARIANTE
[Answer]: Mock LLM determinístico (sin Sonnet real en tests), como C2/C3. Partes determinísticas (inconsistencias duras, severidad) → PBT/unit. Assert: fraude no muta Caso.estado, evidencia obligatoria, redacción aplicada.

---

## Reliability (P4) — ANSWERED

**Q3.1 Escalamiento vs. invención:**
[Answer]: Sin umbral alerta operacional duro (P7 = ops producción). Tasa escalamiento = métrica U5 evals (proxy calidad extracción/cobertura), reportada honesta, no SLA.

**Q3.2 LLM fraude falla:** 🔒 INVARIANTE
[Answer]: Degradación graceful: si Sonnet falla (timeout/error), fraude retorna solo inconsistencias determinísticas (AlertaFraude válida, degradada) + loguea fallo. NO crashea — fraude no es gating, LLM caída no bloquea cobertura (P2 independiente).

---

## Security (P5) — ANSWERED

**Q4.1 Redacción en fraude (LLM input):** 🔒 INVARIANTE
[Answer]: Sí, LLMPayloadBuilder redacta antes de Sonnet. Redacta: nombres, cédulas, direcciones, teléfonos, emails. NO redacta: montos (operacionales, no PII — razonamiento fraude los necesita: "monto > suma"). Mismo redact_pii_spans_es_co.

**Q4.2 Logs de motor:**
[Answer]: Montos no son PII → van en logs. Nunca crudo al log: texto_crudo (tiene PII). Motor loguea dictamen (resultado, regla, cláusula) — sin PII. Usa PIIRedactingLogSerializer para eventos estructurados con riesgo PII.

---

## Tech Stack — ANSWERED

**Q5.1 Framework de test:**
[Answer]: pytest + Hypothesis, cero deps nuevas. NO freezegun ni Factory-Boy. Para testear R1 vigencia, inyecta fecha referencia (hoy) al motor en vez de freezegun — más limpio, sin dep. Faker queda en U1 synthetic, fuera PBT.

**Q5.2 Fixture strategy:**
[Answer]: Factory functions (poliza_builder(vigencia=…, coberturas=…, clausulas=…)) para unit + estrategias Hypothesis para PBT. No Factory-Boy.

**Q5.3 Database mocking:** 🔒 INVARIANTE
[Answer]: Motor NO accede a BD. Lee Clausula desde ResultadoPoliza.poliza.clausulas (in-memory, contrato C4). Eso lo hace función pura (P2) — cero I/O, cero DB. BD mocking N/A.

---

## Maintainability — ANSWERED

**Q6.1 Code comments en motor:**
[Answer]: Sí, docstrings R1-R5: regla + input/output + comportamiento cita/early-exit (auditabilidad = diferenciador P3).

**Q6.2 Test documentation:**
[Answer]: Sí, docstring por test nombrando propiedad/caso/estrato (convención rules/testing.md).

---

## INVARIANTES CONFIRMADOS (6 🔒)

1. **Q2.1:** 100% motor R1-R5 vía PBT (función pura ideal)
2. **Q2.2:** Estrategias Hypothesis, NO Faker en @given (preserva shrinking/seed)
3. **Q2.4:** Mock LLM determinístico + assert no-muta-estado + evidencia obligatoria
4. **Q3.2:** Degradación graceful si LLM falla (no crashea, retorna degradada)
5. **Q4.1:** Redacta nombres/cédulas/direcciones, NO montos (operacionales)
6. **Q5.3:** Motor puro sin BD (in-memory Clausula, P2 foundation)

## N/A HONEST (P7)

- SLA latencia duro (se mide, no se promete)
- RPS producción (portafolio, una persona)
- Alertas escalamiento prod (métrica U5, no SLA)

