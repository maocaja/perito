# Business Rules — U1 · Fundaciones & Contratos

> Reglas numeradas que gobiernan la unidad. Cada una: descripción · condición · consecuencia · fuente (historia/requisito de Inception).
> U1 gobierna **contratos** (validación/round-trip/invariantes de forma) y el **generador sintético**. Las reglas de negocio de cobertura (R1-R5) viven en U3; las de terminación/HITL en U4 — aquí solo sus **invariantes de contrato**.

## Reglas de Contratos

### RULE-CTR-01: Round-trip de contrato
- **Descripción**: todo contrato debe poder serializarse y deserializarse produciendo un objeto igual al original.
- **Condición**: cualquier objeto de dominio válido (`Caso`, `Poliza`, `Dictamen`, `Extraccion`, `AlertaFraude`, `Cotas`, `GroundTruth`…).
- **Consecuencia**: `deserializar(serializar(x)) == x`. Si no se cumple, el contrato está mal definido (falla PBT-02).
- **Fuente**: H-17, RNF-24 (PBT-02).

### RULE-CTR-02: Validación fail-closed de contrato
- **Descripción**: un objeto/payload que no valida contra su contrato tipado se **rechaza** — no se procesa.
- **Condición**: entrada a cualquier tool/nodo que recibe un contrato.
- **Consecuencia**: la validación **falla ruidosamente**; el caso NO avanza con datos malformados (fail-closed).
- **Fuente**: H-17 🔒, H-02 🔒, RNF-13, SECURITY-05.

### RULE-CTR-03: Dictamen sin cláusula es inválido
- **Descripción**: un `Dictamen` sin `clausula` asociada no es un dictamen válido.
- **Condición**: construcción/validación de cualquier `Dictamen`.
- **Consecuencia**: se rechaza como inválido (el % de dictámenes con cláusula se mantiene en 100%).
- **Fuente**: H-08 🔒, P2/P3, RNF-06. *(El cálculo del dictamen es U3; el invariante de contrato vive en U1.)*

### RULE-CTR-04: Deducible no negativo
- **Descripción**: `deducible` (Poliza) y `deducible_calculado` (Dictamen) nunca son negativos.
- **Condición**: cualquier valor de deducible en un contrato.
- **Consecuencia**: un deducible < 0 es inválido (falla PBT-03).
- **Fuente**: RNF-23 (PBT-03), H-07 🔒.

### RULE-CTR-05: `Caso.estado` inmutable salvo vía HITL  🔒
- **Descripción**: el estado de un `Caso` **solo** cambia a través de la máquina de estados de `hitl` (U4). No existe setter público de `estado`.
- **Condición**: cualquier intento de mutar `Caso.estado` desde un componente distinto de `hitl`.
- **Consecuencia**: prohibido por construcción (sin setter); el estado terminal exige `aprobado_por`. Un camino que mute estado fuera de `hitl` viola P1.
- **Fuente**: P1 (`hitl.md`), nota de endurecimiento Q2, `component-methods.md` (`_transicion_valida`).

### RULE-CTR-06: Salida cerrada de enums
- **Descripción**: `EstadoCaso`, `ResultadoCobertura`, `CalidadDoc` y `RolUsuario` son conjuntos cerrados; solo se aceptan sus valores declarados.
- **Condición**: asignación de un estado, resultado de cobertura, calidad de doc o rol.
- **Consecuencia**: un valor fuera del enum es inválido.
- **Fuente**: RNF-23 (PBT-03), Apéndice C del PRD, Segmento 5.

### RULE-CTR-07: Consistencia de `ResultadoPoliza` (no forzar match)  🔒
- **Descripción**: `ResultadoPoliza` es coherente con la semántica de grounding: `encontrada = True ⇒ poliza ≠ None`; `encontrada = False ⇒ poliza = None` (las candidatas nunca se promueven a match).
- **Condición**: construcción/validación de cualquier `ResultadoPoliza`.
- **Consecuencia**: un `ResultadoPoliza` con `encontrada = False` y `poliza ≠ None` es inválido (violaría "no forzar match", P4). *(La búsqueda es U2; el invariante de contrato vive en U1.)*
- **Fuente**: H-04 🔒, RF-10, **P4**.

### RULE-CTR-08: `aprobado_por` obligatorio en terminal
- **Descripción**: fijar `Caso.estado` a `APROBADO`/`RECHAZADO` requiere un `Usuario` en `aprobado_por`.
- **Condición**: cualquier transición a estado terminal.
- **Consecuencia**: sin `Usuario` no hay firma → la transición se bloquea (fail-closed). *(La transición la ejecuta `hitl` en U4; el contrato del dato — `aprobado_por: Usuario` — se fija aquí en la fundación.)*
- **Fuente**: **P1** (`hitl.md`), H-12 🔒, contrato `Usuario`.

## Reglas del Generador Sintético

### RULE-GEN-01: Fila → caso sintético completo
- **Descripción**: el generador transforma una `FilaEntrada` en un aviso es-CO + su `Poliza` sintética + su `GroundTruth`.
- **Condición**: cada fila de entrada procesada.
- **Consecuencia**: produce la terna `(AvisoNormalizado, Poliza, GroundTruth)` consistente entre sí.
- **Fuente**: H-16, RF-30.

### RULE-GEN-02: Fraude etiquetado ⇒ inconsistencia encodada (FAIL-CLOSED)  🔒
- **Descripción**: si una fila está etiquetada como fraude, el aviso generado **DEBE** encodar una inconsistencia **detectable**.
- **Condición**: `FilaEntrada.etiqueta_fraude == True`.
- **Consecuencia**: el generador **inyecta** la inconsistencia y fija `GroundTruth.inconsistencia_esperada`. Si por cualquier razón produce una fila etiquetada-fraude **sin** inconsistencia detectable, el generador **rechaza/rompe** (fail-closed) — **no** emite la fila. *(Check duro, no suave: si fuera suave, el eval de fraude mediría ruido.)*
- **Fuente**: H-16 🔒, RF-31, nota de endurecimiento Q4, `rules/testing.md` (validez del eval de fraude).

### RULE-GEN-03: Dataset vía adapter (Kaggle intercambiable)
- **Descripción**: el generador consume `FilaEntrada` (contrato abstracto); la fuente concreta (Kaggle) es un **adaptador** que produce `FilaEntrada`.
- **Condición**: ingesta de cualquier dataset de origen.
- **Consecuencia**: cambiar de Kaggle a CUAD/pólizas sintéticas = cambiar el adaptador, sin rediseñar el generador (respeta Plan B del riesgo #1).
- **Fuente**: Q3-A, PRD §12 (riesgo #1), RF-30.

## Reglas de RAG de Pólizas

### RULE-RAG-01: Indexación y recuperación de cláusula
- **Descripción**: `policy_rag` indexa cada `Poliza` con sus `Clausula`s y recupera la cláusula aplicable para grounding/cobertura.
- **Condición**: alta de póliza (indexar) / consulta de cláusula (recuperar).
- **Consecuencia**: la cláusula recuperada es la fuente citada del dictamen (P3).
- **Fuente**: H-04, H-08, RF-29.

---

## Trazabilidad reglas → fuente
| Regla | Fuente Inception | Principio |
|---|---|---|
| RULE-CTR-01 | H-17, RNF-24 | P3 (PBT-02) |
| RULE-CTR-02 🔒 | H-17, H-02, RNF-13 | P4/seguridad (fail-closed) |
| RULE-CTR-03 🔒 | H-08, RNF-06 | P2, P3 |
| RULE-CTR-04 | RNF-23, H-07 | P2 (PBT-03) |
| RULE-CTR-05 🔒 | P1, endurecimiento Q2 | **P1** |
| RULE-CTR-06 | RNF-23, Apéndice C | P2 (PBT-03) |
| RULE-CTR-07 🔒 | H-04, RF-10 | **P4** |
| RULE-CTR-08 | P1, H-12 | **P1** |
| RULE-GEN-01 | H-16, RF-30 | P7 (infra honesta) |
| RULE-GEN-02 🔒 | H-16, RF-31, endurecimiento Q4 | validez eval fraude |
| RULE-GEN-03 | Q3, riesgo #1 | resiliencia |
| RULE-RAG-01 | H-04, H-08, RF-29 | P3 |
