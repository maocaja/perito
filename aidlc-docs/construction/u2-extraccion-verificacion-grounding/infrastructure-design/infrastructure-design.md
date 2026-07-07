# Infrastructure Design — U2 Extracción·Verificación·Grounding (MVP)

## Resumen: Dev Environment Mínimo

**Alcance:** Local development only. NO production infrastructure (U5 owns cloud readiness). 
**Objetivo:** Ejecutar U2 en máquina del desarrollador con mínimas dependencias externas.

---

## Stack Mínimo (Docker Compose)

```yaml
# backend/docker-compose.yml
version: "3.9"
services:
  # U2: FastAPI + LLM calls (local, no container init code)
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}  # Required (from .env)
      - EXTRACTOR_MODEL=claude-haiku-4-5
      - VERIFIER_MODEL=claude-sonnet-5
      - CONFIDENCE_THRESHOLD=0.70
      - LOG_LEVEL=INFO
      - DATABASE_URL=postgresql://perito:perito@postgres:5432/perito_db
      - LANGFUSE_API_KEY=${LANGFUSE_API_KEY}    # Optional (empty = logs to stdout)
    volumes:
      - ./app:/app  # Hot-reload dev
    depends_on:
      - postgres
  
  # C4: PolicyLookup (mock BD)
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: perito
      POSTGRES_PASSWORD: perito
      POSTGRES_DB: perito_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql  # Seed mock policies
    ports:
      - "5432:5432"

volumes:
  postgres_data:

# Optional: Langfuse (tracing) — omit if offline dev
  # langfuse:
  #   image: langfuse/langfuse:latest
  #   ports:
  #     - "3000:3000"
  #   environment:
  #     DATABASE_URL: postgresql://...
```

---

## Backend Structure (Python)

```
backend/
├── pyproject.toml                      # Dependencies (NEW: anthropic)
├── Dockerfile                          # Python 3.10+ slim
├── docker-compose.yml                  # See above
├── .env.example                        # Template (ANTHROPIC_API_KEY, etc)
├── .env                                # GITIGNORE: secrets
│
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI entry (Step 7: code gen)
│   ├── config.py                       # Settings + pydantic (model IDs here)
│   │
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── extraccion.py               # ExtraccionValidada (Pydantic v2)
│   │   ├── verificacion.py             # VerificacionAdversarial
│   │   ├── senales.py                  # SeñalEscalamiento
│   │   └── casos.py                    # AvisoNormalizado (hereda U1)
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── pii_redactor.py             # LLMPayloadBuilder (new U2)
│   │   ├── extractor.py                # C2 call (client.messages.parse)
│   │   ├── verifier.py                 # C3 Capa 1 & 2 (Sonnet + code)
│   │   ├── message_log.py              # Traza (M9 integration)
│   │   └── templates/                  # Prompt strings (no secrets)
│   │       ├── extraction_system.txt
│   │       ├── extraction_user.txt
│   │       ├── verification_system.txt
│   │       └── verification_user.txt
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                   # SQLAlchemy Policy, Caso (hereda U1)
│   │   ├── session.py                  # SessionLocal (PostgreSQL)
│   │   └── crud.py                     # C4 lookup (policy by numero_poliza)
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── u2_handler.py               # Orquesta C2→C3→C4, devuelve SeñalesYExtraccion
│   │
│   └── routes/
│       ├── __init__.py
│       ├── health.py                   # GET /health (liveness)
│       └── procesar_aviso.py          # POST /api/casos (entrada) (Step 7: code gen)
│
└── tests/
    ├── conftest.py                     # Fixtures pytest (mock LLM, BD)
    ├── unit/
    │   ├── test_extractor_haiku.py      # C2 call mocked
    │   ├── test_verifier_sonnet.py      # C3 Capa 1 mocked
    │   ├── test_consistency.py          # C3 Capa 2 (determinístico)
    │   ├── test_redaction_denybydefault.py  # LLMPayloadBuilder (P5)
    │   ├── test_senales.py              # SeñalEscalamiento contracts
    │   └── test_pii_schema.py           # DEFAULT_PII_SCHEMA coverage
    │
    ├── integration/
    │   ├── conftest_integration.py      # Real LLM (needs ANTHROPIC_API_KEY)
    │   ├── test_e2e_happy_path.py       # Limpio → extraccion correcta
    │   ├── test_e2e_campos_faltantes.py # Incompleto → señal
    │   ├── test_e2e_fraude.py           # Inconsistencias → C3 detecta
    │   └── test_e2e_pii_redaction.py    # PII no cruza al LLM
    │
    └── strats/                         # Estratificación (specs/prd.md Seg. 11)
        ├── happy.py                    # happy path fixtures
        ├── campos_faltantes.py
        ├── poliza_no_encontrada.py
        ├── cobertura_negativa.py
        ├── fraude.py
        ├── soat.py
        └── documento_sucio.py
```

---

## Dependencias (pyproject.toml)

```toml
[project]
name = "perito-backend"
version = "0.1.0"
description = "Perito: AI-DLC U2 Extraction & Verification"
requires-python = ">=3.10"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0",
    "anthropic>=0.27.0",  # TBD: Code Gen to verify min version for messages.parse
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.1",  # PostgreSQL driver
    "langfuse>=0.6.0",  # Tracing (optional for MVP, can be empty key)
    "python-dotenv>=1.0",  # .env loading
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",  # Test client (FastAPI)
    "ruff>=0.1.0",
]

test = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
]
```

---

## Environment Configuration

### .env.example

```bash
# REQUIRED
ANTHROPIC_API_KEY=sk-ant-...  # From console.anthropic.com

# Database (docker-compose)
DATABASE_URL=postgresql://perito:perito@postgres:5432/perito_db

# Observabilidad (optional, empty = logs to stdout)
LANGFUSE_API_KEY=

# LLM Models (override if needed, else config.py defaults)
EXTRACTOR_MODEL=claude-haiku-4-5
VERIFIER_MODEL=claude-sonnet-5

# Logs
LOG_LEVEL=INFO
```

### Load Pattern

```python
# app/config.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str  # Required, error if missing
    DATABASE_URL: str = "postgresql://perito:perito@postgres:5432/perito_db"
    
    EXTRACTOR_MODEL: str = "claude-haiku-4-5"
    VERIFIER_MODEL: str = "claude-sonnet-5"
    EXTRACTOR_MAX_TOKENS: int = 2000
    VERIFIER_MAX_TOKENS: int = 3000
    
    CONFIDENCE_THRESHOLD: float = 0.70
    MAX_ROUNDS: int = 1
    MAX_TOKENS_BUDGET: int = 10_000
    
    LANGFUSE_API_KEY: str = ""  # Empty = no tracing
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra vars

settings = Settings()
```

---

## Local Dev Workflow

### Step 0: Setup

```bash
cd backend

# Create .env
cp .env.example .env
# Edit .env: paste ANTHROPIC_API_KEY

# Create Python venv
python3.10 -m venv venv
source venv/bin/activate

# Install dev deps
pip install -e ".[dev]"
```

### Step 1: Start Docker Compose

```bash
docker-compose up -d

# Wait for postgres (health check)
docker-compose logs postgres

# Seed BD (init-db.sql runs auto)
docker-compose exec postgres psql -U perito -d perito_db -c "SELECT COUNT(*) FROM policies;"
```

### Step 2: Run Unit Tests (Mocked LLM)

```bash
pytest tests/unit/ -v

# Coverage
pytest tests/unit/ --cov=app --cov-report=term-missing
```

### Step 3: Run Integration Tests (Real LLM)

```bash
# Requires ANTHROPIC_API_KEY in .env
pytest tests/integration/ -v

# Or skip if offline:
pytest tests/integration/ -v -m "not requires_anthropic"
```

### Step 4: Run App Locally

```bash
# Hot-reload dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or in container
docker-compose up app
```

### Step 5: Test Endpoint

```bash
curl -X POST http://localhost:8000/api/casos   -H "Content-Type: application/json"   -d '{
    "numero_poliza": "POL-001",
    "cedula": "9876543210",
    "nombre_asegurado": "Juan Pérez",
    "tipo_siniestro": "AUTO_COLISION",
    "fecha_siniestro": "2026-07-05"
  }'

# Response: SeñalesYExtraccion (JSON)
```

---

## Testing Strategy (MVP)

### Unit Tests (No LLM)

- **Mocked Anthropic client** → determinístico, rápido
- Fixtures en `conftest.py`: fake ExtraccionValidada, VerificacionAdversarial
- Coverage: PII redaction, contracts, consistency logic

```python
# tests/unit/test_redaction_denybydefault.py
from unittest.mock import MagicMock
from app.llm.pii_redactor import LLMPayloadBuilder

def test_redaction_denybydefault():
    builder = LLMPayloadBuilder()
    aviso = AvisoNormalizado(
        numero_poliza="POL-001",
        cedula="9876543210",  # PII
        nombre_asegurado="Juan Pérez",  # PII
    )
    prompt = builder.build_extraction_prompt(aviso)
    
    assert "[REDACTED]" in prompt
    assert "9876543210" not in prompt
    assert "POL-001" in prompt
```

### Integration Tests (Real LLM)

- **Real Anthropic API calls** (expensive, slower)
- Requires `ANTHROPIC_API_KEY`
- Ran solo cuando desarrollo local o CI necesita validar real behavior
- Stratified: happy, campos-faltantes, fraude, documento-sucio (specs/prd.md Seg. 11)

```python
# tests/integration/test_e2e_happy_path.py
@pytest.mark.requires_anthropic
def test_e2e_happy_path():
    """Real LLM: documento limpio → extraccion correcta, confianza alta."""
    aviso = AvisoNormalizado(...)  # datos completos, correctos
    
    resultado = process_caso(aviso)  # Real C2 + C3
    
    assert resultado.extraccion is not None
    assert resultado.extraccion.numero_poliza == "POL-001"
    assert resultado.verificacion.confianza > 0.70
    assert len(resultado.signals) == 0
```

---

## Observabilidad Mínima (MVP)

### Logs a Stdout

```python
# app/llm/message_log.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_llm_call(
    etapa: str,
    entrada_redactada: str,
    modelo: str,
    tokens_input: int,
    tokens_output: int,
    latencia_ms: int
):
    logger.info(
        f"[{etapa}] Modelo={modelo} Tokens={tokens_input}+{tokens_output} Latencia={latencia_ms}ms"
    )
```

### Langfuse Integration (Optional)

```python
from langfuse.decorators import observe

@observe(name="U2_EXTRACCION")
def call_c2_extractor(prompt: str) -> ExtraccionValidada:
    response = client.messages.parse(...)
    # Langfuse auto-logs tokens, latencia
    return response
```

**Nota:** Si LANGFUSE_API_KEY vacía, logs van a stdout solo.

---

## Restricciones MVP

| Item | Alcance | Razón |
|------|---------|-------|
| **Cloud Hosting (P7)** | N/A | U5 owns production infrastructure |
| **HA / Replicación** | N/A | Single-region dev |
| **Caching distribuido** | N/A | In-memory only |
| **Live Dashboard** | N/A | Metrics feed U5 evals harness |
| **Load testing** | N/A | Single-user dev |
| **HTTPS / TLS** | N/A | HTTP localhost |
| **Secrets rotation** | N/A | .env gitignore only |

---

## Next: Code Generation (Step 7)

Esta estructura permite:
1. **Developers escribir código** en app/ + tests/ sin configuración cloud
2. **CI correr unit tests** rápido (sin LLM)
3. **Manual integration tests** con ANTHROPIC_API_KEY antes de merge
4. **Langfuse optional** para tracing en dev (no bloqueante)
5. **Deploy a prod** (U5 adds cloud infra, no cambio en app/)

---
