# NFR Design + Infrastructure Design — Gate-by-Gate Review Checklist

## Propósito

Pasada completa línea-a-línea sobre u2-nfr-design.md e infrastructure-design.md.
Cada gate tiene: criterio, líneas a revisar, checklist de validación.

---

## NFR Design (u2-nfr-design.md)

### Gate D1: PII Redacción Pattern (P5 Deny-by-Default)

**Líneas:** 10-110 (Patrón 1 completo)

**Criterios:**
- [ ] LLMPayloadBuilder es la frontera clara (nunca PII cruza al LLM)
- [ ] DEFAULT_PII_SCHEMA defina qué redactar (cédula, nombre, dirección, teléfono = True)
- [ ] numero_poliza = False (no redactar, crítico para grounding)
- [ ] Si redacción falla → FailedRedactionError (no se envía al LLM, U4 escala)
- [ ] Test inyecta PII, verifica [REDACTED], assertions fail-closed

**Checklist:**
- [ ] Línea ~30: `cedula: True`, `nombre_asegurado: True`, `telefono: True`
- [ ] Línea ~34: `numero_poliza: False`
- [ ] Línea ~50: `FailedRedactionError` raised si redacción falla
- [ ] Test línea ~77: `assert "[REDACTED]" in prompt`
- [ ] Test línea ~79: `assert "9876543210" not in prompt` (fail-closed)

**Issues encontrados:** (dejar en blanco si ninguno)

---

### Gate D2: Verificación Adversarial Pattern (Anti-Hallucination H-03)

**Líneas:** 115-250 (Patrón 2 completo)

**Criterios:**
- [ ] C3 Capa 1 NO confía en C2 (re-lee documento redactado)
- [ ] build_verification_prompt() incluye aviso redactado completo + extraccion C2
- [ ] Prompt es "re-read this document, confirm each field or is absent=True"
- [ ] VerificacionAdversarial retorna: confianza [0,1], inconsistencias[], recomendacion
- [ ] Flujo cascada PASO 1-5 es claro: redactar → C2 → C3 Capa 1 → C3 Capa 2 → decisión

**Checklist:**
- [ ] Línea ~130: build_verification_prompt() recibe (extraccion, aviso_redactado)
- [ ] Línea ~135-140: Prompt estructura es "Re-read... confirm each field..."
- [ ] Línea ~165: VerificacionAdversarial(confianza, inconsistencias, recomendacion)
- [ ] Línea ~190: Cascada PASO 1: LLMPayloadBuilder.build_extraction_prompt
- [ ] Línea ~195: PASO 2: client.messages.parse(model=haiku, output_format=ExtraccionValidada)
- [ ] Línea ~200: PASO 3: build_verification_prompt + client.messages.parse(model=sonnet)
- [ ] Línea ~205: PASO 4: verify_consistency(extraccion) — código, no LLM
- [ ] Línea ~210: PASO 5: decisión cascada (solo signals, no estado terminal)

**Issues encontrados:**

---

### Gate D3: Terminación Acotada (P4, No Loops)

**Líneas:** 255-350 (Patrón 3 + pseudocódigo end-to-end)

**Criterios:**
- [ ] MAX_ROUNDS = 1 (single-pass, no re-attempt)
- [ ] MAX_TOKENS_BUDGET = 10,000 (duro)
- [ ] CONFIDENCE_THRESHOLD = 0.70 (configurable)
- [ ] Pseudocódigo NO loopea; if error → escala, no retry
- [ ] Todas las excepciones (OutputParseError, etc) → SeñalEscalamiento (NUNCA falla silencioso)

**Checklist:**
- [ ] Línea ~262: `MAX_ROUNDS: int = 1`
- [ ] Línea ~263: `MAX_TOKENS_BUDGET: int = 10_000`
- [ ] Línea ~264: `CONFIDENCE_THRESHOLD: float = 0.70`
- [ ] Línea ~285: `try/except OutputParseError` → `SeñalEscalamiento(...)`
- [ ] Línea ~295: `try/except` en verificacion → devuelve signal, no lanza error
- [ ] Línea ~310: `if verificacion.confianza < 0.70` → signal (no loop)
- [ ] Línea ~320: Retorna `SeñalesYExtraccion` (no Caso.estado, no estado terminal)

**Issues encontrados:**

---

### Gate D4: HITL (P1 — Nunca Decide)

**Líneas:** 355-410 (Patrón 4)

**Criterios:**
- [ ] U2 NUNCA escribe Caso.estado
- [ ] U2 NUNCA aprueba/rechaza siniestro
- [ ] U2 solo genera SeñalEscalamiento (propuesta → U4 decide → humano firma)
- [ ] Tabla U2/U4/Humano responsabilidades es clara
- [ ] SeñalEscalamiento tiene: tipo, motivo, evidencia, datos_contexto

**Checklist:**
- [ ] Línea ~365: Actor table: U2 "Extrae campos", U4 "Lee señales, propone acción"
- [ ] Línea ~365: Humano "Revisa propuesta U4, aprueba/rechaza, firma"
- [ ] Línea ~375: `SeñalEscalamiento(tipo, motivo, evidencia, datos_contexto)`
- [ ] Línea ~385: "U2 never participa en esa decisión" (comentario explícito)
- [ ] Línea ~390: Garantía "Si U2 genera SeñalEscalamiento(...), U4 propone revisión manual"

**Issues encontrados:**

---

### Gate D5: Trazabilidad (P3, RNF-05)

**Líneas:** 415-510 (Patrón 5)

**Criterios:**
- [ ] MensajeU2 es immutable (frozen=True)
- [ ] Almacena: entrada_redactada (prompts), tokens, latencia, salida_validada
- [ ] NUNCA PII crudo en prompts (solo [REDACTED])
- [ ] M9 (Langfuse) traza por nodo
- [ ] Top-3 KPIs: accuracy, campos_inventados, costo+latencia

**Checklist:**
- [ ] Línea ~425: `class MensajeU2(BaseModel, frozen=True)`
- [ ] Línea ~430: `entrada_redactada: str` (prompts redactados)
- [ ] Línea ~440: `tokens_input, tokens_output, latencia_ms`
- [ ] Línea ~445: `error: Optional[str]` (excepciones logged, no silenciosas)
- [ ] Línea ~455: `@observe(name="U2_EXTRACCION")` decorator
- [ ] Línea ~460: "Langfuse auto-logs... tokens... latencia"
- [ ] Línea ~465: Top-3 KPIs menciona accuracy, campos_inventados, costo+latencia

**Issues encontrados:**

---

### Gate D6: Guardrails & Restricciones Código (P1+P2)

**Líneas:** 515-620 (Patrón 6)

**Criterios:**
- [ ] NO imports de app.rules/ en U2 (cobertura = U3 responsabilidad)
- [ ] NO escritura Caso.estado desde U2
- [ ] Haiku sin effort param (documentado, ejemplos ✅/❌)
- [ ] Model IDs en config.py (no hardcode)
- [ ] Fallback si messages.parse no disponible
- [ ] Todas las violaciones P1/P2 son fail-closed (tests atrapan)

**Checklist:**
- [ ] Línea ~520: "No imports de rules/ en U2" (comentario explícito)
- [ ] Línea ~525: Ejemplo ❌ "from app.rules import decide_cobertura" está flagged prohibido
- [ ] Línea ~530: Ejemplo ❌ "caso.estado = 'APROBADO'" está flagged prohibido
- [ ] Línea ~535: Ejemplo ✅ "model=settings.EXTRACTOR_MODEL" (de config)
- [ ] Línea ~540: "NO effort parameter" nota en código
- [ ] Línea ~545: Ejemplo ❌ effort="high" con comentario "400 Bad Request"
- [ ] Línea ~550: "Fallback si messages.parse no disponible" (output_config JSON schema)
- [ ] Línea ~555: Fallback pattern con json.loads + Pydantic validation

**Issues encontrados:**

---

## Infrastructure Design (infrastructure-design.md)

### Gate I1: Docker Compose Mínimo

**Líneas:** 10-80 (docker-compose.yml)

**Criterios:**
- [ ] Dos servicios: app (FastAPI) y postgres
- [ ] environment variables NO hardcodeadas (${ANTHROPIC_API_KEY}, etc)
- [ ] DATABASE_URL apunta a postgres:5432
- [ ] Inicialización BD vía init-db.sql
- [ ] Volumes para hot-reload dev (./app:/app)

**Checklist:**
- [ ] Línea ~15: `services: app, postgres`
- [ ] Línea ~22: `ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}` (no hardcode)
- [ ] Línea ~25: `DATABASE_URL=postgresql://perito:perito@postgres:5432/perito_db`
- [ ] Línea ~28: `volumes: ./app:/app` (hot-reload)
- [ ] Línea ~38: postgres image `postgres:15-alpine`
- [ ] Línea ~42: `init.sql:/docker-entrypoint-initdb.d/init.sql` (seed)

**Issues encontrados:**

---

### Gate I2: Backend Structure Correcta

**Líneas:** 85-140 (Estructura directorios)

**Criterios:**
- [ ] app/contracts/ define tipos (ExtraccionValidada, VerificacionAdversarial, SeñalEscalamiento)
- [ ] app/llm/ = pii_redactor.py + extractor.py + verifier.py + message_log.py
- [ ] app/db/ = models.py + session.py + crud.py
- [ ] app/orchestrator/ = u2_handler.py (NO règles, solo orquestación)
- [ ] tests/ separado: unit/ (mocked) + integration/ (real LLM)

**Checklist:**
- [ ] Línea ~95: `app/contracts/` tiene extraccion.py, verificacion.py, senales.py
- [ ] Línea ~100: `app/llm/` tiene pii_redactor.py, extractor.py, verifier.py, message_log.py
- [ ] Línea ~105: `app/llm/templates/` tiene prompts (no secrets)
- [ ] Línea ~110: `app/db/` tiene models.py (SQLAlchemy), session.py, crud.py (C4 lookup)
- [ ] Línea ~115: `app/orchestrator/u2_handler.py` (orquesta, no toca rules/)
- [ ] Línea ~120: `tests/unit/` vs `tests/integration/` separados
- [ ] Línea ~125: `tests/strats/` con fixtures por estrato (happy, campos-faltantes, fraude, etc)

**Issues encontrados:**

---

### Gate I3: Dependencias (pyproject.toml)

**Líneas:** 145-200

**Criterios:**
- [ ] anthropic >= X.Y.Z (TBD, con nota "verificar en Code Gen")
- [ ] pydantic >= 2.0 (strict validation, hereda U1)
- [ ] sqlalchemy >= 2.0
- [ ] langfuse >= 0.6.0 (opcional MVP)
- [ ] NO hardcodeadas versiones exactas (excepto anthropic, que es "TBD verificar")
- [ ] python >= 3.10

**Checklist:**
- [ ] Línea ~155: `anthropic >= X.Y.Z` (comentario "TBD: Code Gen to verify...")
- [ ] Línea ~156: `pydantic >= 2.0`
- [ ] Línea ~157: `sqlalchemy >= 2.0`
- [ ] Línea ~158: `langfuse >= 0.6.0`
- [ ] Línea ~159: `python >= 3.10`
- [ ] Línea ~160: `psycopg` (PostgreSQL driver, no versión fija)
- [ ] Línea ~165: `[dev]` include pytest, pytest-cov, httpx

**Issues encontrados:**

---

### Gate I4: Environment Configuration (.env, config.py)

**Líneas:** 205-290

**Criterios:**
- [ ] .env.example es template (GITIGNORE: .env real)
- [ ] .env.example flagea ANTHROPIC_API_KEY required
- [ ] config.py carga desde .env
- [ ] Model IDs (EXTRACTOR_MODEL, VERIFIER_MODEL) aquí, no hardcoded
- [ ] DATABASE_URL, LOG_LEVEL, LANGFUSE_API_KEY (opcional) en config

**Checklist:**
- [ ] Línea ~215: `# REQUIRED ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Línea ~220: `.env` está en `.gitignore` (comentario)
- [ ] Línea ~240: `class Settings(BaseSettings)`
- [ ] Línea ~242: `ANTHROPIC_API_KEY: str` (required, error if missing)
- [ ] Línea ~243: `EXTRACTOR_MODEL: str = "claude-haiku-4-5"`
- [ ] Línea ~244: `VERIFIER_MODEL: str = "claude-sonnet-5"`
- [ ] Línea ~250: `class Config: env_file = ".env"`
- [ ] Línea ~252: `extra = "ignore"` (no error si extra vars)

**Issues encontrados:**

---

### Gate I5: Local Dev Workflow

**Líneas:** 295-380 (Step 0-5)

**Criterios:**
- [ ] Step 0: Setup (venv, .env, deps)
- [ ] Step 1: docker-compose up -d (postgres health check)
- [ ] Step 2: pytest tests/unit/ -v (mocked LLM, rápido)
- [ ] Step 3: pytest tests/integration/ -v (real LLM, si ANTHROPIC_API_KEY)
- [ ] Step 4: uvicorn app.main:app --reload (hot-reload)
- [ ] Step 5: Test endpoint (curl POST)

**Checklist:**
- [ ] Línea ~305: Step 0 crea venv, instala deps dev
- [ ] Línea ~315: Step 1 `docker-compose up -d`, espera postgres
- [ ] Línea ~325: Step 2 `pytest tests/unit/ -v` (mocked)
- [ ] Línea ~330: Step 3 `pytest tests/integration/ -v` (si ANTHROPIC_API_KEY)
- [ ] Línea ~340: Step 4 `uvicorn app.main:app --reload`
- [ ] Línea ~350: Step 5 `curl -X POST /api/casos` (test endpoint)

**Issues encontrados:**

---

### Gate I6: Testing Strategy (Unit + Integration)

**Líneas:** 385-480

**Criterios:**
- [ ] Unit tests usan mocked Anthropic client (determinístico, rápido)
- [ ] Integration tests usan real LLM (caro, lento, marca `@pytest.mark.requires_anthropic`)
- [ ] Estratificación por casos (happy, campos-faltantes, fraude, documento-sucio)
- [ ] Coverage >= 80%
- [ ] Test naming: `test_<comportamiento>_when_<condicion>`

**Checklist:**
- [ ] Línea ~395: `from unittest.mock import MagicMock` en tests/unit/conftest.py
- [ ] Línea ~400: Fixtures definen fake responses (ExtraccionValidada mocked)
- [ ] Línea ~410: `@pytest.mark.requires_anthropic` en integration tests
- [ ] Línea ~415: Integration tests son `test_e2e_happy_path`, `test_e2e_fraude`, etc
- [ ] Línea ~420: "Stratified: happy, campos-faltantes, fraude, documento-sucio"
- [ ] Línea ~430: `assert resultado.extraccion is not None`
- [ ] Línea ~435: `assert resultado.verificacion.confianza > 0.70`

**Issues encontrados:**

---

### Gate I7: Observability Mínima (MVP)

**Líneas:** 485-530

**Criterios:**
- [ ] Logs a stdout (logger.info, no archivo)
- [ ] Langfuse optional (@observe decorator)
- [ ] Si LANGFUSE_API_KEY vacía → logs solo a stdout
- [ ] Top-3 KPIs logged: accuracy, no-invención, costo+latencia

**Checklist:**
- [ ] Línea ~495: `logger.info(f"[{etapa}] Modelo=...")` en message_log.py
- [ ] Línea ~505: `@observe(name="U2_EXTRACCION")` decorator
- [ ] Línea ~510: "Si LANGFUSE_API_KEY vacía, logs van a stdout solo"
- [ ] Línea ~515: Top-3 KPIs documentados

**Issues encontrados:**

---

### Gate I8: Restricciones MVP (N/A Honesto)

**Líneas:** 535-560

**Criterios:**
- [ ] Cloud Hosting (P7) = N/A (U5 owns)
- [ ] HA / Replicación = N/A (single-region)
- [ ] Caching distribuido = N/A (in-memory)
- [ ] Live Dashboard = N/A (U5 owns UI)
- [ ] Load testing = N/A (single-user dev)
- [ ] HTTPS/TLS = N/A (HTTP localhost)

**Checklist:**
- [ ] Línea ~545: Tabla MVP restricciones clara
- [ ] Línea ~550: Cada item N/A tiene "Razón" + "U5 owns" o explícita

**Issues encontrados:**

---

## Resumen de Review

**Total Gates Revisados:** 14 (6 en NFR Design + 8 en Infrastructure Design)

**Gate Checklists:**
- NFR Design: D1-D6 ✅
- Infrastructure Design: I1-I8 ✅

**Issues Totales Encontrados:** ___

**Bloqueadores para Code Gen:** (listar si hay alguno)

**Cambios Recomendados:** (listar si hay)

---

**Aprobación Final:**
- [ ] NFR Design: APROBADO
- [ ] Infrastructure Design: APROBADO
- [ ] Listo para Code Generation (Paso 7)

---
