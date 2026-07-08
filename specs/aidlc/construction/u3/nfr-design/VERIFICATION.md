# U3 NFR Design — Verificación Contra Vigilancia del Usuario

**Timestamp:** 2026-07-07
**Status:** LOCKED 🔒 — Listo para Code Generation

---

## Checklist: 5 Vigilancia Puntos Usuario

### (1) Motor = Paso Único, Sin Loops

**Especificación:** `motor-algoritmo.md` § 2 (Flujo Cascada R1→R5)

✅ **Verificado:**
- Cada Rx es función pura independiente (`_r1_vigencia`, `_r2_cobertura`, etc.)
- Caller secuencial: R1 → if falla, retorna Dictamen(NO_CUBIERTO) + early-exit
- R2 → if falla, retorna Dictamen(NO_CUBIERTO) + early-exit
- R3 → if falla, retorna Dictamen(NO_CUBIERTO) + early-exit
- R4 siempre computa (cálculo de límite)
- R5 siempre computa (cálculo de deducible)
- **Cero loops:** O(1) rondas, O(n) solo en R3 exclusiones (n ≈ 3-5 típicamente)
- **Falla-es-falla:** No hay retry, no hay iteración; resultado es determinístico

**Evidencia:** 
- Pseudocódigo lines 17-57 en `motor-algoritmo.md`
- Función pura signature línea 11

### (2) Decimal + Redondeo Determinístico (COP Entero)

**Especificación:** `motor-algoritmo.md` § 4 (Función de Redondeo)

✅ **Verificado:**
- **COP no usa centavos:** Documentado línea 91
- **Precisión:** 0 decimales (enteros)
- **Método:** ROUND_HALF_UP
- **Función centralizada:** `redondear_monto(Decimal) -> Decimal`
- **Implementación:** `.quantize(Decimal("1"), rounding=ROUND_HALF_UP)` línea 104
- **Reutilización:** R4 y R5 usan `redondear_monto()` explícitamente
- **Test específico:** Redondeo 10.5 → 11 (ROUND_HALF_UP, entero) — corrección aplicada en plan Q4.2

**Evidencia:**
- Líneas 90-113 en `motor-algoritmo.md`
- Redondeo en R4 línea 153, R5 línea 191-192

### (3) Selección Cláusula Determinística (Orden Fijo, NO dict-hash)

**Especificación:** `motor-algoritmo.md` § 5 (Selección Determinística de Cláusula)

✅ **Verificado:**
- **Criterio:** Si varias Clausula del mismo tipo, ordena por `clausula.id`
- **Método:** `sorted(candidatas, key=lambda c: c.id)[0]`
- **Reproducible:** Mismo (poliza, tipo) → siempre misma cláusula
- **NO dict-hash-dependent:** Orden por entidad ID, no por dict insertion
- **Implementación:** Líneas 117-138 en `motor-algoritmo.md`

**Evidencia:**
- Función `obtener_clausula()` línea 117
- Sorting por ID línea 133

### (4) Función Pura: Motor SIN State Machine, Inputs → Dictamen

**Especificación:** `motor-algoritmo.md` § 1 (Firma Pura)

✅ **Verificado:**
- **Firma:** `motor_cobertura(extraccion: ExtraccionValidada, poliza: Poliza) -> Dictamen`
- **Sin state machine:** Cero mutación externa, todo temporal local
- **Precondición adicional:** Si `ResultadoPoliza.encontrada=False` → REQUIERE_REVISION antes de invocar motor
- **Docstring:** Invariantes documentadas (resultado∈enum, deducible≥0, cláusula≠None, determinismo)
- **Fail-closed:** Nunca retorna None o Exception; siempre retorna Dictamen válido

**Evidencia:**
- Líneas 9-25 en `motor-algoritmo.md`
- Precondición línea 255-261

### (5) Fraude: Determinístico + LLM Mockeable

**Especificación:** `fraude-determinismo.md` (Capas 1-3)

✅ **Verificado:**

#### Capa 1: Chequeos Duros Determinísticos
- Función pura: `detectar_inconsistencias_fraude(extraccion, poliza) -> list[EvidenciaOrigen]`
- Sin LLM
- Chequeos enumerados: fecha_anterior_vigencia, fecha_posterior_vigencia, fecha_futuro, monto_excede_suma, tipo_no_cubierto
- Retorna lista[EvidenciaOrigen], NO list[str]
- Orden determinístico: sorted por tipo.name

**Evidencia:** `fraude-determinismo.md` líneas 25-93

#### Capa 2: Mapa Severidad Determinístico
- Función pura: `calcular_severidad(inconsistencias) -> SeveridadFraude`
- Reglas fijas:
  - Tipos DUROS (FECHA_FUTURO, MONTO_EXCEDE_SUMA) → ALTA
  - Vigencia → MEDIA
  - 3+ inconsistencias → sube un nivel
- Mismo input → mismo output siempre
- Severidad como enum (BAJA | MEDIA | ALTA)

**Evidencia:** `fraude-determinismo.md` líneas 95-142

#### Capa 3: LLM Separado, Mockeable
- Función: `razonar_fraude(inconsistencias, poliza_redactada) -> str`
- **CRÍTICO:** LLM NO modifica `inconsistencias` ni `severidad`
- LLM es SOLO explicación (razonamiento secundario)
- En tests: completamente mockeado (determinístico)
- Output va a `AlertaFraude.explicacion`
- Graceful fail: si LLM timeout, retorna explicación default

**Evidencia:** `fraude-determinismo.md` líneas 144-192

#### AlertaFraude: Cero Inconsistencias → None (P6)
- Contrato: inconsistencias ≠ ∅ validado
- Si detectar_inconsistencias retorna [], NO se emite AlertaFraude
- `Caso.alerta_fraude = None` en ese caso
- No hay "alerta vacía"

**Evidencia:** `fraude-determinismo.md` líneas 194-240, especialmente línea 214

#### Redaction (P5)
- Redacta: nombres, cédulas, direcciones, teléfonos, emails
- Preserva: montos (operacionales)
- Via `LLMPayloadBuilder`

**Evidencia:** `fraude-determinismo.md` líneas 242-273

---

## Bonus: Edge Cases Determinísticos

### Q3.1: Deducible ≥ Monto

**Especificación:** `edge-cases-spec.md` § 1

✅ **Verificado:**
- Deducible ≥ monto → resultado = CUBIERTO (no CUBIERTO_PARCIAL)
- pago = 0, pero siniestro está cubierto
- **Diferencia clave:** Deducible es copago (cliente paga primero)
- **No confundir con:** Límite (reduce suma disponible) → CUBIERTO_PARCIAL

**Invariante:** `if pago_final == 0: resultado = CUBIERTO` (línea 37 en `edge-cases-spec.md`)

### Q3.2: Campo Ausente

**Especificación:** `edge-cases-spec.md` § 2

✅ **Verificado:**
- Validación pre-motor: `validar_precondicion_motor(extraccion)`
- Si campo obligatorio ausente → REQUIERE_REVISION (no pasar None a Rx)
- Motor pre-chequea presencia; nunca pasa None a `calcular_r1`
- Escalamiento, no decisión sobre datos incompletos (P4)

**Invariante:** CAMPOS_OBLIGATORIOS_MOTOR = ["fecha_siniestro", "tipo_siniestro", "monto_reclamado"] (línea 58)

### Q3.3: Cláusula Faltante

**Especificación:** `edge-cases-spec.md` § 3

✅ **Verificado:**
- Validación pre-motor: `validar_poliza_completa(poliza)`
- Si falta cláusula crítica → REQUIERE_REVISION (no crash)
- Motor escala; no puede citar cláusula inexistente (P3)
- Controlado con nota "cláusula X faltante" en Dictamen

**Invariante:** `clausulas_requeridas = [VIGENCIA, COBERTURA, DEDUCIBLE]` (línea 81)

---

## Invariantes PBT-03 Sostenibles

### Motor Invariantes (Testables)

1. **Idempotencia:** `motor(ex, pol) == motor(ex, pol)` ✅
2. **Resultado enum-válido:** resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION} ✅
3. **Monto no negativo:** monto_pagable >= 0 ✅
4. **Cláusula citada:** si resultado terminal, clausula ≠ None ✅
5. **Deducible congruente:** si resultado == CUBIERTO && deducible >= monto, pago == 0 ✅
6. **Redondeo fijo:** todas las cantidades tienen 0 decimales ✅
7. **Early-exit respetado:** si R1 falla, no se llama R2-R5 ✅
8. **Selección cláusula determinística:** múltiples clausulas → siempre la misma ✅

**Evidencia:** `motor-algoritmo.md` § 8 (líneas 265-276)

### Fraude Invariantes (Testables)

1. **Idempotencia:** `construir_alerta(ex, pol) == construir_alerta(ex, pol)` ✅
2. **Cero inconsistencias → None:** [] → alerta == None ✅
3. **Severidad determinística:** Mismo conjunto inconsistencias → misma severidad ✅
4. **Orden inconsistencias fijo:** Sorted por TipoInconsistencia.name ✅
5. **No inconsistencias ficticias:** Solo tipos conocidos (enum) ✅
6. **LLM no modifica severidad:** Output LLM no cambia inconsistencias ni severidad ✅
7. **Redaction simétrica:** PII redactada reproduciblemente (P5) ✅

**Evidencia:** `fraude-determinismo.md` § 8 (líneas 305-322)

---

## Correciones Aplicadas

### Ejemplo Redondeo (Q4.2)

❌ **Antes:** `redondear(Decimal("10.125")) == Decimal("10.13")` (2 decimales — INCORRECTO)

✅ **Después:** `redondear(Decimal("10.5")) == Decimal("11")` (ROUND_HALF_UP, entero — CORRECTO)

**Cambio:** Plan Q4.2 actualizado; ejemplos en tests ahora refleja 10.5 → 11 (COP entero, ROUND_HALF_UP)

---

## Artefactos Generados

```
/Users/mauricio/dev/perito/aidlc-docs/construction/u3/nfr-design/
├── motor-algoritmo.md               [11.5 KB] ✅ Paso único, función pura, redondeo fijo
├── fraude-determinismo.md           [15.4 KB] ✅ Capas 1-3, severidad determinística, LLM mockeable
├── edge-cases-spec.md               [11.5 KB] ✅ Deducible, campo ausente, cláusula faltante
└── VERIFICATION.md                  [This file] ✅ Checklist vs. vigilancia
```

---

## Status: READY FOR CODE GENERATION (C5)

**Gate:** ✅ PASSED

**Invariantes Locked 🔒:**
- P1 (HITL): Motor no decide siniestro solo (escalamiento a REQUIERE_REVISION cuando falta dato)
- P2 (Cobertura determinística): Motor R1-R5 es 100% determinístico, función pura
- P3 (Trazabilidad): Cada Dictamen cita la regla y cláusula aplicada
- P4 (Terminación): Paso único (O(1) rondas), campos ausentes escalados no loopean
- P5 (PII): LLMPayloadBuilder redacta nombres/cedulas/direcciones, preserva montos
- P6 (Explicabilidad): AlertaFraude contiene lista[EvidenciaOrigen] (no ficticias), severidad determinística

**Next:** Code Generation (U3-C5)
- Implementar `backend/app/rules/motor_r1_r5.py` (Motor R1-R5)
- Implementar `backend/app/fraud/fraude.py` (Fraude Capas 1-3)
- Implementar precondiciones en orquestador C5
- PBT-03 tests en `backend/tests/` (invariantes por propiedad)

