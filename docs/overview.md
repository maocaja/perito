# Overview del Dominio — Perito

> Análisis del dominio: tecnologías clave, tendencias y contexto del problema.
> Fuente: `research/validacion.md` y `research/critica.md` (deep research jul 2026, verificado adversarialmente). Cifras no verificadas marcadas como tal.

## El problema de dominio

El **FNOL (First Notice of Loss / aviso de siniestro)** es el primer reporte que hace un asegurado cuando ocurre un evento potencialmente cubierto. La **admisión y el triage** de ese aviso —leer el reporte, extraer los datos, verificar cobertura contra la póliza, evaluar señales de fraude y asignar al ajustador— es hoy mayormente **manual**.

Evidencia verificada del dolor:
- **STP (straight-through processing) en P&C por debajo del 10%**; ~60% de aseguradoras sin ningún STP (Neudesic, Aite-Novarica).
- **Solo 7% de aseguradoras han escalado IA con éxito** pese a que 67% la están probando (BCG 2025).
- La automatización reduce tiempos **de días a minutos**, pero solo en el subconjunto de siniestros simples elegibles para STP.

> ⚠️ Cifras puntuales de FNOL (ej. "4-12h → 5-15min de asignación", "8-15 horas por 100 siniestros") fueron **refutadas** en verificación por venir de blogs de vendors. No se usan como fundamento.

## Tecnologías clave (probadas en producción)

- **LLM multimodal + IDP (Intelligent Document Processing)** para clasificar y extraer datos de documentación caótica de siniestros. Probado a escala: **Shift Technology** (Azure OpenAI + AI Vision + Document Intelligence) sobre 2.6B+ pólizas/siniestros.
- **RAG sobre pólizas** para recuperar la cláusula aplicable.
- **Motor de reglas determinístico** para la decisión de cobertura (NO el LLM).
- **Orquestación de agentes** con terminación acotada, trazabilidad y human-in-the-loop.

## Por qué el problema es durable (WORKFLOW, no OUTPUT)

El valor durable **no está en la extracción cruda** (se commoditiza con cada generación de modelos multimodales, y el core ya la incorpora — ver `mercado.md`, Duck Creek Agentic FNOL). Está en la **orquestación del workflow**:
- integración con el core de la aseguradora,
- motor de reglas de cobertura,
- cumplimiento de datos personales (Habeas Data / Circular SIC 002/2024),
- trazabilidad auditable con HITL.

Esa capa sobrevive a GPT-5/Claude 5 porque es un problema de integración, reglas y cumplimiento, no de generación de texto.

## Stack técnico previsto para Perito (proyecto de práctica)

- **Backend/API:** FastAPI (Python).
- **Datos:** Postgres + pgvector (RAG sobre pólizas).
- **LLM por capas:** Haiku 4.5 (extracción masiva barata) / Sonnet 5 (grueso) / Opus 4.8 (razonamiento de cobertura ambigua) — control de costo desde el diseño.
- **Extracción documental:** visión multimodal de Claude sobre PDFs/fotos, o doc-AI dedicado si se requiere OCR robusto.
- **Orquestación:** grafo/máquina de estados con límites duros (rondas, presupuesto de tokens, detección de ciclos).
- **Observabilidad:** trazas + costo de tokens (Langfuse/LangSmith).
- **Motor de reglas de cobertura:** Python determinístico.

## Datos para la demo (sin acceso a data real)

- **Backbone tabular público** (Kaggle, insurance fraud → la etiqueta de fraude y los campos son ground truth).
- **Capa de documentos FNOL sintéticos** generada por LLM sobre cada fila, en español colombiano (COP, SOAT, aseguradoras locales).
- Alternativa con documentos reales + ground truth experto: CUAD (contratos legales), mismo patrón de agente.
