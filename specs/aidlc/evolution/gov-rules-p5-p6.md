# Gobernanza — Reglas enforceable P5 (PII) y P6 (fraude solo sugiere)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md` §7
> **Fase:** Gobernanza · **LLM/det:** — (docs de política) · **Depende de:** —

## 1. Intent

`.claude/rules/` hoy carga P1 (`hitl.md`), P2 (`coverage-determinism.md`) y P4 (`termination.md`), pero **P5
(minimización de PII) y P6 (fraude solo sugiere) NO son reglas cargadas** — se protegen por revisión manual +
tests fail-closed. El roadmap §7 declaró que se añadirían antes/junto a las units que los tocan (U4/U5/U7 →
P5; U6/U10 → P6). Esta Unit **cierra ese gap**: convierte P5/P6 de *advisory* a **reglas modulares
enforceable**, al mismo nivel que las otras.

## 2. Criterios de completitud (verificables)

1. **`.claude/rules/pii-minimization.md` (P5)** existe y declara, como invariantes no negociables:
   - Ningún texto con PII llega a un LLM sin **redacción previa** (`redact_pii_spans_es_co` /
     `redact_pii_extendida`).
   - Ningún adjunto con PII cruda se **muestra o persiste**: se redacta o se guarda **solo la huella**.
   - La evidencia de fraude/historia referencia solo `caso_id` opaco, **nunca** PII.
   - Gaps declarados (P7): NER-lite heurístico; redacción **visual** de imágenes = fase-2 (no prometida).
2. **`.claude/rules/fraud-suggests.md` (P6)** existe y declara:
   - El fraude **solo sugiere revisión / carril SIU**; **ninguna** señal cambia `caso.estado`, deshabilita la
     firma ni bloquea — **ni la cross-claim con foto idéntica (distancia 0)**.
   - Toda señal lleva `confianza ∈ [0,1)` (**nunca 1.0** = veredicto). El LLM solo **explica**, no detecta.
   - La detección es **determinística**; el humano/SIU decide.
3. **Trazabilidad:** cada regla cita el principio del PRD (P5/P6) y los **tests fail-closed** que ya la
   verifican (`test_u6_cross_claim.py`, `test_u7_triage.py`, `test_u4_multimodal.py`), para que la regla no sea
   letra muerta sino un índice de sus garantías vivas.
4. **`CLAUDE.md` / índice de reglas** referencia las dos nuevas (coherencia con cómo se listan las demás).

## 3. Invariantes / restricciones

- Las reglas **describen** invariantes ya existentes en el código; **no** cambian comportamiento ni relajan
  nada. Son gobernanza, no lógica.
- No inventan alcance nuevo: reflejan lo que P5/P6 ya significan en el PRD y lo que los tests ya garantizan.

## 4. Fuera de alcance

- Hooks nuevos que **bloqueen** ediciones (como el de `rules/`+`orchestrator/`): esta Unit añade las reglas
  como documento cargado; convertirlas en hook *enforced* (exit code 2) es opcional y aparte.
- Cambiar la redacción o la lógica de fraude (ya construidas).

## 5. Verificación

- Los dos archivos existen y son coherentes con el formato de las reglas actuales (`hitl.md`, etc.).
- Cada regla enumera prohibiciones (`🚫`) y cita PRD + tests.
- **No** hay cambio de código de producto → la suite sigue en 332 verde (las reglas no ejecutan).

## 6. Notas CÓMO

Dos archivos markdown en `.claude/rules/` calcando el formato existente (título, invariantes, `🚫 Prohibido`,
`⚠️` nota, referencia al PRD). Actualizar la sección "Reglas modulares" de `CLAUDE.md`. Cero código.

## 7. Precisiones tras code-review

- **🔴 No sobrevender tests (honestidad):** P5 **no** tiene un único test titulado `test_p5_*`; su garantía vive
  **repartida** en tests reales. Las reglas citan los que **existen**, sin prometer uno inexistente. Tabla de
  referencias por regla:

  | Regla | Tests fail-closed que la verifican (reales) |
  |---|---|
  | `pii-minimization.md` (P5) | `test_u2_redaction.py`, `test_redaction_denybydefault.py` (deny-by-default), `test_u7_triage.py` (cuerpo redactado antes del LLM), `test_u4_multimodal.py` (inyección + redacción de adjunto) |
  | `fraud-suggests.md` (P6) | `test_u6_cross_claim.py::test_p6_foto_identica_no_cambia_estado_ni_firma`, `test_contrato_rechaza_confianza_1_0`, `test_u4_c7_orchestrator.py` (corona: nunca terminal) |

  Un `test_p5_pii_minimization.py` consolidado es **opcional** (mejora de claridad), no un requisito de esta Unit.
- **🟠 P6: distinguir protección TÉCNICA de la OPERACIONAL:** la regla aclara ambos niveles. **Técnico** (lo que
  el sistema *no puede* hacer): `AlertaFraude.confianza < 1.0` (contrato), C6 no-escalante, `estado` frozen
  (RULE-CTR-05). **Operacional:** el humano **sí** puede decidir sobre el caso (eso es P1/HITL, no una
  violación) — la regla constriñe al **sistema**, nunca al operador. El fraude gobierna la sugerencia; el HITL
  firma.
- **🟡 P5: minimización ≠ redacción (dos niveles):** la regla los separa. **(1) Minimización** — no incluir PII
  en el prompt de entrada (deny-by-default). **(2) Redacción** — si algo debe ir, remover los spans
  (`redact_pii_spans_es_co` / `redact_pii_extendida`). Ambas son P5.
- **CLAUDE.md:** el CÓMO actualiza la sección "Reglas modulares" añadiendo las dos nuevas (P5, P6) al índice,
  coherente con cómo se listan `hitl.md`/`coverage-determinism.md`/`termination.md`.
