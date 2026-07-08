# U3 Business Logic Model — Motor R1-R5 & Fraude

**Unit:** U3 · Cobertura determinística · Fraude
**Components:** C5 (Motor), C6 (Fraude)
**Invariants:** P2 (motor determinístico, cero LLM), P6 (fraude explicable), P1 (fraude no decide)

---

## C5: Motor de Cobertura (P2 Core)

### Architecture: R1-R5 Cascade with Early Exit

```
Input: ExtraccionValidada.campos + ResultadoPoliza.poliza

R1 (Vigencia):           [GATING]
  ├─ fecha_siniestro ∈ [vigencia.desde, vigencia.hasta]?
  ├─ Falla → EARLY EXIT: Dictamen(resultado=NO_CUBIERTO, regla=R1, clausula=poliza.clausulas.find(tipo=vigencia))
  └─ Pasa → continúa

R2 (Cobertura Contratada): [GATING]
  ├─ tipo_siniestro ∈ poliza.coberturas_contratadas?
  ├─ Falla → EARLY EXIT: Dictamen(resultado=NO_CUBIERTO, regla=R2, clausula=poliza.clausulas.find(tipo=cobertura))
  └─ Pasa → continúa

R3 (Exclusiones):         [GATING]
  ├─ ¿Existe exclusión que aplique?
  ├─ Falla → EARLY EXIT: Dictamen(resultado=NO_CUBIERTO, regla=R3, clausula=poliza.clausulas.find(tipo=exclusion))
  └─ Pasa → continúa

R4 (Límite):             [MONTO]
  ├─ monto_reclamado ≤ suma_asegurada?
  ├─ Si monto_reclamado > suma_asegurada → CUBIERTO_PARCIAL, cobertura_otorgada = suma_asegurada
  └─ Si ≤ → cobertura_otorgada = monto_reclamado

R5 (Deducible):          [MONTO]
  └─ pago_final = max(0, cobertura_otorgada - poliza.deducible)
     deducible_calculado = min(poliza.deducible, cobertura_otorgada)

Output: Dictamen(resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION},
                 regla_aplicada ∈ {R1, R2, R3, R4, R5},
                 clausula (siempre ≠ None),
                 deducible_calculado ≥ 0)
```

### Key Decisions

1. **Early Exit (Gating):** R1/R2/R3 descalificadores → no ejecutar R2-R5 si R1 falla
2. **CUBIERTO_PARCIAL:** Solo si monto > suma_asegurada (R4-driven, no deducible)
3. **Cláusula Siempre Citada:** Motor busca Clausula por tipo (R1→vigencia, R2→cobertura, R3→exclusion, R4→limite, R5→deducible)
4. **Sin Cláusula → REQUIERE_REVISION:** Escalar, no fabricar cobertura
5. **Deducible Único:** Por póliza, no por tipo (U1 contrato, MVP)
6. **Pago Formula:** max(0, min(monto, suma_asegurada) - deducible); edge: deducible ≥ monto → pago 0

---

## C6: Fraude (P6 Explicabilidad, P1 No Decide)

### Architecture: Inconsistency Detection + LLM Reasoning

```
Input: ExtraccionValidada.campos, ResultadoPoliza.poliza, Dictamen (opcional contexto)

STEP 1: Deterministic Hard Inconsistencies
  ├─ fecha_siniestro > vigencia_fin? → INCONSISTENCIA_TIPO="VIGENCIA_EXPIRADA"
  ├─ monto_reclamado > suma_asegurada? → INCONSISTENCIA_TIPO="MONTO_EXCEDE_SUMA"
  ├─ [otros hard-rules por tipo siniestro]
  └─ Collect: inconsistencias_duras: list[str]

STEP 2: LLM Reasoning (Sonnet via LLMPayloadBuilder)
  ├─ Input redacted (P5): ExtraccionValidada, poliza basics, inconsistencias_duras
  ├─ LLM: "¿Hay otros patrones sospechosos? (sin datos PII)"
  ├─ Output: razonamientos sutiles, patrones históricos
  └─ Collect: inconsistencias_sutiles: list[str]

STEP 3: Severity Scoring (Deterministic)
  ├─ Mapeo duro: VIGENCIA_EXPIRADA = ALTA; MONTO_EXCEDE = MEDIA; pattern_count >= 3 = ALTA
  └─ severidad ∈ {BAJA, MEDIA, ALTA}

STEP 4: AlertaFraude Construction
  ├─ severidad, inconsistencias_duras + inconsistencias_sutiles, LLM_explicacion
  ├─ evidencia: list[EvidenciaOrigen] (punto a cada inconsistencia en campos)
  └─ AlertaFraude validado por contrato U1 (inconsistencias ≠ vacío)

Output: AlertaFraude({severidad, inconsistencias: list[EvidenciaOrigen], explicacion})
        ✅ Sugerencia únicamente — NO cambia Caso.estado (P1)
        ✅ No importa rules/ (frontera modular)
```

### Key Decisions

1. **Híbrido Determinístico + LLM:** Inconsistencias duras (código), explicación/patrones (LLM)
2. **LLM SÍ, Pero Solo Sugiere:** A diferencia de cobertura (P2), fraude puede razonar — pero no es decisor (P6)
3. **Redacción P5:** Usa LLMPayloadBuilder (como C2/C3) — no envía campos PII innecesarios
4. **Severidad Determinística:** Mapeo fijo para reproducibilidad (evals)
5. **Independiente de Dictamen:** AlertaFraude emitida siempre que hay inconsistencias; no modifica resultado_cobertura
6. **Estado Intacto:** AlertaFraude nunca cambia Caso.estado (eso solo hace U4 con humano)

---

## Module Boundaries (Verified)

### fraud/ ↔ rules/ (No Imports Between)
- fraud/ puede leer Dictamen (dato/contrato), no importa lógica de rules/
- rules/ no importa fraud/ (cobertura es independiente de fraude sugerido)
- Ambas procesadas en paralelo; resultado final es (Dictamen, AlertaFraude) independientes

### Data Flow Integration
```
U2-C2 ExtraccionValidada
    ↓
U2-C4 ResultadoPoliza
    ↓ (ambas entran a U3)
    ├→ C5 Motor (regla pura)
    │  └→ Dictamen (regla_aplicada, clausula, resultado)
    │
    └→ C6 Fraude (LLM razonamiento)
       └→ AlertaFraude (severidad, inconsistencias, solo sugiere)
```

---

## Error Handling Strategy (Fail-Closed, P4)

| Scenario | Decision | Rationale |
|----------|----------|-----------|
| Campo obligatorio ausente | REQUIERE_REVISION | No decidir sobre datos incompletos (P4) |
| Cláusula no encontrada | REQUIERE_REVISION | Sin evidencia no hay dictamen (P3) |
| Inconsistencia fraude | AlertaFraude ALTA severidad | Sugiere; U4+humano deciden |
| LLM falla | Fraude con inconsistencias_duras solo | Graceful fallback (P7) |
| Vigencia falla (R1) | NO_CUBIERTO temprano | No ejecutar R2-R5 |

---

## Testability Strategy (PBT-03)

### Unit-Testable Functions
- `calcular_r1_vigencia(fecha_siniestro, vigencia) → bool`
- `calcular_r2_cobertura(tipo_siniestro, coberturas) → bool`
- `calcular_r3_exclusiones(tipo_siniestro, exclusiones) → bool`
- `calcular_r4_limite(monto, suma_asegurada) → (resultado, cobertura_otorgada)`
- `calcular_r5_deducible(cobertura_otorgada, deducible) → (pago, deducible_calculado)`
- `motor_cobertura(extraccion, poliza) → Dictamen` [pure, deterministic]
- `detectar_inconsistencias(extraccion, poliza) → list[str]` [deterministic]
- `llamar_llm_fraude_reasoning(inconsistencias) → list[str]` [mocked in tests]
- `calcular_severidad_fraude(inconsistencias) → str` [deterministic]

### Property-Based Testing (Hypothesis)
1. Resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}
2. deducible_calculado ≥ 0
3. deducible_calculado ≤ min(monto, suma_asegurada)
4. Si CUBIERTO o CUBIERTO_PARCIAL → Dictamen.clausula ≠ None (SIEMPRE)
5. Mismo input → mismo output (determinístico)
6. Orden fijo — permutar R1-R5 no cambia resultado
7. R1 falla ⇒ NO_CUBIERTO citando R1
8. Campo ausente → REQUIERE_REVISION (no inventar)

