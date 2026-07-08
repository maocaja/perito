# U3 NFR Design — Route Correction (P2 Boundary)

**Timestamp:** 2026-07-07
**Status:** CRITICAL FIX APPLIED ✅

---

## Issue: Incorrect fraude.py Path

### ❌ BEFORE
- Motor R1-R5: `backend/app/rules/motor_r1_r5.py` ✅
- Fraude: `backend/app/rules/fraude.py` ❌ WRONG

### ✅ AFTER
- Motor R1-R5: `backend/app/rules/motor_r1_r5.py` ✅
- Fraude: `backend/app/fraud/fraude.py` ✅

---

## Rationale: P2 Boundary Enforcement

### 1. Frontera Lógica (P2)
```
backend/app/rules/         ← LLM-free motor (determinístico)
  motor_r1_r5.py           ← Pure function, no anthropic imports
  precondiciones.py        ← Pre-validation layer
  __init__.py

backend/app/fraud/         ← LLM-driven fraud detection (non-deterministic reasoning)
  fraude.py                ← Uses LLM (import anthropic)
  __init__.py
```

**Invariant:** `fraud/ ⊄ rules/` — fraude módulo separado, nunca importa rules/

---

### 2. Hook Semantics (protect-critical-paths.sh)

**Current behavior:**
```bash
# protect-critical-paths.sh watches backend/app/rules/
# Requires explicit confirmation on changes
```

**Why separation matters:**
- Motor changes (rules/) → hook fires, needs explicit P2 verification ✅
- Fraude changes (fraud/) → NO hook, LLM changes are iterative (not P2-critical) ✅

**If fraude.py lived in rules/:**
```
Every fraude.py change (LLM prompt tuning, inconsistency types)
  → Hook fires for "motor change"
  → User confused: "Why is my fraude LLM prompt triggering motor approval?"
  → Semantics broken
```

---

### 3. Import Graph Check (P2 Validation)

**Verification command:**
```bash
grep -r "import anthropic\|from anthropic" backend/app/rules/
# Expected output: (empty)
# This proves: rules/ is LLM-free
```

**If fraude.py in rules/:**
```bash
grep -r "import anthropic" backend/app/rules/
# Returns: backend/app/rules/fraude.py:1: from anthropic import Anthropic
# FAILURE: P2 boundary broken at grep level
```

---

### 4. Module Isolation (No Circular Deps)

**Invariant:** `backend.app.fraud` does NOT import `backend.app.rules`

**C5 Orchestrator:**
```python
# backend/app/orchestrator/c5.py

# ✅ Correct:
from backend.app.rules.motor_r1_r5 import motor_cobertura
from backend.app.fraud.fraude import construir_alerta_fraude

# ❌ Wrong (if fraude in rules/):
# Import graph becomes: orchestrator → rules → (motor + fraude)
# fraud uses LLM, so rules/ has anthropic
# P2 boundary: BROKEN
```

---

## Files Corrected

1. **VERIFICATION.md:235**
   ```diff
   - Implementar `backend/app/rules/fraude.py` (Fraude Capas 1-3)
   + Implementar `backend/app/fraud/fraude.py` (Fraude Capas 1-3)
   ```

2. **fraude-determinismo.md:296**
   ```diff
   - monkeypatch.setattr("backend.app.rules.fraude.razonar_fraude", mock_call)
   + monkeypatch.setattr("backend.app.fraud.fraude.razonar_fraude", mock_call)
   ```

---

## Verification Checklist (Pre-Code Generation)

- [ ] Motor in `backend/app/rules/motor_r1_r5.py`
- [ ] Fraude in `backend/app/fraud/fraude.py`
- [ ] `grep anthropic backend/app/rules/` → empty (P2 check)
- [ ] `grep "import.*rules" backend/app/fraud/` → empty (isolation check)
- [ ] Hook protects backend/app/rules/ only (motor changes need approval)
- [ ] PBT-03 suite covers both: motor (deterministic) + fraude (with LLM mock)

---

## Ready for Code Generation

✅ NFR Design approved (all specs intact)
✅ Routes corrected (P2 boundary enforced at file level)
✅ Mock layers aligned (fraude.py monkeypatch path fixed)

**Next:** Code Generation (U3-C5 Motor), then U3-C6 Fraude

