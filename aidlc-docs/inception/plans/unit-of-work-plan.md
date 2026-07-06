# Plan de Units of Work — Perito

> Descompone el sistema en **unidades de trabajo** (agrupaciones lógicas de historias para construcción).
> Base: `application-design/*` (10 componentes) + `stories.md` (18 historias) + plan de 5 días del PRD §13.
> Inputs de endurecimiento arrastrados (Application Design §7.1): (1) `Caso.estado` inmutable salvo vía hitl; (2) `test_gate_regla` = firma, no build.

---

## A. Metodología (checklist)
- [ ] A1. Fijar modelo de despliegue + organización de código (ver Q1).
- [ ] A2. Agrupar las 18 historias en unidades (ver Q2/Q3).
- [ ] A3. Construir grafo de dependencias entre unidades (acopla H-04→H-07, H-16/H-17→resto).
- [ ] A4. Mapear cada historia a su unidad (cobertura 100%).
- [ ] A5. Generar artefactos: `unit-of-work.md`, `unit-of-work-dependency.md`, `unit-of-work-story-map.md`.

## B. Artefactos mandatorios (tras aprobación)
- [ ] `application-design/unit-of-work.md` (definiciones + responsabilidades + organización de código)
- [ ] `application-design/unit-of-work-dependency.md` (matriz de dependencias + secuencia/paralelización)
- [ ] `application-design/unit-of-work-story-map.md` (historia → unidad)

---

## C. Decisiones a confirmar

### Question 1 — Modelo de despliegue y organización de código
El PRD asume un backend Python/FastAPI para una persona. ¿Cómo estructuro las unidades?

A) **Monolito modular, único servicio desplegable (recomendado)**: una unidad = un **módulo lógico** dentro de `backend/app/` (agents/, rules/, orchestrator/, hitl/, observability/, rag/, intake/, synthetic/). Alineado con el repo y con "construible por una persona" (PRD §2). Sin sobre-ingeniería de microservicios (evita riesgo #2).
B) **Microservicios**: cada unidad = servicio desplegable independiente. Más "escalable" pero contradice el encuadre portafolio/una-persona y multiplica infra (que además es SKIP).
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Monolito modular — única opción consistente con "construible por una persona", portafolio e Infra Design=SKIP; B resucitaría infra ya declarada SKIP.)

### Question 2 — Estrategia de agrupación de historias en unidades
¿Bajo qué criterio agrupo las 18 historias?

A) **Por incremento de construcción alineado al plan de 5 días del PRD §13 (recomendado)**: cada unidad cierra "algo demostrable" y respeta el orden de dependencias natural (fundaciones → extracción/verificación → cobertura/fraude → orquestación/HITL → evals). Maximiza demostrabilidad incremental.
B) **Por bounded context de dominio**: agrupar por subdominio (admisión, cobertura, fraude, gobernanza) sin atención al orden de construcción.
C) **Por persona**: unidades por rol (analista, cumplimiento, dev).
D) Otro (describe después de `[Answer]:`)

[Answer]: A  (Por incremento del plan de 5 días — respeta el orden de dependencias y "cada día algo demostrable".)

### Question 3 — Granularidad (número de unidades)
Con el criterio A de Q2, propongo **5 unidades** espejo de los días 1-5 (fundaciones/contratos · extracción-verificación-grounding · cobertura-fraude · orquestación-terminación-HITL · observabilidad-evals-redteam). ¿Confirmas?

A) **5 unidades (recomendado)** — espejo del plan de 5 días; núcleo irrenunciable = unidades 2-4.
B) **Menos, más gruesas** (~3) — agrupa más agresivamente.
C) **Más, más finas** (~7-8) — separa RAG, infra, red-team, etc. en unidades propias.
D) Otro (describe después de `[Answer]:`)

[Answer]: A  (5 unidades espejo de los días; núcleo irrenunciable = U2-U4.)

---

## Nota de coherencia para el grafo (A3), aprobada por el usuario
- **H-04→H-07** (U2→U3): resultado de grounding alimenta cobertura.
- **H-06 escalamiento** (U2 marca ausente) **→ requiere U4** (orquestador escala): H-06 NO es autocontenida en U2; su comportamiento fail-closed se ejercita cuando existe U4. Capturar **U2→U4** como dependencia de comportamiento.
- Igual: **H-03 señal de verifier** y **H-04 señal "sin match"** (U2) → el orquestador (U4) actúa sobre la señal.

**Plan APROBADO: "1-A · 2-A · 3-A, genera los 3 artefactos de unidades".**

---

## D. Recomendación por defecto
**1-A · 2-A · 3-A** — monolito modular, unidades por incremento del plan de 5 días, 5 unidades. Fiel al PRD, al repo y al encuadre portafolio. Decides tú; no genero artefactos hasta tu aprobación.
