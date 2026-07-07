# Plan / Decisión de Infrastructure Design — U1 · Fundaciones & Contratos

> **Fase**: Construction · **Actividad**: 4 (Infrastructure Design) · **Regla**: `construction/infrastructure-design.md` (CONDITIONAL).

## Decisión: SKIP de infra de producción + spec mínimo de dev-env

**Producción = SKIP (N/A honesto)**. Razón: encuadre **portafolio, nada se despliega** (RES-02, P7); ya decidido en el AJIT (Infrastructure Design SKIP) y en ADR-002 (monolito local). Correr el cuestionario cloud del framework (compute/storage/messaging/networking/multi-tenancy) sería **inventar preocupaciones de producción inexistentes** — el anti-patrón "demo como producción" (P7). Por eso **no** se generan preguntas cloud huecas; se declara N/A explícito (misma disciplina que disponibilidad/escalabilidad en NFR Requirements).

**Dev-env = spec mínimo (SÍ)**. La única "infra" real de U1 es el **entorno de dev local reproducible**: `docker-compose` con postgres/pgvector + langfuse. Se deja como **contrato de entorno explícito** antes de que Code Generation lo construya (execution-plan lo asignó como entregable de Code Gen; aquí se especifica su contrato).

## Evaluación de categorías del framework (todas justificadas)
| Categoría | Estado | Rationale |
|---|---|---|
| Deployment Environment | **Dev local** | docker-compose; producción N/A (P7). |
| Compute | **N/A** | Sin Lambda/VM/contenedores de prod; corre local. |
| Storage | **Dev local** | PostgreSQL + pgvector en contenedor local. |
| Messaging | **N/A** | Sin colas (monolito, orquestación in-proc — LangGraph). |
| Networking | **N/A** | Sin LB/API-GW/VPC (mismo origen, ADR-001 HTMX). |
| Monitoring | **Dev local** | Langfuse en contenedor local (o floor JSON, ADR-003). |
| Shared Infra | **N/A** | Una unidad, un despliegue. |

## Artefactos a generar
- [ ] `construction/u1-fundaciones-contratos/infrastructure-design/infrastructure-design.md` (dev-env spec + N/A producción)
- [ ] `construction/u1-fundaciones-contratos/infrastructure-design/deployment-architecture.md` (topología del docker-compose local; deployment de producción = N/A)

> Sin preguntas: la decisión (SKIP prod + dev-env mínimo) está determinada por el encuadre P7 ya aprobado en el AJIT. Si el usuario prefiere plegar esto dentro de Code Generation, se puede — pero se deja el spec mínimo aquí para fijar el contrato de entorno.
