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

## Estructura

```
docs/       — artefactos de producto del curso (PVB, luego PRD)
research/   — deep research de validación y de crítica (Estación 1)
```

## Estado

Estación 1 (Hardcore AI C3): definiendo el Product Vision Board a partir de la investigación.
