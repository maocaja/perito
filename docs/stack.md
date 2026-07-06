# Stack Técnico — Perito

> Decisiones de herramientas confirmadas (jul 2026). Verificado contra el ecosistema actual. Alimenta el Segmento 9 del PRD y la Estación 3 (arquitectura).

## Observabilidad (prioridad del proyecto)
- **Langfuse (self-hosted, open-source, MIT)** — tracing multi-turno + versionado de prompts + evals (LLM-as-judge / feedback / custom). Se controla, es gratis, y montar la infra propia es señal de ingeniería.
- **Convenciones OpenTelemetry GenAI** (`gen_ai.*`: modelo, tokens, finish reason) para trazas portables entre backends. ⚠️ En estado "Development/experimental" a may-2026 — suma pero no es estándar estable.
- Alternativa de cero-setup: **LangSmith** (pairing nativo con LangGraph, pero propietario/de pago). Se prefirió Langfuse por costo/control.

## Evals
- **DeepEval** para métricas agénticas (tool correctness, task completion).
- **pytest + assertions** para lo determinista (accuracy de extracción vs. ground truth, coverage-match, precisión/recall de fraude vs. etiqueta Kaggle). La mayoría de evals de Perito son de código, no LLM-as-judge.

## Orquestación
- **LangGraph** (grafo) — estándar de industria, grafo visual, señal de CV.
- **+ Capa de terminación acotada OBLIGATORIA propia** (contador de rondas + presupuesto de tokens + detección de ciclos), porque LangGraph es el framework más propenso a loops infinitos (33.8% en el estudio de 2026). Narrativa: "el estándar + el control que le falta". Refuerza P4.

## Agente y modelos
- **Tools con contrato tipado (Pydantic) + validación de output**: `extractor`, `policy_lookup`, `coverage_rules`, `fraud_signals`.
- **Claude por capas** (Anthropic API): **Haiku 4.5** (extracción masiva barata) / **Sonnet 5** (grueso) / **Opus 4.8** (cobertura ambigua). Control de costo desde el diseño.
- **Extracción multimodal:** visión de Claude directa sobre PDF/foto (sin doc-AI aparte en el MVP).
- **Motor de reglas de cobertura:** Python determinístico (R1-R5). NO el LLM (P2).

## Datos e infraestructura
- **Backend/API:** FastAPI (Python).
- **Base + RAG:** Postgres + pgvector (RAG sobre pólizas). Una sola base.
- **Frontend:** panel mínimo (Next.js o React simple) — bandeja del analista + panel de trazas/evals.
- **Datos sintéticos:** Claude generando avisos FNOL es-CO (COP, SOAT, aseguradoras locales) sobre backbone tabular público de Kaggle (etiqueta de fraude = ground truth).

## Restricción
- 5 días × 10h (~50h). MVP = espinazo agéntico demostrable (ver Segmento 8 MoSCoW).
