# Programa de Evolución — Perito FNOL completo (mini-Inception)

> **Tipo:** documento de programa (brownfield; NO re-Inception) · **Fase AI-DLC:** define el QUÉ del programa.
> **Estado:** 🟡 propuesto — fuente de verdad que descompone el programa en 9 Units de trabajo.
> Cada Unit tiene su propia change-level spec (QUÉ) → validación humana + code-reviewer → Bolt (CÓMO) → tareas.

## 1. Intent

Llevar a Perito de un **núcleo FNOL profundo pero angosto** (extraer → verificar → cobertura citada →
fraude intra-caso → HITL) a la **consola FNOL completa** que un operador real usa: leer adjuntos de cualquier
formato, validar cobertura **por producto**, detectar fraude **cross-claim**, y preparar el expediente
priorizado y enrutado — **manteniendo la decisión en el humano** (P1) y la cobertura/fraude en **reglas
determinísticas** (P2/P6). Motivado por la investigación del flujo real (MAPFRE/SURA/AXA): el operador **no
decide** — transforma el caos en un expediente estructurado y verificable.

## 2. Qué SÍ / qué NO

**SÍ (el programa, 9 units):** front-end determinístico (clasificación/prioridad/routing/checklist),
cobertura product-aware, intake multimodal + redacción PII, fraude cross-claim, triage, entity resolution,
loop reflexivo interno.

**NO haremos (explícito — nos harían PEORES):**
- ❌ Multi-agente / swarm · ❌ memoria conversacional de largo plazo (la historia de siniestros para fraude
  NO es esto: es un store de datos, no memoria conversacional).
- ❌ Que el LLM **decida** cobertura o fraude — siempre determinístico + humano.
- ❌ Auto-cierre / auto-pago / auto-envío sin firma humana (P1).
- ❌ Modelar el catálogo de **todos** los productos — solo 2-3 reales como ejemplares (P7).

## 3. Las 9 Units (grafo de dependencias + fase)

| Unit | Título | LLM/det | Invariante 🔒 | Depende de | Fase |
|---|---|---|---|---|---|
| **U1** | Clasificación + Prioridad + Routing | ⚙️ det | — | — | Demo |
| **U2** | Documentos requeridos + Checklist por producto | ⚙️ det | — | (U4 para "qué llegó") | Demo (parcial) |
| **U3** | Cobertura product-aware | ⚙️ det | 🔒 P2 (`rules/`+`contracts/`) | — | Demo (2-3 productos) |
| **U4** | Intake multimodal + redacción PII + extracción rica | 🤖+⚙️ | 🔒 P5 | — | Producto |
| **U5** | Historia de siniestros + consultas cross-claim | ⚙️ det | P5 | C1 (Postgres) | Producto |
| **U6** | Fraude cross-claim (pHash, frecuencia, redes) | ⚙️+🤖 | 🔒 P6 | U4, U5 | Producto |
| **U7** | Triage (¿es siniestro? nuevo/existente) | 🤖 | P1, P5 | redacción de cuerpo | Producto |
| **U8** | Entity resolution (fallback placa/cédula/nombre) | ⚙️+🤖 | — | U4 | Producto |
| **U9** | Loop reflexivo C2↔C3 (evaluator-optimizer) | 🤖 | 🔒 P4 (`orchestrator/`) | — | Interno |
| **U10** | Wiring del fraude cross-claim al pipeline (visible en bandeja) | ⚙️ det | 🔒 P4 + P6 | U5, U6 | Producto |
| **GOV** | Reglas enforceable P5 (PII) y P6 (fraude sugiere) | — docs | — | — | Gobernanza |

**Orden de ataque sugerido:** U1 → U2 → U3 (fase demo) → U4 → U8 → U5 → U6 → U7 → U9.
Notas de orden (tras code-review del QUÉ): **U9 después de U3** (U9 toca `tipo_siniestro`, que U3 vuelve
product-aware); **U7 depende de una redacción del cuerpo del correo antes del LLM (P5)** → es Producto, no
Demo; **U6 después de U5** (necesita el store de historia/huellas).
**Units con ruta protegida (🔒):** U3, U4, U6, U9 → **OK explícito del humano + code-reviewer obligatorio antes del CÓMO.**

## 7. Reglas modulares pendientes (tras code-review)

Hoy `.claude/rules/` cubre P1/P2/P4 y testing, pero **no P5 ni P6** como reglas enforceable. Antes de las
units que los tocan (U4/U5/U7 → P5; U6 → P6) se añadirán `rules/pii-minimization.md` (P5) y
`rules/fraude-solo-sugiere.md` (P6) para convertirlos de advisory a enforced.

## 4. Ritmo por Unit (idéntico a Units H…M)

`QUÉ (change-level spec)` → **validación humana** → `code-reviewer` (obligatorio en 🔒) → `CÓMO (Bolt en tareas)`
→ tests fail-closed → verify → PR. **Una unit a la vez**, en orden de dependencia. Los specs 🟡 no se
construyen hasta validarse.

## 5. Invariantes transversales (todo el programa)

P1 (humano decide/firma) · P2 (cobertura por reglas, citada) · P4 (terminación acotada) · P5 (PII redactada,
incluidos adjuntos) · P6 (fraude solo sugiere) · P7 (nada fabricado; ejemplares honestos). La regla de oro:
**los LLM leen y entienden el caos; los motores determinísticos aplican política citable; el humano decide.**

## 6. Índice de las QUÉ (una por Unit)

- U1 → `u1-clasificacion-prioridad-routing.md`
- U2 → `u2-documentos-checklist.md`
- U3 → `u3-cobertura-product-aware.md`
- U4 → `u4-intake-multimodal.md`
- U5 → `u5-historia-cross-claim.md`
- U6 → `u6-fraude-cross-claim.md`
- U7 → `u7-triage.md`
- U8 → `u8-entity-resolution.md`
- U9 → `u9-loop-reflexivo.md`
