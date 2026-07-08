# NFR Requirements — U1 · Fundaciones & Contratos

> NFR **aterrizados sobre los contratos** de U1, con valores verificables y **traza a un RNF de Inception**. **N/A honesto** (P7) donde el atributo no aplica a una capa de fundación que nunca se despliega — N/A no es "cubrir menos", es no inventar.

## NFR aplicables

### Correctitud (el atributo central de una capa de contratos)

| ID | Métrica / target | Condición de fallo | Traza |
|---|---|---|---|
| **NFR-U1-01** · Round-trip | **100%** de los contratos: `deserializar(serializar(x)) == x` | cualquier contrato que no haga round-trip | RNF-24, RULE-CTR-01 (PBT-02) |
| **NFR-U1-02** · Validación fail-closed | **100%** de entradas inválidas rechazadas; **0** malformados aceptados | un objeto que no cumple contrato avanza en el flujo | RNF-13, H-17 🔒, SECURITY-05/15 |
| **NFR-U1-03** · Invariantes de contrato | **100%**: `deducible ≥ 0` · `Dictamen` con `clausula` · enums cerrados · `ResultadoPoliza` consistente · `aprobado_por` en terminal | cualquier objeto válido que viole un invariante | RNF-05/23, RULE-CTR-03/04/06/07/08 (PBT-03) |
| **NFR-U1-04** · No-invención por construcción | `CampoExtraido.ausente=True ⇒ valor=null` (el contrato **no permite** inventar un valor) | un `CampoExtraido` ausente con valor no nulo | RNF-07 *(re-atribuido — ver nota)* |
| **NFR-U1-05** · Validez del eval de fraude | **100%** de filas etiquetadas-fraude con inconsistencia encodada, o **rechazo** (fail-closed) | una fila etiquetada-fraude sin inconsistencia se emite | RF-31, H-16 🔒, RULE-GEN-02 |

> **Nota de atribución (NFR-U1-04)**: "campos inventados ≈ 0" (RNF-07) es una **métrica de extracción** — su medición vive en **U2** (extractor). U1 no extrae; su generador sintetiza por diseño. En U1, RNF-07 se realiza como el **invariante de contrato** `ausente ⇒ null` (no-invención por construcción). Mismo patrón que `Dictamen`-sin-cláusula (invariante en U1, cálculo en U3).

### Seguridad

| ID | Métrica / target | Condición de fallo | Traza |
|---|---|---|---|
| **NFR-U1-06** · Etiquetado de PII | Los contratos que tocan PII (`Usuario`, campos del aviso) **marcan** qué campos son PII; datos **sintéticos** ⇒ **sin PII real** | un campo PII sin etiquetar (impide minimización aguas abajo) | RNF-11/12, P5, RES-03 |

> El etiquetado de PII en la **fundación** es lo que hace *enforceable* la minimización en U2 (no se puede minimizar lo que no está etiquetado) y da de dónde agarrarse al export-PIA (RNF-21) y al logging-sin-PII (RNF-12). La minimización **efectiva** al LLM se ejerce en U2.

### Mantenibilidad

| ID | Métrica / target | Condición de fallo | Traza |
|---|---|---|---|
| **NFR-U1-07** · Fuente única de tipos | Los contratos compartidos son la **única** definición de sus tipos; **ningún** módulo (U2-U5) redefine un contrato compartido | un módulo define su propia versión de `Caso`/`Poliza`/etc. | Q1-A (fundación), CLAUDE.md (contratos estables antes de agent-teams) |

### Rendimiento (única medida real de U1 — el generador)

| ID | Métrica / target | Condición de fallo | Traza |
|---|---|---|---|
| **NFR-U1-08** · Throughput del generador | Generar el dataset completo (~140-280 casos: ~20-40 × 7 estratos) en **tiempo de build razonable (orden de minutos)** | la generación del dataset tarda un tiempo impráctico para el ciclo de dev | RF-30 (infra-test, no runtime) |

## NFR marcados N/A (honestidad de alcance — P7)

| Atributo | Estado | Rationale |
|---|---|---|
| **Disponibilidad** | **N/A** | U1 es fundación local; **nada se despliega** (RES-02, P7). Prometer uptime sería "demo como producción" — el mismo anti-patrón que Infra Design=SKIP y el SPOF sin HA. |
| **Escalabilidad** | **N/A** | Portafolio, una persona; el generador corre en build. Sin carga de producción que escalar. |
| **Usabilidad** | **N/A en U1** | U1 no tiene UI; usabilidad se evalúa en U4/U5 (bandeja, panel). |

---

## Resumen
NFR de U1 = **correctitud (5), seguridad (1), mantenibilidad (1), rendimiento del generador (1)**; disponibilidad/escalabilidad/usabilidad = **N/A honesto**. Todos los targets aplicables tienen valor verificable y traza a un RNF de Inception. Ninguno es de catálogo.
