# Unit de Evolución — Observabilidad real con Langfuse (B1)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes de implementar el CÓMO.

## 1. Intent (el goal)

Elevar la observabilidad del **floor** actual (Tracer → JSON en `ReplayStore` + panel) al **target real**
del PRD: **Langfuse**. Que cada caso emita su traza (nodos, tokens, latencia, estado) a Langfuse, donde se
puede inspeccionar/auditar/medir costo — **sin romper** el floor JSON (que queda como fallback) ni el pipeline.

## 2. Qué cierra (trazabilidad)

- **Must #10** del PRD (observabilidad con **herramienta real** Langfuse/OTel) — hoy en el *floor* declarado.
- **RF-25** (traza por nodo con herramienta real + replay), **M9**, **ADR-003** (Langfuse target + floor JSON fallback).

## 3. Criterios de completitud (verificables) — el núcleo del "QUÉ"

Se considera **hecho** cuando:

1. **Config:** `settings` tiene `langfuse_public_key`, `langfuse_secret_key` (+ `langfuse_host` ya existe). Si
   faltan las keys → Langfuse **desactivado** (solo floor JSON), sin error.
2. **Emisión:** al guardar la traza de un caso (`ReplayStore.save()`), si Langfuse está configurado, se envía
   una **traza por caso** con un **span por nodo** (intake/extractor/verifier/policy/motor/fraude), con
   `tokens_in/out`, `latencia_ms`, `resultado`, y metadata (`caso_estado`, `motivo_escalamiento`).
3. **Fail-open (NFR clave):** si el SDK de Langfuse falla o el servicio está caído, se **captura y continúa** —
   el caso y el floor JSON **nunca** se rompen por observabilidad. Verificable con un test que simula el SDK lanzando.
4. **P5 (cero PII):** a Langfuse se envía **solo lo redactado**. Los eventos ya salen redactados
   (`tracer.get_trace_log()`); **además el sink redacta `motivo_escalamiento`** — string libre que puede traer PII
   (ej. `"Orquestación falló: {e}"`, `ingest.py:64`) — con `redact_pii_spans_es_co` antes de enviar. Nunca
   `texto_crudo`. Verificable: un caso con PII en el aviso **y** en el motivo → cero cédula/celular en lo que recibe el sink.
7. **No bloquear el HTTP (P4/UX):** el push a Langfuse **no agrega latencia perceptible** a la respuesta del
   caso. El SDK `langfuse` es no-bloqueante (encola + flush en un thread de fondo); se **confirma en el de-risk**.
   Si resultara bloqueante, se envuelve en `fastapi.BackgroundTasks`. Verificable con un test de push lento.
5. **Floor intacto:** el `ReplayStore` (JSON) + el panel `/panel` siguen funcionando igual (fallback declarado del PRD).
6. **Suite completa verde** (159 + nuevos) + un **smoke real** contra Langfuse levantado en Docker (traza visible en la UI).

## 4. Invariantes / NFR que DEBE respetar

- **P5 (PII):** único redactor (el del `Tracer`, ya aplicado); a Langfuse solo eventos redactados. NO enviar el aviso crudo.
- **P4 (terminación):** Langfuse es observación pasiva — no toca rondas/tokens/escalamiento del orquestador.
- **Fail-open:** la observabilidad **degrada suave**; jamás propaga excepción al pipeline (a diferencia del pipeline de dominio, que es fail-*closed*). Diferencia consciente: un fallo de traza no es un fallo de negocio.
- **No mutar dominio:** el sink vive en `observability/`; no importa `rules/`/`orchestrator/` lógica; no cambia contratos.
- **Reuso:** cablear en `ReplayStore.save()` (un solo punto; todos los callers —orquestador, ingesta, seeder— ya lo llaman). NO tocar cada caller.

## 5. Diseño breve (el CÓMO a alto nivel — se detalla en el Bolt)

- **`app/observability/langfuse_sink.py`** (NUEVO): adaptador delgado sobre el SDK `langfuse`.
  - `is_enabled()` → True si hay keys en `settings`.
  - `emit_trace(caso_id, caso_estado, motivo, trace_events, token_summary)` → crea una traza + spans por nodo.
    **Redacta `motivo` con `redact_pii_spans_es_co` antes de crear la traza** (BLOCKER del review). Los eventos
    ya vienen redactados.
  - **Todo envuelto en try/except** con log (fail-open) — nunca propaga al caller.
- **`app/observability/replay.py`** (MODIFICADO): `ReplayStore.save()` llama a `langfuse_sink.emit_trace(...)` con
  los eventos **ya redactados** (`tracer.get_trace_log()`), después de guardar el floor JSON. Guarded + fail-open.
- **`app/config.py`** (MODIFICADO): añadir `langfuse_public_key`, `langfuse_secret_key` (opcionales).
- **Config del smoke (realidad):** NO existe `docker-compose.yml` en el repo (los specs lo listaban como
  entregable pendiente, nunca creado). El **smoke real se hace contra Langfuse Cloud** (free tier,
  `cloud.langfuse.com` → obtener keys) — sin Docker, apropiado para demo (P7). Auto-hospedar Langfuse (stack
  pesado ClickHouse/Redis/MinIO) queda **fuera de alcance** (tool sprawl, riesgo #2). Vars a poner en `.env`
  (el asistente NO puede editar `.env*` por permisos → las agrega el usuario):
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST=https://cloud.langfuse.com`.
- **context7 MCP** para la API real del SDK `langfuse` (no alucinar).

## 6. Fuera de alcance (otras Units / Bolts)

- **OTel spans** (B2, Should). **Postgres para casos/pólizas** (C, aparte — aquí Langfuse trae su propio Postgres vía compose).
- Métricas agregadas del panel (H-21, F2).

## 7. Cómo se validará el Bolt (gate de salida)

- **De-risk primero:** smoke mínimo contra Langfuse real (Docker) — como con el LLM — antes de cablear a fondo.
  Ahí se **confirma sync/async** del SDK (criterio 7).
- **Tests (ejecutan):**
  - keys ausentes → sink desactivado, sin error.
  - **fail-open:** `monkeypatch.setattr("app.observability.langfuse_sink.emit_trace", lambda *a, **k: (_ for _ in ()).throw(ConnectionError()))` → `ReplayStore.save()` termina sin excepción y el floor JSON queda (`load()` no None).
  - **P5:** caso con PII en aviso **y** en `motivo_escalamiento` → lo que recibe el sink no contiene cédula/celular.
  - suite completa verde.
- **Verificación por ejecución** + `code-reviewer` (foco P5/fail-open/passive) → **PR** a `main`.

## 9. Veredicto del review (code-reviewer, incorporado)

Alineado con RF-25/M9/ADR-003/Must #10; punto de integración `ReplayStore.save()` = "excelente"; frontera
`observability/` respetada; `settings` con `extra="forbid"` compatible. **Ajustes del review ya incorporados:**
1. 🔴 **BLOCKER P5** → el sink redacta `motivo_escalamiento` antes de enviar (criterio 4 + diseño §5).
2. 🟡 **Latencia** → declarado SDK no-bloqueante + confirmación en de-risk + fallback `BackgroundTasks` (criterio 7).
3. 🟡 **Compose** → Langfuse con su propio Postgres aislado, sin publicar 5432 al host (§5).
4. 🟢 **Fail-open test** → ejemplo de `monkeypatch` explícito (§7).

## 8. Decisiones (resueltas con el usuario)

- **D1 — Punto de integración:** ✅ **`ReplayStore.save()`** — un solo lugar, cero cambios a callers.
- **D2 — Dependencia:** ✅ SDK `langfuse` (pip) — con confirmación explícita antes de instalar (guardrail).
- **D3 — Smoke real:** ✅ los **tests mockeados son el gate automático** del Bolt; el smoke real contra Langfuse
  en Docker queda como **paso manual** (no bloquea el Bolt), cuando el usuario levante el compose.
