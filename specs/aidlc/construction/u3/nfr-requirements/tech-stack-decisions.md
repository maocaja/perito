# U3 Tech Stack Decisions — pytest + Hypothesis, Fixtures, LLM Mocking, Logging

**Unit:** U3 · Cobertura determinística · Fraude
**Design Principle:** Motor puro determinístico (P2) con 100% PBT coverage (RNF-05)

---

## Testing Framework: pytest + Hypothesis

### Core Stack

**pytest:**
- Unit testing, fixture management, introspection
- No alternative needed (already U1 baseline)

**Hypothesis:** 🔒 100% motor R1-R5 coverage via property-based testing
- Generadores built-in: `st.dates()`, `st.decimals()`, `st.sampled_from()`
- Shrinking + seed replay (deterministic failure reproduction)
- PBT-08 compliance: no Faker in @given (breaks shrinking)

**Cero deps nuevas:**
- ❌ NO freezegun (inyecta fecha ref al motor en vez de mocking time)
- ❌ NO Factory-Boy (factory functions en Python suficientes)
- ❌ NO pytest-mock (MagicMock built-in)

---

## Fixture Strategy

### Unit Test Fixtures

**Factory Functions** (Python, no Factory-Boy):
```python
def poliza_builder(
    vigencia_desde=date(2026, 1, 1),
    vigencia_hasta=date(2027, 12, 31),
    coberturas_contratadas=None,
    exclusiones=None,
    clausulas=None,
    suma_asegurada=Decimal("50000000"),
    deducible=Decimal("500000"),
):
    """Build Poliza with defaults, overrideable."""
    return Poliza(
        numero="POL-2026-001",
        vigencia=RangoFechas(desde=vigencia_desde, hasta=vigencia_hasta),
        coberturas_contratadas=coberturas_contratadas or ["AUTO_COLISION"],
        # ... resto
    )

def claim_builder(
    tipo_siniestro="AUTO_COLISION",
    fecha_siniestro=date(2026, 7, 6),
    monto_reclamado=Decimal("10000000"),
):
    """Build ExtraccionValidada with defaults."""
    return ExtraccionValidada(
        campos=[
            CampoExtraido(nombre="tipo_siniestro", valor=tipo_siniestro, ...),
            # ... resto
        ]
    )
```

**pytest.fixture wrappers** (optional, for reuse):
```python
@pytest.fixture
def poliza_standard():
    return poliza_builder()

@pytest.fixture
def claim_standard():
    return claim_builder()
```

---

## Property-Based Testing Strategy (PBT-03) 🔒

### Hypothesis Strategies for Motor R1-R5

**Date generation (R1 Vigencia):**
```python
from hypothesis import given
from hypothesis import strategies as st

# Estrategia: fecha entre 2020 y 2030
dates_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31)
)

@given(fecha_siniestro=dates_strategy)
def test_r1_vigencia_property(fecha_siniestro):
    """R1 siempre retorna bool, nunca None."""
    result = calcular_r1_vigencia(fecha_siniestro, vigencia)
    assert isinstance(result, bool)
```

**Decimal generation (R4/R5 montos):**
```python
montos_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999999"),
    places=2
)
```

**Enums (R2 cobertura tipos):**
```python
tipos_strategy = st.sampled_from(list(TipoSiniestro))
```

**Motor composite (happy path):**
```python
@given(
    monto=st.decimals(min_value=Decimal("1"), max_value=Decimal("100000000"), places=2),
    suma_asegurada=st.decimals(min_value=Decimal("1"), max_value=Decimal("100000000"), places=2),
)
def test_motor_properties_composite(monto, suma_asegurada):
    """All R1-R5 invariants hold for random valid inputs."""
    result = motor_cobertura(extraccion, poliza)
    
    # Invariant 1: resultado en enum
    assert result.resultado in {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}
    
    # Invariant 2: deducible >= 0
    assert result.deducible_calculado >= 0
    
    # Invariant 3: cláusula ≠ None
    assert result.clausula is not None
```

### PBT vs. Unit Test Split

**PBT (Hypothesis):**
- Propiedades invariantes (1-8 de nfr-requirements.md)
- Cobertura de input space (miles de casos generados)
- Regression detection (failures reproducible by seed)

**Unit Tests:**
- Casos específicos de cita-regla ("R1 vigencia expirada → cita R1 por Clausula.tipo")
- Edge cases determinísticos (deducible = 0, monto = suma exacto, etc.)
- Comportamientos de escalamiento (campo ausente → REQUIERE_REVISION con motivo específico)

---

## LLM Mocking Strategy (Fraude C6)

### Mock Sonnet Determinístico

**Pattern (como C2/C3):**
```python
@patch("app.llm.fraude.Anthropic")
def test_fraude_razonamiento(mock_anthropic):
    """Fraude with mocked Sonnet response."""
    
    # Mock response: inconsistencias sutiles
    mock_response = MagicMock()
    mock_response.content[0].text = json.dumps({
        "inconsistencias_sutiles": ["Patrón de reclamación sospechoso"],
        "severidad_ajustado": "MEDIA"
    })
    mock_anthropic.return_value.messages.create.return_value = mock_response
    
    # Call
    alerta = detectar_fraude(extraccion, poliza)
    
    # Assert
    assert alerta.inconsistencias is not None
    assert alerta.explicacion is not None
    assert alerta.severidad in {BAJA, MEDIA, ALTA}
    assert alerta.severidad == "MEDIA"  # Dari mock determinístico
```

**No Sonnet real en tests** (determinístico, reproducible, fast)

### Fraude Assertions

```python
def test_fraude_no_muta_estado():
    """AlertaFraude never changes Caso.estado (P1)."""
    caso = Caso(estado=RECIBIDO, ...)
    alerta = detectar_fraude(extraccion, poliza)
    
    # Caso.estado unchanged
    assert caso.estado == RECIBIDO
    
    # AlertaFraude returned independently
    assert alerta is not None
    assert isinstance(alerta, AlertaFraude)

def test_fraude_evidencia_obligatoria():
    """AlertaFraude.inconsistencias never empty (P6)."""
    alerta = detectar_fraude(extraccion, poliza)
    
    # Contract enforced by Pydantic
    assert len(alerta.inconsistencias) > 0

def test_fraude_redaccion_aplicada():
    """LLMPayloadBuilder redacts PII before Sonnet (P5)."""
    # Mock Sonnet and capture input
    with patch("app.llm.fraude.LLMPayloadBuilder") as mock_builder:
        mock_builder_instance = MagicMock()
        mock_builder.return_value = mock_builder_instance
        
        detectar_fraude(extraccion_con_pii, poliza)
        
        # Assert redaction was called
        mock_builder_instance.build_fraude_prompt.assert_called_once()
```

---

## Logging Strategy (P5 + Auditability)

### Motor Logging (sin PII)

**Dictamen logging:**
```python
logger.info(
    f"Dictamen: resultado={resultado}, regla={regla_aplicada}, "
    f"clausula_id={clausula.id}, deducible={deducible_calculado}"
)
# Nota: montos PERMITIDOS en logs (no PII)
```

**PII masking para eventos:**
```python
from app.security.redaction import PIIRedactingLogSerializer

serializer = PIIRedactingLogSerializer()
event = {
    "tipo_siniestro": "AUTO_COLISION",
    "monto_reclamado": 10000000,  # ✅ permitido
    "texto_crudo": "Juan Pérez, cedula 1234567..."  # ❌ redactar
}
safe_event = serializer.redact(event, AvisoNormalizado)
# Resultado: texto_crudo → [REDACTED]
```

### Fraude Logging

**Inconsistencies detected:**
```python
logger.warning(
    f"Fraude: severidad={severidad}, "
    f"inconsistencias={','.join(inconsistencias[:3])}..."
)

# Si LLM falla, graceful degradation:
logger.error(f"Fraude LLM call failed: {error}; retornando solo determinísticas")
```

---

## Factory Functions Patterns

### poliza_builder

Located: `backend/tests/factories/poliza_factory.py`

```python
def poliza_builder(
    numero="POL-2026-001",
    vigencia_desde=date(2026, 1, 1),
    vigencia_hasta=date(2027, 12, 31),
    coberturas_contratadas=None,
    exclusiones=None,
    clausulas=None,
    suma_asegurada=Decimal("50000000"),
    deducible=Decimal("500000"),
    es_soat=False,
):
    """Build Poliza with sensible defaults."""
    return Poliza(
        numero=numero,
        vigencia=RangoFechas(desde=vigencia_desde, hasta=vigencia_hasta),
        coberturas_contratadas=coberturas_contratadas or ["AUTO_COLISION"],
        exclusiones=exclusiones or [],
        clausulas=clausulas or [
            Clausula(id="vigencia-1", tipo=TipoClausula.VIGENCIA, texto="...", referencia="Art.1"),
            # ... R2-R5 clausulas
        ],
        suma_asegurada=suma_asegurada,
        deducible=deducible,
        es_soat=es_soat,
    )
```

### claim_builder

```python
def claim_builder(
    numero_poliza="POL-2026-001",
    tipo_siniestro="AUTO_COLISION",
    fecha_siniestro=date(2026, 7, 6),
    monto_reclamado=Decimal("10000000"),
):
    """Build ExtraccionValidada (claim)."""
    return ExtraccionValidada(campos=[
        CampoExtraido(nombre="numero_poliza", valor=numero_poliza, ...),
        CampoExtraido(nombre="tipo_siniestro", valor=tipo_siniestro, ...),
        CampoExtraido(nombre="fecha_siniestro", valor=str(fecha_siniestro), ...),
        CampoExtraido(nombre="monto_siniestro", valor=str(monto_reclamado), ...),
    ])
```

---

## Database Access Policy 🔒

### Motor R1-R5: Cero BD

**Motor reads ONLY from in-memory Poliza.clausulas:**
- Cláusulas passed via `ResultadoPoliza.poliza` (from U2-C4)
- Cero database lookups inside R1-R5
- This makes motor a **pure function** (P2 foundation)

**BD mocking: N/A** — no I/O en el motor

### Fraude C6: Optional BD (future)

- Inconsistencias duras: no BD needed
- LLM Sonnet: calls API (mocked in tests)
- Historiales/patrones: future feature (not MVP)

---

## Zero New Dependencies ✅

**Approved Stack:**
- pytest (existing U1)
- hypothesis (existing U1)
- pydantic (existing U1)
- anthropic (existing U2)

**Rejected:**
- freezegun (use date injection instead)
- factory-boy (use functions instead)
- pytest-mock (use unittest.mock)

