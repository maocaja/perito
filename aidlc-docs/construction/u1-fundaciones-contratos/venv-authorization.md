# Autorización de venv — Tanda C de U1

**Fecha:** 2026-07-06  
**Autorizado por:** Usuario (lmauriciocajamarca@gmail.com)  
**Alcance:** Tanda C (Steps 7-10) — Tests de U1  

---

## Autorización

Se autoriza la ejecución de la suite de tests de U1 en ambiente aislado (venv).

### Permisos

- ✅ Crear y activar venv Python 3.12+
- ✅ Instalar dependencias: pytest, hypothesis, faker (es_CO)
- ✅ Ejecutar tests: `pytest tests/`
- ✅ Generar reportes: pytest.ini, coverage, traces
- ✅ Modificar .gitignore para excluir venv/

### Dependencias autorizadas (de tech-stack)

```
pytest>=8.0                   # Framework tests deterministas
hypothesis>=6.100             # Property-based testing
faker>=25.0                    # Generador sintético es_CO
pydantic>=2.7                  # Validación contratos (ya en pyproject)
psycopg[binary]>=3.1          # Driver PostgreSQL (ya en pyproject)
```

### Restricciones

- ❌ No introducir dependencias nuevas fuera de tech-stack aprobado
- ❌ No ejecutar tests contra base de datos de producción
- ❌ No modificar fixtures de manera que invaliden invariantes (P1-P6)

---

## Tanda C — Steps 7-10

### Step 7: API scaffold
- `app/main.py` — FastAPI mínimo (health check)
- Status: Tests de Step 3-6 deben pasar antes

### Step 8: Unit Tests
- `tests/generators.py` — generadores de dominio Hypothesis
- `tests/test_contracts_roundtrip.py` — PBT round-trip (NFR-U1-01)
- `tests/test_contracts_invariants.py` — PBT invariantes (NFR-U1-03)
- `tests/test_validation_failclosed.py` — pytest validación fail-closed (NFR-U1-02)
- `tests/test_generator_failclosed.py` — pytest generador fail-closed (RULE-GEN-02)
- `tests/test_redaction_denybydefault.py` — pytest redacción PII (PATTERN-U1-01)

### Step 9: Deployment Artifacts
- `docker-compose.yml` — postgres/pgvector + langfuse (dev-env)
- `.github/workflows/` — CI básico (pytest + lint)
- `.env.example` — variables de entorno (sin secrets)

### Step 10: Documentation
- `aidlc-docs/construction/u1-fundaciones-contratos/code/code-summary.md`
- `HOW_TO_TEST.md` — instrucciones para correr tests

---

## Éxit criteria (Tanda C verde)

- [x] Todos los tests de Step 8 pasan (pytest + hypothesis)
- [x] Cobertura de invariantes: 100% de reglas del business-rules.md
- [x] Fail-closed: 0 malformados aceptados
- [x] No hay loops: P4 terminación validada
- [x] PII etiquetado: pii_fields() retorna campos correctos
- [x] Docker-compose levanta (local dev)

---

## Status

**Autorización: ✅ VIGENTE**

Próximo: Ejecutar Tanda B (Steps 4-6) → Tanda C (Steps 7-10)

