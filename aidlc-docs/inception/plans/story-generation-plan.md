# Plan de Generación de User Stories — Perito

> Rol: Product Owner. Idioma: es-CO. Formato de criterios de aceptación: **Gherkin** (Q4=A).
> Prerrequisito aprobado: `requirements.md`. Este plan requiere tu aprobación antes de generar `stories.md`/`personas.md`.

---

## A. Metodología propuesta (checklist de ejecución)

- [ ] A1. Generar `personas.md` con los 3 roles activos del MVP (+ ajustador como afectado/contexto, fuera de MVP).
- [ ] A2. Definir Epics alineados a los módulos/journeys (ver B).
- [ ] A3. Escribir historias siguiendo **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable).
- [ ] A4. Cada historia con criterios de aceptación **Gherkin** (Given/When/Then), incluyendo al menos 1 happy path + 1 camino de error/escalamiento.
- [ ] A5. Escenarios explícitos para invariantes no negociables (P1 HITL, P2 cobertura por reglas, P4 terminación) como criterios "fail-closed".
- [ ] A6. Mapear cada historia a: RF/RNF de origen, principio(s) P1-P7, y **estrato de eval** correspondiente.
- [ ] A7. Generar `stories.md` (historias + Epics + matriz de mapeo) y mapa persona↔historia.

---

## B. Decisiones que necesito que confirmes

### Question 1 — Método de desglose (breakdown approach)
El PRD ya trae personas, journeys (J1-J4), casos de uso (UC1-UC5) y módulos (M1-M10). ¿Cómo estructuro las historias?

A) **Híbrido (recomendado)**: Epics por **capacidad/journey** (admisión happy, escalamiento, cobertura+cita, fraude, HITL, observabilidad/evals), historias dentro de cada Epic **atribuidas a la persona** que obtiene el valor, y escenarios Gherkin derivados de UC/journeys mapeados a estratos de eval.
B) **Persona-based puro**: agrupar todas las historias por rol (Analista / Operador / Admin).
C) **Feature/Módulo-based puro**: una familia de historias por módulo M1-M10.
D) Otro (describe después de `[Answer]:`)

[Answer]: A  (Híbrido — único que preserva la trazabilidad RF↔P1-P7↔estrato de eval; hace que cada Gherkin se reuse como escenario de eval.)

### Question 2 — Granularidad
¿Qué tamaño de historia prefieres?

A) **Historias medianas orientadas a capacidad demostrable** (recomendado) — cada una entrega una porción demostrable end-to-end (encaja con "cada día cierra con algo demostrable" del PRD §13). ~12-18 historias.
B) **Historias finas por módulo/función** — más numerosas (~25-35), más cercanas a tareas.
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Medianas, 12-18 — capability-level demostrable; las finas son nivel-tarea = Workflow Planning, no historias.)

### Question 3 — Alcance de las personas
¿Incluyo al **Ajustador** (río abajo, fuera del MVP) como persona documentada?

A) **Sí, como persona de contexto** (recomendado) — documentada pero sin historias en el MVP (marca su exclusión explícita y el riesgo de sabotaje del PRD §3).
B) No, solo las 3 personas activas del MVP.
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Ajustador como persona de contexto, sin historias — documenta la exclusión y el riesgo de sabotaje del §3, honesto con P7.)

---

## Nota de coherencia para la generación (recordatorio del usuario, aprobado)
1. **SOAT diferido se propaga**: NINGUNA historia de SOAT (consistente con RF-27.1).
2. **Fail-closed real**: los escenarios de invariantes deben ser de **rechazo/escalamiento** (Dado un intento de auto-decisión → Entonces el sistema escala/bloquea/deniega), no un happy-path disfrazado.

**Plan APROBADO por el usuario 2026-07-06: "1-A · 2-A · 3-A, genera personas.md + stories.md".**

---

## C. Artefactos mandatorios (se generarán tras tu aprobación)
- [ ] `aidlc-docs/inception/user-stories/personas.md`
- [ ] `aidlc-docs/inception/user-stories/stories.md` (INVEST + Gherkin + matriz de mapeo RF/RNF · P1-P7 · estrato de eval)

## D. Recomendación por defecto
Si quieres avanzar rápido: **1-A · 2-A · 3-A**. Decides tú; no genero historias hasta tu aprobación.
