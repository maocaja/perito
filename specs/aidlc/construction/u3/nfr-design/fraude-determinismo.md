# U3 NFR Design — Fraude: Determinístico + LLM Mockeable

**Invariant Lock:** Severidad determinística (función pura), LLM solo explicación (P6), P5 redaction

---

## 1. Arquitectura Fraude — Capas Separadas

```
Capa 1: Chequeos Duros Determinísticos (función pura)
  ↓
Capa 2: Mapa Severidad Determinístico (función pura)
  ↓
Capa 3: Razonamiento LLM (mockeable, explicación)
  ↓
AlertaFraude (severidad + inconsistencias + explicacion)
```

**Invariante crítica (P6):** inconsistencias ≠ vacío. Si Capa 1 retorna [], NO se emite AlertaFraude (Caso.alerta_fraude = None).

---

## 2. Capa 1: Chequeos Duros Determinísticos

### Función Pura: Detectar Inconsistencias

```python
def detectar_inconsistencias_fraude(
    extraccion: ExtraccionValidada,
    poliza: Poliza
) -> list[EvidenciaOrigen]:
    """
    Chequeos duros, SIN LLM.
    Retorna lista[EvidenciaOrigen] de inconsistencias encontradas.
    
    Invariante:
    - Función pura: mismo (extraccion, poliza) → misma lista siempre
    - Orden determinístico: inconsistencias en orden creciente de tipo
    - No modifica inputs
    
    Args:
        extraccion: ExtraccionValidada (campos con valores o ausente=True)
        poliza: Poliza (clausulas, exclusiones, vigencia)
    
    Returns:
        list[EvidenciaOrigen]: lista de inconsistencias
        (vacía si cero inconsistencias detectadas)
    
    Raises:
        Never (fail-closed: retorna lista, posiblemente vacía)
    """
    inconsistencias = []
    
    # Chequeo 1: Fecha siniestro fuera vigencia
    if extraccion.fecha_siniestro and not extraccion.fecha_siniestro.ausente:
        fecha = extraccion.fecha_siniestro.valor
        clausula_vigencia = obtener_clausula(poliza, TipoClausula.VIGENCIA)
        
        if clausula_vigencia:
            if fecha < clausula_vigencia.vigencia_desde:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoInconsistencia.FECHA_ANTERIOR_VIGENCIA,
                        referencia=f"Siniestro {fecha}, vigencia desde {clausula_vigencia.vigencia_desde}"
                    )
                )
            elif fecha > clausula_vigencia.vigencia_hasta:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoInconsistencia.FECHA_POSTERIOR_VIGENCIA,
                        referencia=f"Siniestro {fecha}, vigencia hasta {clausula_vigencia.vigencia_hasta}"
                    )
                )
    
    # Chequeo 2: Fecha siniestro en el futuro
    if extraccion.fecha_siniestro and not extraccion.fecha_siniestro.ausente:
        fecha = extraccion.fecha_siniestro.valor
        hoy = date.today()
        if fecha > hoy:
            inconsistencias.append(
                EvidenciaOrigen(
                    tipo=TipoInconsistencia.FECHA_FUTURO,
                    referencia=f"Siniestro en futuro: {fecha} > {hoy}"
                )
            )
    
    # Chequeo 3: Monto reclamado > suma asegurada
    if extraccion.monto_reclamado and not extraccion.monto_reclamado.ausente:
        monto = extraccion.monto_reclamado.valor
        suma = poliza.suma_asegurada
        
        if monto > suma:
            inconsistencias.append(
                EvidenciaOrigen(
                    tipo=TipoInconsistencia.MONTO_EXCEDE_SUMA,
                    referencia=f"Reclamado {monto} > suma asegurada {suma}"
                )
            )
    
    # Chequeo 4: Tipo siniestro no en coberturas contratadas
    if extraccion.tipo_siniestro and not extraccion.tipo_siniestro.ausente:
        tipo = extraccion.tipo_siniestro.valor
        coberturas = [c.tipo_cobertura for c in poliza.coberturas_contratadas]
        
        if tipo.tipo_cobertura not in coberturas:
            inconsistencias.append(
                EvidenciaOrigen(
                    tipo=TipoInconsistencia.TIPO_NO_CUBIERTO,
                    referencia=f"Tipo {tipo.name} no en coberturas {coberturas}"
                )
            )
    
    # Chequeo 5: Otros indicadores (ej: monto muy redondo, documento sospechoso)
    # Se agregan según dominio (por ahora: empty)
    
    # Retornar en orden determinístico (por tipo enum)
    return sorted(inconsistencias, key=lambda e: e.tipo.name)
```

### Contrato EvidenciaOrigen

```python
class TipoInconsistencia(str, Enum):
    """Tipos de inconsistencias determinísticas."""
    FECHA_ANTERIOR_VIGENCIA = "FECHA_ANTERIOR_VIGENCIA"
    FECHA_POSTERIOR_VIGENCIA = "FECHA_POSTERIOR_VIGENCIA"
    FECHA_FUTURO = "FECHA_FUTURO"
    MONTO_EXCEDE_SUMA = "MONTO_EXCEDE_SUMA"
    TIPO_NO_CUBIERTO = "TIPO_NO_CUBIERTO"

class EvidenciaOrigen(BaseModel):
    """
    NO list[str] — cada inconsistencia es un objeto con tipo + referencia.
    Permite PBT, razonamiento LLM sobre inconsistencias, auditoría.
    """
    tipo: TipoInconsistencia
    referencia: str  # Detalles específicos del hallazgo (ej: "Siniestro 2025-01-01, vigencia hasta 2024-12-31")
    
    class Config:
        frozen = True  # Inmutable
```

---

## 3. Capa 2: Mapa Severidad Determinístico

### Función Pura: Calcular Severidad

```python
def calcular_severidad(
    inconsistencias: list[EvidenciaOrigen]
) -> SeveridadFraude:
    """
    Mapeo determinístico: inconsistencias → Severidad.
    
    Reglas:
    1. Si algún tipo DURO (FECHA_FUTURO, MONTO_EXCEDE_SUMA) → ALTA
    2. Si algún tipo VIGENCIA (FECHA_ANTERIOR, FECHA_POSTERIOR) → MEDIA (a menos que esté con otro)
    3. Si 3+ inconsistencias → sube un nivel (BAJA→MEDIA, MEDIA→ALTA)
    4. Si cero inconsistencias → N/A (no se emite AlertaFraude)
    
    Invariante:
    - Función pura: mismo input → mismo output siempre
    - Determinístico: severidd es reproducible en todos los evals/tests
    - No depende de orden de inconsistencias (ya están sorted)
    
    Args:
        inconsistencias: list[EvidenciaOrigen] (ya sorted por tipo)
    
    Returns:
        SeveridadFraude enum: BAJA | MEDIA | ALTA
    """
    if not inconsistencias:
        # No se llama a calcular_severidad si cero inconsistencias
        # Pero por defensa, retornar algo
        return SeveridadFraude.BAJA
    
    tipos = {e.tipo for e in inconsistencias}
    
    # Regla 1: Tipos duros → ALTA
    duros = {TipoInconsistencia.FECHA_FUTURO, TipoInconsistencia.MONTO_EXCEDE_SUMA}
    if tipos & duros:
        return SeveridadFraude.ALTA
    
    # Regla 2: Base por tipo predominante
    severidad_base = SeveridadFraude.BAJA
    
    if TipoInconsistencia.FECHA_ANTERIOR_VIGENCIA in tipos or TipoInconsistencia.FECHA_POSTERIOR_VIGENCIA in tipos:
        severidad_base = SeveridadFraude.MEDIA
    
    # Regla 3: Contar inconsistencias, subir nivel
    if len(inconsistencias) >= 3:
        if severidad_base == SeveridadFraude.BAJA:
            severidad_base = SeveridadFraude.MEDIA
        elif severidad_base == SeveridadFraude.MEDIA:
            severidad_base = SeveridadFraude.ALTA
    
    return severidad_base


class SeveridadFraude(str, Enum):
    """Severidad determinística."""
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
```

---

## 4. Capa 3: Razonamiento LLM (Mockeable)

### Función: Explicación via LLM

```python
def razonar_fraude(
    inconsistencias: list[EvidenciaOrigen],
    poliza_redactada: dict  # Poliza con PII redactada
) -> str:
    """
    LLM-call: genera explicación legible sobre inconsistencias.
    
    INVARIANTE CRÍTICA 🔒:
    - LLM NO modifica inconsistencias ni severidad
    - LLM es SOLO explicación (razonamiento secundario)
    - En tests: mockeado completamente (determinístico)
    - Output va a AlertaFraude.explicacion
    
    Args:
        inconsistencias: list[EvidenciaOrigen] (determinísticas ya calculadas)
        poliza_redactada: dict (PII redactada, montos preservados)
    
    Returns:
        str: explicación legible
    
    Notas:
    - NO retorna nuevas inconsistencias
    - NO retorna severidad
    - Anotaciones: "Consideraciones adicionales", "Contexto", etc.
    """
    
    # Armar payload con PII redactada (via LLMPayloadBuilder)
    payload = {
        "inconsistencias": [
            {"tipo": e.tipo.name, "referencia": e.referencia}
            for e in inconsistencias
        ],
        "poliza_resumen": {
            "suma_asegurada": poliza_redactada.get("suma_asegurada"),
            "vigencia_desde": poliza_redactada.get("vigencia_desde"),
            "vigencia_hasta": poliza_redactada.get("vigencia_hasta"),
            # Asegurado: REDACTADO (nombres, cedulas, direcciones)
        }
    }
    
    prompt = f"""
Dado el siguiente siniestro con inconsistencias, proporciona una explicación breve:

{json.dumps(payload, indent=2, default=str)}

Explicación (máx 200 palabras, sin cambiar la severidad ni agregar nuevas inconsistencias):
"""
    
    # LLM call (mockeado en tests)
    try:
        response = llm_call(
            model="claude-3-5-sonnet-20241022",  # Mockeado: mock_llm()
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256
        )
        return response.content[0].text.strip()
    except Exception as e:
        # Graceful fail (P4): si LLM falla, retornar explicación default
        return f"Fraude detectado por {len(inconsistencias)} inconsistencias. Revisar manualmente."
```

### Capa LLM Mockeada en Tests

```python
# backend/tests/fixtures_u3_fraude.py

@pytest.fixture
def mock_llm_fraude(monkeypatch):
    """Mock determinístico para razonar_fraude."""
    def mock_call(*args, **kwargs):
        inconsistencias = kwargs.get("inconsistencias", [])
        tipos = [e.tipo for e in inconsistencias]
        
        # Respuesta determinística según tipos
        if TipoInconsistencia.FECHA_FUTURO in tipos:
            return "Siniestro reportado en futuro — posible documento falsificado."
        elif TipoInconsistencia.MONTO_EXCEDE_SUMA in tipos:
            return "Monto reclamado supera suma asegurada contratada."
        else:
            return f"Detectadas {len(inconsistencias)} inconsistencias en la solicitud."
    
    monkeypatch.setattr("backend.app.fraud.fraude.razonar_fraude", mock_call)
    return mock_call
```

---

## 5. AlertaFraude — Construcción & Contrato

### Construcción Determinística

```python
def construir_alerta_fraude(
    extraccion: ExtraccionValidada,
    poliza: Poliza,
    poliza_redactada: dict  # Para razonamiento LLM (P5)
) -> Optional[AlertaFraude]:
    """
    Orquesta Capa 1-3 para emitir AlertaFraude.
    
    INVARIANTE 🔒:
    - Cero inconsistencias → retorna None (NO se emite alerta vacía)
    - severidad es determinística (Capa 2)
    - explicacion es LLM (Capa 3, mockeable)
    - inconsistencias = list[EvidenciaOrigen]
    
    Args:
        extraccion: ExtraccionValidada
        poliza: Poliza (clausulas, coberturas)
        poliza_redactada: dict (PII redactada, for LLM)
    
    Returns:
        AlertaFraude si hay inconsistencias, None si cero inconsistencias
    """
    
    # Capa 1: Chequeos duros
    inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)
    
    # INVARIANTE P6: Si cero inconsistencias, NO emitir alerta
    if not inconsistencias:
        return None
    
    # Capa 2: Severidad determinística
    severidad = calcular_severidad(inconsistencias)
    
    # Capa 3: Explicación LLM (mockeable)
    explicacion = razonar_fraude(inconsistencias, poliza_redactada)
    
    # Construir alerta
    alerta = AlertaFraude(
        severidad=severidad,
        inconsistencias=inconsistencias,
        explicacion=explicacion,
        timestamp=datetime.utcnow(),
        redactado_por="motor_fraude_u3"
    )
    
    return alerta
```

### Contrato AlertaFraude

```python
class AlertaFraude(BaseModel):
    """
    INVARIANTES:
    - inconsistencias ≠ ∅ (validado en __init__)
    - severidad ∈ {BAJA, MEDIA, ALTA}
    - explicacion es str (puede venir de LLM)
    """
    severidad: SeveridadFraude
    inconsistencias: list[EvidenciaOrigen]  # NO list[str]
    explicacion: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    redactado_por: str = "motor_fraude_u3"
    
    @field_validator('inconsistencias')
    def inconsistencias_no_vacia(cls, v):
        """P6: Contrato garantiza lista no vacía."""
        if not v or len(v) == 0:
            raise ValueError("AlertaFraude: inconsistencias no puede estar vacía")
        return v
    
    class Config:
        frozen = True  # Inmutable
```

---

## 6. Integración: Caso con AlertaFraude

```python
class Caso(BaseModel):
    # ... otros campos ...
    dictamen: Dictamen  # Motor R1-R5
    alerta_fraude: Optional[AlertaFraude] = None  # Fraude (None si cero inconsistencias)
    
    # Invariante: si alerta_fraude not None, entonces severidad ∈ enum
```

---

## 7. LLMPayloadBuilder — Redaction (P5)

```python
class LLMPayloadBuilder:
    """
    Construye payload para LLM con PII redactada (P5).
    
    Redacta: nombres, cédulas, direcciones, teléfonos, emails
    Preserva: montos (operacionales), fechas, tipos de cobertura
    """
    
    @staticmethod
    def build_for_fraude(
        extraccion: ExtraccionValidada,
        poliza: Poliza
    ) -> dict:
        """
        Retorna dict con PII redactada para razonar_fraude.
        """
        redactado = {
            "suma_asegurada": poliza.suma_asegurada,  # Preserva monto
            "vigencia_desde": poliza.clausula_vigencia.vigencia_desde,
            "vigencia_hasta": poliza.clausula_vigencia.vigencia_hasta,
            "fecha_siniestro": extraccion.fecha_siniestro.valor if extraccion.fecha_siniestro else None,
            "monto_reclamado": extraccion.monto_reclamado.valor if extraccion.monto_reclamado else None,
            # Asegurado: REDACTADO
            "nombres": "[REDACTADO]",
            "cedula": "[REDACTADO]",
            "email": "[REDACTADO]",
            "telefono": "[REDACTADO]",
        }
        return redactado
```

---

## 8. Garantías de Determinismo (PBT-03)

**Invariantes Testables para Fraude:**

1. **Idempotencia:** `construir_alerta_fraude(ex, pol) == construir_alerta_fraude(ex, pol)`
2. **Cero inconsistencias → None:** Si `detectar_inconsistencias(ex, pol) == []`, entonces `alerta == None`
3. **Severidad determinística:** Mismo conjunto inconsistencias → misma severidad siempre
4. **Orden inconsistencias fijo:** Sorted por TipoInconsistencia.name (reproducible)
5. **No hay inconsistencias ficticias:** Solo tipos conocidos (TipoInconsistencia enum)
6. **LLM no modifica severidad:** Output LLM no cambia inconsistencias ni severidad (solo explicación)
7. **Redaction simétrica:** PII redactada reproduciblemente (P5)

---

## 9. Testing — Estructura

```
backend/tests/test_u3_fraude_determinismo.py:
  - test_detectar_inconsistencias_fecha_futura_alta_severidad
  - test_detectar_inconsistencias_monto_excede_suma
  - test_cero_inconsistencias_no_emite_alerta
  - test_severidad_sube_con_conteo_3_plus
  - test_redondeo_en_monto_excede
  - test_llm_no_modifica_severidad (mock)
  - test_redaction_pi_in_payload

backend/tests/test_u3_fraude_pbt.py:
  - @given(extraccion, poliza) → idempotencia
  - @given(inconsistencias) → severidad determinística
  - @given(empty_list) → no alerta
```

