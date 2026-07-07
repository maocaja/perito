# U3 NFR Design — Edge Cases & Especificación de Escalamiento

**Invariant Lock:** Escalamiento a REQUIERE_REVISION (P4), no relleno de datos, cita de cláusula (P3)

---

## 1. Edge Case Q3.1: Deducible ≥ Monto (R5)

### Caso: Deducible Alto

```
Escenario:
  - monto_reclamado = $5,000
  - deducible_póliza = $10,000
  - suma_asegurada = $50,000 (pasa R4 sin cambios)

Flujo R4-R5:
  R4: monto_tras_limite = min(5000, 50000) = 5000
  R5: pago_final = max(0, 5000 - 10000) = 0
      deducible_aplicado = min(10000, 5000) = 5000

Resultado:
  resultado = CUBIERTO  (siniestro ESTÁ cubierto)
  monto_pagable = 0     (cliente no recibe pago por deducible alto)
  NO CUBIERTO_PARCIAL   (parcial es sobre límite/suma, no deducible)
```

### Pseudocódigo R5 (Decisión 🔒)

```python
def calcular_r5_deducible(
    monto_tras_limite: Decimal,
    deducible: Decimal,
    clausula_deducible: Clausula
) -> tuple[Decimal, Decimal, ResultadoCobertura]:
    
    # Aplicar deducible
    pago_final = max(Decimal(0), monto_tras_limite - deducible)
    deducible_aplicado = min(deducible, monto_tras_limite)
    
    # Redondear
    pago_final = redondear_monto(pago_final)
    deducible_aplicado = redondear_monto(deducible_aplicado)
    
    # Decisión: ¿CUBIERTO o CUBIERTO_PARCIAL?
    # 🔒 deducible >= monto → resultado = CUBIERTO (no es "parcial")
    # CUBIERTO_PARCIAL ocurre solo si hay límite que frena (R4)
    
    if pago_final == Decimal(0):
        # Deducible >= monto, o monto es 0
        resultado = ResultadoCobertura.CUBIERTO
    elif pago_final < monto_tras_limite:
        # Hay pago parcial (deducible bajó el monto)
        resultado = ResultadoCobertura.CUBIERTO_PARCIAL
    else:
        # pago_final == monto_tras_limite (deducible <= 0 o muy bajo)
        resultado = ResultadoCobertura.CUBIERTO
    
    return pago_final, deducible_aplicado, resultado
```

### Invariante: Diferencia Deducible vs. Límite

```
LÍMITE (R4):
  - Reduce monto disponible
  - Genera CUBIERTO_PARCIAL si monto_reclamado > suma_asegurada

DEDUCIBLE (R5):
  - Cliente paga primero, asegurador paga resto
  - Si deducible >= monto: cliente paga todo
  - Resultado sigue siendo CUBIERTO (no es negación, es copago)
  - Nunca genera CUBIERTO_PARCIAL

Ejemplo que ilustra diferencia:
  monto_reclamado = 10000
  suma_asegurada = 5000
  deducible = 1000

  R4: monto_tras_limite = min(10000, 5000) = 5000 → CUBIERTO_PARCIAL
  R5: pago = max(0, 5000 - 1000) = 4000 → sigue CUBIERTO_PARCIAL
      (el estado es el de R4, R5 solo reduce monto)
```

---

## 2. Edge Case Q3.2: Campo Ausente en R1-R5

### Precondición: Validación Pre-Motor

**INVARIANTE 🔒:** Campos obligatorios ANTES de invocar motor_cobertura.

```python
CAMPOS_OBLIGATORIOS_MOTOR = [
    "fecha_siniestro",
    "tipo_siniestro",
    "monto_reclamado"
]

def validar_precondicion_motor(
    extraccion: ExtraccionValidada
) -> Optional[Dictamen]:
    """
    Chequea campos obligatorios.
    Si alguno ausente → REQUIERE_REVISION (no continuar al motor).
    """
    
    for campo in CAMPOS_OBLIGATORIOS_MOTOR:
        campo_obj = extraccion.get_campo(campo)  # Busca en extraccion.campos
        
        if campo_obj is None or campo_obj.ausente:
            return Dictamen(
                resultado=ResultadoCobertura.REQUIERE_REVISION,
                motivo=f"Campo obligatorio ausente: {campo}",
                referencia_regla="PRE_MOTOR",
                timestamp=datetime.utcnow()
            )
    
    return None  # OK, puede continuar
```

### Semántica: No Pasar None a Rx

```
PROHIBIDO:
  R1: calcular_r1_vigencia(fecha=None, vigencia)  # Qué devuelve? 🚫

CORRECTO:
  if fecha_siniestro.ausente:
      return Dictamen(REQUIERE_REVISION, "fecha_siniestro ausente")
  
  R1: calcular_r1_vigencia(fecha=fecha_siniestro.valor, vigencia)  # valor ≠ None
```

### Flujo:

```
C5 (motor main) recibe (extraccion, poliza):

1. validar_precondicion_motor(extraccion)
   → Si REQUIERE_REVISION, retorna Dictamen + escalamiento (P4)
   → Si OK, continúa

2. motor_cobertura(extraccion, poliza)
   → Todos los campos son not None (ya validados)
   → R1-R5 usan .valor directamente
   → Ningún chequeo None internamente (imposible)
```

### Test Cobertura:

```python
def test_campo_ausente_fecha_siniestro_requiere_revision():
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(
                nombre="fecha_siniestro",
                valor=None,
                ausente=True  # ← Ausente
            ),
            # otros campos ...
        ]
    )
    poliza = poliza_builder().build()
    
    resultado = validar_precondicion_motor(extraccion)
    
    assert resultado is not None
    assert resultado.resultado == ResultadoCobertura.REQUIERE_REVISION
    assert "fecha_siniestro" in resultado.motivo

def test_todos_campos_presentes_pasa_precondicion():
    extraccion = ExtraccionValidada(
        campos=[
            CampoExtraido(nombre="fecha_siniestro", valor=date(2025, 1, 15), ausente=False),
            CampoExtraido(nombre="tipo_siniestro", valor="ROBO", ausente=False),
            CampoExtraido(nombre="monto_reclamado", valor=Decimal("5000"), ausente=False),
        ]
    )
    poliza = poliza_builder().build()
    
    resultado = validar_precondicion_motor(extraccion)
    
    assert resultado is None  # OK, motor puede ejecutar
```

---

## 3. Edge Case Q3.3: Cláusula No Encontrada (Póliza Incompleta)

### Precondición: Validación de Estructura Póliza

**INVARIANTE 🔒:** Si falta cláusula → REQUIERE_REVISION, no crash.

```python
def validar_poliza_completa(poliza: Poliza) -> Optional[Dictamen]:
    """
    Verifica que poliza tenga las cláusulas críticas para R1-R5.
    
    Si falta: escalar a REQUIERE_REVISION (no intentar dictaminar).
    """
    
    clausulas_requeridas = [
        TipoClausula.VIGENCIA,
        TipoClausula.COBERTURA,
        TipoClausula.DEDUCIBLE
    ]
    
    tipos_presentes = {c.tipo for c in poliza.clausulas}
    
    for tipo in clausulas_requeridas:
        if tipo not in tipos_presentes:
            return Dictamen(
                resultado=ResultadoCobertura.REQUIERE_REVISION,
                motivo=f"Póliza incompleta: falta cláusula {tipo.name}",
                referencia_regla="PRE_MOTOR_POLIZA",
                timestamp=datetime.utcnow()
            )
    
    return None  # OK
```

### En Motor: Cita Determinística

```python
def obtener_clausula(
    poliza: Poliza,
    tipo_clausula: TipoClausula
) -> Clausula:
    """
    Retorna cláusula del tipo solicitado.
    Si no existe: debe haber sido atrapada en validar_poliza_completa.
    Por defensa: lanzo excepción (fail-closed).
    """
    candidatas = [c for c in poliza.clausulas if c.tipo == tipo_clausula]
    
    if not candidatas:
        # Esto NO debería ocurrir si validar_poliza_completa() pasó
        raise ValueError(f"Cláusula {tipo_clausula.name} no encontrada — póliza incompleta")
    
    # Retornar la primera por ID (determinístico)
    return sorted(candidatas, key=lambda c: c.id)[0]
```

### Flujo:

```
C5 (motor main):

1. validar_poliza_completa(poliza)
   → Si falta cláusula, retorna Dictamen(REQUIERE_REVISION)
   → Si OK, continúa

2. motor_cobertura(extraccion, poliza)
   → obtener_clausula(poliza, TipoClausula.VIGENCIA)
   → Garantizado que existe (por (1))
   → Cita determinística (por ID)
```

### Test Cobertura:

```python
def test_clausula_vigencia_faltante_requiere_revision():
    poliza = poliza_builder()
        .con_clausula(TipoClausula.COBERTURA, ...)  # Solo cobertura
        .sin_clausula(TipoClausula.VIGENCIA)  # Falta vigencia
        .build()
    
    resultado = validar_poliza_completa(poliza)
    
    assert resultado is not None
    assert resultado.resultado == ResultadoCobertura.REQUIERE_REVISION
    assert "VIGENCIA" in resultado.motivo

def test_poliza_completa_pasa_validacion():
    poliza = poliza_builder()
        .con_clausula(TipoClausula.VIGENCIA, ...)
        .con_clausula(TipoClausula.COBERTURA, ...)
        .con_clausula(TipoClausula.DEDUCIBLE, ...)
        .build()
    
    resultado = validar_poliza_completa(poliza)
    
    assert resultado is None  # OK
```

---

## 4. Determinismo en Edge Cases

### Invariante: Determinismo Reproducible

```
Même entrada (extraccion, poliza) → Mismo Dictamen siempre.

Incluso en edge cases:
  - Deducible alto: 5000 - 10000 = 0 (siempre)
  - Campo ausente: Siempre REQUIERE_REVISION
  - Cláusula faltante: Siempre REQUIERE_REVISION
  - Cláusula múltiple: Siempre ordena por ID, toma primera
```

### Redondeo Edge Case

```
Decimal("10.5") + ROUND_HALF_UP → Decimal("11")  (siempre)
Decimal("10.4") + ROUND_HALF_UP → Decimal("10")  (siempre)
Decimal("10.500") + redondear_monto() → Decimal("11") (idempotente)

Nunca:
  - Banker's rounding (ROUND_HALF_EVEN) — NO es "mitad sube"
  - Redondeo variable
  - Cambios por tipo de entrada
```

---

## 5. Escalamiento (P4): Cuándo No Dictaminar

**REQUIERE_REVISION = Escalamiento a humano. Nunca forzar cierre.**

| Condición | Resultado | Motivo | Regla |
|-----------|-----------|--------|-------|
| Campo obligatorio ausente | REQUIERE_REVISION | No hay dato para R1-R5 | PRE_MOTOR |
| Póliza sin cláusula crítica | REQUIERE_REVISION | No hay base para dictaminar | PRE_MOTOR_POLIZA |
| Resultado póliza = candidatas_sólo | REQUIERE_REVISION | No hay póliza confirmada | RF-10/P4 |
| Cláusula no encontrada (edge) | REQUIERE_REVISION | No puede citar | P3 |
| LLM timeout en fraude | AlertaFraude con explicación genérica | Graceful fail | P4 |

---

## 6. Contrato de Precondiciones

```python
class PrevalidacionMotor(BaseModel):
    """Resultado de validaciones pre-motor."""
    valida: bool  # True → motor puede ejecutar; False → retorna Dictamen escalamiento
    motivo: Optional[str]  # Si no valida, por qué
    campo_faltante: Optional[str]  # Si es campo, cuál
    clausula_faltante: Optional[TipoClausula]  # Si es cláusula, cuál

def prevalidar(
    extraccion: ExtraccionValidada,
    poliza: Poliza
) -> PrevalidacionMotor:
    """
    Orquesta todas las validaciones pre-motor.
    Retorna diagnóstico.
    """
    
    # Chequeo 1: Campos obligatorios
    for campo in CAMPOS_OBLIGATORIOS_MOTOR:
        campo_obj = extraccion.get_campo(campo)
        if campo_obj is None or campo_obj.ausente:
            return PrevalidacionMotor(
                valida=False,
                motivo=f"Campo obligatorio ausente: {campo}",
                campo_faltante=campo
            )
    
    # Chequeo 2: Póliza completa
    clausulas_requeridas = [TipoClausula.VIGENCIA, TipoClausula.COBERTURA, TipoClausula.DEDUCIBLE]
    tipos_presentes = {c.tipo for c in poliza.clausulas}
    
    for tipo in clausulas_requeridas:
        if tipo not in tipos_presentes:
            return PrevalidacionMotor(
                valida=False,
                motivo=f"Póliza incompleta: falta {tipo.name}",
                clausula_faltante=tipo
            )
    
    return PrevalidacionMotor(valida=True)
```

---

## 7. Notas de Implementación

- **Ubicación:** `backend/app/rules/precondiciones.py`
- **Tests:** `backend/tests/test_u3_motor_edge_cases.py`
- **Patrón:** Validar primero, luego invocar motor (fail-closed)
- **P4 Terminación:** Escalamiento es acotado (cero loops, decisión inmediata)
- **P3 Trazabilidad:** Cada REQUIERE_REVISION cita la razón (campo/cláusula faltante)

