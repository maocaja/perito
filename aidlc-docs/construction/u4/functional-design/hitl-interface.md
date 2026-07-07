# U4 Functional Design — C8 HITL Interface & C11 Dashboard

**Components:** C8 HITL (Mutador de Estado) + C11 Dashboard (Demo-grade UI)

---

## 1. C8 HITL Service Interface (Unique State Mutator)

```python
class HITLService:
    """HITL: Human-in-the-Loop state management.
    
    RULE-CTR-05 (P1): Este es el ÚNICO componente que muta Caso.estado.
    Todas las transiciones pasan por estos métodos.
    """
    
    def transicionar(
        self,
        caso: Caso,
        nuevo_estado: EstadoCaso,
        actor: str = "SISTEMA",
        motivo: str = None
    ) -> Caso:
        """Transición genérica (no-terminal).
        
        ✅ RECIBIDO→EN_PROCESO, EN_PROCESO→LISTO_PARA_APROBAR, etc.
        ❌ NO permite APROBADO/RECHAZADO (usa aprobar/rechazar)
        """
        pass
    
    def aprobar(
        self,
        caso: Caso,
        usuario: str,  # Usuario ANALISTA/CUMPLIMIENTO
        motivo: str = None
    ) -> Caso:
        """Aprueba caso (terminal).
        
        ✅ Requiere usuario ≠ None (P1)
        ✅ Setea aprobado_por=usuario
        ✅ Valida Caso.estado=EN_REVISION
        ✅ Test H-12: aprobar(usuario=None) → raises
        """
        pass
    
    def rechazar(
        self,
        caso: Caso,
        usuario: str,
        motivo: str = None
    ) -> Caso:
        """Rechaza caso (terminal).
        
        ✅ Requiere usuario ≠ None (P1)
        ✅ Setea aprobado_por=usuario
        ✅ Motivo va a motivo_escalamiento (P3 trazabilidad)
        """
        pass
    
    def corregir(
        self,
        caso: Caso,
        cambios: dict,
        usuario: str
    ) -> Caso:
        """Actualiza sub-objetos en REQUIERE_REVISION.
        
        ✅ No cambia estado (sigue siendo REQUIERE_REVISION)
        ✅ Actualiza extraccion, poliza_match, dictamen (esos SÍ son mutables)
        ✅ Prepara para siguiente ronda de orquestación
        """
        pass
```

---

## 2. C11 Dashboard (Demo-grade)

**Nota:** Dashboard es vista informativa. TODAS las decisiones van via C8 HITL (backend).
Dashboard solo presenta datos y delega en hitl.* methods.

### Case List View

**Endpoint:** `GET /casos`

```json
{
  "casos": [
    {
      "id": "caso-123",
      "estado": "LISTO_PARA_APROBAR",
      "timestamp": "2026-07-07T10:00:00Z",
      "tipo_siniestro": "AUTO_COLISION",
      "resultado_dictamen": "CUBIERTO",
      "motivo_escalamiento": null
    },
    {
      "id": "caso-124",
      "estado": "REQUIERE_REVISION",
      "timestamp": "2026-07-07T09:30:00Z",
      "tipo_siniestro": "HOGAR_AGUA",
      "resultado_dictamen": null,
      "motivo_escalamiento": "Póliza no encontrada (solo candidatas)"
    }
  ]
}
```

**Campos mínimos:**
- `id`: Caso.id
- `estado`: EstadoCaso actual
- `timestamp`: Caso.timestamp_actualizacion
- `tipo_siniestro`: (extraído de extraccion)
- `resultado_dictamen`: Dictamen.resultado (si existe)
- `motivo_escalamiento`: Caso.motivo_escalamiento (si REQUIERE_REVISION)

---

### Case Detail View

**Endpoint:** `GET /casos/{caso_id}`

```json
{
  "caso": {
    "id": "caso-123",
    "estado": "LISTO_PARA_APROBAR",
    "aviso": {
      "texto_crudo": "[REDACTED]",  // P5: PII redactada
      "calidad": "LIMPIO"
    },
    "extraccion": {
      "campos": [
        {
          "nombre": "fecha_siniestro",
          "valor": "2026-07-07",
          "confianza": 0.98,
          "origen": { "tipo": "SPAN", "referencia": "doc:page1:span5" }
        }
      ]
    },
    "poliza_match": {
      "encontrada": true,
      "poliza": {
        "numero": "POL-2025-123456",
        "suma_asegurada": "50000.00",
        "deducible": "500.00",
        "clausulas": [ ... ]
      }
    },
    "dictamen": {
      "resultado": "CUBIERTO",
      "regla_aplicada": "R5_DEDUCIBLE",
      "clausula": {
        "id": "DED-001",
        "tipo": "DEDUCIBLE",
        "texto": "Deducible: COP 500"
      },
      "monto_pagable": "9500.00"
    },
    "alerta_fraude": {
      "severidad": "BAJA",
      "inconsistencias": [],
      "explicacion": "Sin hallazgos de fraude"
    },
    "motivo_escalamiento": null
  },
  "actions": [
    {
      "label": "Aprobar",
      "method": "POST /casos/{caso_id}/aprobar",
      "requires_usuario": true
    },
    {
      "label": "Rechazar",
      "method": "POST /casos/{caso_id}/rechazar",
      "requires_usuario": true,
      "requires_motivo": true
    }
  ]
}
```

**Información expuesta:**
- ✅ Aviso redactado (P5: PII stripped)
- ✅ Extracción con confianza y origen (P3 trazabilidad)
- ✅ Póliza match (si encontrada)
- ✅ Dictamen con regla + cláusula (diferenciador auditable)
- ✅ Alerta de fraude con evidencia
- ✅ Motivo de escalamiento (si REQUIERE_REVISION)
- ✅ Acciones disponibles (aprobar, rechazar, si aplica)

---

### Case Actions

**Aprobar:** `POST /casos/{caso_id}/aprobar`

```json
{
  "usuario": "analista@banco.com",
  "motivo": "Revisado y conforme"
}
```

Resultado: `Caso(estado=APROBADO, aprobado_por=usuario, timestamp=now)`

---

**Rechazar:** `POST /casos/{caso_id}/rechazar`

```json
{
  "usuario": "cumplimiento@banco.com",
  "motivo": "Inconsistencia en extracción; solicitar corrección"
}
```

Resultado: `Caso(estado=RECHAZADO, aprobado_por=usuario, motivo_escalamiento=motivo, timestamp=now)`

---

**Corregir (Reingreso de datos):** `PUT /casos/{caso_id}/corregir`

```json
{
  "usuario": "operador@banco.com",
  "cambios": {
    "extraccion": {
      "campos": [
        {
          "nombre": "numero_poliza",
          "valor": "POL-2025-999999",  // Corrección del usuario
          "confianza": 1.0,
          "origen": { "tipo": "MANUAL", "referencia": "corrección usuario" }
        }
      ]
    }
  }
}
```

Resultado: `Caso(extraccion=updated, estado=REQUIERE_REVISION, timestamp=now)` 
→ Orquestador reintenta (ronda 2 de max_rondas=1)

---

## 3. Invariantes Enforced

✅ **Dashboard es pasivo:**
- Solo presenta datos
- NO invoca lógica; delega en endpoints backend (C8 HITL)
- Buttons llaman `hitl.aprobar()`, `hitl.rechazar()`, etc.

✅ **Aprobado_por obligatorio:**
- Acciones terminal (aprobar, rechazar) piden usuario
- Backend (C8) valida usuario ≠ None
- Test H-12: usuario=null → API retorna 400 (validation error)

✅ **P3 Trazabilidad:**
- Cada campo de extracción cita su origen (EvidenciaOrigen)
- Dictamen cita regla + cláusula
- Alerta de fraude cita inconsistencias (EvidenciaOrigen)

✅ **P5 Redaction:**
- Aviso redactado (PII stripped via LLMPayloadBuilder)
- Nombres, cédulas, direcciones, teléfonos, emails: [REDACTED]
- Montos preservados (operacionales)

---

## 4. Demo-grade Notes

- Auth: stub (selector de rol, no real OAuth)
- Persistence: en-memory (no DB real)
- Real-time: polling (no WebSocket)
- Mobile: no soportado (desktop/tablet only)

