# Code Generation Plan — U2 Extracción·Verificación·Grounding

## Resumen: Primero Código Real Que Llama a Claude

U2 Code Gen es **el paso crítico**: inyecta primeras llamadas a LLM con restricciones P1-P6.
Artefactos anteriores (Functional Design, NFR, Infrastructure) definen qué construir.
Ahora: **verificar que el código respeta los guardrails** mientras se genera.

---

## 6 Gates Verificación Crítica

### Gate 1: Anthropic SDK Versioning (No Asumir 0.42.0)

**Acción:** Verificar exact minimum version soporta `messages.parse(output_format=...)`

```bash
# Step 7.1: Investigar changelog anthropic SDK
# Candidatos históricos:
# - 0.27.0: Primera versión con messages.parse?
# - 0.30.0: Structured output stable?
# - 0.40.0+: Messages.parse confirmado?

# Prueba:
python3 << 'TESTPARSE'
import anthropic
from typing import Optional

client = anthropic.Anthropic(api_key="test")

# Test: ¿messages.parse existe?
if hasattr(client.messages, 'parse'):
    print("✅ messages.parse disponible")
else:
    print("⚠️ messages.parse NO disponible — usar fallback output_config")
TESTPARSE

# Resultado: determinar versión mínima verificada
# Actualizar backend/pyproject.toml:
# anthropic >= X.Y.Z  # Verified: messages.parse + output_config working
```

**Guardrail:** Si versión < X.Y.Z o messages.parse no funciona:
- Usar fallback: `output_config={"json_schema": {...}}` + `json.loads` + Pydantic validation
- Documentar en comentario por qué fallback (versión insuficiente)

**Checkpoint:** Antes de escribir C2/C3 calls, confirmar versión.

---

### Gate 2: Model IDs en config.py (No Hardcode)

**Acción:** Revisar que IDs aparecen SOLO en app/config.py, nunca en código lógica

```bash
# Step 7.2: Grep para detectar hardcodes
grep -r "claude-haiku-4-5" backend/app/ --include="*.py"   | grep -v "config.py" | grep -v "__pycache__" || echo "✅ No hardcodes en app/"

grep -r "claude-sonnet-5" backend/app/ --include="*.py"   | grep -v "config.py" | grep -v "__pycache__" || echo "✅ No hardcodes en app/"
```

**Estructura correcta:**

```python
# ✅ app/config.py
class Settings(BaseSettings):
    EXTRACTOR_MODEL: str = "claude-haiku-4-5"
    VERIFIER_MODEL: str = "claude-sonnet-5"

# ✅ app/llm/extractor.py
from app.config import settings

def call_c2_extractor(prompt: str):
    response = client.messages.parse(
        model=settings.EXTRACTOR_MODEL,  # AQUÍ
        ...
    )
```

**Checkpoint:** grep limpio → model IDs leídos de config, no hardcodeados.

---

### Gate 3: Haiku Sin Effort Parameter

**Acción:** Revisar código C2 y confirmar NO pasa `effort` param (400 error)

```bash
# Step 7.3: Grep para "effort"
grep -r "effort" backend/app/llm/extractor.py || echo "✅ Sin effort en C2"
```

**Estructura correcta:**

```python
# ✅ Correcto (Haiku 4.5)
response = client.messages.parse(
    model="claude-haiku-4-5",
    max_tokens=2000,
    # NO effort param
    messages=[...],
    output_format=ExtraccionValidada
)

# ❌ Error (causaría 400 Bad Request)
response = client.messages.parse(
    model="claude-haiku-4-5",
    effort="high",  # PROHIBIDO
    ...
)
```

**Nota en código:**
```python
# app/llm/extractor.py
def call_c2_extractor(...):
    """
    C2 Extractor (Haiku 4.5).
    
    IMPORTANTE: claude-haiku-4-5 NO soporta parámetro 'effort'.
    Si pasado, causaría 400 Bad Request. Usar defaults.
    """
    response = client.messages.parse(
        model=settings.EXTRACTOR_MODEL,  # claude-haiku-4-5
        max_tokens=settings.EXTRACTOR_MAX_TOKENS,
        # effort param OMITIDO intencionalmente
        ...
    )
```

**Checkpoint:** Búsqueda "effort" limpia, nota presente en código.

---

### Gate 4: C3 Capa 1 Pasa Por LLMPayloadBuilder (P5)

**Acción:** Revisar que C3 Capa 1 SIEMPRE redacta antes de llamar Sonnet

```bash
# Step 7.4: Verificar flujo C3 Capa 1
# Estructura esperada:
#   1. LLMPayloadBuilder.build_verification_prompt(extraccion, aviso_redactado)
#   2. client.messages.parse(model=sonnet, ...)
```

**Código correcto:**

```python
# app/llm/verifier.py
from app.llm.pii_redactor import LLMPayloadBuilder
from app.config import settings

def call_c3_verifier_capa1(
    extraccion: ExtraccionValidada,
    aviso_redactado: str
) -> VerificacionAdversarial:
    """
    C3 Capa 1: Confirmación Adversarial (Sonnet 5).
    
    PASO 1: Redactar (P5 — PII not in prompt)
    """
    # OBLIGATORIO: redactar primero
    builder = LLMPayloadBuilder()
    prompt_ver = builder.build_verification_prompt(
        extraccion=extraccion,
        aviso_redactado=aviso_redactado  # Ya redactado de C2
    )
    
    # PASO 2: Llamar Sonnet (prompt redactado)
    response = client.messages.parse(
        model=settings.VERIFIER_MODEL,  # claude-sonnet-5
        max_tokens=settings.VERIFIER_MAX_TOKENS,
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt_ver}]}],
        output_format=VerificacionAdversarial
    )
    
    return response
```

**Checkpoint:** Revisar app/llm/verifier.py línea por línea: LLMPayloadBuilder ANTES del call.

---

### Gate 5: Correr Suite Completa en Venv (No Mock Tests Only)

**Acción:** Ejecutar tests reales en venv con varias estrategias

```bash
# Step 7.5: Preparar venv
cd backend
python3.10 -m venv venv_test
source venv_test/bin/activate
pip install -e ".[dev,test]"

# Unit tests (mocked, rápido)
pytest tests/unit/ -v --tb=short

# Integration tests (real LLM, si ANTHROPIC_API_KEY)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    pytest tests/integration/ -v --tb=short
else
    echo "⚠️ ANTHROPIC_API_KEY no set — integration tests skipped"
fi

# Coverage report
pytest tests/unit/ tests/integration/ --cov=app --cov-report=term-missing
```

**Checkpoint:** Todos los tests pasan sin error; coverage ≥80%.

---

### Gate 6: U2 No Toca Rules ni Caso.estado (P1+P2)

**Acción:** Verificar código NO importa rules/ ni escribe Caso.estado

```bash
# Step 7.6: Grep para imports prohibidos
grep -r "from app.rules" backend/app/llm/ backend/app/orchestrator/ || echo "✅ Sin imports rules/"
grep -r "caso.estado" backend/app/llm/ backend/app/orchestrator/ || echo "✅ Sin tocar Caso.estado"
grep -r "Caso.estado = " backend/app/llm/ backend/app/orchestrator/ || echo "✅ Sin asignar estado"
```

**Contrato explícito en código:**

```python
# app/orchestrator/u2_handler.py
"""
U2 Handler (Orchestrator).

RESTRICCIÓN P1 + P2:
- U2 NUNCA decide cobertura (motor R1-R5 = U3)
- U2 NUNCA escribe Caso.estado (U4/humano = P1 HITL)
- U2 solo genera SeñalEscalamiento (propuesta, no decisión)

Si alguien edita este código para violar P1/P2, tests fail-closed lo atrapan.
"""

def process_caso(aviso_normalizado: AvisoNormalizado) -> SeñalesYExtraccion:
    # ...lógica U2...
    # NUNCA: from app.rules import decide_cobertura
    # NUNCA: caso.estado = "APROBADO"
    # SOLO: signals.append(SeñalEscalamiento(...))
    return SeñalesYExtraccion(signals=signals, extraccion=extraccion)
```

**Checkpoint:** Grep limpio, contrato documentado en docstring.

---

## Pasos 7-10: Generación de Código

### Paso 7: FastAPI main.py + Config

**Archivos:** 
- `backend/app/main.py` (FastAPI scaffold)
- `backend/app/config.py` (Settings, pydantic BaseSettings)

**Verificaciones Gate 1-3:** anthropic versión, model IDs en config, sin hardcodes

**Contenido mínimo main.py:**
```python
from fastapi import FastAPI
from app.config import settings
from app.routes import health, procesar_aviso

app = FastAPI(title="Perito U2", version="0.1.0")

app.include_router(health.router)
app.include_router(procesar_aviso.router, prefix="/api")

@app.on_event("startup")
async def startup():
    # Verify ANTHROPIC_API_KEY
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    print(f"✅ App started. Models: {settings.EXTRACTOR_MODEL}, {settings.VERIFIER_MODEL}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### Paso 8: Unit Tests (6 ficheros)

**Archivos:**
1. `tests/unit/test_extractor_haiku.py` — C2 call (mocked)
2. `tests/unit/test_verifier_sonnet.py` — C3 Capa 1 (mocked)
3. `tests/unit/test_consistency.py` — C3 Capa 2 (determinístico)
4. `tests/unit/test_redaction_denybydefault.py` — LLMPayloadBuilder (P5)
5. `tests/unit/test_senales.py` — SeñalEscalamiento contracts
6. `tests/unit/test_pii_schema.py` — DEFAULT_PII_SCHEMA coverage

**Patrón (conftest.py fixtures):**
```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock
from app.contracts.extraccion import ExtraccionValidada
from app.contracts.verificacion import VerificacionAdversarial

@pytest.fixture
def mock_haiku_response():
    return ExtraccionValidada(
        numero_poliza="POL-001",
        cedula="[REDACTED]",
        tipo_siniestro="AUTO_COLISION",
        fecha_siniestro="2026-07-05",
        monto_siniestro=1000.00,
        ausentes=[]
    )

@pytest.fixture
def mock_sonnet_response():
    return VerificacionAdversarial(
        confianza=0.95,
        inconsistencias=[],
        recomendacion="ACEPTA"
    )
```

**Checkpoint:** pytest tests/unit/ -v → todos pasan, coverage ≥80%

---

### Paso 9: Docker + CI Workflow

**Archivos:**
- `backend/Dockerfile` (Python 3.10 slim + dependencies)
- `backend/docker-compose.yml` (app + postgres)
- `.github/workflows/test-u2.yml` (CI: unit tests on push/PR)

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY app/ ./app/
COPY tests/ ./tests/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**CI Workflow:**
```yaml
name: Test U2
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v
      - run: pytest tests/unit/ --cov=app
```

**Checkpoint:** CI pasa en todos los commits

---

### Paso 10: Documentación

**Archivos:**
- `backend/README.md` (setup, run, test)
- `backend/docs/api.md` (endpoints)
- `backend/docs/architecture.md` (C2-C4, señales)

**README.md mínimo:**
```markdown
# Perito U2 Backend

## Quick Start
\`\`\`bash
cd backend
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY
docker-compose up
pytest tests/unit/ -v
\`\`\`

## Architecture
- C2: Haiku extraction (claude-haiku-4-5, no effort param)
- C3 Capa 1: Sonnet adversarial verification (claude-sonnet-5)
- C3 Capa 2: Deterministic consistency checks (code)
- C4: Policy lookup (PostgreSQL)

## Invariants
- P1 HITL: U2 never decides, only proposes signals
- P2 Coverage: U2 never decides coverage (U3 rules)
- P5 PII: LLMPayloadBuilder deny-by-default redaction
- P4 Termination: Single-pass, no loops, hard caps
```

---

## Orden Ejecución

1. **Gate 1:** Verificar anthropic SDK versión mínima, probar messages.parse
2. **Gate 2:** Model IDs en config.py, grep for hardcodes
3. **Paso 7:** Generar main.py + config.py (apply Gate 1-2)
4. **Gate 3:** Revisar C2 sin effort param (grep, nota en código)
5. **Gate 4:** Revisar C3 pasa por LLMPayloadBuilder (grep, flujo)
6. **Paso 8:** Generar unit tests
7. **Gate 5:** Correr tests en venv (no mocks only)
8. **Gate 6:** Verificar P1+P2 (grep rules/, Caso.estado)
9. **Paso 9:** Generar Docker + CI
10. **Paso 10:** Generar documentación

---

## Checklist Pre-Approve (Final)

- [ ] Gate 1: anthropic versión verificada, messages.parse funciona
- [ ] Gate 2: No hardcodes model IDs, config.py es SSOT
- [ ] Gate 3: Haiku sin effort, nota en código
- [ ] Gate 4: C3 Capa 1 → LLMPayloadBuilder → Sonnet
- [ ] Gate 5: Todos los tests pasan en venv
- [ ] Gate 6: P1+P2 intactos (grep limpio, contratos)
- [ ] Paso 9: Docker builds, CI pasa
- [ ] Paso 10: README completo

**Si todos ✅:** U2 Code Gen aprobado → merge a spec/aidlc-inception

---
