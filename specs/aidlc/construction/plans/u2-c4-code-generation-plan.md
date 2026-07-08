# U2-C4 PolicyLookup Code Generation Plan

**Component:** C4 Policy Lookup / Grounding (U2 leg 3 of 4)
**Unit:** U2 · Extracción · Verificación · Grounding
**Stories Implemented:** H-04 (Policy lookup + candidatas por similitud, sin forzar match)
**Dependencies:** U1 (Contracts: ResultadoPoliza, Poliza), U2-C2 (ExtraccionValidada output)

---

## Context

### Purpose
Deterministic policy grounding: given `numero_poliza` from C2 extraction, return exact match or similarity-based candidates without LLM involvement. Desbloquea U3 (coverage rules consume policy match output).

### Stories Covered
- **H-04**: Policy lookup deterministic (SQL), candidatas por similitud (RF-10/P4), no forzar match

### Interfaces & Contracts
- **Input:** `ExtraccionValidada` (from C2)
  - Read: `numero_poliza` via `.campos` (not flat attribute)
- **Output:** `ResultadoPoliza` (from U1 contracts — REUSE, do NOT redefine)
  - `encontrada: bool`
  - `poliza: Poliza | None`
  - `candidatas: list[Poliza]` (optional, when encontrada=False)
- **Validator:** RULE-CTR-07 in `ResultadoPoliza` enforces: `encontrada=False ⇒ poliza=None`

### Key Invariants (Traps to Avoid)
1. **Trap 1: Cero LLM** — SQL determinístico puro, zero `anthropic` imports
2. **Trap 2: .campos access** — `next((c.valor for c in extraccion.campos if c.nombre=="numero_poliza" and not c.ausente), None)` — NOT `extraccion.numero_poliza`
3. **Trap 3: No forzar match** — Sin exacto → `encontrada=False, poliza=None, candidatas=[...]`; REUSE `ResultadoPoliza` validator, no re-impl
4. **Trap 4: Mock BD + suite completa** — Unit tests mock Postgres (NOT real DB); `pytest backend/tests/ -q` always, never subset

---

## Code Generation Steps

### Step 1: Business Logic — Policy Lookup Module
- [ ] **File:** `backend/app/policy/lookup.py` (NEW)
- [ ] **Content:**
  - Function `call_c4_policy_lookup(extraccion: ExtraccionValidada) -> ResultadoPoliza`
  - Extract `numero_poliza` via `.campos` (Trap 2 compliance)
  - **Exact match:** Query Postgres by `numero_poliza` (deterministic SQL, Trap 1 zero anthropic)
  - **No match:** Query candidates via SQL LIKE or Levenshtein distance (deterministic similarity, no LLM)
  - Return `ResultadoPoliza(encontrada=True, poliza=match)` or `ResultadoPoliza(encontrada=False, poliza=None, candidatas=[...])`
  - Validate output against `ResultadoPoliza` contract (RULE-CTR-07 enforced by Pydantic, Trap 3)
  - Fail-closed: raise `PolicyLookupError` if lookup fails (no relax/invent)
- [ ] **Imports:**
  - `from app.contracts.extraccion import ExtraccionValidada`
  - `from app.contracts.poliza import ResultadoPoliza, Poliza`
  - `from app.contracts.enums import ResultadoCobertura` (if needed for context)
  - Database adapter (e.g., SQLAlchemy session, or raw psycopg2)
  - **NO:** `from anthropic import Anthropic` or similar (Trap 1)
- [ ] **Error Handling:**
  - Missing `numero_poliza` in `.campos` → return `ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])`
  - DB error → raise `PolicyLookupError` (fail-closed, P4)

### Step 2: Business Logic — Similarity Search Helper (Optional)
- [ ] **File:** `backend/app/policy/similarity.py` (NEW, optional if SQL LIKE insufficient)
- [ ] **Content (if implemented):**
  - Helper function `candidates_by_similarity(numero_poliza: str, limit: int = 5) -> list[Poliza]`
  - Deterministic scoring (SQL distance, no ML/LLM)
  - Return sorted list, but do NOT promote any to `poliza=` (Trap 3)

### Step 3: Business Logic Unit Testing
- [ ] **File:** `backend/tests/test_u2_policy_lookup.py` (NEW)
- [ ] **Mock BD Setup:**
  - Fixture `mock_poliza_repo()` — dict or ORM mock, not real Postgres
  - Mock queries: exact match, partial match (candidates), no match
- [ ] **Test Cases:**
  - [ ] `test_exact_match_returns_poliza()` — numero_poliza found → `encontrada=True, poliza=<obj>`
  - [ ] `test_no_match_returns_candidatas()` — numero_poliza not found → `encontrada=False, poliza=None, candidatas=[...]`
  - [ ] `test_missing_numero_poliza_empty_candidatas()` — extraction has no numero_poliza → `encontrada=False, poliza=None`
  - [ ] `test_candidata_not_promoted_to_poliza()` — even if 1 candidate, `poliza=None` (Trap 3)
  - [ ] `test_resultadopoliza_contract_validation()` — output passes Pydantic validation (RULE-CTR-07 enforced)
- [ ] **No real Postgres:** All tests use mock (Trap 4)

### Step 4: Integration with C2 Output
- [ ] **File:** `backend/tests/test_u2_c2_c4_integration.py` (NEW, optional)
- [ ] **Content (if deemed necessary):**
  - Test ExtraccionValidada (from C2) → PolicyLookup → ResultadoPoliza flow
  - Verify `.campos` extraction of `numero_poliza` works end-to-end
  - Mock both extraction output and Poliza repo

### Step 5: Contract Validation & No Re-implementation
- [ ] **Verify in code:**
  - `ResultadoPoliza` imported from `app.contracts.poliza`, NOT redefined
  - `Poliza` imported from `app.contracts.poliza`, NOT redefined
  - RULE-CTR-07 (encontrada=False ⇒ poliza=None) enforced by Pydantic contract, NOT custom code
- [ ] **Grep checks:**
  - `grep -r "class ResultadoPoliza\|class Poliza" backend/app/policy/` → **zero hits** (no redefinition)
  - `grep "encontrada.*True.*poliza" backend/app/policy/lookup.py` → **zero hits** (no force)
  - `grep -r "anthropic\|Anthropic" backend/app/policy/` → **zero hits** (Trap 1)

### Step 6: Build & Test (Full Suite)
- [ ] **Execute:** `ANTHROPIC_API_KEY=test pytest backend/tests/ -q`
- [ ] **Expected:** 36+ tests passing (U1 + U2-C2/C3 + U2-C4 new tests)
- [ ] **Failure handling:** If any test fails, diagnose before moving to next step (fail-closed discipline)

### Step 7: Documentation
- [ ] **File:** `backend/app/policy/README.md` (optional)
- [ ] **Content:** Brief description of C4 flow, no external dependencies, deterministic guarantee

### Step 8: Code Summary
- [ ] **File:** `aidlc-docs/construction/u2-c4/code/policy-lookup-summary.md` (NEW)
- [ ] **Content:**
  - Components created/modified
  - Key decisions (SQL deterministic, no LLM, Trap 1-4 honored)
  - Test coverage summary
  - Integration points with C2, C5 (U3)

---

## Total Steps: 8

**Estimated Scope:** 
- 1 core module (policy/lookup.py, ~150-200 lines)
- 1 optional helper (policy/similarity.py, ~50-100 lines)
- 4 test cases + 1 integration test
- Full suite regression (36+ tests)

**Delivery:** Code in `backend/app/policy/`, tests in `backend/tests/`, summary in `aidlc-docs/`.

---

## Approval Checklist (User Review)

Before Part 2 (Generation), confirm:
- [ ] **4 Traps prominently in mind** — plan honors all 4
- [ ] **SQL deterministic** — zero LLM, grep check ready
- [ ] **.campos access** — not plano attribute access
- [ ] **ResultadoPoliza reuse** — no redefinition, contract validation honored
- [ ] **Mock BD + suite completa** — test discipline clear, pytest backend/tests/ (not subset)


---

## ✅ EXECUTION COMPLETE (2026-07-07)

All 8 steps executed and verified:

- [x] Step 1: Business Logic — Policy Lookup Module (`backend/app/policy/lookup.py`)
- [x] Step 2: Similarity Helper — Integrated (difflib stdlib, no new deps)
- [x] Step 3: Business Logic Unit Testing (`test_u2_policy_lookup.py`, 5 tests, mock BD)
- [x] Step 4: Integration Tests (`test_u2_c2_c4_integration.py`, 3 tests, C2→C4 flow)
- [x] Step 5: Contract Verification — All traps honored (grep checks passed)
- [x] Step 6: Build & Test — Full suite `pytest backend/tests/ -q` → **44 passed**
- [x] Step 7: Documentation (`backend/app/policy/README.md`)
- [x] Step 8: Code Summary (`aidlc-docs/construction/u2-c4/code/policy-lookup-summary.md`)

## Verification Results (User Verified, Not Declared)

✅ Suite: 44 passed (zero failures)
✅ TRAP 1: Cero LLM (only stdlib + contracts imports)
✅ TRAP 2: .campos access (not plano)
✅ TRAP 3: No forced match (candidatas never promoted)
✅ Watch 1: Deps clean (difflib stdlib only)
✅ Watch 2: None/ausente handled (no crash)

## Note on Scope (Honest Assessment)

_lookup_exact() uses in-memory dict (_POLIZA_STORE). Real Postgres persistence is stubbeaded.
- Defensible for MVP/testing/demo with synthetic data
- Do NOT count as "queries the database" — it's a placeholder
- Integration with real Postgres deferred to U4 integration or RAG wiring
- When connected to actual data layer, replace `_lookup_exact()` with SQL SELECT

## APPROVED ✅

Deterministic, zero LLM, mock BD testable, full suite green, framework executed clean on first pass.

