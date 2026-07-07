# U2 Code Generation — Complete

## Files Created (7)

### 1. contracts/enums.py (new)
- TipoSiniestro enum (AUTO_COLISION, AUTO_HURTO, HOGAR_AGUA)

### 2. contracts/verificacion.py (new)
- SeñalEscalamiento (P1: no Caso.estado, only signal)
- VerificacionAdversarial (C3 Capa 1 output)
- VerificacionConsistencia (C3 Capa 2 output)
- All with strict + extra=forbid (Pydantic v2)

### 3. security/redaction.py (additive)
- redact_pii_spans_es_co() — regex for C.C., celular, email
- build_extraction_prompt_u2() — redacts, builds prompt
- Gap P7 declared: names/addresses need NER

### 4. app/config.py (additive)
- EXTRACTOR_MODEL: "claude-haiku-4-5"
- VERIFIER_MODEL: "claude-sonnet-5"
- CONFIDENCE_THRESHOLD: 0.70
- MAX_ROUNDS: 1, MAX_TOKENS_BUDGET: 10_000

### 5. llm/extractor.py (new, C2)
- call_c2_extractor(texto_crudo) → ExtraccionValidada
- output_config.format correct form (GATE 1)
- Model from config (GATE 2)
- No effort param documented (GATE 3)
- Redacted prompt (GATE 4, P5)
- Pydantic model_validate strict (fail-closed, P4)

### 6. llm/verifier.py (new, C3 two layers)
- call_c3_verifier_capa1() — Sonnet adversarial re-read
- call_c3_verifier_capa2() — deterministic checks, emits SeñalEscalamiento
- output_config.format correct (GATE 1)
- Reads .campos via iteration, not flat attributes
- Emits signal if confianza < 0.70 or inconsistency (P1, P4)

### 7. tests/ (new)
- test_u2_redaction.py — P5 redaction (cédula/celular/email → [REDACTED], póliza preserved)
- test_u2_verifier_signal.py — P1/P4 signals (confianza low → signal, not estado)

## Verification Results

✅ **Check 1:** No imports from app/rules/ or Caso.estado mutations
✅ **Check 2:** output_config uses correct form: `{"format": {"type": "json_schema", ...}}`
✅ **Check 3:** No model IDs with date suffixes (claude-haiku-4-5, claude-sonnet-5)
✅ **Check 4:** Model IDs from config.py (source of truth)

## Invariants by Construction

- **P1 (HITL):** SeñalEscalamiento emitted, never touches Caso.estado
- **P2 (Coverage):** No imports from rules/ (U3 responsibility)
- **P3 (Traceability):** logging at each step, EvidenciaOrigen in CampoExtraido
- **P4 (Termination):** ausente=True ⇒ valor=None, single-pass (MAX_ROUNDS=1), caps set
- **P5 (PII):** redact_pii_spans_es_co before LLM calls, gap P7 declared
- **P6 (Explainability):** inconsistencias list, confianza per field, checks dict

## Gates Applied

- **Gate 1:** output_config.format (API-level, stable)
- **Gate 2:** Model IDs from config (no hardcode)
- **Gate 3:** Haiku no-effort constraint documented
- **Gate 4:** LLMPayloadBuilder equivalent (redact_pii_spans_es_co) called before LLM
- **Gate 6:** P1+P2 protected (no estado mutations, no rules imports)

## Ready for Review

All files staged. Tests verify:
- P5 redaction: cédula/celular/email → [REDACTED], operational fields preserved
- P1 signals: confianza < 0.70 → SeñalEscalamiento (not Caso.estado)
- Fail-closed: Pydantic validation, exception raising on contract mismatch

Next: User review → commit.
