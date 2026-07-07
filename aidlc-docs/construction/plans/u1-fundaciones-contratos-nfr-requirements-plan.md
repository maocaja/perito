# Plan de NFR Requirements — U1 · Fundaciones & Contratos

> **Fase**: Construction · **Actividad**: 2 (NFR Requirements) · **Regla**: `construction/nfr-requirements.md`.
> **Premisa**: U1 es capa de **contratos + generador sintético + RAG** (fundación), **no** un servicio de cara al usuario con latencia crítica. Los NFR se aterrizan sobre los contratos y se **trazan a los RNF de Inception** — no catálogo genérico.
> Fuentes: `u1/functional-design/*`, `requirements.md` (RNF), ADRs del AJIT.

---

## A. Metodología (checklist)
- [ ] A1. Fijar el **marco de NFR** de U1 (qué atributos aplican, cuáles son N/A honesto).
- [ ] A2. Definir **NFR con valores verificables**, cada uno trazado a un RNF de Inception.
- [ ] A3. Documentar **tech-stack** de U1 (confirmación desde ADRs/RES-04, no reinvención).
- [ ] A4. Generar `nfr-requirements.md` + `tech-stack-decisions.md`.

## B. Artefactos a generar (tras aprobación)
- [ ] `construction/u1-fundaciones-contratos/nfr-requirements/nfr-requirements.md`
- [ ] `construction/u1-fundaciones-contratos/nfr-requirements/tech-stack-decisions.md`

---

## C. Preguntas

### Question 1 — Marco de NFR para U1
U1 es fundación (contratos/generador/RAG), no runtime de cara al usuario. ¿Enfoco los NFR donde aplican y marco N/A explícito los de producción cloud?

A) **Sí** — NFR centrados en **correctitud** (round-trip, validación fail-closed), **seguridad** (PII/fail-closed) y **mantenibilidad** (contratos estables); **N/A honesto** para disponibilidad/escalabilidad de producción (P7, nada se despliega). *(recomendado)*
B) Cubrir los 6 atributos del catálogo con números aunque algunos sean artificiales.
X) Otro

[Answer]: 

### Question 2 — Números de correctitud (los NFR reales de U1)
Propongo estos targets, trazados a Inception:

| NFR | Target | Traza |
|---|---|---|
| Round-trip de contratos | **100%** de los contratos (por construcción, PBT-02) | RNF-24 |
| Validación fail-closed | **100%** de entradas inválidas rechazadas (0 malformados aceptados) | RNF-13, H-17 🔒 |
| Invariantes de contrato | 100% (deducible ≥ 0; dictamen con cláusula; enums cerrados; ResultadoPoliza consistente) | RNF-05/23, RULE-CTR-03/04/06/07 |
| Campos inventados | **≈ 0** | RNF-07 |

A) **Sí, esos targets.** *(recomendado)*
B) Ajustar (X).
X) Otro

[Answer]: 

### Question 3 — Rendimiento del generador (único throughput real de U1)
El generador produce el dataset de eval (~20-40 casos × 7 estratos ≈ 140-280 casos). ¿Qué target?

A) **Generar el dataset completo en tiempo de build razonable** (orden de minutos), sin latencia por-caso estricta — es infra-test, no runtime de producción. *(recomendado)*
B) Definir latencia por-caso estricta.
X) Otro

[Answer]: 

### Question 4 — PII en los contratos (P5)
Algunos contratos tocan PII (`Usuario`, campos del aviso). ¿El NFR de U1 exige minimización desde la fundación?

A) **Sí** — los contratos **marcan qué campos son PII**; U1 no obliga a propagar PII innecesaria (la minimización efectiva al LLM se ejerce en U2). Datos **sintéticos** ⇒ sin PII real (RES-03). *(recomendado, RNF-11/P5)*
B) N/A en U1 (todo se maneja en U2).
X) Otro

[Answer]: 

---

## D. Recomendación por defecto
**1-A · 2-A · 3-A · 4-A** — NFR aterrizados sobre los contratos de U1, con números verificables trazados a RNF de Inception, N/A honesto donde no aplica (P7). Decides tú; no genero artefactos hasta tu aprobación.

---

## E. RESPUESTAS (aprobadas 2026-07-06)
**1-A · 2-A · 3-A · 4-A**, con dos precisiones del usuario incorporadas a los artefactos:
1. **RNF-07 re-atribuido**: en U1 NO es "campos inventados ≈0" (métrica de extracción, U2). Se enuncia como **invariante de contrato**: `CampoExtraido.ausente=True ⇒ valor=null` (no-invención por construcción); la métrica ≈0 se mide en U2. (igual que Dictamen-sin-cláusula: invariante en U1, cálculo en U3).
2. **tech-stack**: confirmar desde ADRs/RES-04 (Python/Pydantic/Hypothesis/pgvector), no reinventar. Marcar cualquier dependencia nueva no justificada en Inception.
