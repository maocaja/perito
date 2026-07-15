# Perito — AI Claims-Processing System (Hardcore AI capstone)

**Qué es:** Sistema de IA para procesamiento de siniestros de seguros (FNOL / SOAT, Colombia). Extrae información de documentos/fotos, determina cobertura con reglas determinísticas + LLM, y presenta casos a un operador humano. Producto del Demo Day del programa **Hardcore AI 30x by 30X (Agentic Engineering Intensive, 2026)**.
**Naturaleza:** Proyecto personal / capstone del curso (no empleo). Grado de ingeniería: producción-grade.
**Dominio:** Seguros (regulado) — alto valor para AXA (rol de IA en seguros) y Caseware (nice-to-have: dominios regulados/compliance, workflows financieros).

> Última actualización verificada contra el repo: 2026-07-14 (rama `main`).

---

## 1) Stack técnico (lo que corre en producción)

**Backend / núcleo**
- Python 3.12+ · FastAPI + Uvicorn (app factory en `main.py`)
- Contratos: **Pydantic v2 (strict)** + pydantic-settings — toda la capa `contracts/` tipada (columna vertebral)
- Persistencia: **SQLAlchemy 2.0 Core + psycopg v3 → Postgres** (dialecto psycopg3 forzado)
- RAG: **pgvector declarado** (esquema en `rag/schema.py`) — ⚠️ embeddings aún no conectados (ver §4)

**Agente y modelos**
- Anthropic SDK con **Claude por capas para control de costo desde el diseño**: Haiku 4.5 (extracción) → Sonnet 5 (grueso) → Opus 4.8 (cobertura ambigua). En `llm/` (`extractor.py`, `verifier.py`, `summary.py`).
- Orquestación: **LangGraph + capa propia de terminación acotada** (contador de rondas + presupuesto de tokens + detección de ciclos) en `orchestrator/c7.py`.
  - 🎣 **Hook de narrativa:** "el estándar de industria (LangGraph) + el cap de loops que le falta (LangGraph loopea ~33.8%)". Diferenciador real de ingeniería.
- **Motor de reglas determinístico (R1–R5)** en `rules/motor_r1_r5.py` — el LLM NO decide cobertura (invariante P2). Governance/safety de verdad.
- **Match de póliza determinístico** (`policy/lookup.py`): SQL + `difflib.SequenceMatcher`, cero LLM (P2-adjacent). Devuelve candidatas, nunca fuerza match (P4).
- **Extracción multimodal:** visión de Claude directa sobre PDF/foto (sin doc-AI aparte).

**Frontend**
- Server-rendered con **Jinja2 + HTMX** (ADR-001, mismo origen, sin SPA). Templates en `dashboard/templates/`. Ruta única: `/` redirige a `/workbench` (la estación de decisión; el board legacy `/casos` se retiró).
- ⚠️ `stack.md` línea 27 aún dice "Next.js o React" (desactualizado) — corregir antes de la demo.

**Observabilidad y evals**
- **Langfuse** (self-hosted, opcional) — tracing + versionado de prompts, `observability/langfuse_sink.py`. Convenciones **OpenTelemetry GenAI** (`gen_ai.*`).
- **pytest** (determinista) + **Hypothesis** (property-based) + **DeepEval** (Claude-as-judge, solo `pytest -m agentic`). **~632 tests en 65 archivos**.

**Datos e intake**
- Faker (es_CO) + Claude → avisos FNOL sintéticos (COP, SOAT) sobre backbone Kaggle (etiqueta de fraude = ground truth). En `synthetic/`.
- **Intake por correo real vía IMAP/SMTP** (stdlib, ya en `main`) — `intake/mailbox.py` + `poller.py`, hilo daemon self-gated por `DEMO_LIVE` y cableado en `main.py`.
  - 🎣 **Wow del Demo Day:** mandas un correo → aparece el caso en la bandeja, en vivo.

---

## 2) Tooling de Claude Code / AI-DLC (la historia de agentic engineering)

Tan importante como el producto — es lo que un empleador "AI-first" (Caseware) valora explícitamente.
- **Reglas modulares** (`.claude/rules/`): `hitl.md`, `coverage-determinism.md`, `termination.md`, etc. → invariantes **P1–P7** como guardrails del propio agente de desarrollo.
- **Hooks** (`.claude/settings.json`): `protect-critical-paths.sh` (confirma al tocar `rules/` y `orchestrator/`) + `post-edit-lint.sh` (ruff auto). *(Nota real: el gate fuerte de esas rutas es revisión manual, no un pre-commit que bloquee.)*
- **Subagentes** (`.claude/agents/`): code-reviewer (Haiku), test-writer (Sonnet).
- **Skills propias** (`.claude/skills/`): `/check-hitl`, `/review-pr`, `/front-modernize`.
- **MCPs** (`.mcp.json`): context7 (docs al día), sequential-thinking, playwright.
- **Patrones de costo:** `opusplan` (Opus planifica → Sonnet ejecuta), `semantic-review.sh` headless con `--max-budget-usd`.
- **AI-DLC** (`specs/aidlc/`): framework Inception → Construction con verificación real contra git/tests.

---

## 3) Invariantes / guardrails (P1–P7)
Diseño agéntico con guardrails explícitos: HITL (P1), cobertura determinística (P2), terminación acotada (P4), minimización de PII (P5), el fraude solo sugiere nunca decide (P6). En `security/redaction.py`, `rules/*.md`.

---

## 4) Estado del curso: dominado vs. por profundizar

**✅ Dominado (aplicado de verdad)**
- Claude Code como entorno de ingeniería (rules, hooks, skills, subagentes, MCPs, agent teams).
- Diseño agéntico con guardrails (HITL P1, cobertura determinística P2, terminación acotada P4).
- Control de costo por capas de modelo (Haiku/Sonnet/Opus).
- Contratos tipados como columna vertebral (Pydantic strict).
- Evals por estrato (pytest + Hypothesis + DeepEval), ~632 tests.
- Extracción multimodal (visión de Claude sobre PDF/foto).
- Intake por correo real (IMAP/SMTP) con idempotencia y fail-safe.

**⚠️ Por profundizar (gaps, ordenados por valor para el job search)**
1. **RAG real (pgvector)** — hoy es esquema declarado + match por similitud de strings (`difflib`), sin embeddings conectados. **Gap técnico #1** — y lo que AXA y Caseware más miran. Prioridad: chunking + embeddings + retrieval evaluado sobre las pólizas.
2. **Langfuse / observabilidad en vivo** — integrado pero opcional; encenderlo y dejarlo visible suma en demo y en CV.
3. **LangGraph a fondo** — checkpointing, human-in-the-loop nativo, streaming.
4. **Evals agénticos** (DeepEval / Claude-as-judge) — fuera del CI por costo; cuándo un juez LLM es confiable vs. métrica determinista.
5. **Deploy / infra real** — no hay Docker ni CI de despliegue activo. Contenerizar + deploy si quiere ser usable post-demo. (Coincide con el gap AWS/IaC del plan Caseware.)
6. **Seguridad PII + prompt injection** — `redaction.py` existe; en seguros escala en importancia (redacción robusta + defensa de inyección en el intake por correo).

---

## 5) Cómo usarlo en el job search

**Relevancia por objetivo:**
- **AXA (Ingeniero Sr. de IA):** match casi perfecto — es un agente de IA de seguros que hace análisis de documentos y determina cobertura. Es TU proyecto estrella para esa aplicación.
- **Caseware (AI Platform):** cierra gran parte del gap de "operar IA en producción" (agentes, evals, observabilidad, guardrails, governance). Lo que falta es portarlo al stack AWS-nativo (Bedrock/OpenSearch/IaC) → ver plan.
- **General:** segundo proyecto insignia de IA junto a Inbest; refuerza la narrativa "construyo productos de IA end-to-end".

**Bullets de CV candidatos (IA-forward):**
- Construí un sistema de IA para procesamiento de siniestros de seguros: agentes (Anthropic SDK + LangGraph) con capa propia de terminación acotada (rondas + presupuesto de tokens + detección de ciclos), motor de reglas determinístico para cobertura, y extracción multimodal (visión de Claude sobre PDF/foto).
- Control de costo por diseño: enrutamiento por capas de modelo (Haiku → Sonnet → Opus) según dificultad de la tarea.
- Observabilidad y evaluación de LLM: Langfuse (tracing + prompt versioning, OpenTelemetry GenAI) y evals por estrato (pytest + Hypothesis property-based + DeepEval Claude-as-judge, ~632 tests).
- Ingeniería agéntica (AI-DLC) con Claude Code: reglas/guardrails modulares (invariantes P1–P7), hooks, subagentes, skills y MCPs para gobernar el propio proceso de desarrollo.

**Ángulos de entrevista (fuertes):**
- "¿Cómo evitas que un agente cicle infinitamente?" → tu capa de terminación acotada vs. el 33.8% de LangGraph.
- "¿Cómo garantizas decisiones correctas/auditables con LLMs?" → motor de reglas determinístico (el LLM no decide cobertura) + audit trail + evals.
- "¿Cómo controlas costo en producción?" → capas de modelo por dificultad.
- "¿Cómo evalúas un sistema agéntico?" → determinista (pytest/Hypothesis) + LLM-judge (DeepEval), y cuándo confiar en cada uno.
