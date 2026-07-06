# AI-DLC Audit Trail — Perito

> Registro cronológico de solicitudes, decisiones y gates. No borrar entradas.

## 2026-07-06 — Initial User Request (raw)

Rama: `spec/aidlc-inception`. El usuario arrancó el workflow AI-DLC con el prompt de inicio (`START-HERE.md`) y confirmó ("ya estamos!"):

> Usando AI-DLC, construiremos Perito, un copiloto agéntico de admisión y triage de
> siniestros de seguros (FNOL) que extrae datos de avisos caóticos, valida cobertura
> contra la póliza con reglas determinísticas, señala fraude con evidencia y deja la
> decisión a un humano (HITL). Es un proyecto de portafolio, greenfield.
> Con base en el Product Requirements Document (PRD) @PRD.md.

## 2026-07-06 — Workspace Detection

- Verificación: sin código de aplicación (`.py/.ts/.js/...` = 0), sin build files, sin `backend/`.
- **Project Type**: Greenfield.
- **Reverse Engineering**: Skip (greenfield).
- **Next phase**: Requirements Analysis.
- Sin aprobación de usuario requerida (informativo). Procede automáticamente.

## 2026-07-06 — Requirements Analysis (Step 6 GATE)

- Rol asumido: Product Owner.
- Depth propuesto: **Comprehensive** (sistema agéntico multi-módulo, riesgo regulatorio, invariantes de seguridad P1-P7).
- Creado `aidlc-docs/inception/requirements/requirement-verification-questions.md` (incluye opt-ins de extensiones Security Baseline y Property-Based Testing + clarificaciones de alcance).
- **GATE abierto**: esperando respuestas del usuario antes de generar `requirements.md`.

## 2026-07-06 — Requirements Analysis (respuestas recibidas)

- Respuestas: **1-B · 2-A · 3-A · 4-A · Security-A · PBT-B**. Sin contradicciones ni ambigüedades (respuestas mutuamente consistentes; Q1=B alineado con "MoSCoW estricto" del riesgo #2).
- **Extension config**: Security Baseline = Enabled (blocking); Property-Based Testing = Enabled (Partial: PBT-02/03/07/08/09).
- Deferred loading: cargadas reglas completas `security-baseline.md` y `property-based-testing.md`.
- Generado `aidlc-docs/inception/requirements/requirements.md` (Comprehensive, español, con matriz de trazabilidad a P1-P7 y sección de compliance de extensiones).
- **GATE de aprobación abierto**: esperando aprobación del usuario antes de pasar a User Stories.

## 2026-07-06 — Requirements Analysis APROBADO

- El usuario revisó el doc (foco §6 trazabilidad y §7.1 security). Veredicto: fiel, no viola invariantes, N/A de security correctos para alcance no-desplegado (RES-02).
- Ajuste menor aplicado (Opción 1): **RF-27.1** — estrato SOAT diferido/placeholder para consistencia con Q1=B (MoSCoW estricto). RF-14 (override SOAT) se mantiene como forward-compat.
- **Requirements Analysis: COMPLETO.** Procede a **User Stories** (Gherkin, Q4=A).

## 2026-07-06 — User Stories (Planning — GATE de aprobación del plan)

- Assessment: `plans/user-stories-assessment.md` → Execute = Yes (High Priority: new user features, multi-persona, complex business logic).
- Plan con preguntas embebidas: `plans/story-generation-plan.md` (Q1 método de desglose, Q2 granularidad, Q3 personas).
- **GATE**: esperando respuestas + aprobación explícita del plan antes de generar `stories.md`/`personas.md`.

## 2026-07-06 — User Stories: Plan APROBADO + Generación

- Respuestas + aprobación del usuario: **"1-A · 2-A · 3-A, genera personas.md + stories.md"**. Recordatorios aprobados: (1) cero historia SOAT; (2) fail-closed reales de rechazo/escalamiento.
- Generados: `user-stories/personas.md` (P-A Analista, P-O Cumplimiento, P-D Admin/Dev + P-X Ajustador contexto) y `user-stories/stories.md` (8 Epics, **18 historias** INVEST + Gherkin).
- Cobertura: P1-P7 todos con historias; estratos de eval todos cubiertos (SOAT diferido, RF-27.1); 12 historias con escenario 🔒 fail-closed.
- **GATE de aprobación de historias abierto**.

## 2026-07-06 — User Stories APROBADO

- El usuario verificó estados contra Apéndice C del PRD (todos reales, ninguno inventado) y confirmó el manejo INVEST/dependencias.
- Dos notas menores aplicadas: (1) conteo fail-closed reconciliado a **14** historias; (2) declaración explícita de `ESPERANDO_INFO` diferido (cola de SLA = Should), por simetría con SOAT.
- **User Stories: COMPLETO.** Procede a **Workflow Planning**.

## 2026-07-06 — Workflow Planning (GATE de aprobación)

- Generado `plans/execution-plan.md`. Risk: Medium (greenfield, complejidad alta). Impacto: user-facing + structural + data + API + NFR.
- Decisiones: EXECUTE Application Design + Units Generation (Inception); EXECUTE Functional Design / NFR Requirements / NFR Design / Code Gen / Build&Test (Construction, sesión posterior); **SKIP Infrastructure Design** (nada se despliega, RES-02/P7; Won't) — coherente con N/A de SECURITY-02/06/07.
- Alcance activo de esta sesión: hasta Units Generation + Arquitectura JIT → cosecha a specs/aidlc/.
- **GATE**: esperando aprobación del plan antes de pasar a Application Design.

## 2026-07-06 — Workflow Planning APROBADO

- Usuario aprobó. Refuerzo aceptado: Infrastructure Design completo **contradiría P7** ("demo como producción") → SKIP firme, NO reincorporar como fase. Anotado que `docker-compose.yml` (postgres+pgvector+langfuse) es **entregable de Code Generation** (entorno de dev reproducible), no infra de prod.
- **Workflow Planning: COMPLETO.** Procede a **Application Design**.

## 2026-07-06 — Application Design (Planning — GATE del plan)

- Generado `plans/application-design-plan.md` con 3 decisiones: Q1 granularidad de componentes, Q2 aislamiento del motor determinístico/tools, Q3 ubicación del enforcement de invariantes P1-P4.
- **GATE**: esperando respuestas + aprobación antes de generar artefactos de diseño.

## 2026-07-06 — Application Design: Plan APROBADO + Generación

- Respuestas + aprobación: **1-A · 2-A · 3-A**. Criterio de aceptación del usuario: `coverage_rules` sin arista entrante desde LLM en el grafo (prueba de P2).
- Generados 5 artefactos en `application-design/`: `components.md` (10 comp + 1 infra, 1:1 M1-M10), `component-methods.md` (firmas), `services.md` (5 servicios), `component-dependency.md` (matriz + grafo + **verificación P2/P4/P1/P3**), `application-design.md` (consolidado).
- **P2 probado en el grafo**: 0 aristas LLM→coverage_rules; único invocador = orchestrator; lectura de cláusula desde policy_rag.
- **GATE de aprobación de diseño abierto**.

## 2026-07-06 — Application Design APROBADO

- Usuario verificó columna coverage_rules celda por celda (0 aristas LLM) y las firmas (P2 triple-bloqueado, P1 en _transicion_valida, P4 en chequear_cotas). Aprobado.
- Dos notas de endurecimiento anotadas en el consolidado §7.1 (input para Functional Design/Units): (1) `Caso.estado` inmutable salvo vía hitl (P1 inevadible); (2) `test_gate_regla` = firma forward-compat, NO build (versionado de reglas = Could, diferido).
- **Application Design: COMPLETO.** Procede a **Units Generation** (última etapa de esta Inception).

## 2026-07-06 — Units Generation (Planning — GATE del plan)

- Generado `plans/unit-of-work-plan.md`: Q1 modelo de despliegue/código, Q2 estrategia de agrupación, Q3 granularidad (nº de unidades). Recomendación 1-A/2-A/3-A (monolito modular · incremento del plan 5 días · 5 unidades).
- Inputs de endurecimiento arrastrados a Units (App Design §7.1).
- **GATE**: esperando respuestas + aprobación antes de generar artefactos de unidades.

## 2026-07-06 — Units Generation: Plan APROBADO + Generación

- Respuestas + aprobación: **1-A · 2-A · 3-A** (monolito modular · incremento 5 días · 5 unidades). Nota del usuario capturada: dependencia de comportamiento **U2→U4** (H-06 escalamiento) + H-04→H-07.
- Generados 3 artefactos: `unit-of-work.md` (5 unidades + organización de código backend/app/*), `unit-of-work-dependency.md` (matriz + grafo DAG + dependencia de comportamiento ⚑), `unit-of-work-story-map.md` (18/18 historias mapeadas).
- Cobertura verificada: 18/18 historias, P1-P7 presentes, estratos completos (SOAT diferido), 14 fail-closed. Diferidos: test_gate_regla (firma), SOAT, cola SLA.
- **GATE de aprobación de unidades abierto** — última etapa de la Inception. Tras aprobación: cosechar a `specs/aidlc/` y cerrar Estación 4.

## 2026-07-06 — Units Generation APROBADO → INCEPTION COMPLETA

- Usuario verificó DAG (U4→U2 por import; U2→U4 solo comportamiento/retorno, sin ciclo), P2 preservado a nivel de import aunque U3 agrupe cobertura+fraude (fraud/ vs rules/ separados; agents/ no importa rules/), P1 (solo hitl/ muta Caso.estado), y los 3 diferidos declarados. Aprobado.
- **FASE INCEPTION COMPLETA.** Pendiente: proponer y (tras aprobación) ejecutar cosecha a `specs/aidlc/`.

## 2026-07-06 — Validación con framework + adición de FRONTEND (post-cosecha)

- El usuario preguntó si las US cubrían el front. Validación contra fuente: AWS AI-DLC blogs + repo `hardcoreIA` (`c3/Estación 4/`) + proyecto de ejemplo EntreVista AI.
- **Hallazgo del framework**: AI-DLC NO escribe "historias de front" técnicas. El front se define en 3 momentos: (1) User Stories = capacidades de pantalla centradas en persona; (2) Application Design = componente/servicio "dashboard" + stack; (3) AJIT/C4 = contenedor "Frontend". Prueba: EntreVista tiene EPIC-04 "Dashboard & HITL" (historias de persona) y el "React" aparece solo en Application Design (SVC-07).
- **Framing acordado con el usuario**: Perito = backend/agéntico-pesado + front delgado pero crítico para la demo (vitrina de P1/auditabilidad). Front demo-grade (Must = bandeja HITL; tablero rico = Should; auth real = Won't).
- **Añadido (orden de dependencia: historias→diseño→unidades)**:
  - 3 historias UI centradas en persona: **H-19** (bandeja ver/filtrar), **H-20** (detalle con evidencia renderizada), **H-21** (panel cumplimiento). Total 21 historias.
  - Componente **C11 `dashboard`** en Application Design (stack propuesto: FastAPI + templates/HTMX, se formaliza en ADR del AJIT). Regla dura: no decide cobertura ni alcanza terminal.
  - Asignación a unidades: H-19/H-20 → U4; H-21 → U5. Dir `backend/app/dashboard/`.
- **Pendiente (siguiente paso, con OK del usuario)**: **AJIT (C4 + contenedor Frontend + ADR del stack)**, y re-cosechar los deltas a `specs/aidlc/` en main.

## 2026-07-06 — AJIT arrancado (Segmentos 1-2)

- Creado `aidlc-docs/architecture/architecture-ajit.md`. Segmento 1 (Contexto C4): Perito + 3 actores + Claude API + Langfuse. Segmento 2 (Contenedores C4): monolito modular — Frontend/dashboard + Backend(FastAPI+LangGraph) + Postgres/pgvector; Frontend aterriza aquí.
- Nota clave para ADR: con FastAPI+HTMX el front NO es contenedor separado (server-rendered en el backend); con React+Vite sí. Decisión = ADR-001.
- **GATE**: esperando visto bueno de Segmentos 1-2 antes de Segmento 3 (NFR).

## 2026-07-06 — AJIT Segmentos 1-2 APROBADOS + Segmentos 3-4 generados

- Usuario aprobó C4 con nota: el diagrama de contenedores está en topología HTMX (FE→REST→API); React cambiaría el borde (Browser→API directo + CORS + authz server-side). Nota incorporada al Segmento 2 y marcada como material obligatorio de ADR-001.
- Segmento 3 (Matriz NFR): 6 NFR = invariantes; 3 titulares P4/P2/P1 con aserción fail-closed + tácticas.
- Segmento 4 (Riesgos/SPOF): Claude API y Postgres como SPOF reales, contingencia fail-closed acotada + persistencia, sin prometer HA (P7). Loops, Langfuse floor, dataset Día 0, inyección.
- **GATE**: Segmento 5 (ADRs) pendiente — decisión ADR-001 (HTMX vs React con trade-offs de topología/CORS/authz).

## 2026-07-06 — AJIT COMPLETO (3 ADRs decididos)

- **ADR-001**: Frontend = FastAPI + templates/HTMX. Registrada la reversibilidad de bajo lock-in (dominio en contratos Pydantic; migración futura a React = wrappers JSON sobre los mismos servicios, sin tocar dominio; RNF-24/PBT-02). El C4 queda correcto tal cual (topología HTMX).
- **ADR-002**: Monolito modular (1 despliegue).
- **ADR-003**: Langfuse target + floor JSON fallback detrás de interfaz de instrumentación.
- Archivos: `architecture/adr-001-frontend-stack.md`, `adr-002-monolito-modular.md`, `adr-003-observabilidad.md`, `architecture-ajit.md` (C4+NFR+Riesgos+ADRs).
- **AJIT COMPLETO.** Transición Inception→Construction lista (back+front definidos). Pendiente: re-cosecha de deltas (front + AJIT) a specs/aidlc/ en main; luego fase Construction.
