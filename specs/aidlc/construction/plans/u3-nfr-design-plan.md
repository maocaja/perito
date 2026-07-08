# U3 NFR Design Plan — Motor R1-R5 Algoritmo, Fraude Determinístico, Decimal Redondeo

**Unit:** U3 · Cobertura determinística · Fraude
**Design Focus:** Paso único sin loops, función pura, Decimal determinístico, cláusula/exclusiones orden fijo
**Vigilancia usuario:** Motor determinístico (PBT-03 sostenible), Fraude determinístico con LLM mockeable

---

## Part 1: NFR Design Assessment & Questions

### Motor R1-R5: Paso Único, Función Pura

**Q1.1 Estructura del motor (sin loops):**
¿Cómo se especifica el motor para garantizar paso único R1→R5 (determinístico, no iterativo)?

[Answer]: Cada Rx = función pura independiente (_r1_vigencia(...) -> ResultadoRegla). Caller secuencial con early-exit en R1/R2/R3 (falla → Dictamen citando esa regla); R4/R5 siempre computan (para CUBIERTO_PARCIAL). Cero loop/retry — falla-es-falla, paso único.

---

**Q1.2 Aritmética de dinero (Decimal + redondeo):**
Decimal es tipo en contratos (✅ ya está). ¿Cómo se especifica el redondeo determinístico?

[Answer]: 🔒 COP no usa centavos → enteros (0 decimales), ROUND_HALF_UP. Una función redondear_monto(Decimal) -> Decimal (.quantize(Decimal("1"), ROUND_HALF_UP)) reutilizada en R4/R5.

---

**Q1.3 Selección de cláusula (cuando hay múltiples del mismo tipo):**
Si Poliza.clausulas tiene varias Clausula con `tipo=VIGENCIA`, ¿cuál se cita en el Dictamen?

[Answer]: 🔒 Selección determinística por clave fija, NO orden de dict/hash. Si hay varias Clausula del mismo tipo: ordena por clausula.id y toma la primera (sorted(..., key=lambda c: c.id)[0]).

---

**Q1.4 Orden de aplicación de exclusiones (R3):**
R3 evalúa si existe una exclusión que aplique. Si hay N exclusiones, ¿el orden de chequeo es determinístico?

[Answer]: R3: itera poliza.exclusiones en orden determinístico (lista ordenada / sorted), cada una aplica_exclusion(...) -> bool puro. Primera que aplica → NO_CUBIERTO citando esa exclusión (semántica OR: cualquier exclusión excluye). Early-exit en el primer match.

---

**Q1.5 Función pura (inputs → Dictamen, no state):**
¿El motor se especifica como función pura sin state machine?

[Answer]: 🔒 motor_cobertura(extraccion: ExtraccionValidada, poliza: Poliza) -> Dictamen. Cero mutación externa, sin state machine, todo temporal local. Y antes de invocar el motor: si ResultadoPoliza.encontrada=False (solo candidatas) → REQUIERE_REVISION, no dictamines sobre candidatas (RF-10/P4). El motor solo corre con una póliza confirmada.

---

### Fraude: Determinístico + LLM Mockeable

**Q2.1 Chequeos duros (determinísticos, sin LLM):**
¿Cuál es la lista de inconsistencias determinísticas que fraude chequea SIN LLM?

[Answer]: 🔒 inconsistencias es list[EvidenciaOrigen] (contrato AlertaFraude), NO list[str]. Cada chequeo duro puro (fecha_siniestro > vigencia_fin, < vigencia_desde, monto > suma_asegurada, fecha > hoy, tipo ∉ coberturas) que dispara → produce un EvidenciaOrigen(tipo, referencia). Retorna la lista.

---

**Q2.2 Mapa de severidad (determinístico):**
¿Cómo se define el mapeo inconsistencias → severidad (determinístico, reproducible para evals)?

[Answer]: calcular_severidad(inconsistencias) -> Severidad determinística: tipo duro (fecha>vigencia, monto>>suma) → ALTA; el conteo sube un nivel (3+). Mismo input → mismo output. severidad como enum.

---

**Q2.3 LLM en fraude (razonamiento):**
¿Cómo se especifica la integración LLM en fraude?

[Answer]: 🔒 LLM = SOLO explicación. razonar_fraude(chequeos, poliza_redactada) -> str → va a AlertaFraude.explicacion, vía LLMPayloadBuilder (P5). NO cambia severidad ni la lista inconsistencias (esas son determinísticas).

---

**Q2.4 Estructura de AlertaFraude (contract vs. construcción):**
¿Cómo se construye AlertaFraude desde los chequeos?

[Answer]: 🔒 AlertaFraude(severidad=calc(...), inconsistencias=[EvidenciaOrigen...], explicacion=llm(...)). El contrato exige inconsistencias no vacío (P6). Cero inconsistencias → NO se emite AlertaFraude (Caso.alerta_fraude queda None) — no un alerta vacío.

---

### Edge Cases & Specification Clarity

**Q3.1 Deducible ≥ monto (R5 edge case):**
Si deducible ≥ monto_reclamado, ¿qué se retorna?

[Answer]: 🔒 deducible ≥ monto → pago = 0, resultado = CUBIERTO (el siniestro está cubierto; solo que la pérdida está bajo el deducible). NO CUBIERTO_PARCIAL (parcial es sobre el límite/suma, no el deducible). deducible_calculado = deducible.

---

**Q3.2 Campo ausente en R1-R5:**
Si fecha_siniestro está ausente (ExtraccionValidada.campos con ausente=True), ¿R1 retorna qué?

[Answer]: Campo obligatorio ausente → REQUIERE_REVISION antes de evaluar la regla. El motor pre-chequea presencia; no pasa None a calcular_r1. Escalar, no decidir sobre datos incompletos (P4).

---

**Q3.3 Cláusula no encontrada:**
Si Poliza.clausulas no tiene una Clausula con tipo=VIGENCIA (ej: póliza incompleta), ¿R1 retorna qué?

[Answer]: Cláusula faltante (póliza sin tipo=VIGENCIA) → REQUIERE_REVISION, no excepción. El motor lo ve y escala (no puede citar una cláusula inexistente; P3). Controlado, con nota "cláusula X faltante" — no crash.

---

### Testing & Documentation

**Q4.1 Especificación paso-único para PBT-03:**
¿Cómo se documenta el motor para que el PBT sepa qué invariantes probar?

[Answer]: Docstring del motor: "R1-R5 secuencial, paso único, sin loops; early-exit en R1/R2/R3" + los invariantes (resultado∈enum, deducible≥0, cláusula≠None, determinismo). El PBT los lee como propiedades.

---

**Q4.2 Decimal redondeo en tests:**
¿Cómo los tests verifican que el redondeo es determinístico?

[Answer]: Property @given(st.decimals(...)) → redondear(x)==redondear(x) (idempotente) + redondear(x) tiene 0 decimales + caso específico redondear(Decimal("10.5")) == Decimal("11") (ROUND_HALF_UP, entero).

---

## Part 2: Execution Status

**ANSWERED & LOCKED 🔒**

NFR Design ha generado los 3 artefactos:
- [x] `aidlc-docs/construction/u3/nfr-design/motor-algoritmo.md`
- [x] `aidlc-docs/construction/u3/nfr-design/fraude-determinismo.md`
- [x] `aidlc-docs/construction/u3/nfr-design/edge-cases-spec.md`

---

## Approval Gate

**User Vigilance Points:**
- [x] Motor sin loops, paso único (P2 + P4 determinismo)
- [x] Decimal ROUND_HALF_UP (redondeo fijo, reproducible)
- [x] Cláusula/exclusiones orden determinístico (no dict-hash)
- [x] Función pura (inputs → Dictamen, cero state)
- [x] Fraude determinístico (chequeos + severidad fija) + LLM mockeable
- [x] PBT-03 sostenible (invariantes para todo input generado)

