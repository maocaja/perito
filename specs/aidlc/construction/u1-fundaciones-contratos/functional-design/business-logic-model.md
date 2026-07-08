# Business Logic Model — U1 · Fundaciones & Contratos

> Integra entidades + reglas en **flujos E2E** de la unidad. Descrito en lenguaje de negocio (sin clases/métodos/frameworks). Incluye la sección **Propiedades testables (PBT-01)** que exige la extensión de property-based testing.

---

## Flujo 1: Generación de un caso sintético
### Descripción
A partir de una fila de dataset (vía adapter), producir un caso de demo/eval **completo y consistente**: un aviso es-CO, su póliza sintética y su verdad esperada. Es lo que alimenta todos los estratos de eval.

### Pasos
1. Recibir una `FilaEntrada` desde el adapter (Kaggle u otro — RULE-GEN-03).
2. Derivar los datos del siniestro y construir un `AvisoNormalizado` en español coloquial es-CO.
3. Construir la `Poliza` sintética coherente con el siniestro (vigencia, coberturas, exclusiones, suma asegurada, deducible, cláusulas).
4. **Si la fila está etiquetada como fraude** (RULE-GEN-02 🔒):
   a. Inyectar en el aviso una **inconsistencia detectable** (p. ej. fecha del aviso vs. metadato).
   b. Fijar `GroundTruth.inconsistencia_esperada` con la evidencia de esa inconsistencia.
   c. **Verificar** que la inconsistencia quedó encodada; **si no**, el generador **rechaza/rompe** la fila (fail-closed) y no la emite.
5. Construir el `GroundTruth`: campos esperados, póliza esperada, resultado de cobertura esperado, etiqueta de fraude (+ inconsistencia si aplica).
6. Emitir la terna `(AvisoNormalizado, Poliza, GroundTruth)`.

### Reglas aplicadas
- RULE-GEN-01 (paso 1-6), RULE-GEN-02 🔒 (paso 4), RULE-GEN-03 (paso 1).

### Resultados posibles
- `EMITIDO` → terna consistente producida.
- `RECHAZADO_FAIL_CLOSED` → fila etiquetada-fraude sin inconsistencia encodada → se rompe (no se emite ruido al eval).

---

## Flujo 2: Validación y round-trip de un contrato
### Descripción
Todo dato que cruza entre módulos debe ser válido por construcción. Este flujo gobierna cómo se acepta o rechaza un contrato.

### Pasos
1. Recibir un objeto candidato para un contrato (Extracción, Póliza, Dictamen, etc.).
2. Validar contra el contrato tipado (tipos, rangos, enums cerrados, campos obligatorios).
3. Si **no** valida → **rechazar** ruidosamente; el caso no avanza (RULE-CTR-02 🔒).
4. Si valida → aceptar; el objeto puede serializarse y deserializarse produciendo un valor idéntico (RULE-CTR-01).

### Reglas aplicadas
- RULE-CTR-01 (paso 4), RULE-CTR-02 🔒 (paso 3), RULE-CTR-03/04/06 (invariantes en paso 2).

### Resultados posibles
- `VALIDO` → aceptado, round-trip garantizado.
- `RECHAZADO` → no cumple contrato → fail-closed, no procesa.

---

## Flujo 3: Indexación y recuperación de cláusula
### Descripción
Las pólizas sintéticas se indexan para que grounding (U2) y cobertura (U3) recuperen la cláusula citada.

### Pasos
1. Al alta de una `Poliza`, indexar la póliza y sus `Clausula`s.
2. Ante una consulta, recuperar la `Clausula` aplicable.
3. Entregar la cláusula como fuente citable del dictamen (la cita la usa U3).

### Reglas aplicadas
- RULE-RAG-01.

### Resultados posibles
- `CLAUSULA_RECUPERADA` → disponible para cita (P3).
- `SIN_CLAUSULA` → señal para las unidades consumidoras (grounding/cobertura deciden qué hacer — no es dominio de U1).

---

## Nota sobre `Caso.estado` (frontera U1/U4)
U1 define la **entidad `Caso` y el enum `EstadoCaso`** (el dato). U1 **no** ejecuta transiciones: el estado es inmutable desde fuera de `hitl` (RULE-CTR-05 🔒). Los flujos de transición (`RECIBIDO→EN_PROCESO→…→APROBADO/RECHAZADO`, con `aprobado_por`) se modelan en el `business-logic-model.md` de **U4**.

---

## Propiedades testables (PBT-01)
> Requerido por la extensión PBT. Estas propiedades se implementan como property-based tests (Hypothesis) en Code Generation, con generadores de dominio (PBT-07).

| Contrato / función | Propiedad | Categoría | Regla / fuente |
|---|---|---|---|
| Todos los contratos | `deserializar(serializar(x)) == x` | Round-trip | RULE-CTR-01 (PBT-02) |
| `Dictamen` | siempre tiene `clausula`; si falta → inválido | Invariante | RULE-CTR-03 (H-08 🔒) |
| `Dictamen`, `Poliza` | `deducible ≥ 0` para toda entrada válida | Invariante | RULE-CTR-04 (PBT-03) |
| `EstadoCaso`, `ResultadoCobertura`, `CalidadDoc`, `RolUsuario` | salida siempre ∈ enum | Invariante | RULE-CTR-06 (PBT-03) |
| `ResultadoPoliza` | `encontrada=False ⇒ poliza=None`; `encontrada=True ⇒ poliza≠None` (no forzar match) | Invariante | RULE-CTR-07 🔒 (RF-10, P4) |
| `Usuario` / `Caso` | transición terminal ⇒ `aprobado_por ≠ None` | Invariante | RULE-CTR-08 (P1) |
| Validación de contrato | entrada inválida ⇒ rechazo (nunca acepta malformado) | Invariante | RULE-CTR-02 🔒 |
| Generador | fila etiquetada-fraude ⇒ `GroundTruth.inconsistencia_esperada ≠ None` y encodada; si no ⇒ rechazo | Invariante (fail-closed) | RULE-GEN-02 🔒 |
| Generador | terna `(Aviso, Poliza, GroundTruth)` internamente consistente | Invariante | RULE-GEN-01 |

**Generadores de dominio (PBT-07)**: se definen generadores para `Caso`, `Poliza`, `Dictamen`, `Extraccion`, `FilaEntrada`, `ResultadoPoliza`, `Usuario` que respetan las restricciones de negocio (fechas válidas con `desde ≤ hasta`, montos ≥ 0, enums cerrados, consistencia `encontrada`/`poliza`). No se usan primitivos crudos.

> 💡 **Validación del artefacto**: los flujos están descritos sin mencionar clases, métodos ni frameworks → el modelo de dominio está listo para pasar a NFR/Code Generation.
