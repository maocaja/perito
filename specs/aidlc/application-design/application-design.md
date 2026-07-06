# Application Design (Consolidado) — Perito

> Consolida `components.md` · `component-methods.md` · `services.md` · `component-dependency.md`.
> Decisiones: **Q1=A** (1:1 con M1-M10) · **Q2=A** (motor determinístico aislado) · **Q3=A** (enforcement distribuido con dueños únicos). Idioma es-CO.

---

## 1. Visión de arquitectura
Perito es un **sistema agéntico con control-plane determinístico**: un orquestador (LangGraph) dirige herramientas LLM que **razonan y alimentan datos**, mientras las **decisiones que importan** (cobertura) las toma un **motor de reglas puro**, y las **decisiones terminales** las firma un **humano**. Los invariantes no negociables son topología, no convención.

## 2. Componentes (10 + 1 infra) — mapeo 1:1 con M1-M10
| ID | Componente | Clase | Módulo | Dueño de invariante |
|---|---|---|---|---|
| C1 | intake | IO | M1 | P3 |
| C2 | extractor | LLM | M2 | P3, P4 |
| C3 | verifier | LLM | M3 | P4 |
| C4 | policy_lookup | LLM+IO | M4 | P4, P3 |
| **C5** | **coverage_rules** | **DET** | M5 | **P2** |
| C6 | fraud_signals | LLM | M6 | P6, P1 |
| **C7** | **orchestrator** | **DET** | M7 | **P4** |
| **C8** | **hitl** | **DET** | M8 | **P1** |
| C9 | observability | IO | M9 | P3, P5 |
| C10 | policy_rag | STORE | M10 | P3 |
| C11 | dashboard (front) | UI/FE | — (demo-grade) | experimenta P1/P3 |
| CT1 | synthetic_generator | INFRA-TEST | infra | P7 |

## 3. Capa de servicio
`IntakeService` (entrada) · **`OrchestrationService`** (núcleo agéntico, dueño P4, único invocador del motor) · **`HITLService`** (dueño P1) · `ObservabilityService` (P3/P5) · `AdminService` (infra/dev). Detalle y endpoints en `services.md`.

## 4. Flujo end-to-end
Aviso → intake → **orchestrator** → extractor → verifier (señal si no confirma) → policy_lookup (señal si sin match) → **[orchestrator invoca coverage_rules — determinístico]** → fraud_signals (solo sugiere) → caso+dictamen+evidencia → **hitl** → **Humano decide (`aprobado_por`)** → APROBADO/RECHAZADO. Al agotar cotas → `REQUIERE_REVISION`. Diagrama en `component-dependency.md`.

## 5. Cómo la arquitectura realiza los invariantes (P1-P7)
| P | Realización arquitectónica | Prueba en diseño |
|---|---|---|
| **P1 HITL** | Estado terminal exclusivo de `hitl` con actor humano; guardia `_transicion_valida` | Grafo: sin arista a APROBADO/RECHAZADO salvo vía Humano |
| **P2 Determinismo** | `coverage_rules` = función pura; único invocador = orchestrator | **Cero aristas LLM → coverage_rules** (§4 de dependency) |
| **P3 Trazabilidad** | Evidencia enlazada (extractor) + cláusula (rag) + instrumentación total | Dictamen sin cláusula = inválido |
| **P4 Terminación** | `orchestrator` dueño de caps (rondas/tokens/ciclos) + escala | Señales, no saltos; una sola salida al agotar cotas |
| **P5 Habeas Data** | Minimización PII en prompts; export PIA; sin PII en logs | ObservabilityService |
| **P6 Explicabilidad** | `fraud_signals` con evidencia obligatoria; no bloquea | Alerta sin evidencia = inválida |
| **P7 Honestidad** | `synthetic_generator` marcado infra-test; Infra Design SKIP | Encuadre portafolio |

## 6. Alineación con el repositorio
`backend/app/orchestrator/` (C7, P4) · `backend/app/rules/` (C5, P2) · `backend/app/agents/` (C2/C3/C4/C6, LLM). El diseño respeta las fronteras protegidas por los hooks/reglas del proyecto.

## 7. Diferido / fuera de alcance (coherencia)
- **SOAT**: override contemplado en `coverage_rules` (RF-14, forward-compat); sin flujo/estrato propio (RF-27.1).
- **ESPERANDO_INFO / cola SLA**: Should — no modelado como servicio (invariante "no adivinar" ya cubierto por orchestrator).
- **Auth real**: Won't — selector de rol stub.
- **Infrastructure Design**: SKIP (portafolio, P7); `docker-compose` local = entregable de Code Generation.

## 7.1 Notas de endurecimiento (input aprobado para Functional Design / Units)
1. **P1 inevadible por construcción**: en Functional Design, `Caso.estado` debe ser **inmutable salvo vía la máquina de estados de `hitl`** (prohibida la asignación directa en otros componentes). Así el guard `_transicion_valida` pasa de "existe" a "inevadible"; la aserción fail-closed de H-12 queda como red de seguridad, no como única defensa.
2. **`test_gate_regla` = firma forward-compat, NO build**: el versionado de reglas con test-gate es **Could** (§2.2). La firma en `observability` (y H-15) se conserva como forward-compat, pero **Units NO debe agendar construir el sistema de versionado de reglas completo** en esta Inception (misma honestidad que SOAT/ESPERANDO_INFO). El build queda diferido.

## 8. Qué se detalla después (Construction)
- **Functional Design (por unidad)**: reglas R1-R5 en detalle, política de caps, contratos Pydantic completos, propiedades PBT (PBT-01).
- **NFR Requirements/Design**: stack confirmado, framework PBT (Hypothesis), patrones fail-closed, minimización PII.
- **Units Generation (siguiente)**: descomposición en unidades de trabajo + grafo de dependencias de construcción (acopla H-04→H-07, H-16/H-17→resto).
