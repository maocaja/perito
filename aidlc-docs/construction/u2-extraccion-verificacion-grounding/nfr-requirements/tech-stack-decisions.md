# Tech Stack Decisions — U2 Extracción·Verificación·Grounding

## Overview

U2 integra **dos llamadas LLM sintéticas** (C2: extracción, C3: verificación) orquestadas por LangGraph. Stack minimalista, cloud-agnostic MVP.

---

## LLM — Anthropic Claude

### Modelos Seleccionados

| Componente | Modelo | Rationale |
|------------|--------|-----------|
| **C2 Extractor** | `claude-haiku-4-5-20250108` | Velocidad + costo (200K ctx). No soporta `effort` param. |
| **C3 Verifier Capa 1** | `claude-sonnet-5-20250514` | Razonamiento adversarial (anti-hallucination H-03). 1M ctx. Adaptive thinking ON by default. |
| **C3 Verifier Capa 2** | N/A (código Python) | Validaciones determinísticas (no LLM). |

**Configuración:** Model IDs en `backend/app/config.py` (não hardcoded). Facilita cambio sin redeploy.

### Anthropic SDK — Versión Mínima

| Aspecto | Especificación | Notas |
|--------|-----------------|-------|
| **Feature crítica** | `client.messages.parse(output_format=...)` | Validación automática contra Pydantic; retorna struct tipado. |
| **Fallback** | `output_config={"format": {"json_schema": ...}}` + `json.loads` + validar contra Pydantic | Si `messages.parse` no disponible en piso versión. |
| **Versión mínima** | **TBD — VERIFICAR EN CODE GEN (Step 7)** | Asumido 0.42.0 puede estar bajo. Pinear a versión conocida-buena con messages.parse probada. |
| **Constraint** | anthropic >= X.Y.Z (verificado) | Documentar en `backend/pyproject.toml` con rationale. |

**FLAG CRÍTICO:** 0.42.0 (asumido inicial) puede NO soportar `messages.parse`. Durante Step 7 (Code Gen):
1. Revisar anthropic SDK changelog/docs → versión mínima que introduce messages.parse/output_config
2. Probar la versión mínima candidata (ej. 0.27.0, 0.30.0, etc) contra un call simple con output_format
3. Pinear a versión verificada o más reciente (ej. 0.42.0+ si comprobado, o 0.50.x si msg.parse reciente)
4. Documentar rationale en comentario `backend/pyproject.toml`

---

## Arquitectura de Llamadas LLM

### C2 Extractor (Haiku)

```python
# Pseudocódigo
response = client.messages.parse(
    model="claude-haiku-4-5-20250108",
    max_tokens=2000,
    system=[...],  # Instrucciones extracción
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_redactado_via_LLMPayloadBuilder}
            ]
        }
    ],
    output_format=ExtraccionValidada  # Pydantic model
)
# Retorna: ExtraccionValidada (fail-closed si no valida)
```

**Restricción:** `claude-haiku-4-5` NO soporta parámetro `effort` (error si pasado).

### C3 Verifier Capa 1 — Confirmación Adversarial (Sonnet)

```python
# Pseudocódigo
response = client.messages.parse(
    model="claude-sonnet-5-20250514",
    max_tokens=3000,
    system=[...],  # Adversarial challenge: "re-read source, confirm each field"
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_verificacion_redactado_via_LLMPayloadBuilder}
            ]
        }
    ],
    output_format=VerificacionAdversarial  # Pydantic model
)
# Retorna: VerificacionAdversarial (confianza, inconsistencias, recomendación)
```

**Comportamiento Sonnet 5:**
- Adaptive thinking ON por defecto (razonamiento mejorado)
- `budget_tokens` parámetro ELIMINADO (ya no válido)
- Non-default sampling params (temperature, top_p, etc) rechazadas si conflictan con adaptive thinking
- messages.parse soportado

### C3 Verifier Capa 2 — Validación Determinística (Python)

```python
# Pseudocódigo
def verify_consistency(extraccion: ExtraccionValidada) -> VerificacionConsistencia:
    # Sin LLM
    checks = [
        fecha_siniestro <= datetime.now(),
        monto_siniestro > 0,
        tipo_siniestro in TipoSiniestroEnum,
        cedula matches regex,
        numero_poliza non-empty
    ]
    return VerificacionConsistencia(checks=checks, aprobado=all(checks))
```

---

## Seguridad — PII Redacción (P5, Deny-by-Default)

### LLMPayloadBuilder — Capa de Redacción

**Ubicación:** `backend/app/llm/pii_redactor.py`

**Interfaz:**
```python
class LLMPayloadBuilder:
    def build_extraction_prompt(
        self, 
        aviso: AvisoNormalizado, 
        pii_schema: Dict[str, bool] = DEFAULT_PII_SCHEMA
    ) -> str:
        # Redacta campos PII según schema (deny-by-default)
        # Retorna: prompt con [REDACTED] en lugar de valores sensibles
        
    def build_verification_prompt(
        self, 
        extraccion: ExtraccionValidada,
        aviso_redactado: str
    ) -> str:
        # Redacta verification prompt; mantiene estructura para adversarial
```

**Política PII (Deny-by-Default):**
- Cédula, nombre, dirección, teléfono → [REDACTED]
- Número póliza → PASA (no-PII crítico)
- Si redacción falla → no enviar al LLM, escalar (P1+P4)

**Validación:**
- `test_redaction_denybydefault.py`: inyecta PII en prompt, verifica [REDACTED] aparece, nunca valor crudo
- Spot-check logs (M9/Langfuse)

---

## Base de Datos — PolicyLookup (C4)

| Aspecto | Especificación |
|---------|-----------------|
| **Base** | PostgreSQL (MVP local docker-compose) |
| **Tabla crítica** | `policies` (numero_poliza PK, vigencia, cobertura) |
| **Query C4** | SELECT * FROM policies WHERE numero_poliza = ?; cached 1h |
| **Fallback** | Si no encontrado → SeñalEscalamiento (POLIZA_NO_ENCONTRADA) |

**Nota:** No es responsabilidad de U2 construir datos; U4 orquesta lookup. Si no hay BD, C4 retorna stub.

---

## Observabilidad — LangGraph + Langfuse (M9)

| Layer | Tool | Qué Traza |
|-------|------|----------|
| **Graph execution** | LangGraph StateGraph | Transiciones nodo (C2 → C3 Capa 1 → C3 Capa 2 → C4) |
| **LLM calls** | Langfuse (M9) | Prompts redactados (entrada), tokens_used, latencia, modelo, output |
| **Business metrics** | Custom logs + M9 | accuracy, campos inventados, confianza, SeñalEscalamiento |

**Restricción:** Langfuse pide API keys (ej. Langfuse Cloud) o self-hosted. MVP sin API → logs a stdout + opcionalmente a archivo.

---

## Dependencias de Proyecto

### backend/pyproject.toml — Nuevas para U2

```
# Externo a U1
anthropic >= X.Y.Z  # TBD en Code Gen: verificar messages.parse support
pydantic >= 2.0     # Strict validation (inherit U1)
langchain >= 0.1.0  # LangGraph (inherit U1 si existe)
langfuse >= 0.6.0   # Observabilidad (opcional MVP)
python >= 3.10

# Internal (U1 containers)
backend/app/contracts/
backend/app/llm/  # NEW: pii_redactor.py + template dir
backend/app/rules/ # Hereda U3 (no U2)
backend/app/orchestrator/ # Hereda U4
```

**Cambio clave:** anthropic NO estaba en U1 (no se usaba LLM). Es NUEVA para U2.

---

## Arquitectura de Configuración

### app/config.py

```python
class Settings(BaseSettings):
    # LLM Models (NO hardcoded en código)
    EXTRACTOR_MODEL: str = "claude-haiku-4-5-20250108"
    VERIFIER_MODEL: str = "claude-sonnet-5-20250514"
    
    # LLM Behavior
    EXTRACTOR_MAX_TOKENS: int = 2000
    VERIFIER_MAX_TOKENS: int = 3000
    CONFIDENCE_THRESHOLD: float = 0.7  # Umbral cuand escalar
    
    # Orchestration (P4)
    MAX_ROUNDS: int = 3  # Cap rondas orquestador
    MAX_TOKENS_BUDGET: int = 10000  # Cap tokens total U2
    
    # Database
    POLICY_DB_URL: str = "postgresql://..."
    
    # Observabilidad
    LANGFUSE_API_KEY: str = ""  # Vacio si MVP local
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"  # Lee de .env si existe
```

---

## Stack — Decisiones Justificadas

| Aspecto | Opción | Alternativa | Por Qué |
|--------|--------|------------|--------|
| **LLM Provider** | Anthropic Claude | OpenAI GPT, Cohere | Soporte para structured output (messages.parse), caché tokens (costo), eval framework DeepEval integración |
| **Verifier LLM** | Sonnet (razonamiento) | Haiku (costo) | Adversarial H-03 exige razonamiento; Sonnet costo justificado (~$0.03-0.015/caso). Haiku insuficiente. |
| **Orchestration** | LangGraph | Airflow, DAG local | LangGraph nativo a modelo agentic; Airflow overkill MVP |
| **PII Redaction** | Deny-by-default código | LLM redaction | Fail-closed; no depende LLM para criticidad P1/P5 |
| **Database** | PostgreSQL local | SQLite, mock | Escalable si Production; mock insuficiente (grounding requiere B.D. real) |
| **Observability** | Langfuse + logs | DataDog, custom | Langfuse integración nativa LangGraph; MVP sin cloud SLA |

---

## Fallback Strategies (Robustez)

### Si messages.parse No Disponible

```python
import json
import anthropic

# Fallback: output_config JSON schema
response = client.messages.create(
    model="...",
    max_tokens=2000,
    output_config={
        "type": "json",
        "json_schema": {
            "type": "object",
            "properties": {
                "numero_poliza": {"type": "string"},
                ...
            },
            "required": [...]
        }
    },
    ...
)

# Manual validation
output_dict = json.loads(response.content[0].text)
extraccion = ExtraccionValidada(**output_dict)  # Pydantic validation
```

---

## N/A — Fuera del Stack MVP

- **Cloud hosting (P7):** Single region, no HA. U5 owns.
- **Caching distribuido:** Single process, no Redis. Caché HTTP Headers vía app/config.
- **Live dashboard:** Metrics to U5 evals harness, no UI. U5 owns UI.
- **CDN, DDoS protection:** N/A MVP.

---
