# Tech Stack Decisions — U1 · Fundaciones & Contratos

> **Regla**: confirmar el stack desde los ADRs (AJIT) y RES-04, **no reinventar**. Toda dependencia **no justificada en Inception** se marca 🆕 para tu confirmación.

## Confirmado desde Inception (sin decisión nueva)

| Componente | Elección | Fuente en Inception |
|---|---|---|
| Lenguaje | **Python** | RES-04, PRD stack |
| Contratos / validación | **Pydantic** | H-17, RNF-13, RES-04 |
| Property-based testing | **Hypothesis** | RNF-27, PBT-09 (extensión PBT) |
| Testing base | **pytest** | `rules/testing.md`, RES-04 |
| DB + vector store | **PostgreSQL + pgvector** (un motor) | RES-04, ADR-002 (monolito), PRD §9 (M10) |
| Cifrado en reposo/tránsito (local) | Config de Postgres (TLS + at-rest) | RNF-15, SECURITY-01 |
| Scaffolding API | **FastAPI** | RES-04 (mínimo en U1; su superficie real es U4) |
| Entorno de dev | **docker-compose** (postgres/pgvector + langfuse) | execution-plan (entregable de Code Gen), ADR-003 |
| Observabilidad | **Langfuse/OTel** target · floor JSON | ADR-003 (poca superficie en U1) |

## 🆕 Dependencias nuevas — requieren tu confirmación

> Inception nombra la **capacidad** pero no la **herramienta**. Las marco en vez de asumirlas en silencio.

| # | Necesidad | Decisión (aprobada 2026-07-06) | Notas |
|---|---|---|---|
| 🆕 1 | **Generación de datos sintéticos es-CO** (H-16/RF-30) | **CONFIRMADO: Faker (locale `es_CO`)** | Estándar, mantenido, sin equivalente en el stack; es solo realismo superficial (nombres/fechas/direcciones). La coherencia de dominio + inyección de fraude (RULE-GEN-02) es lógica propia encima. Install real se veta (o no) en Code Generation. |
| 🆕 2 | **Embeddings para el RAG de pólizas** (M10/H-04) | **DIRECCIÓN FIJADA: embedding LOCAL** (sentence-transformers, multilingüe/español). **Modelo concreto diferido a U2/U3** (se elige con requisitos de recall reales en mano). | Razones: mantiene el texto de cláusulas **dentro de la caja** (P5/minimización + monolito local ADR-002), sin costo/red, offline para la demo. Nota: Anthropic **no** ofrece embeddings → "mismo proveedor que Claude" no es argumento; local es el default pragmático. **U1 solo define la estructura de indexación (RULE-RAG-01), no embedda nada real todavía.** |
| — | Acceso a Postgres | `psycopg`/driver async (estándar, implícito) | Confirmar driver en Code Gen. |

> 🔗 **Acoplamiento a anotar (para NFR Design / esquema)**: la **dimensión del vector** de pgvector depende del modelo de embedding (384 vs 768…). Como U1 define la estructura del RAG pero el modelo se confirma en U2/U3, **la dimensión queda como parámetro** — **no se hardcodea** una dimensión ahora que pre-comprometa el modelo.

## Fuera de alcance de U1 (nombrados en Inception, pero no aquí)
- **Claude API (multimodal)** — U1 **no llama al LLM** (extracción/verificación/fraude son U2/U3). Sin dependencia de Anthropic en U1.
- **DeepEval** — métricas agénticas (tool-correctness); aplica desde U2. U1 usa pytest + Hypothesis.

## Resumen
El stack de U1 está **casi enteramente confirmado desde Inception**. Solo **2 decisiones nuevas** aparecen y quedan **marcadas** (Faker es_CO 🆕; modelo de embedding 🆕 — decisión abierta). Ninguna dependencia se introdujo en silencio.
