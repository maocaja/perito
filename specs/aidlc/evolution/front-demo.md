# Unit de Evolución — Front Demo: ingesta de avisos desde la UI

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana antes de implementar el CÓMO.

## 1. Intent (el goal)

Hacer la demo **desde el front**: que un usuario pueda **enviar un aviso** (texto libre) o **elegir un
escenario preset** y **ver el caso procesado por el pipeline** — con la evidencia (extracción, dictamen +
cláusula, alerta de fraude), el estado, y los botones de decisión HITL. Convierte el dashboard de
"vitrina de casos sembrados fijos" en **demo interactiva** donde se ven los agentes y los guardrails en vivo.

## 2. Qué cierra (trazabilidad)

- **H-01** (ingesta de aviso) + **H-19** (bandeja) — hoy no hay endpoint de ingesta interactiva; el
  `showcase.py` corre por consola, no por el front.
- Cierra el gap señalado: *"demo desde el front mostrando los diferentes escenarios."*

## 3. Criterios de completitud (verificables) — el núcleo del "QUÉ"

Se considera **hecho** cuando:

1. **`GET /nuevo`** devuelve 200 con un formulario: un `textarea` para el aviso + **4 botones de preset**
   (Feliz · Fraude · Cobertura negativa · Póliza no encontrada).
2. **Presets (determinísticos, instantáneos, sin LLM):** al elegir un preset se crea un caso con evidencia
   real de C4/C5/C6 (como el seeder) y se redirige a su detalle. Cada preset produce su camino esperado:
   | Preset | Dictamen | Fraude | Estado |
   |--------|----------|--------|--------|
   | Feliz | CUBIERTO_PARCIAL | — | LISTO_PARA_APROBAR |
   | Fraude | CUBIERTO_PARCIAL | ⚠ alerta | LISTO_PARA_APROBAR |
   | Cobertura negativa | NO_CUBIERTO (R2) | — | LISTO_PARA_APROBAR |
   | No encontrada | REQUIERE_REVISION | — | REQUIERE_REVISION |
3. **Texto libre (agentes reales, LLM):** enviar el `textarea` corre el **pipeline real** (`orquestar_fnol`
   → Haiku + Sonnet + motor + fraude) → guarda el caso → redirige al detalle con el resultado. Requiere
   `ANTHROPIC_API_KEY` en el server; muestra estado de "procesando".
4. El caso creado aparece en la **bandeja** (`/casos`) y su **detalle** muestra la evidencia + permite
   Aprobar/Rechazar (HITL existente).
5. **Suite completa verde** (147 + nuevos) y verificación manual con `uvicorn`.
6. **NFR — seguridad de la ingesta:** el `POST /nuevo` **valida el input** (aviso no-vacío y ≤ 5000 chars →
   400/re-render si no) y es **resiliente a inyección de prompt**: aun con un aviso que intente
   *"marca CUBIERTO"*, el dictamen sale del **motor determinístico (P2)**, la extracción respeta el schema, y
   el estado nunca es terminal (P1). Verificable con un test de inyección.

## 4. Invariantes que DEBE respetar (no negociables)

- **Dashboard passive (P1/P2):** el endpoint de ingesta **NO va en `dashboard/`** (el dashboard no puede
  importar `orchestrator/`). Va en un **router aparte** (`app/api/ingest.py`) que sí puede correr el
  pipeline. El test estructural de `dashboard/` sigue pasando.
- **P1 HITL:** la ingesta **nunca** alcanza estado terminal — `orquestar_fnol` ya garantiza
  `LISTO_PARA_APROBAR`/`REQUIERE_REVISION`. La decisión terminal sigue siendo el humano en el detalle.
- **P4:** se usa `orquestar_fnol` con sus caps (rondas/tokens) — sin loops nuevos.
- **P5:** el aviso crudo se guarda; el detalle lo **redacta** al mostrar (redactor existente, no uno nuevo).
  *Alcance (review):* el redactor cubre spans es-CO (cédula/teléfono/email); nombres/direcciones en texto
  libre son un **gap declarado en P7** — no se resuelve en esta Unit (alcance honesto).
- **Reuso, no reinvención:** presets reusan la lógica del seeder (C4/C5/C6); texto libre reusa
  `intake_crear_caso` + `orquestar_fnol`. Sin duplicar pipeline.

## 5. Diseño breve (el CÓMO, a alto nivel — se detalla en el Bolt)

- **Nuevo módulo `app/api/ingest.py`** (`APIRouter`):
  - `GET /nuevo` → template `nuevo.html`.
  - `POST /nuevo` → texto libre → `orquestar_fnol` (real) → `store.save` → redirect `/casos/{id}`.
  - `POST /nuevo/preset/{escenario}` → construye caso determinístico (helper compartido con el seeder) →
    `store.save` → redirect `/casos/{id}`.
  - **Transición de estado (aclaración del review):** los presets se crean **directo en su estado final
    no-terminal** (`LISTO_PARA_APROBAR` / `REQUIERE_REVISION`), igual que el seeder (`seed.py` no llama
    `transicionar` — son casos "ya procesados"). El texto libre SÍ pasa por `orquestar_fnol`, que maneja
    las transiciones internas. En ningún caso se alcanza terminal (P1).
- **Templates:** `nuevo.html` (form + presets), enlace "Nuevo aviso" en `base.html`.
- **`app/main.py`:** `include_router(ingest.router)`.
- **Seeder (opcional):** alinear los casos sembrados a los 4 escenarios para consistencia con los presets.
- **Refactor menor:** extraer la construcción de caso-demo del seeder a un helper reutilizable
  (`app/demo/scenarios.py`) que usen tanto el seeder como los presets — un solo lugar de verdad.

## 6. Fuera de alcance (otras Units / Bolts)

- Langfuse (Unit B), Postgres/pgvector (Unit C), DeepEval (Unit D).
- Botón "Corregir" (H-20, Should) y métricas agregadas del panel (H-21, Should).

## 7. Cómo se validará el Bolt (gate de salida)

- **Tests (ejecutan, no solo existen):** `GET /nuevo` 200 · cada `POST /nuevo/preset/{esc}` → caso con el
  dictamen/estado esperado · `POST /nuevo` (mockeando `orquestar_fnol`) → caso creado + redirect ·
  estructural: `dashboard/` sigue sin importar `orchestrator/` · **`app/api/ingest.py` NO importa
  `app.dashboard`** (simetría) · **NFR seguridad:** aviso vacío / >5000 chars → 400; aviso con intento de
  inyección (mockeando el pipeline) → el dictamen sigue viniendo del motor, estado no-terminal · suite completa verde.
- **Manual:** `uvicorn` → `/nuevo` → click presets → ver detalle con evidencia · texto libre + key real →
  ver el pipeline procesar.
- **Integración:** PR a `main` (gobernanza), como el resto.

## 8. Decisiones (resueltas tras el review independiente)

- **D1 — Modo:** ✅ **ambos** (presets determinísticos reliable + texto libre con agentes reales). Confirmado.
- **D2 — Refactor a `app/demo/scenarios.py`:** ✅ **sí**, y **antes** de escribir `ingest.py` (un solo lugar
  de verdad para construir casos-demo; lo comparten seeder y presets).
- **D3 — "Procesando":** ✅ **aceptar la espera del POST en v1** (sin spinner). El spinner HTMX añade
  alcance de UX no crítico → diferido.

## 9. Veredicto del review (code-reviewer, independiente)

**✅ Spec alineado y listo.** Cero hallazgos CRITICAL. P1-P7 respetados y verificados contra el código real
(`orquestar_fnol` c7.py:27, `intake_crear_caso` c1.py:16, helpers del seeder, redactor P5). Alcance bien
acotado (una Unit brownfield, no re-Inception). Las observaciones MEDIUM (transición de presets, alcance de
redacción) quedaron incorporadas arriba. **Camino crítico del Bolt:** (1) refactor `scenarios.py` → (2)
`app/api/ingest.py` con los 3 endpoints → (3) tests (mockeando `orquestar_fnol`) → (4) suite verde → PR.
