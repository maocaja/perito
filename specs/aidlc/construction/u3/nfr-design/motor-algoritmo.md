# U3 NFR Design — Motor R1-R5 Algoritmo Determinístico

**Invariant Lock:** Paso único, función pura, cero state machine, determinismo garantizado (P2, P4)

---

## 1. Motor Cobertura — Firma Pura

```python
def motor_cobertura(
    extraccion: ExtraccionValidada,
    poliza: Poliza
) -> Dictamen:
    """
    R1-R5 secuencial, paso único, sin loops; early-exit en R1/R2/R3.
    
    Invariantes:
    - resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}
    - deducible >= 0
    - clausula es Always not None (en CUBIERTO/CUBIERTO_PARCIAL/NO_CUBIERTO)
    - determinismo: mismo (extraccion, poliza) → mismo Dictamen siempre
    
    Args:
        extraccion: ExtraccionValidada (campos validados, pueden tener ausente=True)
        poliza: Poliza (resultado de C4 PolicyLookup, confirmada encontrada=True)
    
    Returns:
        Dictamen(resultado, monto_pagable, clausula, fraude)
    
    Raises:
        ValidationError: Never (fail-closed: siempre retorna Dictamen válido)
    """
```

---

## 2. Flujo Cascada R1 → R5

### Pseudocódigo Determinístico

```
Precondición:
  if not extraccion.validada: raise ValidationError
  if not poliza.encontrada: return Dictamen(REQUIERE_REVISION, ...)

Ejecución Secuencial:

  (1) R1 Vigencia: calcular_r1_vigencia(extraccion.fecha_siniestro, poliza.clausula_vigencia)
      → if FALLA: return Dictamen(NO_CUBIERTO, clausula=clausula_vigencia, ...)
      → else: continúa

  (2) R2 Cobertura Contratada: calcular_r2_cobertura(extraccion.tipo_siniestro, poliza.coberturas_contratadas)
      → if FALLA: return Dictamen(NO_CUBIERTO, clausula=clausula_cobertura, ...)
      → else: continúa

  (3) R3 Exclusiones: calcular_r3_exclusiones(extraccion, poliza.exclusiones)
      → if MATCH: return Dictamen(NO_CUBIERTO, clausula=clausula_exclusion, ...)
      → else: continúa

  (4) R4 Límite Póliza: monto_tras_limite = calcular_r4_limite(
        extraccion.monto_reclamado,
        poliza.suma_asegurada,
        poliza.clausula_limite
      )
      → monto_tras_limite puede ser < monto_reclamado (limitado)

  (5) R5 Deducible: 
      pago_final = max(0, monto_tras_limite - poliza.deducible)
      deducible_aplicado = min(poliza.deducible, monto_tras_limite)
      
      → if pago_final == 0:
          resultado = CUBIERTO (cubierto, pero cliente no paga nada)
      → elif pago_final < monto_tras_limite:
          resultado = CUBIERTO_PARCIAL (pago > 0 pero < monto solicitado)
      → else:
          resultado = CUBIERTO (pago == monto íntegro)

  Return Dictamen(
    resultado = resultado,
    monto_pagable = pago_final,
    clausula = clausula_r5_deducible,
    deducible_aplicado = deducible_aplicado,
    redactado_por = "motor_r1_r5"
  )
```

---

## 3. Cada Regla Rx — Función Pura

### R1: Vigencia

```python
def calcular_r1_vigencia(
    fecha_siniestro: date,
    clausula_vigencia: Clausula
) -> bool:
    """
    Retorna True si fecha_siniestro está dentro [vigencia_desde, vigencia_hasta].
    False en cualquier otro caso (fuera de rango, dato ausente).
    
    Invariante: determinístico, cero side-effects.
    """
    if not fecha_siniestro or not clausula_vigencia:
        return False
    
    inicio = clausula_vigencia.vigencia_desde
    fin = clausula_vigencia.vigencia_hasta
    
    return inicio <= fecha_siniestro <= fin
```

### R2: Cobertura Contratada

```python
def calcular_r2_cobertura(
    tipo_siniestro: TipoSiniestro,
    coberturas_contratadas: list[Cobertura]
) -> bool:
    """
    Retorna True si tipo_siniestro ∈ coberturas_contratadas.
    """
    return any(
        c.tipo_cobertura == tipo_siniestro.tipo_cobertura
        for c in coberturas_contratadas
    )
```

### R3: Exclusiones

```python
def calcular_r3_exclusiones(
    extraccion: ExtraccionValidada,
    exclusiones: list[Exclusion]
) -> tuple[bool, Optional[Exclusion]]:
    """
    Itera exclusiones en orden determinístico (sorted por exclusion.id).
    Retorna (aplicada: bool, exclusion_match: Exclusion).
    
    Semántica: primer match gana (OR lógica).
    Invariante: orden fijo (determinístico).
    """
    for exclusion in sorted(exclusiones, key=lambda e: e.id):
        if aplica_exclusion(extraccion, exclusion):
            return True, exclusion
    return False, None

def aplica_exclusion(
    extraccion: ExtraccionValidada,
    exclusion: Exclusion
) -> bool:
    """Chequeo puro: ¿aplica esta exclusión?"""
    # Ej: actividad_profesional == "piloto civil" → excluida si exclusion.actividades_excluidas
    # Implementación específica por tipo de póliza
    pass
```

### R4: Límite de Póliza

```python
def calcular_r4_limite(
    monto_reclamado: Decimal,
    suma_asegurada: Decimal,
    clausula_limite: Clausula
) -> Decimal:
    """
    monto_pagable = min(monto_reclamado, suma_asegurada).
    Retorna Decimal redondeado.
    Invariante: determinístico, resultado >= 0.
    """
    resultado = min(monto_reclamado, suma_asegurada)
    return redondear_monto(resultado)
```

### R5: Deducible

```python
def calcular_r5_deducible(
    monto_tras_limite: Decimal,
    deducible: Decimal,
    clausula_deducible: Clausula
) -> tuple[Decimal, Decimal, ResultadoCobertura]:
    """
    pago_final = max(0, monto_tras_limite - deducible)
    
    Si deducible >= monto_tras_limite:
      pago = 0, resultado = CUBIERTO (cubierto, pero cliente paga todo)
    Si 0 < pago < monto_tras_limite:
      resultado = CUBIERTO_PARCIAL
    Si pago == monto_tras_limite (deducible <= 0 o muy bajo):
      resultado = CUBIERTO (pago íntegro)
    
    Retorna (pago_final, deducible_aplicado, resultado).
    Invariante: determinístico, montos redondeados.
    """
    pago_final = max(Decimal(0), monto_tras_limite - deducible)
    deducible_aplicado = min(deducible, monto_tras_limite)
    
    pago_final = redondear_monto(pago_final)
    deducible_aplicado = redondear_monto(deducible_aplicado)
    
    # Resultado: siempre CUBIERTO o CUBIERTO_PARCIAL en R5
    # (si hubiera exclusión/vigencia, ya habría salido en R1-R3)
    if pago_final == Decimal(0):
        resultado = ResultadoCobertura.CUBIERTO
    elif pago_final < monto_tras_limite:
        resultado = ResultadoCobertura.CUBIERTO_PARCIAL
    else:
        resultado = ResultadoCobertura.CUBIERTO
    
    return pago_final, deducible_aplicado, resultado
```

---

## 4. Función de Redondeo — Determinístico

```python
from decimal import Decimal, ROUND_HALF_UP

def redondear_monto(monto: Decimal) -> Decimal:
    """
    Redondeo determinístico para pesos colombianos (COP).
    COP no usa centavos → enteros (0 decimales).
    
    ROUND_HALF_UP: 10.5 → 11, 10.4 → 10.
    
    Invariante: 
    - redondear(x) == redondear(x) siempre (idempotente)
    - redondear(x) tiene 0 decimales
    - determinístico: reproducible
    
    Args:
        monto: Decimal a redondear
    
    Returns:
        Decimal redondeado a entero
    """
    if monto is None:
        return Decimal(0)
    
    return monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
```

---

## 5. Selección Determinística de Cláusula

Cuando Poliza.clausulas contiene múltiples Clausula del mismo `tipo`:

```python
def obtener_clausula(
    poliza: Poliza,
    tipo_clausula: TipoClausula
) -> Optional[Clausula]:
    """
    Selección determinística: orden por ID.
    
    Invariante: 
    - Mismo (poliza, tipo) → siempre retorna la misma Clausula
    - NO depende de dict.hash, no depende de orden de creación
    - Si hay 2 clausulas vigencia, retorna la con id más bajo
    
    Args:
        poliza: Poliza con clausulas
        tipo_clausula: TipoClausula (VIGENCIA, COBERTURA, etc.)
    
    Returns:
        Clausula primera por id, o None si no hay
    """
    candidatas = [
        c for c in poliza.clausulas
        if c.tipo == tipo_clausula
    ]
    
    if not candidatas:
        return None
    
    # Ordenar por ID determinístico, tomar primera
    return sorted(candidatas, key=lambda c: c.id)[0]
```

---

## 6. Validación Pre-Motor

**Precondición crítica:**

```python
def validar_precondicion_motor(
    extraccion: ExtraccionValidada,
    resultado_poliza: ResultadoPoliza
) -> Optional[Dictamen]:
    """
    Si falla precondición, retorna Dictamen de escalamiento.
    Si OK, retorna None (continúa a motor_cobertura).
    
    P4/P1: No invocar motor sin póliza confirmada.
    """
    
    # Campo obligatorio ausente
    if extraccion.fecha_siniestro.ausente:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            motivo="Campo obligatorio ausente: fecha_siniestro",
            ...
        )
    
    if extraccion.monto_reclamado.ausente:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            motivo="Campo obligatorio ausente: monto_reclamado",
            ...
        )
    
    # Solo candidatas (póliza no confirmada)
    if not resultado_poliza.encontrada:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            motivo="Póliza no encontrada, solo candidatas — requiere revisión humana",
            ...
        )
    
    # Poliza sin cláusulas críticas
    for tipo_requerido in [TipoClausula.VIGENCIA, TipoClausula.COBERTURA]:
        if not any(c.tipo == tipo_requerido for c in resultado_poliza.poliza.clausulas):
            return Dictamen(
                resultado=ResultadoCobertura.REQUIERE_REVISION,
                motivo=f"Póliza incompleta: falta cláusula {tipo_requerido.name}",
                ...
            )
    
    return None  # OK, continúa
```

---

## 7. Contrato Dictamen (No Negociable)

```python
class Dictamen(BaseModel):
    """
    INVARIANTE P3/P6: cláusula NUNCA es None (si retorna un dictamen terminal).
    """
    resultado: ResultadoCobertura  # CUBIERTO | CUBIERTO_PARCIAL | NO_CUBIERTO | REQUIERE_REVISION
    monto_pagable: Decimal = Decimal(0)
    clausula: Optional[Clausula] = None  # NO_CUBIERTO/CUBIERTO/CUBIERTO_PARCIAL: not None
    deducible_aplicado: Decimal = Decimal(0)
    referencia_regla: str  # "R1_VIGENCIA", "R4_LIMITE", etc.
    redactado_por: str = "motor_r1_r5"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('resultado', 'clausula')
    def validar_clausula_en_dictamen(cls, valores):
        """Si resultado terminal, clausula not None."""
        resultado = valores.get('resultado')
        clausula = valores.get('clausula')
        
        if resultado in [
            ResultadoCobertura.CUBIERTO,
            ResultadoCobertura.CUBIERTO_PARCIAL,
            ResultadoCobertura.NO_CUBIERTO
        ]:
            if clausula is None:
                raise ValueError("clausula no puede ser None en resultado terminal")
        
        return valores
```

---

## 8. Garantías de Determinismo (PBT-03)

**Invariantes Testables:**

1. **Idempotencia:** `motor_cobertura(ex, pol) == motor_cobertura(ex, pol)` siempre
2. **Resultado enum-válido:** resultado ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}
3. **Monto no negativo:** monto_pagable >= 0
4. **Cláusula citada:** si resultado terminal, clausula ≠ None
5. **Deducible congruente:** si resultado == CUBIERTO && deducible >= monto, pago == 0
6. **Redondeo fijo:** todas las cantidades tienen 0 decimales (enteros)
7. **Early-exit respetado:** si R1 falla, no se llama R2-R5
8. **Selección cláusula determinística:** múltiples clausulas del mismo tipo → siempre la misma (menor ID)

---

## 9. Notas de Implementación

- **Motor = 1 archivo:** `backend/app/rules/motor_r1_r5.py`
- **Tests PBT:** `backend/tests/test_u3_motor_r1_r5_pbt.py` (Hypothesis properties)
- **Tests unitarios:** `backend/tests/test_u3_motor_r1_r5_units.py` (casos específicos edge)
- **Sin BD:** motor lee solo inputs en memoria (poliza.clausulas, extraccion.campos)
- **Sin LLM:** motor es puro (LLM solo en Fraude, separado)
- **Sin loops:** cascada R1-R5 es O(1) en rondas, O(n) en exclusiones (n=típicamente 3-5)

