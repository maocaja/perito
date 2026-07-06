# Componentes — Perito (Application Design)

> Mapeo **1:1 con M1-M10** del PRD §9 (Q1=A) + infra de demo. Alcance: responsabilidades e interfaces de alto nivel (la lógica detallada va en Functional Design).
> **Clasificación de confianza**: `LLM` (razona, no autoritativo) · `DET` (determinístico/autoritativo) · `IO/STORE` · `INFRA-TEST`.
> Alineado con la estructura del repo: `backend/app/agents/` (LLM tools) · `backend/app/rules/` (motor P2) · `backend/app/orchestrator/` (P4).

---

## C1 · intake  *(M1 — IO)*
- **Propósito**: recibir y normalizar el aviso FNOL (texto/PDF/foto), crear el Caso en `RECIBIDO`, marcar posibles duplicados.
- **Responsabilidades**: ingesta multimodal, normalización a representación interna, creación del Caso, marca de duplicado (heurística mínima).
- **Interfaz**: `recibir_aviso(payload) -> Caso`.
- **Historias**: H-01. **Invariantes**: P3 (origen preservado).

## C2 · extractor  *(M2 — LLM)*
- **Propósito**: extraer campos estructurados del aviso vía Claude multimodal, con **contrato Pydantic** y cada campo enlazado a su origen.
- **Responsabilidades**: extracción, validación contra contrato, marca de campos ausentes/inciertos (**no inventa**).
- **Interfaz**: `extraer(aviso) -> ExtraccionValidada`.
- **Historias**: H-02, H-06. **Invariantes**: P3 (evidencia enlazada), P4 (no inventar).
- ⚠️ **No autoritativo**: alimenta campos; **no decide cobertura** (P2).

## C3 · verifier  *(M3 — LLM)*
- **Propósito**: confirmar adversarialmente la extracción contra la fuente; emitir señal si no puede.
- **Responsabilidades**: verificación campo↔fuente, emisión de señal "no confirma" al orquestador.
- **Interfaz**: `verificar(ExtraccionValidada, aviso) -> ResultadoVerificacion`.
- **Historias**: H-03. **Invariantes**: P4 (señal en vez de avance a ciegas).

## C4 · policy_lookup  *(M4 — LLM-assisted + IO)*
- **Propósito**: ubicar la póliza referida contra la base (vía `policy_rag`); devolver candidatas cercanas si no hay match.
- **Responsabilidades**: match de póliza, "no encontrada" + candidatas (nunca match forzado).
- **Interfaz**: `buscar_poliza(campos) -> ResultadoPoliza`.
- **Historias**: H-04. **Invariantes**: P4 (no forzar match), P3 (cláusula recuperable).

## C5 · coverage_rules  *(M5 — **DET, autoritativo**)*
- **Propósito**: **motor determinístico** que dictamina cobertura aplicando R1→R2→R3→R4→R5 en orden, citando regla y cláusula. Override SOAT contemplado (RF-14, forward-compat).
- **Responsabilidades**: evaluar reglas, emitir dictamen ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION} con regla+cláusula; calcular deducible (≥0).
- **Interfaz**: `dictaminar(campos_estructurados, poliza) -> Dictamen` — **función pura**.
- **Historias**: H-07, H-08. **Invariantes**: **P2 (el motor decide, NUNCA el LLM)**, P3 (cita obligatoria).
- 🔒 **Regla dura**: sin entrada LLM en la ruta de decisión; **cero aristas entrantes desde componentes LLM** (ver `component-dependency.md`). Ubicación: `backend/app/rules/`. Testeable con PBT-03.

## C6 · fraud_signals  *(M6 — LLM)*
- **Propósito**: razonar inconsistencias y emitir alerta explicable con evidencia citada.
- **Responsabilidades**: detección razonada, evidencia obligatoria, **solo sugiere** (no bloquea/decide).
- **Interfaz**: `analizar_fraude(caso) -> AlertaFraude | None`.
- **Historias**: H-09, H-10. **Invariantes**: P6 (explicable), P1 (no decide).

## C7 · orchestrator  *(M7 — DET control-plane)*
- **Propósito**: dirigir el flujo del agente (LangGraph); **dueño de la política de terminación y escalamiento**.
- **Responsabilidades**: secuenciar nodos, imponer **caps duros** (rondas + presupuesto de tokens + detección de ciclos), decidir escalamiento a `REQUIERE_REVISION`, invocar el motor determinístico.
- **Interfaz**: `procesar(caso) -> ResultadoFlujo`.
- **Historias**: H-05. **Invariantes**: **P4 (dueño de terminación)**. Ubicación: `backend/app/orchestrator/`.
- 🔒 **Regla dura**: es el único que invoca `coverage_rules`; los caps no se relajan.

## C8 · hitl  *(M8 — DET state machine + STORE)*
- **Propósito**: máquina de estados del Caso + bandeja; aprobar/corregir/rechazar con persistencia y registro de correcciones.
- **Responsabilidades**: transiciones válidas (Apéndice C), **bloquear todo estado terminal sin `aprobado_por`**, persistencia tolerante a interrupción, correcciones como dato de eval.
- **Interfaz**: `abrir(caso)`, `aprobar(caso, usuario)`, `corregir(caso, cambios, usuario)`, `rechazar(caso, usuario)`.
- **Historias**: H-11, H-12, H-13. **Invariantes**: **P1 (terminal solo con humano)**.
- 🔒 **Regla dura**: `APROBADO`/`RECHAZADO` inalcanzables sin acción humana registrada; ningún componente automático escribe estados terminales.

## C9 · observability  *(M9 — IO/STORE)*
- **Propósito**: traza por nodo (Langfuse/OTel o floor JSON) + costo/caso + replay; harness de evals por estrato versionados + export PIA.
- **Responsabilidades**: instrumentación, métricas, evals (pytest+DeepEval), test-gate de cambios de reglas, export de evidencia.
- **Interfaz**: `instrumentar(evento)`, `correr_evals(estrato)`, `exportar_pia(caso)`.
- **Historias**: H-14, H-15. **Invariantes**: P3 (trazabilidad), P5 (export PIA, sin PII en logs).

## C10 · policy_rag  *(M10 — STORE)*
- **Propósito**: indexar pólizas sintéticas con cláusulas (pgvector); recuperar cláusula aplicable para C4/C5.
- **Responsabilidades**: indexación, recuperación de cláusula.
- **Interfaz**: `indexar(poliza)`, `recuperar_clausula(consulta) -> Clausula`.
- **Historias**: H-04, H-08. **Invariantes**: P3.

---

## CT1 · synthetic_generator  *(Infra de demo/test — INFRA-TEST, NO es producto)*
- **Propósito**: generar avisos es-CO + pólizas sintéticas + ground truth; **inyectar la inconsistencia** en filas etiquetadas fraude.
- **Responsabilidades**: transformación fila→(aviso, póliza, verdad); validez del eval de fraude (rechaza si no encoda la señal).
- **Interfaz**: `generar_caso(fila) -> (Aviso, Poliza, GroundTruth)`.
- **Historias**: H-16. **Invariantes**: P7 (honestidad — es infra, no producto).

## Resumen de clasificación
| Componente | Clase | ¿Decide cobertura? | ¿Puede alcanzar terminal? |
|---|---|---|---|
| intake | IO | No | No |
| extractor | LLM | **No** | No |
| verifier | LLM | No | No |
| policy_lookup | LLM+IO | No | No |
| **coverage_rules** | **DET** | **Sí (autoritativo)** | No |
| fraud_signals | LLM | No | No |
| orchestrator | DET | No (invoca al motor) | No (solo escala) |
| **hitl** | **DET** | No | **Solo con humano (P1)** |
| observability | IO | No | No |
| policy_rag | STORE | No | No |
