# NFR Design Patterns — U1 · Fundaciones & Contratos

> Traduce cada NFR de U1 en un **patrón de diseño concreto** (mecanismo + consecuencias con ⚠️). No intenciones.

---

## PATTERN-U1-01 · Minimización de PII deny-by-default en la frontera
**Realiza**: NFR-U1-06 · RNF-11/12, P5 · coherente con deny-by-default (RNF-14/SECURITY-08).

**Mecanismo** (3 piezas — el marcador solo no basta; el patrón cierra el círculo en el consumo):
1. **Marca tipada por campo**: cada campo PII de un contrato se declara `Annotated[str, PII]` (o `Field(json_schema_extra={"pii": True})`).
2. **Registro introspectable**: una función recorre el modelo y devuelve la lista de campos PII de cada contrato — fuente única de verdad de "qué es PII".
3. **Puntos de consumo que redactan POR DEFECTO** (opt-in para incluir):
   - **`LLMPayloadBuilder`** (se usa en U2): al construir el prompt/payload al LLM, **redacta todos los campos marcados PII salvo whitelist explícita** del caso de uso.
   - **`PIIRedactingLogSerializer`** (transversal, RNF-12): al serializar logs, redacta por la misma marca.

**Por qué deny-by-default y no opt-out**: si mañana se añade un campo PII y se olvida manejarlo, queda **redactado (falla seguro)**, no filtrado. Un opt-out se olvida y filtra.

**Consecuencias**:
- ✅ La minimización pasa de intención a **hecho enforceable**; los consumidores no pueden filtrar PII no-whitelisted por accidente.
- ✅ Coherente con el deny-by-default de autorización (RNF-14/SECURITY-08).
- ⚠️ La whitelist debe mantenerse explícita por caso de uso; si se hace demasiado permisiva se pierde el beneficio (pero el **default protege**).
- ⚠️ Datos sintéticos ⇒ sin PII real (RES-03); el patrón se ejercita igual para que el mecanismo esté probado.

---

## PATTERN-U1-02 · Validación fail-closed (Pydantic estricto)
**Realiza**: NFR-U1-02 · H-17 🔒, SECURITY-05/15.

**Mecanismo**: todos los contratos son modelos Pydantic con **`strict=True` + `extra="forbid"`**. Sin coerción silenciosa: un tipo inválido o un campo desconocido ⇒ `ValidationError` ⇒ **rechazo**. El caso no avanza con datos malformados.

**Nota de dinero (para Code Gen)**: `strict=True` es **doblemente bueno** para `deducible` y `suma_asegurada` — fuerza construir `Decimal` desde `str`/`Decimal`, **no `float`**, evitando la imprecisión de float que rompería el invariante `deducible ≥ 0` (RULE-CTR-04). → Alimentar esos campos como `str`/`Decimal`, nunca `float`, o strict los rechaza (comportamiento correcto).

**Consecuencias**:
- ✅ Fail-closed **por construcción** (la alternativa laxa sería fail-OPEN — acepta malformados, viola NFR-U1-02/H-17/SECURITY-15).
- ✅ Precisión monetaria garantizada (Decimal, no float).
- ⚠️ Los productores deben pasar tipos correctos (money como `str`/`Decimal`); el rechazo ante lo contrario **es** el comportamiento deseado.

---

## PATTERN-U1-03 · Dimensión de vector parametrizada
**Realiza**: acoplamiento embedding↔pgvector (nota del re-check).

**Mecanismo**: el esquema del RAG (tabla pgvector) toma la **dimensión del vector de un parámetro de configuración** (settings), **no hardcodeada**. Se fija al confirmar el modelo de embedding en U2/U3 (embedding local, sentence-transformers — dirección ya fijada en tech-stack).

**Consecuencias**:
- ✅ U1 define la **estructura** del RAG sin pre-comprometer el modelo de embedding.
- ⚠️ Cambiar la dimensión **tras** indexar exige reindexar — pero en U1 no se indexa contenido real todavía (solo estructura), así que el costo es nulo ahora.

---

## Patrones ya decididos (realizaciones de lo aprobado antes)

### PATTERN-U1-04 · `Caso.estado` inmutable salvo vía HITL
**Realiza**: RULE-CTR-05 🔒, P1. **Mecanismo**: `Caso.estado` sin setter público (campo de solo-lectura desde fuera de `hitl`); la única mutación es la máquina de estados de `hitl` (U4). En U1 se expone sin setter. **Consecuencia**: ✅ P1 inevadible por construcción.

### PATTERN-U1-05 · Round-trip garantizado
**Realiza**: NFR-U1-01. **Mecanismo**: `model_dump`/`model_validate` de Pydantic + property-based test (Hypothesis) por contrato. **Consecuencia**: ✅ round-trip verificado, no asumido.

### PATTERN-U1-06 · Generador fail-closed
**Realiza**: NFR-U1-05, RULE-GEN-02 🔒. **Mecanismo**: tras generar una fila etiquetada-fraude, **assert** de inconsistencia encodada; si falta ⇒ excepción (no se emite la fila). **Consecuencia**: ✅ el eval de fraude nunca mide ruido.

### PATTERN-U1-07 · Adapter de dataset
**Realiza**: RULE-GEN-03. **Mecanismo**: puerto `FilaEntrada` (contrato abstracto) + adaptador Kaggle intercambiable. **Consecuencia**: ✅ Plan B del riesgo #1 barato (cambiar adaptador, no generador).

---

## Mapa NFR → Patrón
| NFR | Patrón |
|---|---|
| NFR-U1-01 round-trip | PATTERN-U1-05 |
| NFR-U1-02 fail-closed validación | PATTERN-U1-02 |
| NFR-U1-03 invariantes | PATTERN-U1-02 (strict) + PBT |
| NFR-U1-04 no-invención | contrato `ausente⇒null` (functional design) |
| NFR-U1-05 validez fraude | PATTERN-U1-06 |
| NFR-U1-06 PII | PATTERN-U1-01 |
| NFR-U1-07 fuente única de tipos | contratos compartidos (U1) |
| NFR-U1-08 throughput generador | generación batch en build (sin latencia estricta) |
| RULE-CTR-05 (P1) | PATTERN-U1-04 |
| acoplamiento embedding | PATTERN-U1-03 |
