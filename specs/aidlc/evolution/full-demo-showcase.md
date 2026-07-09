# Unit de Evolución — Demo Full / Showcase de un comando (G)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.

## 1. Intent

Que se pueda **mostrar toda la potencia del sistema con un comando**: `make demo` corre los 4 escenarios por el
**pipeline REAL** (agentes Claude), y el efecto de cada herramienta queda visible — **trazas en Langfuse,
casos persistidos en Neon, métricas en el dashboard**, con evals agénticos a un comando de distancia. Cierra el
gap de reproducibilidad (deps sueltas) y convierte "hay que saber qué instalar" en **"clona → `make setup` →
`make demo`"**. Enfoque **Cloud-híbrido** (Makefile + script + Cloud/Neon vía env), NO compose pesado (P7).

## 2. Qué cierra

- El "one command reproducible" (rec. industria 2026) en su versión honesta (Cloud-híbrida, sin auto-hospedar
  el stack pesado de Langfuse). Consolida A (front) + B1 (Langfuse) + C1 (Neon) + D (evals) en **una experiencia**.

## 3. Criterios de completitud (verificables)

1. **`Makefile`** en la raíz con targets: `setup` · `run` · `demo` · `evals` · `test` (+ `help`).
2. **`make setup`** — crea/usa el venv e instala **desde `pyproject`**: `pip install -e ".[obs,evals]"` +
   `psycopg[binary]`. Tras esto, un entorno limpio corre todo (cierra el gap de deps piecemeal).
3. **`make demo`** — un script (`backend/demo_run.py`) que procesa los **4 escenarios por el pipeline real**
   (intake → `orquestar_fnol` → `ReplayStore.save` → `CasoRepository.save`) y al final **imprime un resumen con
   links**: estado/dictamen de cada caso · URL del proyecto Langfuse (si configurado) · dónde ver el dashboard
   (`/casos`, `/panel`) · persistencia (Neon vs in-memory) · el comando `make evals`.
4. **Tiers (degrada con gracia, P7):** con `ANTHROPIC_API_KEY` real → **agentes reales**; sin key → **presets
   determinísticos** (sin crash). Langfuse/Neon se activan por env (`LANGFUSE_*`, `DATABASE_URL`+`PERSISTENCE`);
   si faltan, floor JSON + in-memory. El resumen **dice qué tier corrió** (honesto, no finge).
5. **`make evals`** — `pytest -m agentic` (la dimensión LLM-juez; cuesta API → explícito, no en `make demo`).
6. **`make test`** — la suite base (`pytest`, 173 verde, sin API/costo).
7. **`docs/DEMO.md` actualizado** — guía "clona → `make setup` → (setea keys) → `make demo` → mira Langfuse +
   dashboard + `make evals`", con la nota honesta de tiers + que Langfuse v4 ya es OTel-based (D3).
8. **Narración en vivo en consola (Exp 1+2 del panel):** con key, `make demo` **imprime cada paso del pipeline
   mientras corre** — C2 extractor (campos + confianza + tokens) → C3 verifier → **C5 motor con la cláusula
   citada** → C6 fraude → estado. La "interacción de los agentes" se ve **sin abrir Langfuse** (Langfuse = la
   vista profunda).
   **Fuente de datos (review 🔴/🟠):** la narración se arma de DOS fuentes — el `tracer.emit(...)` da el esqueleto
   de pasos + `confianza` (C3) + tokens (que el orquestador YA emite), y el **`Caso`** da lo que el tracer NO
   emite: los **valores de campos** (`caso.extraccion.campos`) y la **cláusula** (`caso.dictamen.clausula`, ya que
   c5 solo emite el resultado). NO reimplementa dominio; solo LEE el Caso ya resuelto.
   **P5 (obligatorio):** imprime **solo los 4 campos estructurados** (numero_poliza/fecha/tipo/monto), **NUNCA
   `texto_crudo`** (el aviso, marcado PII). Cada `valor` pasa por `redact_pii_spans_es_co` **antes** de imprimir
   (defensa-en-profundidad: `valor` es string libre del LLM). **Formato** (una línea por paso, ver ejemplo en §5).
9. **Cifras estrella en el resumen (Exp 1 + Shark):** el resumen final destaca **costo/caso** (`costo_usd`) y
   **% escalado** (`pct_escalado`, la frecuencia de intervención) — las dos métricas que el panel exige de un
   operator 2026. Ya las calcula C11 (`_calcular_metricas`); el demo las sube al resumen, no las esconde.
10. **Hilo narrativo P1+P2 + moat honesto en `docs/DEMO.md` (Exp 3 + Shark):** la guía se cuenta sobre los
    invariantes — "**no cierra solo** (P1, humano firma con `aprobado_por`) · **cita la cláusula** (P2, motor
    R1-R5) · **escala en vez de inventar** (P4)". Cierra con **una línea de framing honesto (P7):** Perito es
    una **implementación de referencia** de la capa de confianza (reglas deterministas + HITL auditable), **NO**
    un producto en producción con miles de corridas — el moat es el motor + HITL + auditoría citada, no el LLM.
11. **Advertencia de costo (P7, review 🟡):** `docs/DEMO.md` y el arranque de `make demo` **avisan** que con
    `ANTHROPIC_API_KEY` real la demo ejecuta agentes Claude (C2/C3) y **cuesta** (~USD 0.02 los 4 casos); **sin
    key → presets determinísticos, costo cero**. Nada de "demo = gratis" implícito.

## 4. Invariantes / NFR

- **No lógica de dominio nueva:** `demo_run.py` REUSA el pipeline existente (intake/orquestador/motor/HITL);
  no reimplementa nada. Cero cambios a `rules/`/`orchestrator/`.
- **P5:** el resumen/DEMO muestran conteos/links/estados — **cero PII cruda**. El schema de extracción son 4
  campos estructurados (numero_poliza/fecha/tipo/monto); los nombres/cédulas viven solo en `texto_crudo`, que
  **nunca se imprime**. Aun así cada `valor` de campo se redacta antes de imprimir/trazar.
  **Redacción PII = FAIL-CLOSED (review 🟠):** si el redactor falla, **no se imprime/traza el valor crudo** (se
  omite/redacta, nunca se suelta). El **fail-open** aplica SOLO a la ENTREGA (Langfuse/Neon caídos → la demo
  sigue), **jamás** a soltar PII sin redactar.
- **P7 (honestidad):** los tiers son explícitos; el resumen dice qué corrió de verdad; NO se promete "un comando
  levanta Langfuse/Neon" (son SaaS con keys). "OTel" se menciona como ya-alineado (Langfuse v4), no como feature.
- **Sin deps nuevas** (Makefile + `demo_run.py` sobre módulos existentes). Sin Docker.

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`Makefile`** (raíz) — targets finos; `setup` usa el venv (`/tmp/perito-v` o `.venv`), `pip install -e ".[obs,evals]"`.
- **`backend/demo_run.py`** — por cada escenario: siembra póliza(s) → `intake_crear_caso` → `orquestar_fnol`
  (real o presets según key) → `get_replay_store().save` (→ Langfuse si on) → `get_caso_repository().save`
  (→ Neon si `PERSISTENCE=postgres`). **Fail-open solo en la ENTREGA** (Langfuse/Neon caídos no rompen la demo);
  la **redacción de PII es fail-closed** (§4): si el redactor falla, se omite el valor, nunca se suelta crudo.
  - **Narración en vivo (§3.8):** por caso, combina el `tracer` (pasos + confianza C3 + tokens) con el `Caso`
    resuelto (valores de `extraccion.campos` + `dictamen.clausula` — que el tracer NO emite). **Redacta cada
    `valor` con `redact_pii_spans_es_co` antes de imprimir; nunca imprime `texto_crudo`.** Formato: una línea por
    paso, ej.:
    ```
    🔵 C2 extractor (Haiku)  → POL-DEMO-FELIZ · AUTO_COLISION · $5.000.000  · conf 0.9 · 340 tok
    🔵 C3 verifier           → consistente (conf 0.95)
    ⚙️  C5 motor R1-R5        → CUBIERTO  (regla R2 · cláusula COB-1, Sec. 3.2)
    ✅ estado: LISTO_PARA_APROBAR
    ```
  - **Resumen final (§3.9):** llama una función **pública** de métricas de C11 (exponer `calcular_metricas`, no
    el `_privado` — review 🟡) sobre los casos procesados → **costo/caso** + **% escalado** destacados + links
    (URL Langfuse vía host/SDK, `/casos`+`/panel`, persistencia Neon/memory).
- **`docs/DEMO.md`** — reescribir como la guía del showcase (ya existe de A): hilo P1+P2+P4 (§3.10) + la línea
  de moat honesto (P7).
- **Reuso:** `intake/c1`, `orchestrator/c7`, `observability/replay`+`langfuse_sink`, `dashboard/store`,
  `dashboard/c11` (`_calcular_metricas`), `demo/scenarios` (avisos de los 4 escenarios). Ningún módulo de dominio nuevo.

## 6. Fuera de alcance

- **Self-host de Langfuse** (compose pesado ClickHouse/Redis/MinIO) — descartado (P7). **OTel explícito** (B2) —
  diferido (Langfuse v4 ya es OTel-based). **Dockerfile/compose** — opcional futuro (no ahora). C2 pgvector, E1.

## 7. Cómo se validará el Bolt

- **`make test`** → 173 verde (sin API). **`make setup`** en un venv limpio → instala sin errores.
- **`make demo` sin keys** → corre presets, imprime resumen, NO rompe (tier demo).
- **`make demo` con keys** (manual, usuario) → 4 escenarios reales → **narración en vivo de los pasos** +
  **trazas visibles en Langfuse** + **casos en Neon** + resumen con **costo/caso + % escalado** + links. Se pega
  la salida como evidencia (como los smokes de B1/C1).
- **`make evals`** → `pytest -m agentic` pasa (con key). **`code-reviewer`** (no dominio, passive, P5/P7, tiers) → **PR**.
- **Cobertura de estratos:** la salida enseña los 4 comportamientos — feliz + **los 3 feos** (fraude que sugiere,
  cobertura NO_CUBIERTO con cláusula, póliza no-encontrada que escala). El panel de expertos lo marcó como el
  mayor activo del demo: no solo el happy path.

## 8. Decisiones (resueltas con el usuario)

- **D1 — Enfoque:** ✅ **Cloud-híbrido** (Makefile + `demo_run.py` + Cloud/Neon vía env). No compose pesado.
- **D2 — Evals en `make demo`:** ✅ **NO** — van en `make evals` aparte (cuestan API; `make demo` rápido/repetible).
- **D3 — OTel (B2):** ✅ **Diferir** — Langfuse v4 ya es OTel-based; se menciona, no se implementa.
- **D4 — Guía:** ✅ **Sí** — actualizar `docs/DEMO.md` como el showcase guiado.
- **D5 — Estrella con key:** ✅ el tier **con key (agentes reales por `orquestar_fnol`) es la estrella**; los
  presets determinísticos quedan solo como *fallback* sin key.

## 9. Panel de expertos incorporado (research 2026-07-09 + jurado Shark Tank)

Consultadas 4 voces (3 demo + 1 seed investor) contra fuentes 2026. Coinciden: la arquitectura de Perito **ya
es** lo que 2026 pide de un demo de claims agéntico; el trabajo es **mostrar lo correcto + ser honesto (P7)**.
Aportes plegados como criterios verificables (§3.8-3.10):

- 🎤 **Demo/operators (icmd, AWS):** bucle con verificación + "flight recorder" + recibos/undo + **costo por
  completación y frecuencia de intervención en pantalla** → §3.8 (narración), §3.9 (cifras). Perito ya tiene el
  bucle (C2→C3→motor), el flight recorder (Langfuse) y los recibos (replay); faltaba **subir las cifras**.
- 🔬 **Reliability/evals (Braintrust, LangChain, Arize):** conectar traza↔eval; **no solo el happy path** →
  §3.8 + §7 (los 3 estratos feos). Perito ya tiene los 4 estratos + faithfulness 1.0.
- 🏛️ **Claims regulados (Neota, Assured, Zingtree):** human-centric es el estándar; cobertura/escala/disclosures
  en lógica fija; cada dictamen cita cláusula; fraude sugiere-no-decide → §3.10 (hilo P1+P2+P4). Es el mayor activo.
- 🦈 **Seed investor (Causo, Snowflake VL):** "producción, no demo magic"; unit economics (costo/tarea); moat
  **más allá del modelo** → §3.9 (costo/caso) + §3.10 (línea de moat honesto: reglas deterministas + HITL
  auditable, NO el LLM; referencia, NO producto en producción). Frena la sobreventa (alineado con P7).

Fuentes: icmd *Agentic Product Stack 2026* · Causo *Raising seed for AI agent startup 2026* · Braintrust
*Agent observability 2026* · LangChain *State of Agent Engineering* · Neota *Human-Centric AI 2026* · Assured ·
Zingtree *AI Guardrails 2026* · AWS *Operationalizing Agentic AI (Stakeholder's Guide)* · Snowflake *Startup 2026*.

## 10. Ajustes del review incorporados (code-reviewer)

Validación a dos ojos previa al Bolt. Hallazgos plegados al spec:

- 🔴 **Cláusula no está en el tracer (P2):** c5 solo emite el resultado. → `demo_run.py` lee `caso.dictamen.clausula`
  del Caso resuelto, no del tracer (§3.8, §5). Verificado en `c7.py:178`.
- 🟠 **PII en valores de campo (P5):** la narración imprime valores del LLM (string libre). → solo los 4 campos
  estructurados, `texto_crudo` nunca, y **redactar cada `valor`** antes de imprimir (§3.8, §4). *Matiz verificado:*
  el schema NO extrae nombre/cédula (viven en `texto_crudo`); la redacción es defensa-en-profundidad.
- 🟠 **Fail-open vs PII (P5):** el fail-open aplica solo a la ENTREGA; la **redacción es fail-closed** (§4, §5).
- 🟠 **Desajuste "solo formatea el tracer":** el tracer no emite valores/cláusula. → §3.8/§5 explicitan que se
  LEE el Caso además del tracer (sin reimplementar dominio). *Matiz:* `confianza` (C3) SÍ está en el tracer (`c7.py:139`).
- 🟡 **Formato de narración indefinido:** → ejemplo concreto de formato en §5.
- 🟡 **Acople a `_calcular_metricas` (privada):** → el Bolt expone `calcular_metricas` pública en C11 (§3.9, §5).
- 🟡 **Honestidad de costo (P7):** → §3.11 + `docs/DEMO.md` avisan del costo con key (~USD 0.02) vs. gratis sin key.
- ✅ **Confirmados sin cambio:** P1 (nunca terminal), P4 (`max_rondas=1` acota el gasto), passive/no-dominio, sin deps nuevas.
