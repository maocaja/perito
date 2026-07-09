# Perito — Demo / Walkthrough

**Perito** es un copiloto agéntico de **admisión de siniestros (FNOL)** para seguros (es-CO).
No decide siniestros: **prepara, cita la evidencia y escala; el humano decide** (Human-in-the-Loop).

> **Alcance honesto (P7):** esto es una **implementación de referencia** de la capa de confianza que
> los aseguradores regulados piden en 2026 (reglas deterministas + HITL auditable + trazabilidad),
> **NO** un producto en producción con miles de corridas. El valor defendible NO es el LLM (cualquiera
> llama a Haiku) — es el **motor determinístico de cobertura + HITL + auditoría citada**.

## El pipeline

```
aviso FNOL → C2 Extractor (Haiku) → C3 Verificador (Sonnet) → C4 Grounding de póliza
          → C5 Motor de cobertura R1-R5 (determinístico) → C6 Fraude → LISTO_PARA_APROBAR
```
El **orquestador (C7)** conduce el flujo con **caps de terminación (P4)** y **nunca alcanza un
estado terminal** — APROBADO/RECHAZADO exigen firma humana vía HITL (C8). Los agentes **alimentan
campos**; la **decisión de cobertura la toma el motor de reglas, nunca el LLM (P2)**.

## Un comando

```bash
make setup          # crea el venv e instala deps (obs + evals + psycopg)
make demo           # corre los 4 escenarios
```
El venv es configurable: `make demo VENV=/tmp/perito-v`. Corre `make help` para ver todos los targets.

### `make demo` — dos tiers (degrada con gracia)

| Tier | Cuándo | Qué corre | Costo |
|------|--------|-----------|-------|
| **Real** ⭐ | con `ANTHROPIC_API_KEY` real | agentes Claude vía `orquestar_fnol` (C2 Haiku + C3 Sonnet) | ~USD 0.02 los 4 casos |
| **Determinístico** | sin key | presets (sin LLM) — el comando nunca falla | cero |

> ⚠️ **Costo:** el tier real hace llamadas reales a la API de Anthropic (centavos, ~USD 0.02 por los
> 4 casos). Sin key → presets deterministas, **costo cero**. Ninguna promesa de "demo = gratis".

Para verlo con toda la potencia, configura tus claves en un `.env` (gitignorado, nunca se commitea):

```bash
cp env.example .env          # plantilla con los valores públicos ya seteados
# edita .env y rellena los SECRETOS (los públicos ya vienen):
#   ANTHROPIC_API_KEY=...                      → agentes Claude reales
#   LANGFUSE_PUBLIC_KEY=... LANGFUSE_SECRET_KEY=...   → trazas a Langfuse
#   DATABASE_URL=postgresql://...neon...?sslmode=require   (+ PERSISTENCE=postgres)  → Neon
make demo
```
La config sale de `.env` (raíz del repo). Las variables del shell (`export ...`) **tienen prioridad**
sobre el `.env`, por si quieres sobreescribir algo puntual. `make test` es hermético: ignora el `.env`.

`make demo` **narra cada paso en vivo** (C2 → C3 → C5 motor+cláusula → C6 fraude → estado), sin
necesidad de abrir Langfuse. Luego cierra con **costo/caso + % escalado + links**.

### Los 4 escenarios — el hilo narrativo (no solo el happy path)

| Escenario | Qué demuestra | Invariante |
|-----------|---------------|------------|
| **Feliz** (cobertura OK) | el motor dictamina y **cita regla + cláusula** | P2/P3 |
| **Fraude** (monto excede la suma) | C6 **detecta y explica**; solo **sugiere**, no bloquea | P6 |
| **Cobertura negativa** (tipo no contratado) | **NO_CUBIERTO** — lo decide el **motor**, no el LLM | P2 |
| **Póliza no encontrada** | **escala** a REQUIERE_REVISION — **no inventa** una póliza | P4 |

En **todos**, el estado final ∈ `{LISTO_PARA_APROBAR, REQUIERE_REVISION}` — **el orquestador nunca
cierra el caso** (P1: firma el humano con `aprobado_por`).

### El dashboard (vitrina HITL, HTMX)

```bash
make run                      # http://localhost:8000/casos
```
- **`/casos`** — bandeja con filtro por estado (rol Analista); los casos de `make demo` quedan aquí.
- **`/casos/{id}`** — detalle con el **aviso redactado (P5)**, extracción campo→origen, dictamen con
  cláusula citada, alerta de fraude, y **Aprobar / Corregir / Rechazar** (delegan en HITL; sin firma → 400).
- **`/panel`** — cumplimiento: métricas agregadas + trazas por nodo + tokens/costo + export JSON.

### Evals agénticos (Claude-as-judge)

```bash
make evals                    # pytest -m agentic (requiere key real; cuesta API)
make test                     # suite base (sin API, sin costo)
```
Los evals corren el pipeline real contra un juez Claude por **estrato** (happy / fraude / cobertura
negativa / no-encontrada), con **faithfulness como gate duro**. Van aparte de `make demo` a propósito
(cuestan API y tiempo); `make demo` es rápido y repetible.

## Los invariantes (por qué esto no es "un chatbot que decide siniestros")

- **P1 HITL** — el agente nunca cierra un caso; el humano firma (`aprobado_por`).
- **P2 Cobertura determinística** — la decide el motor R1-R5, **nunca el LLM**.
- **P3 Trazabilidad** — cada campo cita su origen; cada dictamen cita regla + cláusula.
- **P4 Terminación acotada** — caps de rondas/tokens; escala en vez de inventar/loopear.
- **P5 PII** — el aviso se redacta antes de mostrarse / enviarse / trazarse.
- **P6 Fraude explicable** — con evidencia; solo sugiere.
- **P7 Alcance honesto** — implementación de referencia, no producto desplegado.

## Diseño y proceso

- Specs de diseño: `specs/aidlc/` (requisitos, user-stories, units, construction FD/NFR).
- La Unit de esta demo: `specs/aidlc/evolution/full-demo-showcase.md` (qué + panel de expertos 2026).
- Cómo se construyó (honesto): `specs/aidlc/METODOLOGIA.md`.
- El proceso AI-DLC completo vive en la rama `spec/aidlc-inception` / tag `aidlc-process`.
