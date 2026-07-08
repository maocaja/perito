# U3 Functional Design Plan — ANSWERED

**Unit:** U3 · Cobertura determinística · Fraude
**Answers:** User provided, 4 invariants marked 🔒

---

## Checkpoint 1: Motor R1-R5 (C5, P2 Core) — ANSWERED

**Q1.1 Parada temprana vs. ejecutar todas:**
[Answer]: Parada temprana en gating rules (R1/R2/R3): R1 falla → NO_CUBIERTO citando R1+cláusula. R4/R5 siempre se computan para monto/deducible. No correr R2-R5 si R1 descalifica.

**Q1.2 Orden de exclusiones:**
[Answer]: Sí, R3 después de R2 — orden PRD R1·R2·R3·R4·R5. Primero confirmas cobertura contratada, luego aplicas exclusión.

**Q1.3 CUBIERTO_PARCIAL (cuándo):**
[Answer]: Cuando pasa R1/R2/R3 pero monto_reclamado > suma_asegurada → cubierto hasta límite (R4). Es límite-driven, no deducible-driven.

**Q1.4 Mapeo regla→cláusula:**
[Answer]: Sí. Poliza.clausulas: list[Clausula], Clausula.tipo ∈ {vigencia, cobertura, exclusion, limite, deducible}. Motor busca cláusula por tipo: R1→vigencia, R2→cobertura, R3→exclusion, R4→limite, R5→deducible. Usa Clausula.tipo existente.

**Q1.5 Cláusula no encontrada:**
[Answer]: Sí, REQUIERE_REVISION. Sin cláusula no hay dictamen (P2/P3) → escalar, nunca fabricar CUBIERTO.

**Q1.6 Múltiples deducibles:** 🔒 INVARIANTE
[Answer]: Deducible ÚNICO por póliza. Contrato Poliza tiene un deducible: Decimal. No por-tipo (MVP). SOAT sin deducible = forward-compat RF-14 diferido.

**Q1.7 Deducible vs. Límite:**
[Answer]: pago = max(0, min(monto, suma_asegurada) − deducible). monto > suma_asegurada → CUBIERTO_PARCIAL. deducible_calculado ≥ 0 siempre. Edge: deducible ≥ monto → pago 0 (cubierto bajo deducible).

---

## Checkpoint 2: Fraude (C6, P6 & P1) — ANSWERED

**Q2.1 Fuente de inconsistencias:**
[Answer]: Sí: inconsistencias cross-field (C2 vs C4: fecha_siniestro > vigencia_fin, monto > suma_asegurada) e intra-documento (UC4 ⭐ PRD).

**Q2.2 LLM en detección:** 🔒 INVARIANTE
[Answer]: SÍ, fraude puede usar LLM (Sonnet) — a diferencia de cobertura. Clave: solo sugiere (P6), no decide. Híbrido: inconsistencias duras (fecha>vigencia) detectadas código; LLM aporta explicación (P6) y patrones sutiles. Vía LLMPayloadBuilder (P5). fraud/ NO importa rules/.

**Q2.3 Severidad (cálculo):**
[Answer]: severidad ∈ {BAJA, MEDIA, ALTA}, por tipo (fecha>vigencia = ALTA) con conteo como modificador. Mapeo determinístico.

**Q2.4 Formato de evidencia:** 🔒 INVARIANTE
[Answer]: Usa AlertaFraude U1 ({severidad, inconsistencias: list[EvidenciaOrigen], explicacion}). No inventar campo evidencia paralelo. inconsistencias no vacío ya lo exige contrato (P6).

**Q2.5 Integración con Dictamen:**
[Answer]: Independiente. AlertaFraude y Dictamen coexisten en Caso.alerta_fraude y Caso.dictamen. Fraude no modifica dictamen (P2).

**Q2.6 Estado terminal:** 🔒 INVARIANTE
[Answer]: NO. AlertaFraude nunca cambia Caso.estado. Solo hitl/U4 muta con humano (P1). A lo sumo su señal → REQUIERE_REVISION vía U4, nunca RECHAZADO automático.

---

## Checkpoint 3: Módulo Boundaries & Integration — ANSWERED

**Q3.1 ¿fraud/ importa rules/?**
[Answer]: No. Puede leer Dictamen como contexto (dato), no importar lógica. Leer valor ✓; importar código ✗.

**Q3.2 Lectura de campos:**
[Answer]: Sí, vía .campos (itera CampoExtraido por nombre), no plano.

**Q3.3 Campo ausente:** 🔒 INVARIANTE
[Answer]: REQUIERE_REVISION, NO NO_CUBIERTO. No niegues cobertura sobre datos faltantes — eso sería decidir incompleto. Fail-closed = escalar (P4).

---

## Checkpoint 4: Testing & PBT-03 — ANSWERED

**Q4.1 Propiedades invariantes (adicionales):**
[Answer]: Agrega: (a) todo Dictamen.clausula ≠ None siempre; (b) deducible_calculado ≤ min(monto, suma_asegurada); (c) orden fijo — permutar R1-R5 no cambia resultado; (d) R1 falla ⇒ NO_CUBIERTO citando R1.

**Q4.2 Test cases (adicionales):**
[Answer]: Agrega: CUBIERTO_PARCIAL (monto>suma); campo obligatorio ausente → REQUIERE_REVISION; cláusula faltante → REQUIERE_REVISION; fraude: fecha>vigencia → AlertaFraude, Caso.estado intacto; deducible ≥ monto (pago 0). Organiza por estrato (rules/testing.md): happy · cobertura-negativa · campos-faltantes · fraude.

---

## INVARIANTES CONFIRMADOS (4 🔒)

1. **Q1.6:** Deducible único por póliza (contrato U1)
2. **Q2.2:** Fraude SÍ LLM, pero solo sugiere (P6 explicabilidad, no P2 cobertura)
3. **Q2.4:** AlertaFraude de U1, no inventar campos paralelos
4. **Q3.3 & Q2.6:** Campos ausentes/AlertaFraude → REQUIERE_REVISION/sin cambio estado (P4/P1, nunca inventar/decidir)

