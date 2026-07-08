# U2-C4 Policy Lookup — Code Generation Summary

**Date:** 2026-07-07
**Component:** C4 Policy Lookup / Grounding
**Unit:** U2 · Extracción · Verificación · Grounding
**Story:** H-04 (policy lookup deterministic, candidatas sin forzar match)

---

## Components Created

### Core Module
- **File:** `backend/app/policy/lookup.py`
- **Lines:** ~130
- **Key Functions:**
  - `call_c4_policy_lookup(extraccion: ExtraccionValidada) -> ResultadoPoliza`
  - `_lookup_exact(numero_poliza: str) -> Optional[Poliza]`
  - `_lookup_candidates(numero_poliza: str, limit: int) -> list[Poliza]`
  - `set_poliza_store(store: dict[str, Poliza])` — for testing

### Tests
- **File:** `backend/tests/test_u2_policy_lookup.py`
  - 5 test cases: exact match, no match, missing numero_poliza, Trap 3, contract validation
  - Mock Poliza repository (no real Postgres)

- **File:** `backend/tests/test_u2_c2_c4_integration.py`
  - 3 integration tests: C2 output → C4 flow
  - End-to-end .campos access verification

### Documentation
- **File:** `backend/app/policy/README.md`
  - Architecture overview
  - 4 Traps hardened
  - Testing discipline
  - Future: real Postgres migration path

---

## Traps Honored

| Trap | Evidence | Status |
|---|---|---|
| **1. Cero LLM** | `grep "^from anthropic\|^import anthropic" backend/app/policy/lookup.py` → zero | ✅ |
| **2. .campos access** | `numero_poliza = next((c.valor for c in extraccion.campos ...))` | ✅ |
| **3. No forzar match** | `poliza=None` when `encontrada=False`; RULE-CTR-07 enforced by Pydantic | ✅ |
| **4. Mock BD + suite** | All tests mock Poliza store; full suite `pytest backend/tests/ -q` → 44 passed | ✅ |

---

## Test Results

**Full Backend Test Suite:**
```
44 passed in 1.61s
```

- **Previous (U1 + U2-C2/C3):** 36 passed
- **New (U2-C4):** 8 new tests
- **All passing:** ✅ Zero failures, zero warnings

### Test Coverage

**Unit Tests (test_u2_policy_lookup.py):**
- `test_exact_match_returns_poliza()` — encontrada=True
- `test_no_match_returns_candidatas()` — encontrada=False, poliza=None
- `test_missing_numero_poliza_returns_false()` — watch-item 2 (no crash)
- `test_candidata_not_promoted_to_poliza()` — Trap 3 verified
- `test_resultadopoliza_contract_validation()` — RULE-CTR-07 enforced

**Integration Tests (test_u2_c2_c4_integration.py):**
- `test_c2_c4_flow_exact_match()` — ExtraccionValidada → ResultadoPoliza
- `test_c2_c4_flow_missing_numero_poliza()` — graceful fallback
- `test_c2_c4_flow_candidates()` — similarity search verified

---

## Design Decisions

### 1. Similarity: difflib (stdlib)
- Used `SequenceMatcher` (Python stdlib) for similarity scoring
- **Rationale:** No new dependencies (watch-item 1), deterministic, sufficient for MVP
- **Alternative (Future):** SQL LIKE for substring match, or pgvector for pgtext similarity

### 2. Watch-Item 2: Missing numero_poliza
- Returns `ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])`
- Does NOT raise exception (fail-closed, P4 discipline)
- Verified by test: `test_missing_numero_poliza_returns_false()`

### 3. Mock Repository Pattern
- Global `_POLIZA_STORE` dict, setter `set_poliza_store()` for testing
- Production: Replace `_lookup_exact()` and `_lookup_candidates()` with SQL queries
- Keeps unit tests deterministic, no real Postgres dependency

### 4. ResultadoPoliza Reuse
- Imported from `app.contracts.poliza` (U1 contract)
- RULE-CTR-07 validator enforces contract invariant: `encontrada=False ⇒ poliza=None`
- Never redefined locally; pure delegation to Pydantic validation

---

## Integration Points

**Inputs:**
- `ExtraccionValidada` from C2 (Extractor/Verifier)
- .campos iteration to extract numero_poliza

**Outputs:**
- `ResultadoPoliza` to U3-C5 (Coverage Rules motor)

**No dependencies:**
- Zero LLM
- Zero new packages (only stdlib difflib)
- Only contracts from U1 and extraccion from U2-C2

---

## Next Steps

1. **Real Postgres Layer:** Implement SQL queries replacing `_lookup_exact()` and `_lookup_candidates()`
2. **Policy RAG:** Integrate with U1 `rag/` (pgvector) for clause retrieval (not match decision)
3. **U3 Integration:** Pass ResultadoPoliza output to coverage rules motor

---

## Verification Checklist (User Review Criteria)

- [ ] `grep anthropic` in policy/ → zero hits ✅
- [ ] numero_poliza via .campos (not plano) ✅
- [ ] ResultadoPoliza/Poliza imported, not redefined ✅
- [ ] No candidate promoted to poliza (RULE-CTR-07) ✅
- [ ] pytest backend/tests/ -q complete suite → 44 passed ✅

