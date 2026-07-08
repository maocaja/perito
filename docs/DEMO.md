# Perito — Demo / Walkthrough

**Perito** es un copiloto agéntico de **admisión de siniestros (FNOL)** para seguros (es-CO).
No decide siniestros: **prepara, cita la evidencia y escala; el humano decide** (Human-in-the-Loop).

Es una **vitrina de portafolio** (no un producto de mercado): demuestra arquitectura agéntica
con guardrails no negociables (P1-P7), no un servicio desplegado.

## El pipeline

```
aviso FNOL → C2 Extractor (Haiku) → C3 Verificador (Sonnet) → C4 Grounding de póliza
          → C5 Motor de cobertura R1-R5 (determinístico) → C6 Fraude → LISTO_PARA_APROBAR
```
El **orquestador (C7)** conduce el flujo con **caps de terminación (P4)** y **nunca alcanza un
estado terminal** — APROBADO/RECHAZADO exigen firma humana vía HITL (C8).

## Cómo correrlo

Requisitos: Python 3.12+, un venv con las deps (`pip install fastapi uvicorn jinja2 python-multipart httpx pydantic pydantic-settings anthropic faker sqlalchemy pgvector`).

### 1. La suite (sin costo, LLM mockeado)
```bash
cd backend
ANTHROPIC_API_KEY=test python -m pytest tests/ -q      # 147 tests verde
```

### 2. Los agentes reales — showcase (requiere key real de Anthropic)
```bash
cd backend
ANTHROPIC_API_KEY=<tu-key> python showcase.py
```
Corre **4 escenarios reales** por el pipeline completo, con los agentes Claude en acción:

| Escenario | Qué demuestra |
|-----------|---------------|
| **Feliz** (cobertura OK) | C2 extrae, C3 verifica, el motor dictamina y **cita regla + cláusula** (P2/P3) |
| **Fraude** (monto anómalo) | C6 **detecta y explica** la inconsistencia (P6) — solo sugiere, no bloquea |
| **Cobertura negativa** (tipo no contratado) | **NO_CUBIERTO** citando la regla R2 — lo decide el **motor determinístico**, no el LLM (P2) |
| **Póliza no encontrada** | **Escala** a REQUIERE_REVISION — **no inventa** una póliza (P4) |

En **todos**, el estado final ∈ `{LISTO_PARA_APROBAR, REQUIERE_REVISION}` — **el orquestador nunca cierra el caso** (P1).

### 3. El dashboard (vitrina HITL, HTMX)
```bash
cd backend
uvicorn app.main:app          # http://localhost:8000/casos
```
- **`/casos`** — bandeja con filtro por estado (rol Analista).
- **`/casos/{id}`** — detalle con el **aviso redactado (P5)**, extracción campo→origen, dictamen con
  cláusula citada, alerta de fraude, y botones **Aprobar/Rechazar** (delegan en HITL; sin firma → 400).
- **`/panel`** — panel de cumplimiento: trazas por nodo + tokens/costo + export JSON (rol Cumplimiento).

Al arrancar, el dashboard se puebla con casos demo (con evidencia real de C4/C5/C6).

## Los invariantes (por qué esto no es "un chatbot que decide siniestros")

- **P1 HITL** — el agente nunca cierra un caso; el humano firma (`aprobado_por`).
- **P2 Cobertura determinística** — la decide el motor R1-R5, **nunca el LLM**.
- **P3 Trazabilidad** — cada campo cita su origen; cada dictamen cita regla + cláusula.
- **P4 Terminación acotada** — caps de rondas/tokens; escala en vez de inventar/loopear.
- **P5 PII** — el aviso se redacta antes de mostrarse / enviarse al LLM.
- **P6 Fraude explicable** — con evidencia; solo sugiere.
- **P7 Alcance honesto** — portafolio, no producto desplegado.

## Diseño y proceso

- Specs de diseño: `specs/aidlc/` (requisitos, user-stories, units, construction FD/NFR).
- Cómo se construyó (honesto): `specs/aidlc/METODOLOGIA.md`.
- El proceso AI-DLC completo (runtime, historial granular) vive en la rama `spec/aidlc-inception` / tag `aidlc-process`.
