# Perito

**Co-piloto de IA para admisión y triage de siniestros de seguros (FNOL — First Notice of Loss / aviso de siniestro).**

Lee un aviso de siniestro como llega en la vida real (correo desordenado, PDF, fotos, audio) y: extrae los datos estructurados → verifica la extracción contra la fuente → valida la cobertura contra la póliza (reglas determinísticas) → marca señales de fraude → enruta al ajustador → redacta el acuse al asegurado y el resumen para el ajustador. **Human-in-the-loop: nunca cierra un siniestro solo.**

## Qué es y qué no es

- **Es**: un proyecto de portafolio para practicar arquitectura de sistemas agénticos (orquestación, tool contracts, verificación adversarial, reglas determinísticas, HITL, terminación acotada, trazabilidad, observabilidad, evals) sobre un caso con valor de negocio real y ground truth verificable.
- **No es**: un oráculo ni una startup. Co-piloto asistivo. El *fraud flagger* es heurístico (no un modelo entrenado) y los documentos de demo son sintéticos — ambas cosas se declaran.

## Contexto de construcción

- Motor genérico + superficie localizable `es-CO` (español colombiano, COP, SOAT, aseguradoras locales). Regulación (Superintendencia Financiera, Ley 1581 de 2012 / Habeas Data) solo como consciencia de dominio, no implementada.
- Stack previsto: FastAPI + Postgres/pgvector, LLM por capas (Haiku/Sonnet/Opus), orquestación con terminación dura, observabilidad con Langfuse/LangSmith.
- Datos: backbone tabular público (Kaggle, insurance fraud → ground truth) + capa de documentos FNOL sintéticos generada por LLM.

## Cómo correr Perito

Todo se maneja con `make` (usa un venv local; configurable con `make <target> VENV=/ruta`).

```bash
make setup     # crea el venv e instala dependencias (idempotente)
make run       # levanta el dashboard en http://localhost:8000  → redirige al Workbench
make test      # suite base, hermética (sin API, sin costo)
make demo      # 4 escenarios por el pipeline real (o presets sin ANTHROPIC_API_KEY)
```

La superficie del operador es el **Claims Workbench** en `http://localhost:8000/workbench` (la raíz `/` redirige ahí).

### Demo en vivo por correo

Perito puede ingerir siniestros **como llegan en la vida real: por correo**. Un generador envía avisos FNOL sintéticos a un buzón Gmail dedicado, y un *poller* dentro de la app los lee por IMAP y crea el caso. Son **dos piezas** en **dos terminales**:

```
demo_mail.py ──SMTP──▶ 📬 Gmail demo ──IMAP──▶ poller (en la app) ──▶ caso en el Workbench
  (genera y ENVÍA)         (buzón)              (LEE y crea el caso)
```

**1. Configura el buzón demo** en `.env` (sintético, sin PII real):

```bash
DEMO_LIVE=deterministic                        # off | deterministic | real
DEMO_GMAIL_ADDRESS=tu-buzon-demo@gmail.com
DEMO_GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx        # app-password de Gmail (16 chars, sin espacios)
MAIL_TOTAL=5                                    # cuántos correos envía el generador (opcional)
```

Modos del poller (`DEMO_LIVE`):
- **`off`** (default) — el poller nunca arranca (cero costo, cero red).
- **`deterministic`** — mapea el marcador `[DEMO:<escenario>]` del asunto a un preset **sin LLM** (ensayo gratis).
- **`real`** — corre el pipeline agéntico completo sobre el correo (requiere `ANTHROPIC_API_KEY`).

**2. Levanta la app** (arranca el poller que lee el buzón):

```bash
make run
```

**3. En otra terminal, dispara el envío:**

```bash
make demo-mail        # envía MAIL_TOTAL correos (~5/min) y termina solo
```

Verás los casos aparecer en `http://localhost:8000/workbench` conforme el poller los levanta. El generador rota 4 escenarios — `feliz`, `fraude`, `no-encontrada`, `campos-faltantes` — definidos en `backend/demo_run.py` (`ESCENARIOS`, fuente única de verdad). Para cambiar la cantidad: `MAIL_TOTAL=10 make demo-mail`.

> **Nota de honestidad (P7):** los correos y sus adjuntos son **sintéticos** (sin PII real). El modo `deterministic` no llama al LLM; es para ensayar la demo sin costo.

## Estructura

```
backend/    — la app: agentes (C0–C11), motor de reglas, orquestador, Workbench, evals
specs/      — PRD (specs/prd.md) y arquitectura AI-DLC (specs/aidlc/, incl. C4)
docs/       — artefactos de producto + diagramas (c4-arquitectura.html)
research/   — deep research de validación y de crítica
```

## Estado

Feature-complete en `main`: el flujo FNOL de punta a punta (extracción → verificación → cobertura → fraude → HITL) y el Claims Workbench están construidos y probados. El estado real de implementación (qué se construyó, qué quedó como stub) está en el **Apéndice D del PRD** (`specs/prd.md`).
