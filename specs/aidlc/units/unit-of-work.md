# Unidades de Trabajo — Perito

> Decisiones: **Q1=A** monolito modular (único servicio desplegable) · **Q2=A** agrupación por incremento del plan de 5 días · **Q3=A** 5 unidades.
> **Terminología**: 1 Servicio desplegable (`backend`), cada **Unidad = Módulo lógico**. Núcleo irrenunciable = U2-U4.
> Inputs de endurecimiento (App Design §7.1): `Caso.estado` inmutable salvo vía hitl; `test_gate_regla` = firma forward-compat, NO build.

---

## Organización de código (Greenfield — monolito modular)
```
backend/
  app/
    contracts/        # U1 — modelos Pydantic (Caso, Poliza, Dictamen, Extraccion, AlertaFraude, Cotas...)
    intake/           # U2 — C1
    agents/           # U2 — C2 extractor, C3 verifier, C4 policy_lookup, (C6 fraud en U3)
    rules/            # U3 — C5 coverage_rules (motor P2, puro) ⚠️ solo el lead edita
    fraud/            # U3 — C6 fraud_signals
    orchestrator/     # U4 — C7 (dueño P4)
    hitl/             # U4 — C8 (dueño P1; máquina de estados, único mutador de Caso.estado)
    rag/              # U1 — C10 policy_rag (pgvector)
    observability/    # U5 — C9 (trazas, evals, export PIA)
    synthetic/        # U1 — CT1 generador es-CO (infra-test)
    api/              # servicios FastAPI (Intake, HITL, Observability, Admin)
  tests/              # pytest + Hypothesis (PBT) + DeepEval, por estrato
  docker-compose.yml  # U1 — postgres+pgvector + langfuse (entorno dev, entregable Code Gen)
```
> El motor `rules/` (P2) y `orchestrator/` (P4) son fronteras protegidas por hooks del repo; `agents/` no importa `rules/` (refuerza "cero aristas LLM→coverage_rules").

---

## U1 · Fundaciones & Contratos  *(habilita todo — Día 1)*
- **Propósito**: cimientos reproducibles: contratos Pydantic tipados, RAG de pólizas, generador sintético con fraude inyectado, scaffolding FastAPI + `docker-compose` (postgres/pgvector + langfuse).
- **Componentes**: `contracts/`, `rag/` (C10), `synthetic/` (CT1), scaffolding `api/`.
- **Historias**: **H-16** (generador + fraude inyectado), **H-17** (tool contracts tipados + validación, round-trip PBT-02).
- **Entrega demostrable**: fila dataset → aviso es-CO + póliza + ground truth; contratos que validan/round-trip.
- **Habilita**: U2, U3, U4, U5 (nada arranca sin contratos estables — coherente con CLAUDE.md agent-teams).
- **Invariantes tocados**: P3 (contratos/evidencia), P7 (infra honesta), PBT-02/07.

## U2 · Extracción · Verificación · Grounding  *(núcleo — Día 2)*
- **Propósito**: aviso caótico → JSON verificado o señal de escala; ubicar póliza o candidatas.
- **Componentes**: `intake/` (C1), `agents/` (C2 extractor, C3 verifier, C4 policy_lookup).
- **Historias**: **H-01** (ingesta), **H-02** (extracción+contrato+evidencia), **H-03** (verificación adversarial), **H-04** (grounding + candidatas), **H-06** (no inventar — marca ausente).
- **Entrega demostrable**: aviso → extracción verificada con evidencia, o señal "no confirma"/"sin match".
- **Depende de**: U1 (contratos, RAG).
- **Nota de comportamiento**: H-06/H-03/H-04 **emiten señales**; su fail-closed completo (escalar) se ejercita con U4 → dependencia **U2→U4** (ver `unit-of-work-dependency.md`).
- **Invariantes**: P3, P4 (marca/señal, no invención).

## U3 · Cobertura determinística · Fraude  *(núcleo — Día 3)*
- **Propósito**: dictamen `NO_CUBIERTO` con cláusula + alerta de fraude explicada (momento trust del PRD).
- **Componentes**: `rules/` (C5, motor puro), `fraud/` (C6).
- **Historias**: **H-07** (motor R1-R5, LLM no decide), **H-08** (cobertura negativa + cita), **H-09** (fraude explicable), **H-10** (fraude solo sugiere).
- **Entrega demostrable**: dictamen con regla+cláusula + alerta con evidencia.
- **Depende de**: U1 (contratos, cláusula RAG), **U2** (campos estructurados alimentan el motor — **H-04→H-07**).
- **Invariantes**: **P2** (motor decide), P3 (cita), **P6** (fraude explicable), P1 (fraude no decide). PBT-03 sobre el motor.

## U4 · Orquestación · Terminación · HITL  *(núcleo — Día 4)*
- **Propósito**: sistema completo con trazas en vivo; caps duros + escalamiento; bandeja HITL con firma humana.
- **Componentes**: `orchestrator/` (C7, P4), `hitl/` (C8, P1; único mutador de `Caso.estado`).
- **Historias**: **H-05** (terminación acotada + escala), **H-11** (bandeja+estados+persistencia), **H-12** (aprobar/corregir/rechazar + `aprobado_por`), **H-13** (correcciones como dato de eval).
- **Entrega demostrable**: flujo end-to-end con caps; caso llega a HITL y el humano firma.
- **Depende de**: **U2** y **U3** (orquesta sus nodos e invoca el motor). Cierra el fail-closed de U2 (H-06 escalamiento).
- **Invariantes**: **P4** (dueño terminación), **P1** (terminal solo con humano; estado inmutable salvo vía hitl).

## U5 · Observabilidad · Evals · Red-team  *(medición — Día 5)*
- **Propósito**: métricas + demo; harness de evals por estrato + red-team mínimo (inyección + sesgo).
- **Componentes**: `observability/` (C9), `tests/` (pytest+Hypothesis+DeepEval).
- **Historias**: **H-14** (traza por nodo + costo + replay), **H-15** (evals por estrato + versionado + export PIA), **H-18** (red-team inyección + sesgo + PII).
- **Entrega demostrable**: tablero de métricas + evals verdes por estrato + red-team.
- **Depende de**: instrumenta U2-U4 (transversal); evals requieren U2-U4 funcionando.
- **Diferido explícito**: `test_gate_regla` = **firma forward-compat, NO build** (versionado de reglas = Could). Estrato **SOAT** no se corre (RF-27.1).
- **Invariantes**: P3 (trazabilidad), P5 (PII/PIA), + aserciones fail-closed de P1/P2/P4/P6.

---

## Cobertura de historias (100%)
U1: H-16, H-17 · U2: H-01, H-02, H-03, H-04, H-06 · U3: H-07, H-08, H-09, H-10 · U4: H-05, H-11, H-12, H-13 · U5: H-14, H-15, H-18.
**18/18 historias asignadas.** ✅
