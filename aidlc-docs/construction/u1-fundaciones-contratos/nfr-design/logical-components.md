# Logical Components — U1 · Fundaciones & Contratos

> Componentes lógicos de U1 y cómo integran los patrones NFR. Technology-agnostic; se realizan en Code Generation. Nombra explícitamente los **puntos de consumo** del patrón de PII (donde "marcar PII" se vuelve enforceable).

## Componentes de U1

### C-U1-1 · `contracts` (modelos Pydantic estrictos)
- **Responsabilidad**: los contratos compartidos del sistema (Caso, Poliza, Dictamen, Extraccion, AlertaFraude, Cotas, ResultadoPoliza, Usuario, GroundTruth, FilaEntrada, enums…).
- **Patrones**: PATTERN-U1-02 (strict + extra=forbid), PATTERN-U1-04 (Caso.estado sin setter), PATTERN-U1-05 (round-trip).

### C-U1-2 · `contracts.pii` (marcador + registro de PII)
- **Responsabilidad**: el **tipo marcador** `PII` (`Annotated[str, PII]`) y la **función de registro/introspección** que lista los campos PII de cada contrato.
- **Patrón**: PATTERN-U1-01 (pieza 1-2). Es la **fuente única de verdad** de qué es PII.

### C-U1-3 · `security.redaction` (redactores deny-by-default — frontera de PII)
> Aquí es donde el marcador se vuelve enforceable. Los **puntos de consumo**:
- **`PIIRedactingLogSerializer`** (transversal, se usa desde U1): serializa cualquier objeto a log **redactando por defecto** los campos marcados PII (RNF-12). Definido en la fundación porque el logging es transversal.
- **`LLMPayloadBuilder`** (interfaz definida aquí; **consumido en U2**): contrato para construir el payload al LLM **redactando PII por defecto**, con whitelist explícita opt-in por caso de uso (P5). Se define su semántica deny-by-default en U1 para que U2 la implemente contra el registro de C-U1-2.
- **Patrón**: PATTERN-U1-01 (pieza 3, deny-by-default).

### C-U1-4 · `synthetic` (generador + adapter + inyección fail-closed)
- **Responsabilidad**: transformar `FilaEntrada` → `(AvisoNormalizado, Poliza, GroundTruth)`; inyectar inconsistencia de fraude con assert fail-closed.
- **Sub-piezas**: puerto `FilaEntrada` + `KaggleAdapter` (PATTERN-U1-07); inyector de fraude (PATTERN-U1-06). Dep: **Faker `es_CO`** (realismo superficial).

### C-U1-5 · `rag` (esquema de índice de pólizas — dimensión parametrizada)
- **Responsabilidad**: estructura de indexación de `Poliza`→`Clausula`→vector (RULE-RAG-01). **Solo estructura** en U1 (no embedda contenido real).
- **Patrón**: PATTERN-U1-03 (dimensión del vector como parámetro de config; embedding local diferido a U2/U3).

### C-U1-6 · `config` (settings)
- **Responsabilidad**: parámetros de configuración — incluida la **dimensión del vector** (PATTERN-U1-03) y el locale del generador.

## Integración (flujo de patrones)
```
FilaEntrada --KaggleAdapter--> synthetic --(inyección fail-closed)--> (Aviso, Poliza, GroundTruth)
                                                                          |
contracts (strict) <--valida/round-trip-- todos los objetos             Poliza --> rag (dim param)
      |
   contracts.pii (registro) --> security.redaction (deny-by-default)
                                    ├── PIIRedactingLogSerializer (logs, U1+)
                                    └── LLMPayloadBuilder (payload LLM, U2)
```

## Fronteras y notas
- **Deny-by-default de PII**: los dos redactores redactan por defecto; incluir un campo PII es opt-in explícito → fail-closed.
- **`LLMPayloadBuilder`** tiene su **interfaz/semántica** en U1 pero su **implementación** en U2 (U1 no llama al LLM). Se nombra aquí para fijar el contrato deny-by-default en la fundación.
- **`rag`** en U1 = estructura; el modelo de embedding y la dimensión concreta se confirman en U2/U3.
- Ningún componente de U1 muta `Caso.estado` (solo `hitl`/U4).

## Componentes de infraestructura (para Infrastructure Design — Actividad 4)
- **PostgreSQL + pgvector** (casos/estados + índice de pólizas) — cifrado local (SECURITY-01).
- **docker-compose** (postgres/pgvector + langfuse) como entorno de dev — se detalla en Infrastructure Design / Code Generation.
