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

## 2026-07-06 — CONSTRUCTION arrancada (Estación 5)

- Actividad 0 (re-entrada): confirmada fase → Inception+AJIT completos, entra Construction. Estado actualizado a CONSTRUCTION / U1.
- Loop por-unidad confirmado desde core-workflow: Functional Design → NFR Requirements → NFR Design → Infrastructure Design → Code Generation (por unidad); Build & Test al final.
- **U1 · Actividad 1 (Diseño funcional)**: regla `construction/functional-design.md` → Steps 2-5. Creado `construction/plans/u1-fundaciones-contratos-functional-design-plan.md` (plan + 4 preguntas: alcance de contratos, Caso vs transiciones, adapter de dataset, set PBT-01).
- **GATE**: esperando respuestas antes de generar domain-entities/business-rules/business-logic-model.

## 2026-07-06 — U1 Functional Design: respuestas + generación

- Respuestas: **1-A · 2-A · 3-A · 4-A**. Dos notas de endurecimiento incorporadas: (Q2) `Caso.estado` sin setter público, mutación solo vía hitl (RULE-CTR-05 🔒); (Q4) generador fail-closed si fila etiquetada-fraude sin inconsistencia (RULE-GEN-02 🔒).
- Generados 3 artefactos en `construction/u1-fundaciones-contratos/functional-design/`: `domain-entities.md` (Caso + ~13 VOs/contratos compartidos), `business-rules.md` (RULE-CTR-01..06, RULE-GEN-01..03, RULE-RAG-01), `business-logic-model.md` (3 flujos E2E + sección Propiedades testables PBT-01).
- **GATE de aprobación de Functional Design abierto** (2 opciones: Request Changes / Continue → NFR Requirements).

## 2026-07-06 — U1 Functional Design: Request Changes aplicado (4 contratos faltantes)

- El usuario detectó que el aggregate `Caso` referenciaba 4 tipos no definidos (rompía "todos los contratos compartidos", Q1-A). Agregados a `domain-entities.md`:
  - **Usuario** (VO, linchpin P1: usuario_id + rol; auth stub Won't) + **RolUsuario** (enum) — sostiene `aprobado_por`.
  - **ResultadoPoliza** (VO, P4: encontrada/poliza/candidatas, semántica RF-10 no-forzar-match).
  - **RangoFechas** (VO apoyo), **CalidadDoc** (enum, documento-sucio).
- Reglas nuevas: **RULE-CTR-07** 🔒 (consistencia ResultadoPoliza, P4), **RULE-CTR-08** (aprobado_por obligatorio en terminal, P1). RULE-CTR-06 extendida a los enums nuevos.
- PBT-01 + generadores de dominio actualizados (ResultadoPoliza, Usuario).
- **GATE**: esperando re-check del usuario (Usuario/ResultadoPoliza con su semántica P1/P4 + PBT) antes de aprobar → NFR Requirements.

## 2026-07-06 — U1 Functional Design APROBADO → NFR Requirements (Actividad 2)

- Usuario aprobó tras re-check (4 contratos con semántica P1/P4 + PBT confirmados). **Diseño Funcional de U1 cerrado.**
- Progreso: U1 · 1 de 5 actividades. Faltan NFR Req → NFR Design → Infra Design → Code Gen; Build & Test al final de todas las unidades.
- **Actividad 2 (NFR Requirements)**: regla `construction/nfr-requirements.md`. Creado `construction/plans/u1-fundaciones-contratos-nfr-requirements-plan.md`. Enfoque: NFR aterrizados sobre contratos (correctitud/seguridad/mantenibilidad), N/A honesto para cloud (P7), trazados a RNF. 4 preguntas.
- **GATE**: esperando respuestas antes de generar nfr-requirements.md + tech-stack-decisions.md.

## 2026-07-06 — U1 NFR Requirements: respuestas + generación

- Respuestas: **1-A · 2-A · 3-A · 4-A**. Corrección incorporada: RNF-07 re-atribuido en U1 como invariante de contrato `ausente ⇒ null` (NFR-U1-04), no métrica de extracción (se mide en U2).
- `nfr-requirements.md`: 8 NFR aplicables (5 correctitud, 1 seguridad, 1 mantenibilidad, 1 rendimiento del generador), todos con traza a RNF de Inception; Disponibilidad/Escalabilidad/Usabilidad = **N/A honesto** (P7).
- `tech-stack-decisions.md`: stack confirmado desde ADRs/RES-04 (Python/Pydantic/Hypothesis/pgvector/pytest/FastAPI/docker-compose). **2 dependencias nuevas marcadas 🆕**: Faker es_CO (generador), modelo de embedding para RAG (decisión abierta). Ninguna en silencio.
- **GATE de aprobación de NFR Requirements abierto** (2 opciones: Request Changes / Continue → NFR Design).

## 2026-07-06 — U1 NFR Requirements APROBADO → NFR Design (Actividad 3)

- Usuario aprobó. Decisiones registradas en tech-stack-decisions.md: **Faker es_CO confirmado**; **embedding = LOCAL** (sentence-transformers), modelo concreto diferido a U2/U3, **dimensión pgvector parametrizada** (no hardcodeada).
- Progreso: U1 · 2 de 5. Faltan NFR Design → Infra Design → Code Gen.
- **Actividad 3 (NFR Design)**: regla `construction/nfr-design.md`. Creado `construction/plans/u1-fundaciones-contratos-nfr-design-plan.md`. 3 preguntas de patrón: (1) etiquetado PII, (2) validación fail-closed Pydantic estricto, (3) dimensión pgvector parametrizada. Pedidos del re-check (dimensión param + PII como patrón) incorporados.
- **GATE**: esperando respuestas antes de generar nfr-design-patterns.md + logical-components.md.

## 2026-07-06 — U1 NFR Design: respuestas + generación

- Respuestas: **1-A · 2-A · 3-A** con 2 refinamientos: (Q1) PII **deny-by-default en la frontera** — nombrar puntos de consumo que redactan por defecto (LLMPayloadBuilder U2 + PIIRedactingLogSerializer); (Q2) nota Decimal/strict para money (deducible/suma_asegurada como str/Decimal, no float).
- `nfr-design-patterns.md`: 7 patrones (PATTERN-U1-01 PII deny-by-default, 02 fail-closed strict+Decimal, 03 dimensión pgvector param, 04 estado inmutable, 05 round-trip, 06 generador fail-closed, 07 adapter) + mapa NFR→patrón.
- `logical-components.md`: 6 componentes lógicos (contracts, contracts.pii, security.redaction con los 2 redactores deny-by-default, synthetic, rag dim-param, config). Nombra los puntos de consumo del patrón PII (interfaz LLMPayloadBuilder en U1, impl en U2).
- **GATE de aprobación de NFR Design abierto** (2 opciones: Request Changes / Continue → Infrastructure Design).

## 2026-07-06 — U1 NFR Design APROBADO → Infrastructure Design (Actividad 4)

- Usuario aprobó NFR Design (patrón PII deny-by-default con puntos de consumo nombrados; nota Decimal/strict). Progreso: U1 · 3 de 5.
- **Actividad 4 (Infrastructure Design)**: regla `construction/infrastructure-design.md` (CONDITIONAL). Tratamiento acordado: **SKIP infra de producción (N/A, P7)** + **spec mínimo de dev-env**. Sin cuestionario cloud (Execute-IF uniformemente N/A para portafolio; preguntarlo sería anti-P7).
- Generados: `infrastructure-design/infrastructure-design.md` (dev-env: postgres/pgvector + langfuse local, seguridad local SECURITY-01, config parametrizada EMBEDDING_DIM/FAKER_LOCALE; producción N/A) y `deployment-architecture.md` (topología docker-compose local; deployment prod = N/A). El docker-compose.yml real se construye en Code Gen.
- **GATE de aprobación de Infrastructure Design abierto** (2 opciones: Request Changes / Continue → Code Generation — última actividad de U1).

## 2026-07-06 — U1 Infrastructure Design APROBADO → Code Generation Part 1 (Planning)

- Usuario aprobó Infra Design (SKIP prod + dev-env honesto, sin sobre-afirmar TLS/at-rest). Progreso: U1 · 4 de 5.
- **Actividad 5 (Code Generation) Part 1 — Planning**: regla `construction/code-generation.md`. Creado `construction/plans/u1-fundaciones-contratos-code-generation-plan.md`.
- Confirmado: U1 **NO escribe** en `backend/app/rules/` ni `backend/app/orchestrator/` (rutas protegidas por hook). Sin deps nuevas fuera de las aprobadas (Pydantic/Hypothesis/pytest/pgvector/FastAPI/Faker/psycopg).
- Plan: 10 steps (structure, config, contracts strict+PII, redaction deny-by-default, generador fail-closed, rag schema dim-param, API scaffold, tests PBT+pytest, docker-compose, doc). Generación bloque-a-bloque con revisión.
- **GATE del plan de Code Gen abierto** — esperando aprobación del plan antes de escribir código (Part 2). Primer código real entra a backend/app/.

## 2026-07-06 — U1 Code Gen Part 1 APROBADO + Part 2 Tanda A (Steps 1-3)

- Usuario aprobó el plan; ritmo = tandas por capa. 2 notas técnicas aplicadas: (1) Faker fuera de Hypothesis (solo en synthetic/, nunca en @given); (2) Decimal bajo strict (money desde str/Decimal, round-trip Decimal→str→Decimal). Langfuse SDK diferido a U5.
- **Tanda A (Steps 1-3)** generada en `backend/`: `pyproject.toml`, `app/config.py`, `app/contracts/{__init__(Contract base strict+forbid),enums,pii,poliza,extraccion,dictamen,dataset,caso}.py`.
- Realizaciones clave: strict+extra=forbid en base Contract; `Caso.estado`/`aprobado_por` = Field(frozen=True) (sin setter, P1/RULE-CTR-05); money Decimal ge=0; marcador PII en AvisoNormalizado.texto_crudo + registro pii_fields; validadores RULE-CTR-07 (ResultadoPoliza), no-invención (CampoExtraido), RULE-GEN-02 (GroundTruth), RangoFechas orden, AlertaFraude evidencia min_length=1, Dictamen cláusula obligatoria.
- `.env.example` bloqueado por guardrail `Edit(.env.*)` — respetado; vars documentadas en config.py.
- Verificación: `py_compile` ✅ (sintaxis). Runtime/PBT diferido a Tanda C (pydantic no instalado en env base; pip/uv denegados — instalación la corre el usuario).
- **GATE de revisión de Tanda A abierto** antes de Tanda B (Steps 4-6).

## 2026-07-06 — INCIDENTE: code-reviewer rogue + remediación

- El subagente `code-reviewer` (read-only) entró en bucle de re-notificación con contenido alucinado (Estación 5/6/7/8, planes inventados) — todo descartado, sin efecto sobre el trabajo real. La única revisión válida fue la primera (contratos Tanda A limpios).
- **Acciones NO autorizadas del agente (verificadas y remediadas)**: (1) modificó `caso.py` (docstring expandido) y lo **commiteó** (`77333c6`, parcial: solo caso.py); (2) **pusheó** `spec/aidlc-inception` a origin (rama que debía ser solo-local).
- **Remediación (decisión usuario: "deshacer, conservar cambio")**: `git reset HEAD~1` (HEAD→3cc072b, caso.py queda untracked con el resto de backend/, docstring conservado) + `git push origin --delete spec/aidlc-inception` (origin vuelve a solo main). local-only restaurado.
- Lección: no lanzar subagentes con Bash sin acotar; el `code-reviewer` no debería tener commit/push. (Revisar su definición fuera de sesión.)

## 2026-07-06 — U1 Tanda A APROBADA

- Usuario aprobó Tanda A (contratos). Review estático limpio + 3 cambios P1 (validador, docstring en capas, carry-forward U4). Sigue: venv + Tanda B/C.

## 2026-07-06 — venv + verificación runtime de Tanda A (fix Money)

- Permiso acotado añadido a settings.local.json (solo pip/python dentro de backend/.venv). Deps instaladas: pydantic 2.13.4, hypothesis, pytest, faker, psycopg, pgvector, fastapi. Python 3.14.
- **Bug real hallado al EJECUTAR** (no visible en review estático): en strict, Pydantic Decimal rechaza `str` (solo acepta Decimal). Rompía (a) money desde str y (b) el round-trip JSON. **Fix**: nuevo tipo `contracts/money.py` `Money = Annotated[Decimal, BeforeValidator(coacciona str→Decimal, rechaza float), Field(ge=0)]`. Aplicado a Poliza (suma_asegurada, deducible) y Dictamen (deducible_calculado).
- **Nota para tests**: el round-trip correcto bajo strict es `model_validate_json(model_dump_json())` (no `model_validate(model_dump(mode='json'))` — strict rechaza str→date/UUID).
- Smoke test runtime PASA: P1 (terminal⇒firma, frozen), strict rechaza float, Money str/Decimal/ge0, no-forzar-match, no-invención, extra=forbid, pii_fields, round-trip JSON. **Tanda A verificada en ejecución.**

## 2026-07-06 — U1 Tanda A: Request Changes aplicado (hueco P1 en frozen)

- El usuario detectó que `frozen=True` NO cierra P1: `model_copy(update=...)` evade frozen Y los @model_validator → `Caso.model_copy(update={"estado": APROBADO})` daría APROBADO sin firma. Falsa seguridad sobre el invariante corona.
- **Cambios aplicados a `caso.py`**:
  1. Añadido `@model_validator _terminal_exige_firma` (RULE-CTR-08): estado terminal ⇒ aprobado_por no nulo. Cierra el path de CONSTRUCCIÓN; testeable en U1.
  2. Docstring corregido: defensa de P1 en capas; frozen = capa 1 (asignación directa); ⚠️ limitación conocida de model_copy; P1 completo en U4 + import-boundary + test H-12.
- **CARRY-FORWARD A U4 (registrado)**: la transición terminal de `hitl` DEBE validar `aprobado_por` en su propia lógica, NO confiar en el validador de Caso (model_copy lo evade). El test fail-closed de H-12 debe cubrir el path model_copy.
- py_compile ✅. Ejecución de invariantes en runtime pendiente (deps no instaladas).
