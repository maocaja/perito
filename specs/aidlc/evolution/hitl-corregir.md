# Unit de Evolución — HITL "Corregir" (F1 / H-20)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.

## 1. Intent

Completar el HITL. Hoy el analista puede **Aprobar / Rechazar**; falta **Corregir**: cuando un campo se extrajo
mal (ej. `tipo_siniestro` = HOGAR_AGUA cuando era AUTO_COLISION), el analista lo corrige y el sistema
**re-dictamina de forma determinística** (motor R1-R5), dejando el caso **LISTO_PARA_APROBAR** — el humano
sigue decidiendo (P1). Es el bucle "el copiloto prepara, el humano corrige y decide".

## 2. Qué cierra

- **H-20** (acción Corregir en el detalle). Parte de **M8** (HITL completo: aprobar/corregir/rechazar).

## 3. Criterios de completitud (verificables)

1. **Endpoint `POST /casos/{id}/corregir`** (en `app/api/`, capa activa — NO en el dashboard passive): recibe
   los campos corregidos + `usuario` (firma). Requiere `usuario` no vacío → 400 si falta (P1/H-12, igual que aprobar).
   **Guard de integridad (P1):** si el caso **ya es terminal** (APROBADO/RECHAZADO) → **409** (no se reabre una
   decisión firmada). Solo se corrige un caso no-terminal.
2. **Re-dictamen determinístico:** con la extracción corregida, re-ejecuta el **motor C5** (+ **C4 lookup** solo
   si cambió `numero_poliza`) + **fraude C6** (capas 1-2, determinista, sin LLM) → nuevo `dictamen`/`alerta_fraude`.
3. **Estado:** el caso queda **LISTO_PARA_APROBAR** (o REQUIERE_REVISION si la corrección aún escala) — **NUNCA
   terminal** (P1). Se actualiza vía `model_validate` (re-ejecuta validators). Se registra la corrección
   (quién + qué campos) en `motivo_escalamiento`.
4. **P3 (trazabilidad):** el campo corregido marca su origen como **corrección humana** —
   `TipoOrigen.HUMANO` (valor NUEVO, aditivo en `enums.py`) + `referencia="corrección humana: {usuario}"` +
   confianza 1.0. Máquina-legible (no confundir con SPAN del LLM). El corrector se registra AQUÍ, no en
   `motivo_escalamiento` (que es para escalamientos, no para casos LISTO).
5. **Detalle:** el detalle (`/casos/{id}`) muestra un **formulario de corrección** (editar los 4 campos:
   numero_poliza, fecha_siniestro, tipo_siniestro, monto_reclamado) + firma, que POSTea a `/corregir`.
6. **Dashboard passive:** el form vive en el detalle, pero el endpoint + el re-dictamen viven en `api/` — el
   dashboard NO corre el motor (sigue passive). Tests estructurales siguen pasando.
7. **Tests:** corregir un `tipo_siniestro` mal → el dictamen cambia (ej. NO_CUBIERTO → CUBIERTO) + estado
   LISTO_PARA_APROBAR + firma registrada; corregir sin `usuario` → 400; suite verde.

## 4. Invariantes / NFR

- **P1 (HITL):** Corregir **re-prepara**, NUNCA cierra. `usuario` obligatorio (firma). El humano decide después.
- **P2 (cobertura determinística):** el re-dictamen sale del **motor R1-R5**, no del LLM. Cero `anthropic`.
- **P3:** el campo corregido registra origen humano (auditable). **P5:** el aviso sigue redactado en el detalle.
- **Passive:** el motor/fraude se corren en `api/`, no en `dashboard/`.

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`app/api/ingest.py`** (o `app/api/hitl_actions.py`) — `POST /casos/{id}/corregir`: lee campos + usuario →
  construye `ExtraccionValidada` corregida (el campo tocado: `origen`=humano, `confianza`=1.0, `ausente`=False) →
  `call_c4_policy_lookup` si cambió póliza (si no, reusa `caso.poliza_match`) → `motor_cobertura` → `AlertaFraude`
  (capas 1-2) → `caso.model_validate({...extraccion, poliza_match, dictamen, alerta_fraude, estado, motivo...})` →
  `store.save`. Fail-closed si algo falla (REQUIERE_REVISION, no inventar).
- **`app/dashboard/templates/detalle.html`** — sección "Corregir" (form con los 4 inputs pre-llenados + firma) →
  POST `/casos/{id}/corregir`. Solo si el caso NO es terminal.
- **Reuso:** `motor_cobertura`, `call_c4_policy_lookup`, `detectar_inconsistencias_fraude` (ya existen).
- **Edge cases (manejar en el Bolt):**
  - Póliza corregida NO encontrada → motor da REQUIERE_REVISION (P4) y **no se corre fraude** (sin póliza).
  - **Origen humano:** el campo corregido marca `origen` con `referencia="corrección humana: {usuario}"`
    (si `TipoOrigen` no tiene valor HUMANO, no se toca el contrato).
  - Fraude = **solo capas 1-2** determinísticas (nunca capa-3 LLM).
  - Caso terminal → 409 (guard §3.1) — nunca se re-dictamina algo ya decidido.
- **`backend/tests/`** — test del cambio de dictamen + 400 sin usuario + **409 si terminal** + estructural.

## 6. Fuera de alcance

- Editar campos que no sean los 4 de extracción. Re-correr el LLM (C2/C3) — la corrección REEMPLAZA la extracción
  del LLM, no la re-ejecuta. Historial de correcciones múltiples (solo la última).

## 7. Cómo se validará el Bolt

- **Tests (ejecutan):** corregir tipo mal → dictamen cambia + LISTO_PARA_APROBAR + firma en motivo · sin usuario → 400 ·
  estructural (dashboard sigue sin importar rules/orchestrator; el motor se corre en api/) · suite verde.
- **Manual:** `uvicorn` → detalle → corregir un campo → ver el dictamen recalculado → Aprobar.
- **`code-reviewer`** (P1 no-terminal, P2 motor, passive, firma) → **PR**.

## 8. Decisiones (resueltas: usuario + code-reviewer)

- **D1 — Re-dictamen:** ✅ **motor C5 + fraude C6 (capas 1-2)** siempre; **C4 lookup solo si cambió `numero_poliza`**.
- **D2 — Endpoint:** ✅ **nuevo `app/api/hitl_actions.py`** (separación: ingest = C1→C7; hitl_actions = acción HITL post-orquestación).
- **D3 — Registro del corrector:** ✅ en **`origen.referencia`** del campo corregido (no en `motivo_escalamiento`),
  con **`TipoOrigen.HUMANO`** (valor nuevo aditivo en `enums.py`). Sin campo nuevo en `Caso`.

## 9. Ajustes del review incorporados (code-reviewer)

- 🔴 **Guard 409** (caso terminal → no se corrige) — ya en §3.1; requisito del endpoint. ✅
- 🔴 **`TipoOrigen.HUMANO`** (opción A) — se agrega el valor al enum (aditivo, no rompe nada); auditoría P3 limpia — §3.4, §8-D3.
- 🟠 corrector en `origen.referencia` (no `motivo_escalamiento`) — §3.4. 🟠 D2 = módulo nuevo `hitl_actions.py` — §8.
- ✅ Semántica confirmada: saltar C2/C3 es correcto (la corrección humana reemplaza la extracción; confianza 1.0).
  P1 (nunca terminal + 409), P2 (motor), P4 (escala si póliza no encontrada), P5 (aviso redactado) OK.