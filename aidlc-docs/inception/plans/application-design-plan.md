# Plan de Application Design — Perito

> Rol: arquitecto de aplicación. Alcance: identificación de componentes + interfaces + capa de servicio + dependencias. **La lógica de negocio detallada se define después en Functional Design (Construction).**
> Base: `requirements.md` (M1-M10) + `stories.md` (18 historias) + diagrama del PRD §9. Idioma es-CO.

---

## A. Metodología (checklist de ejecución)
- [ ] A1. Mapear capacidades → componentes (partiendo de M1-M10 del PRD §9).
- [ ] A2. Definir responsabilidades e interfaces de cada componente (sin lógica detallada).
- [ ] A3. Diseñar la capa de servicio / orquestación (dueño de terminación y escalamiento).
- [ ] A4. Fijar **dónde viven los invariantes P1-P4** (puntos de enforcement fail-closed).
- [ ] A5. Construir el grafo de dependencias + patrones de comunicación + flujo de datos.
- [ ] A6. Generar artefactos: `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`, `application-design.md`.

## B. Artefactos mandatorios (tras aprobación)
- [ ] `application-design/components.md`
- [ ] `application-design/component-methods.md`
- [ ] `application-design/services.md`
- [ ] `application-design/component-dependency.md`
- [ ] `application-design/application-design.md` (consolidado)

---

## C. Decisiones de diseño a confirmar

### Question 1 — Granularidad de componentes
El PRD §9 define M1-M10. ¿Cómo los mapeo a componentes de diseño?

A) **1:1 con los módulos (recomendado)**: un componente por M1-M10 (intake, extractor, verifier, policy_lookup, coverage_rules, fraud_signals, orchestrator, hitl, observability, policy_rag) + infra sintética. Máxima trazabilidad al PRD y a las historias.
B) **Consolidado por capa**: agrupar (p. ej. "agente-tools" = extractor+verifier+policy_lookup+coverage_rules+fraud_signals como un componente con submódulos; orchestrator; hitl; observability; rag).
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (1:1 con M1-M10 — mantiene coverage_rules aislado y sostiene la frontera P2 de Q2; alineado con backend/app/rules|orchestrator|agents del repo.)

### Question 2 — Aislamiento del motor determinístico (P2) y de las herramientas del agente
¿Cómo modelo `coverage_rules` (R1-R5) y las demás tools respecto al LLM/orquestador?

A) **Motor de reglas como librería pura aislada, invocada por el orquestador — nunca como "tool" que el LLM elige libremente (recomendado)**: `coverage_rules` es una función determinística pura (SECURITY-11 separación de concerns; testeable con PBT-03). El LLM solo alimenta los campos; el orquestador llama al motor. Extractor/verifier/fraud son tools con contrato Pydantic; policy_lookup consulta el RAG.
B) **Todas las capacidades como tools que el agente/LLM decide invocar** (incluida cobertura) — más "agéntico" pero arriesga que el LLM medie la decisión de cobertura.
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Obligatoria, no solo recomendada — expresión arquitectónica literal de coverage-determinism.md. B violaría P2 y no se implementaría.)

### Question 3 — Ubicación del enforcement de invariantes (P1-P4)
¿Dónde viven los guardrails fail-closed?

A) **Orquestador dueño de terminación/escalamiento (P4) + capa de validación de contratos (P3) + máquina de estados HITL que bloquea terminal sin `aprobado_por` (P1) + motor puro para cobertura (P2) — enforcement distribuido pero con dueños claros (recomendado)**. Cada invariante tiene un punto único y testeable.
B) **Un único componente "guardrails" centralizado** que intercepta todo (más acoplado, punto único de fallo).
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Distribuido con dueños únicos — B sacaría P4 del orquestador y contradiría termination.md; crea punto único de fallo.)

---

## Criterio de aceptación del usuario (aprobado 2026-07-06)
Al generar `component-dependency.md`, **`coverage_rules` NO debe tener ninguna arista entrante desde un componente respaldado por LLM** (extractor/verifier/fraud_signals). Ahí se prueba en el grafo que P2 se respetó. Aristas entrantes permitidas: solo desde `orchestrator` (invocación) y lectura de `policy_rag` (cláusula).

**Plan APROBADO: "1-A · 2-A · 3-A, genera los artefactos de diseño".**

---

## D. Recomendación por defecto
Si quieres avanzar: **1-A · 2-A · 3-A** — es la lectura fiel del PRD (motor determinístico aislado, orquestador dueño de la terminación) y la que mantiene cada invariante con un dueño único y testeable. Decides tú; no genero artefactos hasta tu aprobación.
