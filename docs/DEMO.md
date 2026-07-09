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

### Los 5 escenarios — el hilo narrativo (no solo el happy path)

Los avisos van en **lenguaje natural** (como un usuario real escribe; el extractor C2 saca los campos):

| Escenario | Qué demuestra | Invariante |
|-----------|---------------|------------|
| **Feliz** (cobertura OK) | el motor dictamina y **cita regla + cláusula** | P2/P3 |
| **Fraude** (monto excede la suma) | C6 **detecta y explica**; solo **sugiere**, no bloquea | P6 |
| **Cobertura negativa** (tipo no contratado) | **NO_CUBIERTO** — lo decide el **motor**, no el LLM | P2 |
| **Póliza no encontrada** | **escala** a REQUIERE_REVISION — **no inventa** una póliza | P4 |
| **Datos faltantes** (sin monto) | **escala** pidiendo el dato — **no inventa** el faltante | P4 |

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

### Demo EN VIVO — correos de Gmail → bandeja viva → HITL (Unit H)

La demo de un sistema agéntico corriendo: correos FNOL **llegan a un Gmail**, Perito los **procesa solo**,
y en el dashboard ves la **bandeja llenarse en tiempo real**; entras a un caso, ves **qué hizo cada agente**,
y **cierras con tu firma** (HITL).

**Setup (una vez):** un **Gmail dedicado/desechable** (la app-password da acceso total; no tu personal) →
activa 2FA → crea app-password (`myaccount.google.com/apppasswords`). En `.env`:
```
DEMO_GMAIL_ADDRESS=perito.demo@gmail.com
DEMO_GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx     # 16 chars sin espacios
```

**Tres modos (`DEMO_LIVE`, control de costo — riesgo #2):**
| Modo | Qué corre | Costo |
|------|-----------|-------|
| `off` (default) | poller apagado, app normal | cero |
| `deterministic` | presets sin LLM → **ensayo del front GRATIS** | cero (sin `ANTHROPIC_API_KEY`) |
| `real` | agentes Claude de verdad → el show | ~USD 0.01/correo |

**Correrlo (dos terminales):**
```bash
# terminal 1 — la app con el poller vivo (ensaya gratis con deterministic; el show con real)
DEMO_LIVE=deterministic make run        # → http://localhost:8000/casos

# terminal 2 — el generador: manda MAIL_TOTAL correos sintéticos (~5/min) y se para solo
make demo-mail
```
La bandeja (`/casos`) muestra **"● En vivo"** y se **auto-refresca cada 3s** (HTMX polling); los casos aparecen
a medida que el poller los procesa. Entra a uno → **"Traza de agentes · qué hizo cada uno"** → **Aprobar/Corregir/
Rechazar**. El caso **se detiene** en LISTO_PARA_APROBAR esperando tu firma — el poller **nunca cierra** (P1).

**El usuario NO necesita saber la estructura.** Escribe el correo en lenguaje natural (*"choqué el carro, póliza
POL-DEMO-1001, unos 5 millones"*) y el **extractor C2 saca los campos**. Si falta un dato esencial (monto, fecha,
o una póliza reconocible) → **escala a un humano (P4), no inventa**. Para ver un dictamen de cobertura, menciona una
póliza sembrada (`POL-DEMO-1001/1002/1003`); cualquier otra → escala (también es una demo válida).

> **Costo:** el generador tiene tope (`MAIL_TOTAL`, ~15) y se para solo; el poller default está `off`. Una demo
> real ≈ USD 0.20-0.40. Ensaya todo el front en `deterministic` sin gastar. Los correos son **sintéticos** (sin PII).

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
