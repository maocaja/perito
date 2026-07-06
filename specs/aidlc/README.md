# specs/aidlc — Artefactos de Inception + AJIT (AI-DLC) de Perito

> **Qué es esto**: la cosecha de la fase **Inception** + la **Arquitectura Just-in-Time (AJIT)** de AI-DLC (AWS Labs v0.1.8) para Perito, ejecutada en la rama `spec/aidlc-inception` (Estación 4). Son los **entregables de diseño** (el "qué" y el "porqué"), no la maquinaria del framework.
> **Encuadre**: proyecto de **portafolio honesto** (P7) — nada se despliega.
> **Cobertura**: back + front definidos. 21 historias (18 backend/infra + 3 UI demo-grade). Arquitectura C4 + NFR + 3 ADRs.

## Source-of-truth (aguas arriba de esta carpeta)
- **[`../prd.md`](../prd.md)** — Product Requirements Document (Estación 2). **Es el input**; `specs/aidlc/` es aguas abajo de él.
- **[`../../AGENTS.md`](../../AGENTS.md)** — contexto de negocio/arquitectura y principios no negociables.
- **[`../../.claude/rules/`](../../.claude/rules/)** — reglas duras P1-P7: [`hitl.md`](../../.claude/rules/hitl.md) (P1), [`coverage-determinism.md`](../../.claude/rules/coverage-determinism.md) (P2), [`termination.md`](../../.claude/rules/termination.md) (P4), [`testing.md`](../../.claude/rules/testing.md).

> **Nota de rutas**: donde estos documentos citan **`PRD.md`** (la copia uppercase que usó el framework en la rama de trabajo), en `main` léase **[`specs/prd.md`](../prd.md)**. Es la misma fuente; no se reescribió cada doc para evitar deriva vs. lo aprobado.

## Índice
| Artefacto | Contenido |
|---|---|
| [`requirements.md`](requirements.md) | Requisitos funcionales (RF) + no funcionales (RNF) + matriz de trazabilidad a P1-P7 + compliance de extensiones. |
| [`user-stories/stories.md`](user-stories/stories.md) | **21 historias** INVEST + Gherkin (14 fail-closed) — 18 backend/infra + **3 UI** (H-19/20/21) + matriz historia↔RF/RNF↔P↔estrato. |
| [`user-stories/personas.md`](user-stories/personas.md) | 3 personas activas + Ajustador (contexto). |
| [`application-design/application-design.md`](application-design/application-design.md) | Consolidado del diseño de aplicación. |
| [`application-design/components.md`](application-design/components.md) | 10 componentes (1:1 con M1-M10) + **C11 dashboard (front)** + infra-test. |
| [`application-design/component-methods.md`](application-design/component-methods.md) | Firmas de método — **P1/P2/P4 codificados en el contrato**. |
| [`application-design/services.md`](application-design/services.md) | 5 servicios + patrones de orquestación + cliente UI (dashboard). |
| [`application-design/component-dependency.md`](application-design/component-dependency.md) | **Grafo — prueba de P2 (cero aristas LLM→coverage_rules)** + prueba P1/P2 del front (dashboard no toca coverage_rules ni terminal). |
| [`units/unit-of-work.md`](units/unit-of-work.md) | 5 unidades de construcción + organización de código `backend/app/*`. |
| [`units/unit-of-work-dependency.md`](units/unit-of-work-dependency.md) | Grafo DAG de unidades + dependencia de comportamiento U2→U4. |
| [`units/unit-of-work-story-map.md`](units/unit-of-work-story-map.md) | Historia → unidad (21/21). |
| [`execution-plan.md`](execution-plan.md) | Roadmap de fases (EXECUTE/SKIP) + success criteria + **quality gates**. |
| **[`architecture/`](architecture/) (AJIT)** | **Arquitectura Just-in-Time** — puente Inception→Construction. |
| [`architecture/architecture-ajit.md`](architecture/architecture-ajit.md) | C4 Contexto + Contenedores (aquí aterriza el Frontend) + Matriz NFR + Riesgos/SPOF. |
| [`architecture/adr-001-frontend-stack.md`](architecture/adr-001-frontend-stack.md) | **ADR-001: Frontend = FastAPI+HTMX** (bajo lock-in; migración a React sin tocar dominio). |
| [`architecture/adr-002-monolito-modular.md`](architecture/adr-002-monolito-modular.md) | ADR-002: Monolito modular (1 despliegue). |
| [`architecture/adr-003-observabilidad.md`](architecture/adr-003-observabilidad.md) | ADR-003: Langfuse target + floor JSON fallback. |

## Decisiones clave (registro condensado)
| Decisión | Elección | Por qué |
|---|---|---|
| Alcance | **Must completo (M1-M10)** | El "núcleo irrenunciable" es piso de degradación, no objetivo; MVP real = 13 Must. |
| Profundidad | **Comprehensive** con trazabilidad a P1-P7 | La diferenciación de Perito es auditabilidad. |
| User Stories | **Gherkin** | Los Given/When/Then se reutilizan como escenarios de eval por estrato. |
| Extensiones | **Security (blocking)** · **PBT (parcial: PBT-02/03/07/08/09)** | PII/Habeas Data; motor R1-R5 = función pura + contratos = round-trips. |
| Componentes | **1:1 con M1-M10** | Mantiene `coverage_rules` aislado (sostiene P2). |
| Motor de cobertura | **Librería pura, invocada por el orquestador, NUNCA tool del LLM** | Expresión arquitectónica de P2 (coverage-determinism.md). |
| Enforcement invariantes | **Distribuido con dueños únicos** (orquestador=P4, hitl=P1, motor=P2, contratos=P3) | `termination.md`: el orquestador es dueño de P4. |
| Unidades | **Monolito modular, 5 unidades** (espejo del plan de 5 días) | "Construible por una persona"; Infra Design = SKIP. |
| **Frontend (validado con framework)** | **UI = capacidad de persona (historias) + componente dashboard + contenedor C4**, NO historias de build. Stack **FastAPI+HTMX** (ADR-001) | AI-DLC no escribe historias de front técnicas; el front es demo-grade (vitrina de P1/auditabilidad, no la tesis). |

## Diferidos declarados (honestidad de alcance — P7)
- **SOAT**: override contemplado en el motor (RF-14, forward-compat); **sin flujo ni estrato de eval propio** (RF-27.1).
- **`ESPERANDO_INFO` / cola de SLA**: Should — no modelado; el invariante "no adivinar para cerrar" ya lo cubren H-05/H-06.
- **`test_gate_regla` (versionado de reglas con test-gate)**: Could — **firma forward-compat, NO build** en esta Inception.
- **Infrastructure Design**: SKIP — un diseño de infra de producción **contradiría P7** ("demo como producción"). El `docker-compose` local (postgres/pgvector + langfuse) es entregable de Code Generation (entorno de dev), no infra de prod.
- **Auth real**: Won't — selector de rol stub.

## Qué NO está aquí (se quedó en la rama de trabajo, no se mergea a main)
El andamiaje de proceso (`aidlc-docs/audit.md`, `aidlc-state.md`, `plans/` con Q&A, preguntas de verificación) y la maquinaria del framework (`.aidlc/`, `.aidlc-rule-details/`, el `CLAUDE.md` del framework, `START-HERE.md`) **no cruzan a `main`**. El rastro de *cómo* se decidió está condensado en la tabla de decisiones de arriba.

## Estado
Fase **Inception COMPLETA + AJIT COMPLETO** (C4 + NFR + 3 ADRs). Back y front definidos y trazados. Lo siguiente (fase **Construction**: Functional Design → NFR → Code Generation → Build & Test, por unidad U1→U5) se aborda partiendo de estos artefactos.
