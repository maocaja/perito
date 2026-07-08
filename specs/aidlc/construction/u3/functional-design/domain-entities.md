# U3 Domain Entities — Contract Review & Integration

**Unit:** U3 · Cobertura determinística · Fraude
**Scope:** Dictamen, AlertaFraude, Poliza, Clausula contracts (U1 base + U3 usage)

---

## Entity 1: Dictamen (Coverage Ruling)

**Location:** `backend/app/contracts/diccionario.py` (already exists U1)

**Pydantic v2 Contract:**
```python
class Dictamen(Contract):
    """Ruling on claim coverage (P2 + P3).
    
    RULE-CTR-03: sin regla_aplicada + cláusula → inválido.
    Resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}.
    """
    
    resultado: ResultadoCobertura  # enum
    regla_aplicada: str  # "R1", "R2", "R3", "R4", "R5"
    clausula: Clausula  # MUST be non-null (RULE-CTR-03, P3)
    deducible_calculado: Decimal = Field(ge=0)  # R5 output
    
    @model_validator(mode="after")
    def _cita_obligatoria(self) -> "Dictamen":
        if self.clausula is None:
            raise ValueError("Dictamen: clausula obligatoria (P3, RULE-CTR-03)")
        return self
```

**U3 Usage:**
- Motor builds Dictamen after R1-R5 cascade
- Always cites a single regla_aplicada (R1 if early exit, R5 if cascade completes)
- Clausula is looked up by Clausula.tipo (matching regla_aplicada)
- No invented fields; contract enforces completeness

**Integration Points:**
- Input: `ExtraccionValidada.campos` (tipos) + `ResultadoPoliza.poliza` (cláusulas)
- Output: `Caso.dictamen` (persist)
- U4 consumes: Dictamen.resultado (to propose estado)

---

## Entity 2: AlertaFraude (Fraud Signal)

**Location:** `backend/app/contracts/fraude.py` (REVIEW: use U1 contract as-is)

**Pydantic v2 Contract (MUST reuse U1, not invent):**
```python
class AlertaFraude(Contract):
    """Fraud suspicion signal (P6 + P1).
    
    NEVER changes Caso.estado (P1). Severidad + evidencia only.
    inconsistencias must be non-empty (P6: evidence mandatory).
    """
    
    severidad: Literal["BAJA", "MEDIA", "ALTA"]
    inconsistencias: list[EvidenciaOrigen] = Field(min_length=1)  # P6
    explicacion: str = Field(min_length=1)  # Razonamientos LLM + hard rules
    
    @model_validator(mode="after")
    def _evidencia_obligatoria(self) -> "AlertaFraude":
        if not self.inconsistencias:
            raise ValueError("AlertaFraude: inconsistencias no vacío (P6, evidencia obligatoria)")
        return self
```

**⚠️ NO Extend Beyond U1 Contract:**
- DO NOT add new fields like `evidencia: list[{valor_esperado, valor_extraido}]`
- If needed, file issue for U1 extension (out of scope for U3 MVP)

**U3 Usage:**
- Detect hard inconsistencies (code) → EvidenciaOrigen list
- Call LLM for reasoning → explicacion string
- Compute severidad (deterministic mapping)
- Validate via contract (inconsistencias ≠ empty)
- Emit to `Caso.alerta_fraude` (independent of Dictamen)

**Integration Points:**
- Input: `ExtraccionValidada.campos`, `ResultadoPoliza.poliza`
- Output: `Caso.alerta_fraude` (persist, suggest only)
- U4 consumes: AlertaFraude.severidad (may propose REQUIERE_REVISION vía signal)
- **CRITICAL:** Never mutates Caso.estado directly (P1)

---

## Entity 3: Poliza (Insurance Policy)

**Location:** `backend/app/contracts/poliza.py` (already exists U1)

**Contract (unchanged for U3):**
```python
class Poliza(Contract):
    """Insurance policy (from U2-C4 lookup).
    
    Used by U3 as RO (read-only reference for rules).
    """
    
    numero: str  # From ResultadoPoliza.poliza
    vigencia: RangoFechas  # R1 input
    coberturas_contratadas: list[str]  # R2 input
    exclusiones: list[str]  # R3 input
    suma_asegurada: Decimal  # R4 input (limite)
    deducible: Decimal  # R5 input (UNIQUE per policy)
    clausulas: list[Clausula]  # R1-R5 citatation lookup
```

**U3 Usage:**
- Read-only; never modified by C5 or C6
- .clausulas iterated to find regla→tipo match (R1→vigencia, ..., R5→deducible)
- .vigencia, .coberturas_contratadas, .suma_asegurada fed into R1-R5 functions
- .deducible used in R5 calculation

**Key Constraint for U3:**
- Poliza.deducible is UNIQUE (not per tipo_siniestro) — MVP scope
- SOAT forward-compat (RF-14): Poliza.es_soat flag exists but no special logic yet

---

## Entity 4: Clausula (Policy Clause)

**Location:** `backend/app/contracts/poliza.py` (already exists U1)

**Contract (unchanged for U3):**
```python
class Clausula(Contract):
    """Policy clause — source of all rulings (P3).
    
    Cited in every Dictamen.clausula.
    """
    
    id: str  # "vigencia-2026", "cobertura-auto", "exclusion-edad", "limite-50m", "deducible-500k"
    texto: str  # Full clause text (e.g., "Vigencia desde 2026-01-01 hasta 2027-12-31")
    tipo: TipoClausula  # {VIGENCIA, COBERTURA, EXCLUSION, LIMITE, DEDUCIBLE}
    referencia: str  # "Póliza Art. 3", "Anexo II", etc.
```

**U3 Usage:**
- Motor searches by tipo (R1→find(tipo=VIGENCIA), R2→find(tipo=COBERTURA), etc.)
- Selected Clausula is populated into Dictamen.clausula
- No creation or modification; only read + citation

**Key Constraint for U3:**
- Every Dictamen MUST cite a Clausula (never null, RULE-CTR-03)
- If not found by tipo → escalate to REQUIERE_REVISION (don't invent)

---

## Entity 5: ExtraccionValidada (Input from U2-C2)

**Location:** `backend/app/contracts/extraccion.py` (already exists U1)

**Used Fields in U3:**
```python
extraccion.campos: list[CampoExtraido]

# Motor reads via .campos iteration:
numero_poliza: CampoExtraido (used to correlate with ResultadoPoliza)
tipo_siniestro: CampoExtraido (R2 input)
fecha_siniestro: CampoExtraido (R1 input)
monto_siniestro: CampoExtraido (R4 input)

# Fraude uses same .campos for inconsistency detection
```

**U3 Interaction:**
- Do NOT assume fields are present; check `campo.ausente`
- If `campo.ausente = True` → escalate to REQUIERE_REVISION (don't decide on incomplete data)
- Read values ONLY via `.campos` iteration, NEVER as plano attributes

---

## Entity 6: ResultadoPoliza (Input from U2-C4)

**Location:** `backend/app/contracts/poliza.py` (already exists U1)

**Used Fields in U3:**
```python
resultado_poliza.encontrada: bool  # True if exact match found
resultado_poliza.poliza: Poliza | None  # Full policy object if encontrada=True

# U3 Logic:
if resultado_poliza.encontrada:
    poliza = resultado_poliza.poliza
    # Run R1-R5 with poliza
else:
    # No policy found; escalate to REQUIERE_REVISION (can't evaluate rules)
    # Or suggest REQUIERE_REVISION signal via U4
```

**Key Constraint:**
- If `encontrada=False`, U3 should NOT manufacture a Dictamen
- Escalate with clear reason: "Póliza no encontrada"

---

## Integration Diagram

```
U2-C2: ExtraccionValidada
  ↓
U2-C4: ResultadoPoliza
  ├─ encontrada: bool
  └─ poliza: Poliza (if found)
  
  ↓
U3-C5: Motor
  ├─ inputs: extraccion.campos, poliza
  ├─ R1-R5 cascade
  └─ output: Dictamen {
       resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION},
       regla_aplicada ∈ {R1, R2, R3, R4, R5},
       clausula (never null, RULE-CTR-03),
       deducible_calculado ≥ 0
     }

U3-C6: Fraude
  ├─ inputs: extraccion.campos, poliza, (Dictamen optional)
  ├─ inconsistency detection + LLM reasoning
  └─ output: AlertaFraude {
       severidad ∈ {BAJA, MEDIA, ALTA},
       inconsistencias: list[EvidenciaOrigen] (non-empty, P6),
       explicacion
     }
     ✅ No estado change (P1)
     ✅ Independent of Dictamen

  ↓
U4: Orchestrator consumes
  ├─ Dictamen.resultado → proposes Caso.estado (with human approval, P1)
  └─ AlertaFraude.severidad → signals REQUIERE_REVISION (only via U4, not direct)
```

---

## Validation Checklist for U3 Code

- [ ] Dictamen cites Clausula.tipo matching regla_aplicada (never null)
- [ ] AlertaFraude uses U1 contract as-is (no extension fields)
- [ ] Motor reads fields via ExtraccionValidada.campos, not plano
- [ ] Fraude reads Dictamen (context only), does NOT import rules/ module
- [ ] Early exit: R1/R2/R3 fail → NO_CUBIERTO, skip R4-R5
- [ ] Deducible UNIQUE per Poliza (not per tipo_siniestro)
- [ ] Campo ausente → REQUIERE_REVISION (not invented)
- [ ] Cláusula not found → REQUIERE_REVISION (not fabricated)
- [ ] AlertaFraude NEVER changes Caso.estado
- [ ] Pago formula: max(0, min(monto, suma) - deducible)

