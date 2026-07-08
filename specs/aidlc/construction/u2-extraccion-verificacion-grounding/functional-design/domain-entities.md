# Domain Entities — U2 Extracción·Verificación·Grounding

## Visión General

U2 define 3 componentes lógicos (agentes):
1. **Extractor (C2):** LLM extrae campos del AvisoNormalizado
2. **Verifier (C3):** Valida consistencia interna de la extracción
3. **PolicyLookup (C4):** Busca y grounding en póliza

Todos emiten **SeñalEscalamiento** si detectan ambigüedad; **U4 decide escalar** (RULE-CTR-05, P1).

---

## Entidades Principales

### AvisoNormalizado (de U1 — entrada)

```
{
  texto_crudo: str (Annotated[str, PII]),
  calidad: CalidadDoc (enum: LIMPIO, SUCIO)
}
```

**Invariante:** texto_crudo es PII, debe ser redactado antes de ir al LLM (LLMPayloadBuilder).

---

### CampoExtraido (de U1 — componente)

```
{
  nombre: str,                    # "numero_poliza", "fecha_siniestro", etc
  valor: str | None,              # null si ausente=True
  origen: EvidenciaOrigen,        # { tipo, referencia } — dónde salió el campo
  confianza: int (0-100),         # Score Claude por campo
  ausente: bool                   # True ⇒ valor=None (no inventar, P4)
}
```

**Validator (de U1):** `ausente=True ⇒ valor=None` (fail-closed, P4/RULE-GEN-02).

---

### ExtraccionValidada (de U1 — salida de Extractor)

```
{
  campos: list[CampoExtraido]
}
```

**Propiedad:** Todos los campos obligatorios pueden estar presentes o ausentes, pero nunca inventados.

---

### SeñalEscalamiento (NUEVO — tipado)

Contrato que Extractor, Verifier, PolicyLookup emiten cuando detectan ambigüedad:

```
{
  motivo: str,                    # "confianza baja", "inconsistencia detectada", etc
  tipo: enum {
    CONFIANZA_BAJA,
    VERIFIER_RECHAZA,
    POLICY_SIN_MATCH,
    POLICY_MULTIPLES_CANDIDATAS,
    CAMPO_OBLIGATORIO_FALTANTE,
    DOCUMENTO_SUCIO
  },
  evidencia: list[EvidenciaOrigen],  # [{ tipo, referencia }, ...]
  datos_contexto: dict            # info extra (ej: { confianza_promedio: 0.45 })
}
```

**Invariante:** NO setea `Caso.estado`. Solo tipado; U4/hitl lo consume y decide transicionar.

---

### ResultadoPoliza (de U1 — salida de PolicyLookup)

```
{
  encontrada: bool,               # True si match exacto por número_poliza
  poliza: Poliza | None,          # Poliza encontrada (if encontrada=True)
  candidatas: list[Poliza]        # Opciones débiles (encontrada=False), para U4 display
}
```

**Invariante (RULE-CTR-07):** encontrada=True ⇒ poliza ≠ None; encontrada=False ⇒ poliza=None.

**RF-10 (No forzar match):** Si candidatas tienen opciones, U2 NO promueve ninguna automáticamente. El humano elige (U4).

---

## Agentes Lógicos (Componentes)

### C2: Extractor

**Responsabilidad:**
- Recibe AvisoNormalizado (redactado vía LLMPayloadBuilder)
- Invoca Claude Haiku (cost-tiering)
- Retorna ExtraccionValidada

**Contrato:**
```
def extract(aviso: AvisoNormalizado, campos_esperados: list[str]) -> ExtraccionValidada | SeñalEscalamiento:
  # Haiku extrae.
  # Si confianza global < umbral → SeñalEscalamiento(CONFIANZA_BAJA)
  # Si campo obligatorio ausente → SeñalEscalamiento(CAMPO_OBLIGATORIO_FALTANTE)
  # Else → ExtraccionValidada
```

**Garantías:**
- ✅ P5: Usa LLMPayloadBuilder (PII redactada)
- ✅ P4: No inventar — ausente=True ⇒ valor=None
- ✅ P3: Cada campo con EvidenciaOrigen citando fuente

---

### C3: Verifier (Dos Capas: Confirmación Adversarial + Consistencia Interna)

**Responsabilidad:**
- **Capa 1 (LLM Sonnet):** Re-lee AvisoNormalizado redactado via LLMPayloadBuilder, confirma cada campo contra fuente original (P4 anti-alucinación, H-03/RF-07-08, P5)
- **Capa 2 (Código determinístico):** Valida consistencia interna sin LLM (fecha≤hoy, monto>0, tipo∈enum, formato cédula)

**Contrato Capa 1 — Confirmación Adversarial:**
```
def verify_adversarial(
  extraccion: ExtraccionValidada,
  aviso_redactado: str  # salida de LLMPayloadBuilder.build_verification_prompt()
) -> ExtraccionValidada | SeñalEscalamiento:
  # Sonnet re-lee: "¿Cada campo extraído está confirmado en el texto?"
  # Si alucinación detectada → SeñalEscalamiento(VERIFIER_RECHAZA)
  # Else → ExtraccionValidada
```

**Contrato Capa 2 — Consistencia Interna:**
```
def verify_consistency(extraccion: ExtraccionValidada) -> ExtraccionValidada | SeñalEscalamiento:
  # Valida: fecha≤hoy, monto>0, tipo∈enum, nombre≠vacío, cédula válida
  # Código determinístico, sin LLM
  # Si falla → SeñalEscalamiento(VERIFIER_RECHAZA)
  # Else → ExtraccionValidada
```

**Orquestación de C3:**
```
ENTRADA: ExtraccionValidada (sin validar) + AvisoNormalizado original

PASO 1: Redactar (P5)
  aviso_redactado = LLMPayloadBuilder.build_verification_prompt(aviso_original)

PASO 2: Capa 1 — Confirmación Adversarial (Sonnet)
  resultado = verify_adversarial(extraccion, aviso_redactado)
  if SeñalEscalamiento: return (termina)

PASO 3: Capa 2 — Consistencia Interna (Código)
  resultado = verify_consistency(resultado)
  
SALIDA: ExtraccionValidada (confirmada + consistente) OR SeñalEscalamiento
```

**Garantías:**
- ✅ P4: Confirmación adversarial detecta alucinaciones (H-03 anti-invención)
- ✅ P5: Sonnet redactado via LLMPayloadBuilder (deny-by-default)
- ✅ P3: Cita inconsistencia (EvidenciaOrigen + motivo)
- ✅ P2: NO toca vigencia (R1), exclusiones (R3), cobertura → eso es U3

---

### C4: PolicyLookup

**Responsabilidad:**
- Recibe ExtraccionValidada (con número_poliza extraído)
- Busca póliza determinísticamente
- Retorna ResultadoPoliza

**Algoritmo:**
1. número_poliza exacto en BD (SQL) → encontrada=True, poliza={...}
2. Si no hay exacto → búsqueda por similitud (RAG/pgvector retrieval de cláusulas + heurístico)
   → encontrada=False, poliza=None, candidatas=[opciones débiles, ranked]
3. Si documento sucio o sin-match → encontrada=False, emite SeñalEscalamiento

**Contrato:**
```
def lookup(extraccion: ExtraccionValidada) -> ResultadoPoliza | SeñalEscalamiento:
  # Busca número_poliza exacto.
  # Si no hay → candidatas (sin promover).
  # If ambigüedad → SeñalEscalamiento(POLICY_SIN_MATCH o POLICY_MULTIPLES_CANDIDATAS)
  # Else → ResultadoPoliza
```

**Garantías:**
- ✅ P4 (RF-10): No fuerza match. encontrada=False ⇒ poliza=None.
- ✅ P2: RAG recupera cláusulas (info), NO aplica reglas (eso es U3)
- ✅ P5: Refs a cláusulas por ID, no texto crudo

---

## Flujo de Datos de U2

```
AvisoNormalizado (U1)
  ↓ [LLMPayloadBuilder: redacta PII]
  ↓
C2 Extractor (Haiku)
  → ExtraccionValidada | SeñalEscalamiento
  ↓ (if ExtraccionValidada)
  ↓
C3 Verifier
  → ExtraccionValidada | SeñalEscalamiento
  ↓ (if ExtraccionValidada)
  ↓
C4 PolicyLookup
  → ResultadoPoliza | SeñalEscalamiento
  ↓
Caso.extraccion = ExtraccionValidada
Caso.poliza_match = ResultadoPoliza
[AMBOS listos para U3]
```

**Señales → U4:**
```
SeñalEscalamiento (from C2/C3/C4)
  ↓ [NO setea estado]
  ↓
U4 (LangGraph, dueño P4)
  → Decide escalar a REQUIERE_REVISION
  → Emite evento audit
  → Estado muta solo via hitl/ (RULE-CTR-05, P1)
```

---

## Restricciones y Garantías Cruzadas

| Invariante | Cómo lo cierra U2 |
|-----------|-------------------|
| **P1 (HITL)** | SeñalEscalamiento tipado, NO setea estado. Solo U4 muta (RULE-CTR-05). |
| **P2 (Cobertura determinística)** | Verifier (Capa 2) valida consistencia, NO reglas de cobertura. R1-R5 son U3. |
| **P3 (Trazabilidad)** | Cada campo con EvidenciaOrigen. Citas de cláusulas por ID. |
| **P4 (Terminación acotada)** | No inventar (ausente=True), no loops. Escala a U4. |
| **P5 (PII)** | LLMPayloadBuilder redacta antes de LLM. Refs a cláusulas por ID. |
| **P6 (Explicabilidad)** | Señales con motivo + evidencia. No "sugiere" decisión, solo hechos. |

---

## Notas de Implementación

- **C2 (Extractor):** Haiku para costo. Prompt via LLMPayloadBuilder (deny-by-default).
- **C3 (Verifier):** Sonnet (adversarial, mejor reasoning de consistencia).
- **C4 (PolicyLookup):** SQL determinístico + RAG retrieval. NO chat model para "decidir".
- **SeñalEscalamiento:** Contrato tipado, versionable, auditableauditable.

---
