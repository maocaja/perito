# Business Logic Model — U2 Extracción·Verificación·Grounding

## Flujos E2E de U2

### Flujo Happy Path

```
ENTRADA: Caso.aviso = AvisoNormalizado(texto_crudo, calidad)

PASO 1: LLMPayloadBuilder Redacta (P5)
  aviso_redactado = LLMPayloadBuilder.build_extraction_prompt(aviso)
  # texto_crudo → "[REDACTED]", refs a cláusulas por ID

PASO 2: C2 Extractor (Haiku)
  campos_esperados = ["numero_poliza", "fecha_siniestro", "tipo_siniestro",
                      "monto_reclamado", "nombre_asegurado", "cédula_asegurado"]
  extraccion = extractor.extract(aviso_redactado, campos_esperados)
  # Retorna: ExtraccionValidada {
  #   campos: [
  #     CampoExtraido(nombre="numero_poliza", valor="POL-123456", confianza=95, ...),
  #     CampoExtraido(nombre="fecha_siniestro", valor="2025-06-15", confianza=90, ...),
  #     ...
  #   ]
  # }

PASO 3: C3 Verifier (Sonnet)
  verificada = verifier.verify(extraccion)
  # Valida: fecha ≤ hoy, monto > 0, tipo ∈ enum, nombre ≠ vacío, cédula válida
  # → ExtraccionValidada (sin cambios si pasa)

PASO 4: C4 PolicyLookup (SQL + RAG)
  resultado_poliza = policy_lookup(verificada)
  # 1. SELECT FROM polizas WHERE numero = "POL-123456" → FOUND
  # 2. Retorna: ResultadoPoliza {
  #      encontrada: True,
  #      poliza: Poliza(...),
  #      candidatas: []
  #    }

SALIDA: Caso con:
  Caso.extraccion = ExtraccionValidada ✅
  Caso.poliza_match = ResultadoPoliza(encontrada=True) ✅
  → Listo para U3 (motor R1-R5)

FIN FLUJO HAPPY PATH
```

---

### Flujo de Error: Confianza Baja (C2)

```
ENTRADA: Caso.aviso con texto confuso/incompleto

PASO 1-2: Extractor ejecuta
  extraccion = ExtraccionValidada {
    campos: [
      CampoExtraido(nombre="numero_poliza", valor=None, ausente=True, confianza=10),
      CampoExtraido(nombre="fecha_siniestro", valor="...", confianza=25),
      ...
    ]
  }
  confianza_promedio = 30% < umbral_alarma (50%)

PASO 3: Verifier rechaza
  ✗ fecha_siniestro confusa → ValidationError
  
  → SeñalEscalamiento {
      motivo: "Extracción poco confiable + campo fecha ambiguo",
      tipo: CONFIANZA_BAJA,
      evidencia: [
        EvidenciaOrigen(tipo=VALIDACION, referencia="fecha_siniestro: formato ambiguo"),
        ...
      ],
      datos_contexto: { confianza_promedio: 0.30 }
    }

SALIDA A U4:
  SeñalEscalamiento ✅
  Caso.estado = NO CAMBIA (U2 no muta)
  → U4/hitl decide escalar a REQUIERE_REVISION

FIN FLUJO ERROR (CONFIANZA_BAJA)
```

---

### Flujo de Error: Campo Obligatorio Faltante (C2)

```
ENTRADA: Aviso sin número de póliza (técnico)

PASO 1: Extractor ejecuta
  extraccion = ExtraccionValidada {
    campos: [
      CampoExtraido(nombre="numero_poliza", valor=None, ausente=True, confianza=0),
      ...
    ]
  }

PASO 2: Verifier valida
  // No detecta "obligatorio faltante" — eso es responsabilidad de Extractor

PASO 3: C4 PolicyLookup intenta
  número_poliza = None
  → Falla búsqueda SQL
  
  → SeñalEscalamiento {
      motivo: "Campo obligatorio 'numero_poliza' ausente — no se puede localizar póliza",
      tipo: CAMPO_OBLIGATORIO_FALTANTE,
      evidencia: [
        EvidenciaOrigen(tipo=EXTRACTOR, referencia="numero_poliza no extraído del aviso"),
        ...
      ]
    }

SALIDA A U4:
  SeñalEscalamiento ✅
  → U4/hitl decide escalar a REQUIERE_REVISION

FIN FLUJO ERROR (CAMPO_OBLIGATORIO_FALTANTE)
```

---

### Flujo de Error: Sin Match de Póliza (C4)

```
ENTRADA: Extracción correcta, pero número_poliza no existe en BD

PASO 1-3: Happy path hasta Verifier
  ExtraccionValidada ✅

PASO 4: C4 PolicyLookup ejecuta
  numero_poliza = "POL-999999"
  SELECT * FROM polizas WHERE numero = "POL-999999" → NO ENCONTRADO
  
  // Busca candidatas por similitud (RAG)
  candidatas = rag.search_by_similarity(extraccion) → [
    { numero: "POL-999998", similitud: 0.62 },
    { numero: "POL-100000", similitud: 0.51 }
  ]
  
  → SeñalEscalamiento {
      motivo: "Número de póliza no encontrado exacto — se retornan candidatas",
      tipo: POLICY_MULTIPLES_CANDIDATAS,
      evidencia: [
        EvidenciaOrigen(tipo=POLICY_LOOKUP, referencia="candidatas de similitud"),
        ...
      ],
      datos_contexto: {
        numero_solicitado: "POL-999999",
        candidatas: [
          { numero: "POL-999998", similitud: 0.62 },
          { numero: "POL-100000", similitud: 0.51 }
        ]
      }
    }

SALIDA A U4:
  ResultadoPoliza {
    encontrada: False,
    poliza: None,
    candidatas: [...]  ← Para que humano elige en U4
  } + SeñalEscalamiento
  → U4/hitl decide: mostrar candidatas al usuario, o escalar

FIN FLUJO ERROR (POLICY_MULTIPLES_CANDIDATAS)
```

---

### Flujo de Error: Documento Sucio (H-03)

```
ENTRADA: Caso.aviso con calidad = CalidadDoc.SUCIO

PASO 1: Extractor nota calidad
  if aviso.calidad == CalidadDoc.SUCIO:
    → SeñalEscalamiento {
        motivo: "Documento de calidad SUCIO — verificación manual recomendada",
        tipo: DOCUMENTO_SUCIO,
        evidencia: [...]
      }

SALIDA A U4:
  SeñalEscalamiento ✅
  → U4/hitl decide escalar

FIN FLUJO ERROR (DOCUMENTO_SUCIO)
```

---

## Decisiones Clave con Trampa Señalada

### Decisión 1: ¿Quién Setea Caso.estado?

```
❌ INCORRECTO:
  def extract(...):
    ...
    if confianza < umbral:
      caso.estado = EstadoCaso.REQUIERE_REVISION  ← TRAMPA P1
      return caso
  
✅ CORRECTO:
  def extract(...):
    ...
    if confianza < umbral:
      return SeñalEscalamiento(...)  ← U4 decide estado
```

**Por qué:** RULE-CTR-05 (P1). Solo hitl/ (U4) muta Caso.estado. U2 emite tipado, U4 consume.

---

### Decisión 2: ¿Verifier Valida Cobertura?

```
❌ INCORRECTO:
  def verify(extraccion):
    ...
    # Valida si aplica R1 vigencia
    vigencia = poliza.vigencia
    if fecha_siniestro NOT IN vigencia:
      raise ValidationError("no cubre — R1")  ← TRAMPA P2
    return extraccion
  
✅ CORRECTO:
  def verify(extraccion):
    ...
    # Valida si fecha es válida en sí misma
    if fecha_siniestro > hoy:
      raise ValidationError("fecha futura")  ← Consistencia, no cobertura
    return extraccion
    # R1 vigencia la aplica U3 (determinístico)
```

**Por qué:** P2. La cobertura la decide el motor R1-R5 (U3), nunca el LLM. Verifier = consistencia de extracción.

---

### Decisión 3: ¿PolicyLookup Promueve Candidata?

```
❌ INCORRECTO:
  def lookup(extraccion):
    numero = extraccion.numero_poliza
    candidatas = rag.search(numero)
    mejor = max(candidatas, key=lambda x: x.similitud)  ← TRAMPA P4
    return ResultadoPoliza(encontrada=True, poliza=mejor)
  
✅ CORRECTO:
  def lookup(extraccion):
    numero = extraccion.numero_poliza
    exacta = sql_lookup(numero)
    if exacta:
      return ResultadoPoliza(encontrada=True, poliza=exacta)
    else:
      candidatas = rag.search(numero)
      return ResultadoPoliza(encontrada=False, poliza=None, candidatas=candidatas)
      # Human en U4 elige
```

**Por qué:** RF-10 (no forzar match) + RULE-CTR-07. encontrada=True solo con determinismo (SQL exacto). Candidatas son info para humano.

---

### Decisión 4: ¿LLM Redactado?

```
❌ INCORRECTO:
  def extract(aviso):
    prompt = f"Extract: {aviso.texto_crudo}"  ← PII en prompt (viola P5)
    response = claude.complete(prompt)
  
✅ CORRECTO:
  def extract(aviso):
    prompt = LLMPayloadBuilder.build_extraction_prompt(aviso)
    # prompt contiene "[REDACTED]" para PII
    response = claude.complete(prompt)
```

**Por qué:** P5 (PII minimization). LLMPayloadBuilder deny-by-default redacta antes de enviar.

---

### Decisión 5: ¿Verifier Repara?

```
❌ INCORRECTO:
  def verify(extraccion):
    for campo in extraccion.campos:
      if campo.nombre == "telefono":
        campo.valor = normalize_phone(campo.valor)  ← Altera silenciosamente
    return extraccion
  
✅ CORRECTO:
  def verify(extraccion):
    for campo in extraccion.campos:
      if campo.nombre == "telefono":
        try:
          validate_phone(campo.valor)
        except ValueError:
          return SeñalEscalamiento(...)  ← Emite, no repara
    return extraccion
```

**Por qué:** P3 (trazabilidad) + P4 (no-invención). Todo cambio auditable, explícito.

---

## Matriz de Responsabilidades

| Responsabilidad | C2 Extractor | C3 Verifier | C4 PolicyLookup | U4/hitl |
|-----------------|--------------|-------------|-----------------|---------|
| Extraer campos | ✅ | — | — | — |
| Validar consistencia interna | — | ✅ | — | — |
| Buscar póliza | — | — | ✅ | — |
| Validar cobertura (R1-R5) | — | — | — | ✗ (U3) |
| Decidir escalamiento | ✅ (emite) | ✅ (emite) | ✅ (emite) | ✅ (consume + transiciona) |
| Mutar Caso.estado | ✗ | ✗ | ✗ | ✅ |
| Redactar PII | ✅ (via LLMPayloadBuilder) | ✅ | ✅ | ✅ |

---

## Escenarios Complejos

### Caso: Documento Sucio + Confianza Baja

```
ENTRADA: Aviso con calidad=SUCIO + texto confuso

PASO 1: Extractor nota
  if aviso.calidad == SUCIO AND confianza < 50%:
    → SeñalEscalamiento {
        tipo: DOCUMENTO_SUCIO,  # o CONFIANZA_BAJA (primero que dispare)
        motivo: "Ambigüedad: documento sucio + confianza baja",
        evidencia: [...]
      }

SALIDA: U4 ve dos razones para escalar.
```

### Caso: Múltiples Candidatas + Documento Sucio

```
ENTRADA: Extracción OK, pero documento=SUCIO + múltiples candidatas

PASO 4: PolicyLookup emite
  → SeñalEscalamiento {
      tipo: POLICY_MULTIPLES_CANDIDATAS,
      motivo: "Sin match exacto; documento sucio agrava ambigüedad",
      evidencia: [...]
    }

SALIDA: U4 debe validar manualmente candidatas + documento.
```

---

## Propiedades Verificables (Testables)

### PBT-01: Round-Trip Extracción

```
Propiedad: AvisoNormalizado → Extractor → ExtraccionValidada 
  → campos conserva estructura (all campos en lista, ausente coherente)
  → model_dump() → model_validate() == original (round-trip)
```

### PBT-02: No-Invención

```
Propiedad: if campo.ausente=True, then campo.valor=None
  (validator en U1 cierra esto)
```

### PBT-03: Señal Tipado

```
Propiedad: SeñalEscalamiento siempre tiene motivo + tipo + evidencia
  (strict=True, extra="forbid" en U1)
```

### Failsafe-01: Verifier No Repara

```
Propiedad: verify(X) → X (no muta valores)
```

### Failsafe-02: Caso.estado No Cambia

```
Propiedad: extract/verify/lookup jamás toca Caso.estado
  (linting: grep -r "caso.estado =" app/extraction/ → 0 matches)
```

---
