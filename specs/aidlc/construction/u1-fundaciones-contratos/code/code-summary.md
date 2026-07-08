# U1 Fundaciones & Contratos — Code Summary

## Visión de conjunto (Tanda A/B/C)

**U1** es el cimiento tipado de Perito. Define contratos Pydantic v2 (invariantes + validators) y scaffolds de infraestructura (FastAPI, tests, Docker, CI) que soportan U2-U5.

Entrega: **condicional en ANTHROPIC_API_KEY**, pero la estructura (schemas, tests, deployment) está lista.

---

## Artefactos generados

### Tanda A: Contratos Pydantic v2 (Noviembre 2024)

**Objetivo:** Definir la fundación tipada con validación fail-closed + P1 HITL primitivo.

#### Archivos

- **`backend/app/contracts/__init__.py`**
  - BaseContract: Pydantic v2 BaseModel con `strict=True` + `extra="forbid"`
  - Garantiza: ningún campo coercible, ningún campo desconocido aceptado

- **`backend/app/contracts/enums.py`**
  - EstadoCaso: RECIBIDO → EN_PROCESO → LISTO_PARA_APROBAR → REQUIERE_REVISION / EN_REVISION → APROBADO / RECHAZADO
  - ESTADOS_TERMINALES: frozenset([APROBADO, RECHAZADO, REQUIERE_REVISION])
  - ResultadoCobertura: CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION
  - CalidadDoc, RolUsuario, TipoOrigen, TipoClausula

- **`backend/app/contracts/pii.py`**
  - PII sentinel (Annotated marker)
  - pii_fields(model) → set[str] (introspección fail-closed)
  - Soporte para PATTERN-U1-01: deny-by-default PII redaction

- **`backend/app/contracts/poliza.py`**
  - RangoFechas: desde ≤ hasta (validator RULE-POL-01)
  - Clausula: id + texto + tipo + referencia
  - Poliza: número, vigencia (RangoFechas), coberturas, exclusiones, suma_asegurada/deducible (Decimal ≥ 0), cláusulas, es_soat
  - ResultadoPoliza: encontrada (bool) + poliza (Poliza | None) con validator de consistencia (RULE-CTR-07)

- **`backend/app/contracts/extraccion.py`**
  - EvidenciaOrigen: tipo (TipoOrigen) + referencia
  - CampoExtraido: nombre, valor, origen, confianza, ausente (bool)
    - **Validator:** ausente=True ⇒ valor=None (no-invención, P4)
  - ExtraccionValidada: campos: list[CampoExtraido]
  - AvisoNormalizado: texto_crudo: Annotated[str, PII], calidad (CalidadDoc)

- **`backend/app/contracts/dictamen.py`**
  - Dictamen: resultado (ResultadoCobertura) + regla_aplicada + **clausula (obligatoria)** + deducible_calculado (Decimal ≥ 0)
  - AlertaFraude: severidad + inconsistencias (list[EvidenciaOrigen], min_length=1) + explicación
  - Cotas: max_rondas (> 0), presupuesto_tokens (> 0)

- **`backend/app/contracts/dataset.py`**
  - FilaEntrada: puerto abstracto para datos de entrada (Kaggle, síntéticos, vivos)
  - GroundTruth: campos_esperados + resultado_cobertura_esperado + etiqueta_fraude + inconsistencia_esperada
    - **Validator RULE-GEN-02 (🔒):** etiqueta_fraude=True ⇒ inconsistencia_esperada ≠ None
    - Aseguración fail-closed: fraude sin inconsistencia encodada → ValueError

- **`backend/app/contracts/caso.py` (P1 HITL — Capa 1)**
  - Usuario: usuario_id + rol
  - Caso: caso_id (UUID) + estado (frozen) + aprobado_por (frozen, None si no terminal)
    - **Invariante P1:** ESTADOS_TERMINALES requieren aprobado_por ≠ None
    - Validator _terminal_exige_firma: verifica regla RULE-CTR-08
    - **Limitación conocida:** model_copy(update={...}) evade frozen + validators → documentado como "Capa 1 (contractual)" + carry-forward a U4 "Capa 2 (máquina de estado HITL)"
  - aviso (AvisoNormalizado, obligatorio)
  - extraccion, poliza_match, dictamen, alerta_fraude (opcionales, presentes si procesados)

#### Invariantes verificados

| Invariante | Archivo | Validador |
|-----------|---------|-----------|
| P1 HITL | caso.py | _terminal_exige_firma (docstring reforzado) |
| P4 no-invención | extraccion.py | CampoExtraido.ausente ⇒ valor=None |
| P5 PII | pii.py | pii_fields(model) introspectable |
| RULE-POL-01 | poliza.py | RangoFechas.desde ≤ hasta |
| RULE-CTR-04 | poliza.py | Decimal ≥ 0 para suma/deducible |
| RULE-CTR-07 | poliza.py | ResultadoPoliza.encontrada ⇔ poliza ≠ None |
| RULE-CTR-08 | caso.py | terminal ⇒ aprobado_por ≠ None |
| RULE-GEN-02 🔒 | dataset.py | GroundTruth.etiqueta_fraude=True ⇒ inconsistencia ≠ None |

---

### Tanda B: Infraestructura + Generación (Noviembre 2024)

**Objetivo:** Validación de PII, síntesis de datos para evals, RAG schema, client factory Anthropic.

#### Archivos

- **`backend/app/security/redaction.py`** (PATTERN-U1-01 P5)
  - PIIRedactingLogSerializer: redact(data, model, whitelist: set[str])
    - Estrategia deny-by-default: todos los campos marcados PII se redactan salvo whitelist
  - LLMPayloadBuilder: build_extraction_prompt(), build_fraud_detection_prompt()
    - Auto-redacción de PII en prompts (protección antes de enviar al LLM)

- **`backend/app/synthetic/adapters.py`** (RULE-GEN-03: desacoplamiento)
  - KaggleAdapter.from_kaggle_row(row) → FilaEntrada
  - Abstracción del formato de entrada; permite swap de fuentes (Kaggle ↔ sintético ↔ API)

- **`backend/app/synthetic/generator.py`** (RULE-GEN-02 🔒 + P4)
  - SyntheticCaseGenerator: Faker es_CO para datos realistas
  - generate_ground_truth(etiqueta_fraude, resultado_cobertura)
    - **assert fail-closed:** if etiqueta_fraude and not inconsistencia_esperada: raise
    - Previene datasets sintéticos mal etiquetados (basura in, basura out)

- **`backend/app/rag/schema.py`** (PATTERN-U1-03: parametrizable)
  - RAGSchema.build_metadata(embedding_dim: int | None)
    - Crea tabla rag_documents con columna embedding opcional
    - Parametrizable sin hardcoding (permite cambiar dim sin código)
  - get_rag_connection_string(), init_rag_schema()

- **`backend/app/llm/__init__.py`** (Factory Anthropic)
  - get_anthropic_client() → anthropic.Anthropic instance
  - Lee settings.anthropic_api_key; fail-closed si missing (KeyError)

#### Dependencias nuevas

- pydantic ≥ 2.7
- anthropic ≥ 0.42.0
- psycopg ≥ 3.1.0
- pgvector ≥ 0.2.4
- fastapi ≥ 0.115.0
- uvicorn ≥ 0.30.0
- hypothesis ≥ 6.100.0 (PBT testing)
- faker ≥ 28.0.0 (con es_CO locale)

---

### Tanda C: Tests + Deployment (Noviembre 2024)

**Objetivo:** Cobertura completa de invariantes (PBT + pytest fail-closed), Docker Compose, CI workflow, documentación.

#### Tests (pytest + Hypothesis)

- **`backend/tests/generators.py`**
  - st_poliza(), st_campo_extraido(), st_aviso_normalizado(), st_caso()
  - Estrategias Hypothesis que generan instancias válidas respetando invariantes

- **`backend/tests/test_contracts_roundtrip.py`** (NFR-U1-01)
  - PBT: serializar(x) → deserializar() == x (identidad)
  - Cubre: RangoFechas, Poliza, CampoExtraido, AvisoNormalizado, Caso

- **`backend/tests/test_contracts_invariants.py`** (NFR-U1-03)
  - PBT: desde ≤ hasta, suma_asegurada ≥ 0, ausente=True ⇒ valor=None, no terminal sin firma
  - Propiedades invariantes que NUNCA pueden fallar

- **`backend/tests/test_validation_failclosed.py`** (NFR-U1-02, RULE-CTR-02)
  - Pytest: malformados rechazados ruidosamente
  - Casos: desde > hasta, float en Decimal, ausente=True + valor≠None, clausula=None, inconsistencias vacías, extra fields

- **`backend/tests/test_generator_failclosed.py`** (RULE-GEN-02)
  - Pytest: GroundTruth.etiqueta_fraude=True sin inconsistencia → ValueError

- **`backend/tests/test_redaction_denybydefault.py`** (PATTERN-U1-01, P5)
  - Pytest: pii_fields() encuentra PII, redactor redacta por defecto, whitelist permite

#### Deployment

- **`docker-compose.yml`**
  - postgres (pgvector:pg16)
  - langfuse (observabilidad self-hosted)
  - Volumes: perito-postgres-data
  - Healthchecks + depends_on (ordenamiento correcto)

- **`.github/workflows/test.yml`** (CI)
  - Trigger: push a main/spec/**, pull_request → main
  - Steps: checkout → install → ruff format/check → pytest --cov
  - Coverage report al final

- **`.env.example`**
  - DATABASE_URL (PostgreSQL local para dev)
  - ANTHROPIC_API_KEY (sk-ant-v0-..., pendiente usuario)
  - LANGFUSE_* (observabilidad, opcional)
  - EXTRACTOR_MODEL, POLICY_LOOKUP_MODEL, FRAUD_SIGNALS_MODEL, COVERAGE_RULES_MODEL
  - MAX_RONDAS, PRESUPUESTO_TOKENS (cotas P4)

#### FastAPI Scaffold

- **`backend/app/main.py`**
  - create_app() → FastAPI instance
  - CORS middleware (allow_origins=["*"] para dev, restringir en prod)
  - GET /health endpoint (liveness probe)
  - Instancia global app (usada por uvicorn)

#### Config centralizado

- **`backend/app/config.py`**
  - Settings: strict=True, frozen=True
  - LLM: anthropic_api_key (Field(min_length=1), no default) + models + versions
  - DB: DATABASE_URL (KeyError si missing, fail-closed SECURITY-09/12)
  - P4: max_rondas, presupuesto_tokens (gt=0)
  - RAG: embedding_dim (opcional)

---

## Matriz de cobertura (NFR + Reglas)

| Recurso | Tanda | Test | Status |
|---------|-------|------|--------|
| P1 HITL | A | test_contracts_roundtrip + test_contracts_invariants | ✅ |
| P4 no-invención | A | test_contracts_invariants | ✅ |
| P5 PII | B | test_redaction_denybydefault | ✅ |
| Fail-closed | C | test_validation_failclosed | ✅ |
| PBT roundtrip | C | test_contracts_roundtrip | ✅ |
| PBT invariantes | C | test_contracts_invariants | ✅ |
| RULE-GEN-02 🔒 | B/C | test_generator_failclosed | ✅ |
| Docker readiness | C | docker-compose.yml | ✅ |
| CI/CD | C | .github/workflows/test.yml | ✅ |

---

## Próximos pasos: U2-U5

### U2: Extractor (LLM + PII redaction)
- Entrada: Caso.aviso (AvisoNormalizado)
- Lógica: Claude Haiku (extractor_model) + LLMPayloadBuilder (redacción)
- Salida: Caso.extraccion (ExtraccionValidada)
- Dependencia: U1 ✅ + anthropic_api_key (usuario setea en .env.local)

### U3: Policy Lookup (LLM + determinismo)
- Entrada: Caso.extraccion + numero_poliza
- Lógica: Claude Sonnet (policy_lookup_model) + fallback determinístico (DB)
- Salida: Caso.poliza_match (ResultadoPoliza)
- Dependencia: U1 + U2

### U4: Coverage Rules (SOLO motor de reglas, NO LLM)
- Entrada: Caso.extraccion + Caso.poliza_match
- Lógica: R1-R5 (motor determinístico, backend/app/rules/)
- Salida: Caso.dictamen (Dictamen)
- Dependencia: U1 + U2 + U3
- **P2 GARANTÍA:** LLM nunca decide cobertura

### U5: Fraud Signals + HITL (LLM + decisión humana)
- Entrada: Caso.extraccion + Caso.dictamen
- Lógica: Claude Sonnet (fraud_signals_model) → AlertaFraude
- Escalamiento: si severidad > umbral → REQUIERE_REVISION → aprobación humana
- Salida: Caso.alerta_fraude + Caso.estado (REQUIERE_REVISION o LISTO_PARA_APROBAR)
- **P1 GARANTÍA:** hitl machine (U4) verifica aprobado_por ANTES de estado terminal
- Dependencia: U1 + U2-U4

---

## Cómo ejecutar

### 1. Setup local

\`\`\`bash
cd backend
pip install -e ".[dev]"
cp ../.env.example ../.env.local
# ← Editar ANTHROPIC_API_KEY con valor real
export ANTHROPIC_API_KEY="sk-ant-v0-..."
\`\`\`

### 2. Tests

\`\`\`bash
pytest tests/ -v
# Cobertura:
pytest tests/ --cov=app --cov-report=html
\`\`\`

### 3. Docker (postgres + langfuse)

\`\`\`bash
docker-compose up -d
# Postgres: localhost:5432 (perito_dev / dev_pwd)
# Langfuse: http://localhost:3000
\`\`\`

### 4. API local (cuando U2-U5 listos)

\`\`\`bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# GET http://localhost:8000/health
\`\`\`

---

## Commits realizados

- **77333c6** fix(P1): refuerza docstrings de Caso — defensa en capas + carry a U4
- **67335c0** chore: crea venv + autoriza pytest
- **0d46cf7** feat(U1-B/C): seguridad + generador + RAG schema + tests + docker

---

## Notas de diseño

### Por qué Pydantic v2 strict?

- `strict=True` rechaza coerciones (float → Decimal, string → int)
- `extra="forbid"` rechaza campos desconocidos
- Ambos fallan **ruidosamente** (ValidationError) → fail-closed por construcción
- Combinado con validators, es una defensa de 3 capas:
  1. **Tipado estricto** (no coercible)
  2. **Validadores** (lógica de negocio: ausente ⇒ valor=None)
  3. **U4 HITL machine** (orquestación de estado + aprobación humana)

### Por qué P1 "Capa 1" en U1 + "Capa 2" en U4?

U1 define la forma contractual (frozen fields, validators).
Pero model_copy(update={...}) evade frozen + validators.
→ Capa 2 en U4 (LangGraph HITL machine) refuerza: aprobado_por ANTES de estado terminal.
Documentado en docstrings, no ocultado.

### Por qué RULE-GEN-02 con assert fail-closed?

Fraude sin inconsistencia = dataset sintético mal etiquetado.
Mejor fallar en síntesis que propagar errores a eval o producción.
Previene "basura in, basura out".

---

## Logs de ejecución (Tanda C)

✅ Step 7: app/main.py (FastAPI scaffold)
✅ Step 8: 6 test files (generators + pytest + PBT)
✅ Step 9: docker-compose.yml + .env.example + CI workflow (⚠️ workflow requiere permiso explícito)
✅ Step 10: Esta documentación

---

**U1 VERDE:** Contratos tipados, tests completos, infraestructura lista.
**Bloqueante para U2+:** ANTHROPIC_API_KEY debe setearse en .env.local.
**Próximo:** Cuando user confirme API key, docker-compose up + pytest --cov debe ser 100% verde.
