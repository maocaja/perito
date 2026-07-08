# U3 Business Rules — Formal Definitions & Constraints

**Unit:** U3 · Cobertura determinística · Fraude
**Scope:** R1-R5 formal definitions, validation constraints, test coverage by estrato

---

## R1: Vigencia (Validity Period)

**Rule:** Claim date must fall within policy validity range.

**Formal Definition:**
```
R1_VIGENCIA(fecha_siniestro: Date, vigencia: RangoFechas) → bool
  = vigencia.desde ≤ fecha_siniestro ≤ vigencia.hasta
```

**Contract Constraint:**
- `fecha_siniestro` must be a valid date (ExtraccionValidada.campos)
- `vigencia.desde` ≤ `vigencia.hasta` (RangoFechas validator)

**Dictamen Output (Fail):**
- `resultado = NO_CUBIERTO`
- `regla_aplicada = R1`
- `clausula = Poliza.clausulas.find(tipo=VIGENCIA)` ← Required, non-null
- Early exit: do NOT execute R2-R5

**Test Cases:**
- Happy: fecha siniestro dentro rango
- Fail: fecha anterior a vigencia.desde
- Fail: fecha posterior a vigencia.hasta
- Edge: fecha = vigencia.desde (inclusive)
- Edge: fecha = vigencia.hasta (inclusive)
- Missing: fecha_siniestro ausente → REQUIERE_REVISION

---

## R2: Cobertura Contratada (Contracted Coverage Type)

**Rule:** Claim type must be explicitly contracted in the policy.

**Formal Definition:**
```
R2_COBERTURA(tipo_siniestro: str, coberturas_contratadas: list[str]) → bool
  = tipo_siniestro ∈ coberturas_contratadas
```

**Contract Constraint:**
- `tipo_siniestro` ∈ {AUTO_COLISION, AUTO_HURTO, HOGAR_AGUA, ...} (enum TipoSiniestro, extensible)
- `coberturas_contratadas` contains strings matching enum values

**Dictamen Output (Fail):**
- `resultado = NO_CUBIERTO`
- `regla_aplicada = R2`
- `clausula = Poliza.clausulas.find(tipo=COBERTURA)` ← Required, non-null
- Early exit: do NOT execute R3-R5

**Test Cases:**
- Happy: tipo contratado en póliza
- Fail: tipo no contratado
- Fail: empty coberturas_contratadas
- Missing: tipo_siniestro ausente → REQUIERE_REVISION

---

## R3: Exclusiones (Exclusions)

**Rule:** Claim must not be explicitly excluded by policy terms.

**Formal Definition:**
```
R3_EXCLUSIONES(claim_context, exclusiones: list[Clausula]) → bool
  = ¬∃ exclusion ∈ exclusiones | exclusion.aplica_a(claim_context)
```

**Contract Constraint:**
- Each Clausula with `tipo=EXCLUSION` has criteria (domain-specific logic per tipo_siniestro)
- Examples:
  - "Conductores menores de 25 años" (edad_conductor field)
  - "Uso comercial" (uso_vehiculo field)
  - etc.

**Dictamen Output (Fail):**
- `resultado = NO_CUBIERTO`
- `regla_aplicada = R3`
- `clausula = applicable_exclusion` ← Required, non-null
- Early exit: do NOT execute R4-R5

**Test Cases:**
- Happy: sin exclusiones aplicables
- Fail: exclusión aplica
- Happy: exclusión existe pero no aplica (edad ≥ 25)
- Missing: campos contextuales para evaluar exclusión → REQUIERE_REVISION

---

## R4: Límite de Cobertura (Coverage Limit)

**Rule:** Payout is capped at the insured sum (suma_asegurada).

**Formal Definition:**
```
R4_LIMITE(monto_reclamado: Decimal, suma_asegurada: Decimal) → (resultado, cobertura_otorgada)
  if monto_reclamado ≤ suma_asegurada:
    resultado = CUBIERTO
    cobertura_otorgada = monto_reclamado
  else:
    resultado = CUBIERTO_PARCIAL
    cobertura_otorgada = suma_asegurada
```

**Contract Constraint:**
- `monto_reclamado > 0`
- `suma_asegurada > 0`
- `cobertura_otorgada ≤ suma_asegurada` (invariant)

**Dictamen Output:**
- `resultado` ∈ {CUBIERTO, CUBIERTO_PARCIAL}
- `regla_aplicada = R4`
- `clausula = Poliza.clausulas.find(tipo=LIMITE)` ← Required, non-null
- Continue to R5 (monto rule, not gating)

**Test Cases:**
- Happy: monto < suma_asegurada → CUBIERTO
- Partial: monto = suma_asegurada → CUBIERTO
- Partial: monto > suma_asegurada → CUBIERTO_PARCIAL
- Missing: monto_reclamado ausente → REQUIERE_REVISION

---

## R5: Deducible (Deductible / Self-Insured Portion)

**Rule:** Policyholder bears deductible; insurer pays (coverage - deductible).

**Formal Definition:**
```
R5_DEDUCIBLE(cobertura_otorgada: Decimal, deducible: Decimal) → (pago, deducible_calculado)
  pago = max(0, cobertura_otorgada - deducible)
  deducible_calculado = min(deducible, cobertura_otorgada)
```

**Contract Constraint:**
- `deducible ≥ 0`
- `cobertura_otorgada ≥ 0` (from R4)
- `pago ≥ 0` (invariant, max(0, ...))
- `deducible_calculado ≥ 0`
- `deducible_calculado ≤ cobertura_otorgada` (can't charge more deductible than coverage)
- Deducible is UNIQUE per policy (not per type, MVP scope)

**Dictamen Output (Final):**
- `resultado` ∈ {CUBIERTO, CUBIERTO_PARCIAL} (depends on R4, not R5)
- `regla_aplicada = R5`
- `clausula = Poliza.clausulas.find(tipo=DEDUCIBLE)` ← Required, non-null
- `deducible_calculado` recorded for transparency
- End of cascade

**Test Cases:**
- Happy: pago = cobertura - deducible (both > 0)
- Edge: deducible = 0 → pago = cobertura
- Edge: deducible ≥ cobertura → pago = 0 (cubierto pero bajo deducible)
- Edge: cobertura < deducible (from R4 partial) → pago = 0

---

## Fraude: Hard Inconsistencies (Deterministic)

**Definitions:**
```
INCONSISTENCIA_VIGENCIA_EXPIRADA
  = fecha_siniestro > vigencia_fin

INCONSISTENCIA_MONTO_EXCEDE_SUMA
  = monto_reclamado > suma_asegurada

INCONSISTENCIA_FECHA_FUTURA
  = fecha_siniestro > hoy

INCONSISTENCIA_INTRA_DOCUMENTO (UC4, PRD ⭐)
  = [metadata_fecha_emision > fecha_siniestro]
  = documento emitido DESPUÉS del claim → documento falso
```

**Severity Mapping (Deterministic):**
```
TIPO                            SEVERIDAD
VIGENCIA_EXPIRADA              ALTA
MONTO_EXCEDE_SUMA              MEDIA
FECHA_FUTURA                   ALTA
INTRA_DOCUMENTO_FALSO          ALTA
[conteo_inconsistencias >= 3]  ALTA (escalate)
```

---

## Validation Constraints (Cross-Rule)

| Invariant | Formula | Test |
|-----------|---------|------|
| **Resultado válido** | resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION} | enum strict |
| **Deducible no negativo** | deducible_calculado ≥ 0 | PBT property |
| **Deducible acotado** | deducible_calculado ≤ min(monto, suma_asegurada) | PBT property |
| **Cláusula obligatoria** | resultado ≠ REQUIERE_REVISION ⇒ clausula ≠ None | contract validator |
| **Determinismo** | f(x1) = f(x2) si x1 = x2 | idempotency test |
| **Orden insensible** | permutar R1-R5 no cambia resultado | permutation PBT |
| **Fallo temprano** | R1 falla ⇒ resultado = NO_CUBIERTO + R1 citada | integration test |
| **Campo ausente escala** | campo_obligatorio_ausente ⇒ resultado = REQUIERE_REVISION | gating test |

---

## Test Coverage by Estrato (rules/testing.md)

### ESTRATO: happy

- R1 pass, R2 pass, ..., R5 pass → CUBIERTO, pago > 0
- Diferentes tipos_siniestro (AUTO_COLISION, HOGAR_AGUA)
- Deducible (0, > 0)

### ESTRATO: cobertura-negativa

- R1 falla (vigencia expirada)
- R2 falla (cobertura no contratada)
- R3 falla (exclusión aplica)

### ESTRATO: campos-faltantes

- fecha_siniestro ausente → REQUIERE_REVISION
- tipo_siniestro ausente → REQUIERE_REVISION
- monto_reclamado ausente → REQUIERE_REVISION
- Clausula no encontrada → REQUIERE_REVISION

### ESTRATO: fraude

- fecha_siniestro > vigencia_fin → AlertaFraude(ALTA), Dictamen independiente
- monto > suma_asegurada → AlertaFraude(MEDIA), Dictamen = CUBIERTO_PARCIAL
- Intra-documento falso → AlertaFraude(ALTA)
- 3+ inconsistencias → AlertaFraude(ALTA)
- **CRITICAL:** AlertaFraude nunca cambia Caso.estado (P1)

