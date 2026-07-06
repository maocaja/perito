# Perito — Preguntas de Verificación de Requisitos

El `PRD.md` es excepcionalmente completo, así que estas preguntas **no re-preguntan el dominio**
(ya está en el PRD). Solo resuelven decisiones de **alcance y configuración** de esta fase de
Inception AI-DLC, más los opt-in obligatorios de extensiones.

**Cómo responder:** escribe la letra elegida después de cada `[Answer]:`. Si ninguna opción
encaja, elige la última (Otro) y describe. Avísame cuando termines ("listo"/"done").

---

## Question 1 — Alcance de requisitos para esta Inception
El PRD define un MVP amplio (módulos M1-M10) con MoSCoW. ¿Qué alcance debo formalizar como
requisitos AI-DLC (y luego descomponer en unidades de trabajo)?

A) **Núcleo irrenunciable** — Must #2-#8 + #10 (extracción → verificación → grounding → cobertura R1-R5 → terminación → HITL + observabilidad). El resto queda declarado como fuera de alcance de la Inception.
B) **Must completo** — los 13 Must del MoSCoW (M1-M10 incluyendo generador sintético, tool contracts, evals versionados).
C) **Must + Should** — incluye SOAT, acuse, tablero visual, cola de SLA, fraude-vs-Kaggle.
D) Otro (describe después de `[Answer]:`)

[Answer]: B  (Must completo, 13 items M1-M10. El "núcleo irrenunciable" es piso de degradación, no el objetivo; el MVP real y el plan de 5 días asumen los 13 Must. Should = scope creep, descartado.)

---

## Question 2 — Profundidad del análisis (depth level)
Por complejidad (sistema agéntico multi-módulo, riesgo regulatorio, invariantes P1-P7), propongo
profundidad **Comprehensive**. ¿Confirmas?

A) **Comprehensive** — requisitos funcionales + no funcionales + trazabilidad a principios P1-P7 (recomendado).
B) **Standard** — funcionales + no funcionales, sin matriz de trazabilidad detallada.
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Comprehensive — la diferenciación de Perito es auditabilidad; sin matriz de trazabilidad a P1-P7 se pierde lo distintivo.)

---

## Question 3 — Idioma de los artefactos
El proyecto es es-CO. ¿En qué idioma genero los artefactos AI-DLC (requirements, stories, design)?

A) **Español** (consistente con PRD/AGENTS.md).
B) Inglés.
C) Otro (describe después de `[Answer]:`)

[Answer]: A  (Español es-CO.)

---

## Question 4 — Etapa de User Stories
La etapa User Stories es condicional. Dada la complejidad y que el PRD ya trae User Journeys (J1-J4)
y casos de uso (UC1-UC5), ¿la incluyo?

A) **Sí, con Gherkin** — historias por rol con criterios de aceptación en Given/When/Then (recomendado; encaja con los evals por estrato).
B) Sí, historias narrativas simples (sin Gherkin).
C) No, saltar directo a Workflow Planning (los UC/journeys del PRD bastan).
D) Otro (describe después de `[Answer]:`)

[Answer]: A  (Gherkin — los Given/When/Then se reusan como escenarios de eval por estrato.)

---

## Question: Security Extensions
Should security extension rules be enforced for this project?
(Perito trata PII bajo Habeas Data / Circular SIC, con invariantes P3/P5 — la extensión es muy pertinente,
pero la decisión es tuya.)

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: A  (Yes, blocking — P3/P5 + PII bajo Habeas Data/Circular SIC; enforce = demostrar disciplina de ingeniería.)

---

## Question: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?
(El motor de reglas R1-R5 determinístico y los contratos Pydantic son candidatos naturales a PBT.)

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)
C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)
X) Other (please describe after [Answer]: tag below)

[Answer]: B  (Partial — motor R1-R5 = función pura determinística; contratos Pydantic = round-trips. Enforced: PBT-02/03/07/08/09. Forzar PBT sobre nodos LLM no deterministas sería incoherente.)
