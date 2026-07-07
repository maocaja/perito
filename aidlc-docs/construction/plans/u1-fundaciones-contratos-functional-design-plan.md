# Plan de Diseño Funcional — U1 · Fundaciones & Contratos

> **Fase**: Construction · **Actividad**: 1 (Diseño funcional) · **Regla**: `construction/functional-design.md`.
> **Unidad**: U1 (habilita todas las demás). **Historias**: H-16 (generador sintético es-CO + fraude inyectado), H-17 (tool contracts tipados + validación).
> **Alcance**: technology-agnostic — lógica de negocio, modelo de dominio y reglas. **No** infraestructura, **no** código todavía.
> Fuentes: `unit-of-work.md` (U1), `unit-of-work-story-map.md`, `application-design/*`, `requirements.md`, `stories.md`.

---

## A. Metodología (checklist de ejecución)
- [ ] A1. Modelar el **dominio** de U1: entidades y value objects (contratos Pydantic como VOs) → `domain-entities.md`.
- [ ] A2. Definir **reglas de negocio** numeradas (RULE-…) de validación/contrato y del generador → `business-rules.md`.
- [ ] A3. Modelar los **flujos E2E** de U1 (generación de caso sintético; validación/round-trip de contratos) → `business-logic-model.md`.
- [ ] A4. Identificar **propiedades testables (PBT-01)** por contrato (round-trip, invariantes) para alimentar Code Generation.
- [ ] A5. (N/A frontend — U1 no tiene UI; H-19/20/21 son de U4/U5).

## B. Artefactos a generar (tras aprobación de este plan)
- [ ] `construction/u1-fundaciones-contratos/functional-design/domain-entities.md`
- [ ] `construction/u1-fundaciones-contratos/functional-design/business-rules.md`
- [ ] `construction/u1-fundaciones-contratos/functional-design/business-logic-model.md`

---

## C. Preguntas (rellena la letra tras cada `[Answer]:`; "X" = otro, describe)

### Question 1 — Alcance de contratos en U1
U1 es "Fundaciones & Contratos". ¿Qué contratos modelo aquí?

A) **Todos los contratos compartidos del sistema** (Caso, EstadoCaso, Póliza, Cláusula, Extracción, Dictamen, AlertaFraude, Cotas, GroundTruth…) como fundación — habilitan U2-U5 (coherente con "los agent-teams solo arrancan tras contratos estables"). *(recomendado)*
B) **Solo los contratos que la lógica de U1 necesita** (generador + RAG); el resto se define en su propia unidad.
X) Otro

[Answer]: 

### Question 2 — Entidad `Caso` vs su máquina de estados
`Caso` es transversal (todas las unidades la tocan), pero las **transiciones de estado** (Apéndice C del PRD) son dominio de U4 (HITL). ¿Cómo lo reparto?

A) En U1 defino la **entidad `Caso` + el enum `EstadoCaso`** (el dato); las **reglas de transición** se detallan en el Functional Design de **U4**. *(recomendado — separa dato de comportamiento)*
B) Difiero entidad **y** transiciones a U4.
X) Otro

[Answer]: 

### Question 3 — Supuesto del dataset del generador (riesgo #1)
El PRD asume backbone Kaggle + verificación Día 0 (con Plan B si el esquema no sirve). Para el diseño funcional del generador:

A) Diseñar contra un **contrato abstracto de "fila de entrada"** (adapter), de modo que Kaggle sea un adaptador **intercambiable** — no acoplar al esquema Kaggle. *(recomendado — respeta el Plan B del riesgo #1)*
B) Diseñar **directamente contra el esquema Kaggle** asumido.
X) Otro

[Answer]: 

### Question 4 — Set de propiedades PBT-01 para U1
El diseño funcional debe listar propiedades testables. Para U1 propongo como base:
- **Round-trip** de cada contrato (serializar→deserializar = identidad) — PBT-02.
- **Invariantes** de tipo/rango (p. ej. `deducible ≥ 0`, `estado ∈ EstadoCaso`) — PBT-03.
- **"Fila etiquetada fraude ⇒ el documento encoda la inconsistencia"** (H-16, validez del eval).

A) **Sí, ese set** como base (se refina por contrato en los artefactos). *(recomendado)*
B) Ajustar (describe en X).
X) Otro

[Answer]: 

---

## D. Recomendación por defecto
**1-A · 2-A · 3-A · 4-A**. Es la lectura fiel de U1 como fundación, respeta el riesgo #1 (adapter de dataset) y separa dato de comportamiento (Caso vs transiciones). Decides tú; no genero artefactos hasta tu aprobación.

---

## E. RESPUESTAS (aprobadas 2026-07-06)
**1-A · 2-A · 3-A · 4-A.** Dos notas de endurecimiento incorporadas a los artefactos:
1. **Q2** — `Caso.estado`: definir campo + enum en U1, pero `domain-entities.md` deja explícito que **la única vía de mutación es la máquina de estados de `hitl` (U4)** — sin setter público. (preserva P1 "estado inmutable salvo vía hitl").
2. **Q4** — "fraude ⇒ inconsistencia encodada" es **fail-closed** (H-16 🔒): el generador **rechaza/rompe** si genera una fila etiquetada-fraude sin inconsistencia detectable (no check suave — si no, el eval de fraude mide ruido, `rules/testing.md`).
