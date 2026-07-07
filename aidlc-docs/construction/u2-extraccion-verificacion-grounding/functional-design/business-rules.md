# Business Rules — U2 Extracción·Verificación·Grounding

## Reglas de Extracción (C2 Extractor)

### RULE-EXT-01: Campos Obligatorios

**Definición:** U2 debe extraer siempre estos campos del aviso:
- número_poliza (identificador de póliza)
- fecha_siniestro (cuándo ocurrió)
- tipo_siniestro (AUTO_COLISION, ROBO, INUNDACION, etc — enum U1)
- monto_reclamado (cantidad solicitada)
- nombre_asegurado (quién hace el reclamo)
- cédula_asegurado (identificación; PII)

**Implementación:**
```
campos_esperados = [
  "numero_poliza", "fecha_siniestro", "tipo_siniestro",
  "monto_reclamado", "nombre_asegurado", "cédula_asegurado"
]
extraccion = extractor.extract(aviso, campos_esperados)
```

**Fail-closed:** Si Claude no encuentra un obligatorio:
```
CampoExtraido(nombre="...", ausente=True, valor=None, confianza=0)
```
NO inventar, NO omitir del resultado.

---

### RULE-EXT-02: Campos Opcionales

**Definición:** Enriquecedores pero no críticos:
- teléfono_asegurado
- email_asegurado
- dirección_siniestro
- detalles_tercero (si hay colisión)

**Implementación:** Retorna si está en el texto; si no, ausente=True.

---

### RULE-EXT-03: Confianza por Campo

**Definición:** Claude reporta score 0-100 para cada CampoExtraido.

**Uso:** Señal de escalamiento (P4), NUNCA decide cobertura ni terminal.

**Implementación:**
```
if campo.confianza < umbral_alarma (ej: 30):
  → SeñalEscalamiento(CONFIANZA_BAJA, evidencia=[...])
```

---

### RULE-EXT-04: PII Redacción (P5 PATTERN-U1-01)

**Definición:** El aviso contiene PII (cédula, nombre, email, teléfono). NUNCA se envía crudo al LLM.

**Implementación:**
```
prompt = LLMPayloadBuilder.build_extraction_prompt(
  aviso,
  whitelist=set()  # deny-by-default: todo redactado
)
# prompt contiene "[REDACTED]" para PII
```

**Garantía:** PII solo en logs redactados; audit trail auditable.

---

### RULE-EXT-05: Evidencia de Origen

**Definición:** Cada CampoExtraido.origen cita dónde Claude lo encontró.

**Estructura:**
```
EvidenciaOrigen(
  tipo: enum { TEXTO, ATTACHMENT, INFERRED },  # NO INFERRED (P4)
  referencia: str  # "línea 3 del aviso", "attachment_email_subject", ...
)
```

**Implementación:**
```
origen = EvidenciaOrigen(
  tipo=TipoOrigen.TEXTO,
  referencia="párrafo 2: 'Siniestro el 2025-06-15'"
)
```

---

### RULE-EXT-06: No Inventar (P4 H-06)

**Definición:** Si Claude NO encuentra un campo, marca ausente=True, valor=None.

**Prohibido:**
- Inferir de otros campos (ej: "cédula de email")
- Strings literales "[NO_ENCONTRADO]"
- Defaults silenciosos

**Implementación:**
```
if not found:
  campo = CampoExtraido(
    nombre="...", ausente=True, valor=None,
    confianza=0, origen=...
  )
else:
  campo = CampoExtraido(..., ausente=False, valor=texto, confianza=X)
```

**Validator (de U1):** ausente=True ⇒ valor=None (fail-closed).

---

## Reglas de Verificación (C3 Verifier — Dos Capas)

### RULE-VER-01: Confirmación Adversarial (Capa 1, LLM Sonnet, H-03/RF-07-08)

**Definición:** C3 re-lee AvisoNormalizado redactado y pregunta al LLM (Sonnet): "¿Cada campo extraído está realmente en el texto, o es alucinación de Haiku?"

**Implementación:**
```
def verify_adversarial(extraccion: ExtraccionValidada, aviso_redactado: str):
  prompt = LLMPayloadBuilder.build_verification_prompt(aviso_redactado, extraccion)
  # Prompt: "¿Está confirmado número_poliza='POL-123456' en el texto? Sí/No."
  response = sonnet.complete(prompt)
  
  for campo in extraccion.campos:
    if response[campo.nombre] == "NO":
      → SeñalEscalamiento(VERIFIER_RECHAZA, motivo=f"Alucinación: {campo.nombre} no confirmado")
  return ExtraccionValidada (validada)
```

**Garantías:**
- ✅ P4 (anti-invención): Detecta alucinaciones de Haiku
- ✅ P5 (PII): Redactado via LLMPayloadBuilder (deny-by-default)

---

### RULE-VER-02: Consistencia Interna (Capa 2, Código Determinístico)

**Definición:** Valida que ExtraccionValidada sea plausible internamente (no toca cobertura — eso es U3).

**Reglas específicas:**

1. **Fecha siniestro:**
   ```
   fecha_siniestro ≤ hoy  (no siniestro futuro)
   ```

2. **Monto reclamado:**
   ```
   monto_reclamado > 0 AND monto_reclamado < 1e10  (límite anti-outlier)
   ```

3. **Tipo siniestro:**
   ```
   tipo_siniestro ∈ enum TipoSiniestro  (definido en U1)
   ```

4. **Nombre asegurado:**
   ```
   len(nombre_asegurado) > 0 AND len < 200
   ```

5. **Cédula (si presente):**
   ```
   formato válido (heurístico país — para Colombia: XX-XXXXXXXX-X)
   ```

**Implementación:**
```
def verify_consistency(extraccion: ExtraccionValidada):
  # Código puro, sin LLM
  for campo in extraccion.campos:
    if not validate_rule(campo):
      → SeñalEscalamiento(VERIFIER_RECHAZA, motivo=f"Inconsistencia: {campo.nombre}")
  return ExtraccionValidada (consistente)
```

---

### RULE-VER-03: No Reparar (P3 P4)

**Definición:** Verifier NO altera valores, solo valida.

**Prohibido:**
- Normalizar teléfono silenciosamente
- Convertir formato de fecha
- Autocompletar campos débiles

**Garantía:** P3 (trazabilidad) — todo cambio es explícito, auditable.

---

### RULE-VER-04: Orquestación de C3

**Definición:** C3 es una cascada de dos validaciones; primera alucinación, segunda plausibilidad.

**Flujo:**
```
ENTRADA: ExtraccionValidada (sin validar) + AvisoNormalizado original

PASO 1: Redactar (P5)
  aviso_redactado = LLMPayloadBuilder.build_verification_prompt(aviso_original)

PASO 2: Capa 1 — Confirmación Adversarial (Sonnet)
  resultado = verify_adversarial(extraccion, aviso_redactado)
  if SeñalEscalamiento: return (termina aquí)

PASO 3: Capa 2 — Consistencia Interna (Código)
  resultado = verify_consistency(resultado)
  if SeñalEscalamiento: return

SALIDA: ExtraccionValidada (confirmada + consistente) OR SeñalEscalamiento
```

---

## Reglas de Grounding## Reglas de Grounding (C4 PolicyLookup)

### RULE-POL-01: Match Determinístico (P4 RF-10)

**Definición:** Busca póliza por número_poliza exacto en BD (SQL, determinístico, sin LLM).

**Algoritmo:**
```
1. SELECT poliza FROM polizas WHERE numero = extraccion.numero_poliza
2. If resultado → encontrada=True, poliza={...}
3. If NO resultado → encontrada=False, poliza=None → candidatas
```

**Garantía:** encontrada=True ⇒ poliza es la correcta (no "probablemente").

---

### RULE-POL-02: Candidatas sin Promover (P4 RULE-CTR-07)

**Definición:** Si no hay match exacto, devuelve candidatas (similitud RAG/pgvector) sin elegir automáticamente.

**Estructura ResultadoPoliza:**
```
{
  encontrada: False,
  poliza: None,
  candidatas: [
    { numero: "POL-789", similitud: 0.87, razon: "tipo_siniestro match" },
    { numero: "POL-790", similitud: 0.73, razon: "fecha_vigencia overlap" }
  ]
}
```

**Garantía:** El humano elige en U4 (HITL bandeja). U2 no promueve.

---

### RULE-POL-03: Cláusulas por Referencia (P2 P5)

**Definición:** Si se cita una cláusula (ej: "R1 vigencia", "R3 exclusión"), PolicyLookup recupera de RAG por ID.

**Implementación:**
```
clausula_id = "POL-{numero}_VIGENCIA_001"
clausula = rag.retrieve(clausula_id)
evidencia = EvidenciaOrigen(tipo=RAG_CLAUSE, referencia=clausula_id)
```

**Garantía:** P5 (ref por ID, no texto crudo) + P2 (U3 aplica, U2 recupera).

---

## Reglas de Señalización (Común a C2/C3/C4)

### RULE-SIGNAL-01: Cuándo Emitir SeñalEscalamiento

**Condiciones:**

```
FROM C2 (Extractor):
  - Confianza global < 50% → CONFIANZA_BAJA
  - Campo obligatorio ausente → CAMPO_OBLIGATORIO_FALTANTE

FROM C3 (Verifier):
  - Validación falla → VERIFIER_RECHAZA

FROM C4 (PolicyLookup):
  - Sin match exacto → POLICY_SIN_MATCH
  - Múltiples candidatas → POLICY_MULTIPLES_CANDIDATAS
  - Documento calidad=SUCIO → DOCUMENTO_SUCIO

Todas: U2 emite, U4 escala.
```

---

### RULE-SIGNAL-02: Contrato SeñalEscalamiento (P1 RULE-CTR-05)

**Estructura:**
```
{
  motivo: str,
  tipo: enum {
    CONFIANZA_BAJA,
    VERIFIER_RECHAZA,
    POLICY_SIN_MATCH,
    POLICY_MULTIPLES_CANDIDATAS,
    CAMPO_OBLIGATORIO_FALTANTE,
    DOCUMENTO_SUCIO
  },
  evidencia: list[EvidenciaOrigen],
  datos_contexto: dict (ej: { confianza_promedio: 0.45 })
}
```

**Garantía:** NO setea Caso.estado. Tipado, auditableauditable, pronto para U4.

---

### RULE-SIGNAL-03: Sin Preferencia (P6)

**Definición:** SeñalEscalamiento emite el hecho, no la decisión.

**Prohibido:**
- "Use candidata #2" (sugerir elección)
- "Recomiendo escalar" (opinión)

**Permitido:**
- "Múltiples candidatas: POL-789 (87%), POL-790 (73%)" (datos)
- "Documento sucio, verificar manualmente" (hecho)

**Garantía:** P6 (explicabilidad sin decisión).

---

## Mapa de Reglas → Historias

| Historia | Regla(s) |
|----------|----------|
| H-01 (ingesta) | RULE-EXT-01..06 (extracción completa) |
| H-02 (extracción+contrato) | RULE-EXT-01..05 (C2 Extractor) |
| H-03 (verificación adversarial) | RULE-VER-01..03 (C3 Verifier) |
| H-04 (grounding + candidatas) | RULE-POL-01..03 (C4 PolicyLookup) |
| H-06 (no inventar) | RULE-EXT-06 (ausente=True, P4) |

---

## Restricciones de Invariantes

| Invariante | Regla(s) que lo Cierran |
|-----------|------------------------|
| P1 (HITL) | RULE-SIGNAL-02 (NO setea estado, U4 decide) |
| P2 (Cobertura determinística) | RULE-VER-01 (consistencia ≠ cobertura), RULE-POL-03 (U3 aplica reglas) |
| P3 (Trazabilidad) | RULE-EXT-05 (evidencia de origen), RULE-VER-03 (no reparar silenciosamente) |
| P4 (Terminación acotada) | RULE-EXT-06 (no inventar), RULE-POL-01 (determinístico), RULE-SIGNAL-01 (escala a U4) |
| P5 (PII) | RULE-EXT-04 (redacción LLMPayloadBuilder), RULE-POL-03 (refs por ID) |
| P6 (Explicabilidad) | RULE-SIGNAL-03 (hechos, no preferencia) |

---
