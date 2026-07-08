# U4 Functional Design — C1 Intake (Crear Caso)

**Component:** C1 Intake · Ubicación: `backend/app/intake/`
**Responsabilidad:** Crear Caso inicial desde AvisoNormalizado (estado=RECIBIDO)

---

## 1. Intake Constructor

```python
def intake_crear_caso(aviso: AvisoNormalizado) -> Caso:
    """Crea Caso inicial desde aviso FNOL.
    
    Args:
        aviso: AvisoNormalizado (texto_crudo + calidad)
    
    Returns:
        Caso(estado=RECIBIDO, aviso=aviso, extraccion=None, ..., aprobado_por=None)
    
    Raises:
        ValidationError: si AvisoNormalizado.calidad=ILEGIBLE (no se puede procesar)
    """
    
    # --- Chequeo 1: ¿Documento procesable? ---
    if aviso.calidad == CalidadDoc.ILEGIBLE:
        # No intentar extracción; escalar inmediatamente
        raise ValueError(
            "Aviso ILEGIBLE: no se puede procesar. "
            "El caso requiere escalamiento manual a REQUIERE_REVISION."
        )
    
    # --- Crear Caso inicial ---
    caso = Caso(
        id=str(uuid4()),  # UUID único del caso
        estado=EstadoCaso.RECIBIDO,
        aviso=aviso,
        extraccion=None,  # Se rellena en C2
        poliza_match=None,  # Se rellena en C4
        dictamen=None,  # Se rellena en C5
        alerta_fraude=None,  # Se rellena en C6
        aprobado_por=None,  # Solo via hitl.aprobar/rechazar
        motivo_escalamiento=None,
        timestamp_creacion=datetime.utcnow(),
        timestamp_actualizacion=datetime.utcnow()
    )
    
    return caso
```

---

## 2. CalidadDoc Handling (Enumerado en U1)

```python
class CalidadDoc(str, Enum):
    """Marca de calidad del aviso (estrato documento-sucio, H-01)."""
    
    LIMPIO = "LIMPIO"       # Flujo normal: intenta extracción
    DEGRADADO = "DEGRADADO" # Flujo normal pero confianza puede bajar; escala por umbral
    ILEGIBLE = "ILEGIBLE"   # NO procesa; escalamiento inmediato a REQUIERE_REVISION
```

---

## 3. Flow por CalidadDoc

```
Caso: AvisoNormalizado(texto_crudo=..., calidad=X)

├─ calidad=LIMPIO
│  └─ C1.intake_crear_caso() → Caso(RECIBIDO)
│  └─ Orquestador procesa normal (C2→C3→C4→C5→C6)
│  └─ Si confianza de campos baja → escalamiento por C5 (REQUIERE_REVISION)
│
├─ calidad=DEGRADADO
│  └─ C1.intake_crear_caso() → Caso(RECIBIDO)
│  └─ Orquestador procesa pero monitorea confianza
│  └─ Si confianza_promedio < umbral (ej: 70%) → escalamiento por C5
│
└─ calidad=ILEGIBLE
   └─ C1.intake_crear_caso() → raises ValidationError
   └─ El caso NO se crea; se retorna error al usuario
   └─ El usuario debe ingresar el aviso nuevamente
   └─ (Alternativa: crear Caso en REQUIERE_REVISION, pero eso requiere hitl, no C1)
```

---

## 4. Invariantes

✅ **Estado inicial es RECIBIDO:**
- Todo caso empieza en RECIBIDO
- Primer cambio de estado vía `hitl_service.transicionar(caso, EN_PROCESO)`

✅ **Documentos ILEGIBLE no se procesan:**
- Fail-closed (P4): si no se puede extraer, no se inventa
- Retorna error; usuario reintroduce aviso

✅ **Sub-objetos son None inicialmente:**
- extraccion, poliza_match, dictamen, alerta_fraude se rellenan downstream (C2-C6)
- aprobado_por siempre None hasta terminal (solo HITL lo setea)

---

## 5. Error Handling

```python
try:
    caso = intake_crear_caso(aviso)
    # Proceder al orquestador
except ValueError as e:
    if "ILEGIBLE" in str(e):
        # Retornar error HTTP 400 al usuario
        return error_response(
            status_code=400,
            detail="El aviso está ilegible. Por favor, reintente con documento más claro."
        )
    raise
```

