# U3 NFR Requirements Plan — Motor R1-R5 & Fraude

**Unit:** U3 · Cobertura determinística · Fraude
**Focus Areas:** Testability (PBT-03), Performance, Reliability (P4 fail-closed), Security (P5)
**Tech Stack:** pytest + Hypothesis (property-based), deterministic mocks

---

## Part 1: NFR Assessment & Questions

### Performance Requirements

**Q1.1 Latencia del motor:**
¿Cuál es el SLA de latencia para un dictamen? Ej: motor R1-R5 debe retornar < 100ms por claim?
(Implicación: reglas son puras/sin I/O; pero fraude puede llamar LLM — ¿cómo se caps?)

[Answer]: 

---

**Q1.2 Concurrencia de claims:**
¿Motor procesa claims secuencial (1 por vez) o paralelo (N concurrentes)?
¿Hay un límite de RPS (requests per second) que el sistema debe soportar?

[Answer]: 

---

### Testability Requirements (PBT-03 Core)

**Q2.1 Coverage de Hypothesis (property-based testing):**
¿Qué % de código del motor R1-R5 debe estar cubierto por PBT (a diferencia de unit tests)?
Ej: 100% de R1-R5 funcs via PBT generators? O solo happy path + edge cases?

[Answer]: 

---

**Q2.2 Estrategia de generadores (Hypothesis strategies):**
¿Cómo se generan fixtures de polizas/claims para PBT?
- Synth-data generator de U1 (ej: factory de Poliza aleatoria)?
- Hypothesis strategies inline (st.dates(), st.integers(), etc.)?
- Combinación?

[Answer]: 

---

**Q2.3 Propiedades invariantes (PBT-03 framework):**
Las 8 propiedades identificadas en functional design (resultado ∈ enum, deducible ≥ 0, etc.) — ¿todas van a Hypothesis?
¿O algunas son solo unit tests (ej: "sin cláusula → REQUIERE_REVISION")?

[Answer]: 

---

**Q2.4 Fraude testing (LLM + determinístico):**
¿Cómo testas C6 fraude si tiene LLM Sonnet?
- Mock LLM response (determinístico para test, no real Sonnet)?
- Fixture de inconsistencias "esperadas" vs "reales"?
- PBT sobre severidad mapping (determinístico)?

[Answer]: 

---

### Reliability & Fail-Closed (P4)

**Q3.1 Escalamiento vs. invención:**
Campo ausente/cláusula no encontrada → REQUIERE_REVISION.
¿Hay un máximo de % de claims en REQUIERE_REVISION tolerable antes de alertar operacional?
Ej: si > 10% de claims escalan → alert

[Answer]: 

---

**Q3.2 Manejo de errores (LLM fraude falla):**
Si LLM Sonnet no responde (timeout, API error), ¿fraude retorna solo inconsistencias_duras?
¿O marca AlertaFraude como FALLIDA (graceful degradation)?

[Answer]: 

---

### Security & PII (P5)

**Q4.1 Redacción en fraude (LLM input):**
¿LLMPayloadBuilder de C6 redacta PII antes de enviar a Sonnet?
¿Qué se redacta: nombres, cedulas, montos (SÍ/NO)?

[Answer]: 

---

**Q4.2 Logs de motor (P5):**
¿Logs del motor contienen monto_reclamado / suma_asegurada (sensibles)?
¿Se redactan o se guardan sin redactar?

[Answer]: 

---

### Tech Stack & Implementation Strategy

**Q5.1 Framework de test:**
Pytest + Hypothesis solo, o incluyes también:
- Faker (synthetic data generation)?
- Factory Boy (fixtures)?
- Freezegun (mocking dates)?

[Answer]: 

---

**Q5.2 Fixture strategy (mocks de Poliza/Clausula):**
¿Cómo construyes fixtures reutilizables?
- Factory function `poliza_builder(vigencia=..., coberturas=..., ...)`?
- @pytest.fixture que retorna dict/Poliza mock?
- Hypothesis strategies que generan Poliza?

[Answer]: 

---

**Q5.3 Database mocking (si hay):**
¿Motor accede a BD para lookup de Clausula por tipo, o todo en memoria (contract Poliza.clausulas)?

[Answer]: 

---

### Maintainability & Documentation

**Q6.1 Code comments en motor:**
¿Reglas R1-R5 deben tener docstrings con ej. de input/output?
Ej: "R1: fecha debe ∈ [vigencia.desde, vigencia.hasta]; si no, early exit."

[Answer]: 

---

**Q6.2 Test documentation (por estrato):**
¿Cada test tiene docstring explicando qué propiedad/caso representa?
Ej: `def test_r1_vigencia_expirada(): """R1 early exit: vigencia expired → NO_CUBIERTO R1 cited."""`

[Answer]: 

---

## Part 2: Execution Plan (Pending Answers)

Once all [Answer]: tags are filled, NFR Requirements will generate:

- [ ] `aidlc-docs/construction/u3/nfr-requirements/nfr-requirements.md`
  - Performance SLAs (latencia, RPS, concurrencia)
  - Testability targets (% PBT, coverage)
  - Reliability thresholds (max % REQUIERE_REVISION before alert)
  - Security & PII redaction policy

- [ ] `aidlc-docs/construction/u3/nfr-requirements/tech-stack-decisions.md`
  - pytest + Hypothesis rationale
  - Fixture strategy (factory vs. fixture vs. strategies)
  - LLM mocking approach (fraude testing)
  - Logging & redaction strategy

---

## Approval Gate

**User Decision Point:** After answering all [Answer]: tags,
1. Verify testability (PBT-03) targets are clear
2. Confirm performance SLAs compatible with P4 (fail-closed, no loops)
3. Approve or request adjustments

