# NFR Design — U2 Extracción·Verificación·Grounding

## Resumen: De Requisitos a Patrones Concretos

NFR Design traduce los requisitos cuantitativos (nfr-requirements.md) en patrones arquitectónicos implementables. Cada patrón resuelve una restricción (P1-P6) o métrica (RNF-02..07).

---

## Patrón 1: PII Redacción (P5, Deny-by-Default)

### Invariante: Frontera Clara

PII **nunca** cruza desde AvisoNormalizado (crudo) hacia LLM. Redacción es **capa 0** antes de cualquier lógica.

### Flujo

```
AvisoNormalizado (crudo)
    ↓
LLMPayloadBuilder.build_extraction_prompt()
    ├─ Lee campos (cédula, nombre, dirección, teléfono)
    ├─ Busca en DEFAULT_PII_SCHEMA
    ├─ Reemplaza valor → [REDACTED]
    └─ Retorna: prompt redactado (número_poliza se mantiene)
    ↓
client.messages.parse(model=..., messages=[{"role": "user", "content": [{"type": "text", "text": prompt_redactado}]}])
```

### Contrato: LLMPayloadBuilder

```python
class LLMPayloadBuilder:
    DEFAULT_PII_SCHEMA = {
        "cedula": True,           # Redactar
        "nombre_asegurado": True, # Redactar
        "nombre_beneficiario": True,
        "direccion": True,
        "telefono": True,
        "email": True,
        "numero_poliza": False,   # NO redactar (crítico para grounding)
    }
    
    def build_extraction_prompt(
        self,
        aviso: AvisoNormalizado,
        pii_schema: Dict[str, bool] = None
    ) -> str:
        """
        Redacta campos PII del aviso antes de pasarlo a C2.
        
        Garantías:
        - Si un campo está en schema[key]=True, su valor se reemplaza con [REDACTED]
        - Si pii_schema no pasado, usa DEFAULT_PII_SCHEMA (deny-by-default)
        - Si redacción falla (excepción), lanza FailedRedactionError
          → No se intenta enviar al LLM
          → U4 escala a REQUIERE_REVISION
        
        Retorna: str con estructura visible pero PII redactada
        """
        pass
    
    def build_verification_prompt(
        self,
        extraccion: ExtraccionValidada,
        aviso_redactado: str,  # Recibe aviso ya redactado
    ) -> str:
        """
        Construye prompt adversarial para C3 Capa 1.
        
        Entrada: aviso redactado (seguro para LLM)
        Tarea: "Re-read this redacted document. Confirm each extracted field
                comes from it (or is marked absent=True). If a field seems
                invented or inconsistent, flag it."
        
        Garantías:
        - PII ya removida (hereda de aviso_redactado)
        - Estructura clara para adversarial re-reading
        
        Retorna: prompt redactado para Sonnet
        """
        pass
```

### Validación (Test: test_redaction_denybydefault.py)

```python
def test_redaction_denybydefault():
    """Inyectar PII, verificar [REDACTED] aparece, nunca valor crudo."""
    
    aviso = AvisoNormalizado(
        numero_poliza="POL-123",
        cedula="9876543210",  # PII
        nombre_asegurado="Juan Pérez",  # PII
        direccion="Calle 5 #10",  # PII
    )
    
    builder = LLMPayloadBuilder()
    prompt = builder.build_extraction_prompt(aviso)
    
    # Assertions fail-closed
    assert "[REDACTED]" in prompt, "PII debe redactarse"
    assert "9876543210" not in prompt, "Cédula NO debe aparecer"
    assert "Juan Pérez" not in prompt, "Nombre NO debe aparecer"
    assert "Calle 5 #10" not in prompt, "Dirección NO debe aparecer"
    assert "POL-123" in prompt, "Número póliza SÍ debe aparecer"
```

---

## Patrón 2: Verificación Adversarial (P1, Anti-Hallucination H-03)

### Invariante: Re-Reading Before Trust

C3 Capa 1 (Sonnet) **no confía en C2 Haiku**. Sonnet re-lee documento redactado y valida cada campo.

### Arquitectura Capa 1

```
Extraccion (output C2)
    ↓
build_verification_prompt(extraccion, aviso_redactado)
    ├─ Incluye aviso redactado completo
    ├─ Incluye extraccion de C2
    ├─ Prompt: "For each field in extraction, confirm it appears in source
                or is marked absent=True. Flag any invention or inconsistency."
    └─ Retorna: prompt estructurado
    ↓
client.messages.parse(
    model="claude-sonnet-5",
    output_format=VerificacionAdversarial
)
    ↓
VerificacionAdversarial:
  - confianza: float [0,1]
  - inconsistencias: List[str]
  - recomendacion: Literal["ACEPTA", "REVISA", "RECHAZA"]
```

### Contrato: VerificacionAdversarial

```python
class VerificacionAdversarial(BaseModel, frozen=True):
    """Salida de C3 Capa 1 (Sonnet adversarial check)."""
    
    confianza: float = Field(
        ge=0.0, le=1.0,
        description="Confianza que extraccion es fiel al source [0,1]"
    )
    
    inconsistencias: List[str] = Field(
        default_factory=list,
        description="Campos que no aparecen en source o parecen inventados"
    )
    
    recomendacion: Literal["ACEPTA", "REVISA", "RECHAZA"] = Field(
        description="Recomendacion para U4: acepta extraccion, revisa manual, rechaza"
    )
```

### Flujo Cascada

```
PASO 1: Redactar
  → LLMPayloadBuilder.build_extraction_prompt(aviso)
  
PASO 2: C2 Extractor (Haiku)
  → client.messages.parse(model="claude-haiku-4-5", output_format=ExtraccionValidada)
  → output: ExtraccionValidada (strict Pydantic)
  
PASO 3: C3 Capa 1 Adversarial (Sonnet)
  → build_verification_prompt(extraccion, aviso_redactado)
  → client.messages.parse(model="claude-sonnet-5", output_format=VerificacionAdversarial)
  → output: VerificacionAdversarial (confianza, inconsistencias)
  
PASO 4: C3 Capa 2 Consistencia (Código)
  → verify_consistency(extraccion)
  → Validaciones determinísticas (no LLM):
    * fecha_siniestro <= hoy
    * monto > 0
    * tipo_siniestro in enum
    * cedula matches regex
  → output: VerificacionConsistencia(checks, aprobado)
  
PASO 5: Decisión cascada (no LLM, U4 decide)
  IF confianza(Sonnet) < CONFIDENCE_THRESHOLD (70%):
    → SeñalEscalamiento(CONFIANZA_BAJA)
    → U4 propone revisión manual
  ELIF inconsistencias found:
    → SeñalEscalamiento(INCONSISTENCIA_DETECTADA)
    → U4 propone revisión manual
  ELIF verify_consistency() falla:
    → SeñalEscalamiento(FORMATO_INVALIDO)
    → U4 propone revisión manual
  ELSE:
    → Extraccion + Señales lista para C4 PolicyLookup
```

---

## Patrón 3: Terminación Acotada (P4)

### Invariantes

- U2 **nunca loopea**. Máximo 1 ronda: C2 → C3 Capa 1 → C3 Capa 2 → C4.
- Si dato faltante/ambiguo: escalar, no inventar.
- Caps duros: `max_tokens_budget=10,000`, `confidence_threshold=70%`.

### Parámetros de Orquestación

```python
class U2Settings:
    # Terminación
    MAX_ROUNDS: int = 1  # Single pass (no re-attempt)
    MAX_TOKENS_BUDGET: int = 10_000  # Duro (suma C2+C3)
    
    # Escala
    CONFIDENCE_THRESHOLD: float = 0.70  # Si < 70% → escalamiento
    
    # Modelos
    EXTRACTOR_MODEL: str = "claude-haiku-4-5"  # De config, no hardcode
    VERIFIER_MODEL: str = "claude-sonnet-5"
    
    EXTRACTOR_MAX_TOKENS: int = 2000
    VERIFIER_MAX_TOKENS: int = 3000
```

### Decisión Terminal (No LLM)

```python
# Pseudocódigo U2 end-to-end
def process_caso(aviso_normalizado: AvisoNormalizado) -> SeñalesYExtraccion:
    """U2: single-pass, no loops, fail-closed escalation."""
    
    # PASO 1: Redactar (P5)
    try:
        prompt_redactado = LLMPayloadBuilder.build_extraction_prompt(aviso_normalizado)
    except FailedRedactionError:
        return SeñalesYExtraccion(
            signals=[SeñalEscalamiento(tipo="PII_REDACTION_FAILED")],
            extraccion=None  # Null
        )
    
    # PASO 2: Extraer (C2)
    try:
        extraccion = client.messages.parse(
            model="claude-haiku-4-5",  # NO effort param
            max_tokens=2000,
            output_format=ExtraccionValidada,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt_redactado}]}]
        )
    except OutputParseError:
        return SeñalesYExtraccion(
            signals=[SeñalEscalamiento(tipo="EXTRACCION_PARSE_FAILED")],
            extraccion=None
        )
    
    # PASO 3: Verificar adversarial (C3 Capa 1)
    try:
        prompt_ver = LLMPayloadBuilder.build_verification_prompt(extraccion, prompt_redactado)
        verificacion = client.messages.parse(
            model="claude-sonnet-5",
            max_tokens=3000,
            output_format=VerificacionAdversarial,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt_ver}]}]
        )
    except OutputParseError:
        return SeñalesYExtraccion(
            signals=[SeñalEscalamiento(tipo="VERIFICACION_PARSE_FAILED")],
            extraccion=extraccion  # Devuelve extraccion, pero con señal
        )
    
    # PASO 4: Validar consistencia (C3 Capa 2, código, no LLM)
    consistencia = verify_consistency(extraccion)
    
    # PASO 5: Decisión cascada (solo señales, no estado terminal)
    signals = []
    
    if verificacion.confianza < 0.70:
        signals.append(SeñalEscalamiento(tipo="CONFIANZA_BAJA", confianza=verificacion.confianza))
    
    if verificacion.inconsistencias:
        signals.append(SeñalEscalamiento(
            tipo="INCONSISTENCIA_DETECTADA",
            inconsistencias=verificacion.inconsistencias
        ))
    
    if not consistencia.aprobado:
        signals.append(SeñalEscalamiento(
            tipo="VALIDACION_FORMATO_FALLO",
            detalles=str(consistencia.checks)
        ))
    
    # Retorna (no loop, no estado terminal, U4 decide)
    return SeñalesYExtraccion(
        signals=signals,
        extraccion=extraccion,
        verificacion=verificacion,
        consistencia=consistencia
    )
```

---

## Patrón 4: HITL (P1 — Human-in-the-Loop)

### Invariante: U2 Nunca Decide

U2 **nunca** escribe Caso.estado, nunca aprueba/rechaza. Solo propone y prepara señales.

### Responsabilidades Claras

| Actor | Qué Hace | Qué NO Hace |
|-------|----------|-----------|
| **U2** | Extrae campos, verifica fuente, genera señales | Decide siniestro, toca Caso.estado |
| **U4** (orquestador) | Lee señales, propone acción (escalamiento, next step) | Aprueba siniestro sin humano |
| **Humano** | Revisa propuesta U4, aprueba/rechaza, firma | Nada automático |

### Contrato: SeñalEscalamiento

```python
class SeñalEscalamiento(BaseModel, frozen=True):
    """Propuesta de U2 → U4 (U4 NO puede ignorar ni transformar)."""
    
    tipo: Literal[
        "CONFIANZA_BAJA",
        "INCONSISTENCIA_DETECTADA",
        "VALIDACION_FORMATO_FALLO",
        "PII_REDACTION_FAILED",
        "EXTRACCION_PARSE_FAILED",
        "VERIFICACION_PARSE_FAILED",
        "POLIZA_NO_ENCONTRADA",
    ]
    
    motivo: str  # Por qué escalamos
    evidencia: str  # Cita de la fuente o check
    datos_contexto: Dict[str, Any] = {}  # Información para humano
    
    # CRÍTICO: SeñalEscalamiento NUNCA toca Caso.estado
    # U4 decide si escalamiento → manual review, no U2
```

### Garantías

- Si U2 genera SeñalEscalamiento(CONFIANZA_BAJA), U4 propone revisión manual.
- Humano en Caso.revisor_asignado revisa y decide.
- Humano escribe Caso.aprobado_por (firma).
- U2 **nunca** participa en esa decisión.

---

## Patrón 5: Trazabilidad (RNF-05, P3)

### Qué se Traza

```python
class MensajeU2(BaseModel, frozen=True):
    """Traza inmutable de cada etapa U2."""
    
    id_caso: str
    timestamp: datetime
    
    # Etapa
    etapa: Literal["REDACCION", "EXTRACCION", "VERIFICACION", "CONSISTENCIA"]
    
    # Entrada redactada (P5 + P3)
    entrada_redactada: str  # Prompt enviado al LLM (nunca PII crudo)
    
    # Salida
    salida_raw: str  # Response del LLM (JSON)
    salida_validada: Optional[dict]  # Parsed + Pydantic validated
    
    # Consumo
    tokens_input: int
    tokens_output: int
    latencia_ms: int
    modelo: str
    
    # Error (si aplica)
    error: Optional[str] = None  # Exception message
    
    # Señales generadas
    senales: List[SeñalEscalamiento] = []
```

### Cómo Fluye a M9 (Langfuse)

```python
from langfuse.decorators import observe

@observe(name="U2_EXTRACCION")
def call_c2_extractor(prompt_redactado: str) -> ExtraccionValidada:
    response = client.messages.parse(model="claude-haiku-4-5", ...)
    
    # Langfuse auto-logs:
    # - Prompt (entrada redactada)
    # - Tokens
    # - Latencia
    # - Output (salida_validada)
    
    return response
```

### Dashboard (M9 → U5 Evals)

Top-3 KPIs trackeados:
1. **Accuracy por campo** (numero_poliza ≥99%, otros ≥90-95%)
2. **Campos inventados** (≈0% fail-closed)
3. **Costo + Latencia** (<$0.05/caso, medido por estrato)

---

## Patrón 6: Constraints & Guardrails

### Restricciones de Código

1. **No imports de rules/** en U2 (P2 coverage-determinism)
   - U2 extrae; U3 decide cobertura (motor R1-R5)
   - U2 puede usar `backend/app/contracts/` (tipos), no logic

2. **Haiku sin effort param** (API reality)
   ```python
   # ✅ Correcto
   response = client.messages.parse(
       model="claude-haiku-4-5",
       max_tokens=2000,
       # NO effort parameter
   )
   
   # ❌ Error
   response = client.messages.parse(
       model="claude-haiku-4-5",
       effort="high",  # 400 Bad Request
   )
   ```

3. **No hardcode de model IDs** (mantenibilidad)
   ```python
   # ❌ Prohibido
   model = "claude-haiku-4-5"  # En código
   
   # ✅ Correcto
   from app.config import settings
   model = settings.EXTRACTOR_MODEL  # De config.py
   ```

4. **C3 Capa 1 pasa por LLMPayloadBuilder** (P5)
   ```python
   # ✅ Correcto — siempre redactar primero
   prompt_ver = LLMPayloadBuilder.build_verification_prompt(...)
   response = client.messages.parse(model="claude-sonnet-5", messages=[...])
   
   # ❌ Prohibido — directamente al LLM sin redactar
   response = client.messages.parse(model="claude-sonnet-5", messages=[aviso_raw, ...])
   ```

5. **Fallback si messages.parse no disponible** (robustez)
   ```python
   try:
       result = client.messages.parse(output_format=...)
   except AttributeError:
       # Fallback: output_config JSON schema
       response = client.messages.create(output_config={"json_schema": ...})
       result = pydantic_model(**json.loads(response.content[0].text))
   ```

---

## Resumen: NFR Design Patterns

| Patrón | Problema | Solución | Código |
|--------|----------|----------|--------|
| **PII Redacción** | P5: PII no debe llegar a LLM | LLMPayloadBuilder deny-by-default | `app/llm/pii_redactor.py` |
| **Verificación Adversarial** | H-03: C2 alucina | C3 Capa 1 re-lee source (Sonnet) | `app/llm/verifier.py` |
| **Terminación Acotada** | P4: loops infinitos | Single-pass, caps duros, escala | `app/orchestrator/u2_handler.py` |
| **HITL** | P1: agente decide solo | Solo señales, U4/humano decide | `app/contracts/senales.py` |
| **Trazabilidad** | P3: decisiones sin evidencia | Prompts + tokens + latencia en M9 | `app/llm/message_log.py` |
| **Guardrails** | Violaciones en código | Config.py, no hardcode, PII check | `app/config.py`, `backend/pyproject.toml` |

---
