# U4 Functional Design — HITL Contract (P1: Único Mutador)

**Invariant Lock:** HITL (C8) es el ÚNICO responsable de todas las transiciones de Caso.estado (P1 — RULE-CTR-05)

---

## 1. Caso.estado: Frozen Contract

```python
class Caso(Contract):
    """Caso FNOL. Estado es FROZEN — solo se transiciona via hitl.transicionar/aprobar/rechazar.
    
    RULE-CTR-05 (P1): HITL es el único mutador. Los demás componentes (C7, C2-C6) retornan
    sub-objetos (extraccion, poliza_match, dictamen, alerta_fraude) SIN mutar estado.
    """
    
    id: str = Field(min_length=1)
    estado: EstadoCaso  # Enum: RECIBIDO, EN_PROCESO, LISTO_PARA_APROBAR, REQUIERE_REVISION, EN_REVISION, APROBADO, RECHAZADO
    
    aviso: AvisoNormalizado
    extraccion: Optional[ExtraccionValidada] = None      # Sub-objeto, mutable
    poliza_match: Optional[ResultadoPoliza] = None       # Sub-objeto, mutable
    dictamen: Optional[Dictamen] = None                  # Sub-objeto, mutable
    alerta_fraude: Optional[AlertaFraude] = None         # Sub-objeto, mutable (informativo, no cierra)
    
    aprobado_por: Optional[str] = None  # Usuario (RolUsuario) que hizo transición terminal
    motivo_escalamiento: Optional[str] = None  # Razón si REQUIERE_REVISION
    
    timestamp_creacion: datetime
    timestamp_actualizacion: datetime
    
    model_config = ConfigDict(frozen=True)  # ← FROZEN: prevent direct assignment
    
    @field_validator('aprobado_por')
    def _aprobado_por_en_terminal(cls, v, info):
        """RULE-CTR-05: Terminal exige aprobado_por no-nulo."""
        estado = info.data.get('estado')
        if estado in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}:
            if v is None:
                raise ValueError(
                    f"RULE-CTR-05: estado terminal '{estado}' exige aprobado_por no-nulo (P1 auditabilidad)"
                )
        return v
```

---

## 2. Transiciones Válidas (Apéndice C del PRD)

```
RECIBIDO
  → EN_PROCESO (hitl.transicionar)

EN_PROCESO
  → LISTO_PARA_APROBAR (hitl.transicionar, si extracción+póliza+dictamen OK)
  → REQUIERE_REVISION (hitl.transicionar, si escalamiento)

LISTO_PARA_APROBAR
  → EN_REVISION (hitl.transicionar)

EN_REVISION
  → APROBADO (hitl.aprobar, SOLO HUMANO, con aprobado_por)
  → RECHAZADO (hitl.rechazar, SOLO HUMANO, con aprobado_por)
  → REQUIERE_REVISION (hitl.transicionar, si más datos necesarios)

REQUIERE_REVISION
  → EN_PROCESO (hitl.transicionar, humano aporta dato/corrección)

APROBADO, RECHAZADO
  → Terminal (sin transiciones)
```

---

## 3. HITL Interface (Único Mutador)

Ver orchestrator-flow.md para pseudocódigo correcto (sin caso.estado = X).

HITL métodos:
- `hitl.transicionar(caso, nuevo_estado, actor=SISTEMA, motivo)` → no-terminal
- `hitl.aprobar(caso, usuario)` → APROBADO + aprobado_por
- `hitl.rechazar(caso, usuario, motivo)` → RECHAZADO + aprobado_por
- `hitl.corregir(caso, cambios, usuario)` → actualiza sub-objetos

---

## 4. Invariantes Enforced

✅ **RULE-CTR-05 (P1):** HITL es único mutador
- Caso.estado es frozen → direct assignment raises
- Todas las transiciones pasan por hitl.transicionar/aprobar/rechazar
- Orquestador (C7) NUNCA hace `caso.estado = X`

✅ **Aprobado_por Obligatorio (P1):**
- Validator en Caso: terminal exige aprobado_por ≠ None
- hitl.aprobar/rechazar validan usuario ≠ None ANTES de model_copy
- Test H-12: Caso(..., aprobado_por=None) → raises, hitl.aprobar(usuario=None) → raises

✅ **No Ciclos Terminales:**
- Estado terminal (APROBADO/RECHAZADO) no tiene transiciones válidas

