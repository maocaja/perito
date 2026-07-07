# Plan de NFR Design — U1 · Fundaciones & Contratos

> **Fase**: Construction · **Actividad**: 3 (NFR Design) · **Regla**: `construction/nfr-design.md`.
> **Objetivo**: traducir los NFR de U1 en **patrones de diseño concretos + componentes lógicos** (no intenciones).
> Fuentes: `u1/nfr-requirements/*` (NFR-U1-01..08 + tech-stack), `u1/functional-design/*`, ADRs del AJIT.
> **Pedidos del re-check del usuario a resolver como patrón**: (a) dimensión pgvector **parametrizada**, no hardcodeada; (b) **etiquetado de PII** traducido a patrón concreto.

---

## A. Metodología (checklist)
- [ ] A1. Mapear cada NFR aplicable de U1 → **patrón de diseño** concreto.
- [ ] A2. Definir los **componentes lógicos** de U1 y cómo integran los patrones.
- [ ] A3. Resolver explícitamente los 2 pedidos del re-check (dimensión param; patrón PII).
- [ ] A4. Generar `nfr-design-patterns.md` + `logical-components.md`.

## B. Artefactos a generar (tras aprobación)
- [ ] `construction/u1-fundaciones-contratos/nfr-design/nfr-design-patterns.md`
- [ ] `construction/u1-fundaciones-contratos/nfr-design/logical-components.md`

---

## C. Preguntas (patrones concretos)

### Question 1 — Patrón de etiquetado de PII (realiza NFR-U1-06)
¿Cómo se **marca** PII en los contratos, de forma que sea *enforceable* aguas abajo (minimización en U2, logging-sin-PII RNF-12, export-PIA RNF-21)?

A) **Metadata tipada por campo** — cada campo PII se marca en el contrato (p. ej. `Annotated[str, PII]` o `Field(json_schema_extra={"pii": True})`), + una **introspección/registro** que lista los campos PII de cada contrato. Así U2 minimiza automáticamente y los logs filtran por esa marca. *(recomendado — hace la minimización un hecho, no una intención)*
B) Convención de nombres / lista externa mantenida a mano.
X) Otro

[Answer]: 

### Question 2 — Patrón de validación fail-closed (realiza NFR-U1-02)
¿Cómo se garantiza que una entrada inválida se rechaza ruidosamente (0 malformados aceptados)?

A) **Pydantic estricto** — `strict=True` + `extra="forbid"`: sin coerción silenciosa, campo desconocido o tipo inválido ⇒ excepción de validación (rechazo). El caso no avanza. *(recomendado — fail-closed por construcción, SECURITY-05/15)*
B) Validación laxa con coerción de tipos.
X) Otro

[Answer]: 

### Question 3 — Dimensión del vector pgvector (tu nota de acoplamiento)
El modelo de embedding se confirma en U2/U3, pero U1 define el esquema del RAG. ¿Cómo evito pre-comprometer el modelo?

A) **Dimensión como parámetro de configuración** — el esquema del RAG deja la dimensión del vector configurable (no hardcodeada); se fija al confirmar el modelo de embedding en U2/U3. *(recomendado — respeta tu nota)*
B) Fijar una dimensión concreta ahora.
X) Otro

[Answer]: 

---

## D. Nota — patrones ya decididos (se realizan sin pregunta)
- **Inmutabilidad de `Caso.estado`** (RULE-CTR-05 🔒, P1): patrón "estado sin setter público; mutación solo vía máquina de `hitl` (U4)". Ya decidido en Functional Design.
- **Round-trip** (NFR-U1-01): patrón "contratos Pydantic con `model_dump`/`model_validate` + PBT Hypothesis".
- **Generador fail-closed** (RULE-GEN-02 🔒): patrón "assert de inconsistencia encodada; excepción si falta".
- **Adapter de dataset** (RULE-GEN-03): patrón "puerto `FilaEntrada` + adaptador Kaggle intercambiable".

## E. Recomendación por defecto
**1-A · 2-A · 3-A**. Resuelve los 2 pedidos del re-check como patrón concreto y fija la validación fail-closed. Decides tú; no genero artefactos hasta tu aprobación.

---

## F. RESPUESTAS (aprobadas 2026-07-06) — con 2 refinamientos
**1-A · 2-A · 3-A**, endurecidos:
1. **Q1 PII — deny-by-default en la frontera**: además del marcador tipado + registro, nombrar los **puntos de consumo** que redactan **por defecto** (opt-in para incluir): (a) builder de payload-al-LLM (U2) que redacta campos PII salvo whitelist explícita; (b) serializador de logs que redacta por la misma marca (RNF-12). Fail-closed: PII nueva sin manejar ⇒ redactada, no filtrada. Coherente con deny-by-default (RNF-14/SECURITY-08).
2. **Q2 strict — nota Decimal/money**: `strict=True` fuerza `Decimal` desde string/Decimal (no float) en `deducible`/`suma_asegurada` → evita imprecisión float que rompería `deducible ≥ 0`. Code Gen: alimentar money como str/Decimal, no float.
