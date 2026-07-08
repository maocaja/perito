# Plan de Code Generation — U1 · Fundaciones & Contratos

> **Fase**: Construction · **Actividad**: 5 (Code Generation) · **Regla**: `construction/code-generation.md` (Part 1 = Planning, este doc; Part 2 = Generation, tras aprobación).
> **Fuente única de verdad** de la generación de U1. **Workspace root**: `/Users/mauricio/dev/perito`. Greenfield.
> **Historias**: H-16 (generador sintético + fraude fail-closed), H-17 (tool contracts tipados + validación).

## 🔒 Confirmación de rutas protegidas
- U1 **NO** escribe en `backend/app/rules/` (P2, U3) ni en `backend/app/orchestrator/` (P4, U4) — rutas protegidas por el hook `protect-critical-paths.sh`.
- Si cualquier paso pretendiera escribir ahí, **se detiene** y se avisa. (No aplica: ningún paso de U1 los toca.)

## Confirmación de dependencias (sin deps nuevas fuera de lo aprobado)
- Confirmadas en tech-stack: **Pydantic** (strict), **Hypothesis** (PBT), **pytest**, **PostgreSQL+pgvector**, **FastAPI** (scaffold), **Faker `es_CO`** (🆕 aprobada), **psycopg** (driver). **Langfuse** (dev-env, contenedor).
- **Ninguna dep nueva** fuera de estas. Si un paso necesitara otra, se marca y se pregunta antes.

---

## Estructura de código a crear (rutas exactas — nunca `aidlc-docs/`)
```
backend/
  app/
    __init__.py
    config.py                 # settings: EMBEDDING_DIM, FAKER_LOCALE=es_CO, DB/langfuse via env
    contracts/                # H-17 — Pydantic strict (VOs/entidad compartidos)
      __init__.py
      enums.py                # EstadoCaso, ResultadoCobertura, CalidadDoc, RolUsuario
      pii.py                  # marcador PII (Annotated) + registro introspectable
      caso.py                 # Caso (estado sin setter público), Usuario, RangoFechas
      poliza.py               # Poliza, Clausula, ResultadoPoliza
      extraccion.py           # CampoExtraido, EvidenciaOrigen, ExtraccionValidada, AvisoNormalizado
      dictamen.py             # Dictamen, AlertaFraude, Cotas
      dataset.py              # FilaEntrada (puerto), GroundTruth
    security/
      __init__.py
      redaction.py            # PIIRedactingLogSerializer + LLMPayloadBuilder (interfaz deny-by-default)
    synthetic/                # H-16 — generador
      __init__.py
      adapters.py             # KaggleAdapter -> FilaEntrada (Q3 adapter)
      generator.py            # fila -> (Aviso, Poliza, GroundTruth) + inyección fraude fail-closed
    rag/                      # M10 — estructura de índice
      __init__.py
      schema.py               # esquema pgvector con dimensión PARAMETRIZADA (no hardcode)
    main.py                   # FastAPI scaffold mínimo (health) — superficie real en U4
  tests/
    __init__.py
    generators.py             # generadores de dominio Hypothesis (PBT-07)
    test_contracts_roundtrip.py     # PBT: round-trip (RULE-CTR-01)
    test_contracts_invariants.py    # PBT: deducible>=0, enums, ResultadoPoliza, Dictamen-clausula
    test_validation_failclosed.py   # pytest: strict rechaza malformados (RULE-CTR-02)
    test_generator_failclosed.py    # pytest: fraude sin inconsistencia -> rompe (RULE-GEN-02)
    test_redaction_denybydefault.py # pytest: PII redactada por defecto (PATTERN-U1-01)
  pyproject.toml              # deps (pydantic, hypothesis, pytest, faker, psycopg, fastapi...)
  .env.example                # credenciales dev (sin secretos reales; no-default-creds)
docker-compose.yml            # postgres/pgvector + langfuse (contrato de infra-design)
```

---

## Pasos de generación (en orden; cada uno con [ ], generado bloque a bloque con revisión)

- [x] **Step 1 · Project Structure Setup** — árbol `backend/`, `pyproject.toml`. *(.env.example bloqueado por guardrail `Edit(.env.*)`; vars documentadas en config.py)* *(H-17)*
- [x] **Step 2 · Config** — `app/config.py`: `EMBEDDING_DIM` param (None en U1, PATTERN-U1-03), `FAKER_LOCALE=es_CO`, DB via env sin default-creds. *(H-17)*
- [x] **Step 3 · Business Logic — Contracts** — `app/contracts/*` (enums, pii, poliza, extraccion, dictamen, dataset, caso). **strict+forbid**; `Caso.estado`/`aprobado_por` frozen (sin setter); money `Decimal`; marcador PII en `AvisoNormalizado.texto_crudo`. *(H-17)*
- [ ] **Step 4 · Business Logic — Security/Redaction** — `app/security/redaction.py`: `PIIRedactingLogSerializer` + `LLMPayloadBuilder` (interfaz **deny-by-default**, impl real en U2). *(H-17, PATTERN-U1-01)*
- [ ] **Step 5 · Business Logic — Synthetic Generator** — `app/synthetic/*`: `KaggleAdapter`→`FilaEntrada`; `generator` con **assert fail-closed** (fraude sin inconsistencia ⇒ excepción). Faker es_CO. *(H-16 🔒)*
- [ ] **Step 6 · Repository — RAG schema** — `app/rag/schema.py`: estructura de índice pgvector con **dimensión parametrizada**; sin embeddar contenido real (M10). *(H-04 estructura)*
- [ ] **Step 7 · API scaffold** — `app/main.py`: FastAPI mínimo (health check). Superficie real en U4. *(scaffold)*
- [ ] **Step 8 · Unit Tests** — `tests/*`: generadores de dominio (PBT-07) + **PBT Hypothesis** (round-trip, invariantes) + pytest (validación fail-closed, generador fail-closed, redacción deny-by-default). Naming `test_<comportamiento>_when_<condicion>`. *(H-16/H-17, RNF-22..27)*
- [ ] **Step 9 · Deployment Artifacts (dev-env)** — `docker-compose.yml` (postgres/pgvector + langfuse) contra el contrato de `infrastructure-design.md`. *(infra dev)*
- [ ] **Step 10 · Documentation** — `aidlc-docs/construction/u1-fundaciones-contratos/code/code-summary.md`. *(doc)*

## Cobertura de historias
- **H-16** (generador + fraude fail-closed): Steps 5, 8, 9.
- **H-17** (contratos tipados + validación): Steps 1-4, 8.

## Realización del diseño (lo que el re-check verificará que es código real, no doc)
| Diseño | Dónde se realiza |
|---|---|
| `strict=True` + `extra="forbid"` | Step 3 (todos los contratos) |
| Marcadores PII + 2 redactores deny-by-default | Steps 3 (pii.py) + 4 (redaction.py) |
| `Caso.estado` sin setter público (P1) | Step 3 (caso.py) |
| Generador assert fail-closed (RULE-GEN-02 🔒) | Step 5 |
| PBT Hypothesis (round-trip + invariantes) | Step 8 |
| `EMBEDDING_DIM` parametrizado | Steps 2 + 6 |
| money como `Decimal` (no float) | Step 3 |

## Modo de generación
Bloque a bloque (Step por Step), presentando cada bloque para tu revisión — **no "aprueba todo de una vez"** (runbook Estación 5). Tú confirmas antes de pasar al siguiente. La app va a `backend/` (workspace root); la doc a `aidlc-docs/.../code/`.
