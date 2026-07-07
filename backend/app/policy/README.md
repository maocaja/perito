# C4 Policy Lookup — Deterministic Grounding

**Component:** C4 · Policy Lookup / Grounding (U2 leg 3 of 4)
**Invariant:** ZERO LLM, deterministic SQL match + similarity fallback, no forced matches

## Architecture

### Purpose
Given `numero_poliza` extracted by C2, return:
- Exact match: `ResultadoPoliza(encontrada=True, poliza=<Poliza>)`
- No match: `ResultadoPoliza(encontrada=False, poliza=None, candidatas=[...])`

No LLM involved. Desbloquea U3 (coverage rules consume policy match).

### Key Design

1. **Cero LLM (Trap 1):** Pure SQL/dict logic. Zero `anthropic` imports.
   - Exact match: dict lookup by numero_poliza
   - Candidates: difflib.SequenceMatcher (stdlib, no new deps)

2. **.campos Access (Trap 2):** Read numero_poliza from ExtraccionValidada.campos
   ```python
   numero_poliza = next(
       (c.valor for c in extraccion.campos
        if c.nombre == "numero_poliza" and not c.ausente),
       None
   )
   ```

3. **No Forced Match (Trap 3):** RULE-CTR-07 enforced by Pydantic
   - `encontrada=False ⇒ poliza=None` (never promote candidate)
   - Candidatas allowed but separate

4. **Mock BD Testable (Trap 4):** In-memory store for unit tests, not real Postgres

## Interface

### Input
- `ExtraccionValidada` from C2 (contains .campos list)

### Output
- `ResultadoPoliza(encontrada, poliza, candidatas)` — Pydantic contract from U1

## Testing

Unit tests mock the Poliza store (no real Postgres). Test cases:
- Exact match found
- No match → candidates returned
- Missing numero_poliza → graceful fallback
- Trap 3: candidate never promoted to poliza

Run: `pytest backend/tests/ -q` (full suite, not subset)

## Future: Real Postgres

Replace `_lookup_exact()` and `_lookup_candidates()` with real SQL queries when database layer is ready.
