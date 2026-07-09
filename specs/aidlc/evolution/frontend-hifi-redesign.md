# Unit de Evolución — Rediseño hi-fi de Bandeja + Detalle (J)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Construye sobre:** Unit A (dashboard C11) + Unit I (tablero agent-native) + Unit H (demo en vivo).
> **Insumo:** handoff de diseño hi-fi `design_handoff_perito_fnol/` (`Perito Dashboard.dc.html` + `README.md`).

## 1. Intent

Elevar dos vistas del dashboard —**Bandeja** y **Detalle**— al diseño hi-fi del handoff, resolviendo los
problemas de UX que el propio handoff declara: **falta de jerarquía** ("nada dice mira aquí primero"), la
**acción principal enterrada** (completar datos faltantes vivía al fondo) y la **información repetida**. El
detalle es *la vista principal del rediseño*: pasa de un formulario donde todo pesa igual a un flujo orientado
a la tarea —el analista ve el próximo paso, completa lo que falta, re-dictamina y firma— **sin que el copiloto
decida por él** (P1).

**No es un rebuild.** El shell (sidebar+topbar), los tokens (paleta violeta, IBM Plex, tema claro/oscuro) y el
motor de datos ya existen y coinciden con el handoff (el `style.css` fue importado de ese mismo `.dc.html`).
Esto **injerta patrones de UX** sobre el front server-rendered existente, conservando lo que el front ya tiene
por encima del prototipo: **bandeja en vivo (HTMX), notificaciones/toasts, resumen del copiloto y feed de
actividad** — el prototipo no los contempla y **no se pierden**.

## 2. Qué cierra

- El gap **"se ve como app normal / sin jerarquía"** en las dos vistas de mayor tráfico del analista.
- El anti-patrón de **acción principal contradictoria**: el botón "Aprobar" no debe estar activo con el caso
  incompleto. El rediseño lo **deshabilita hasta que el caso esté completo y re-dictaminado** — refuerzo visual
  de P1 (el gate real sigue siendo el servidor).
- La **duplicación** "extracción" + "corregir" en dos bloques separados → **una sola tabla** editable inline.

## 3. Criterios de completitud (verificables)

### Bandeja (`/casos`)

1. **KPIs clicables** — las 4 tarjetas (Listos / Requieren revisión / Fraude alta / Resueltos) se vuelven
   **filtros toggle**: clic filtra la tabla por ese estado; clic de nuevo (o en el KPI activo) vuelve a "Todos".
   Estado activo con realce `border-color:var(--brand); box-shadow:0 0 0 3px var(--brand-weak)`. Reusa los
   `counts` y `estado_actual` que ya llegan al template — **cero backend nuevo** (son enlaces `GET /casos?estado=…`).
2. **Jerarquía de filas** — filas accionables (`LISTO_PARA_APROBAR`, `REQUIERE_REVISION`) llevan acento
   `border-left:3px solid var(--<info|warn>)`; filas resueltas (`APROBADO`/`RECHAZADO`) se atenúan
   (`opacity:.55`). Clase derivada de `caso.estado` en la capa de vista/template — dato ya disponible.
3. **Se conserva** el auto-refresh HTMX cada 3s, el badge "En vivo", las notificaciones/toasts y las columnas
   actuales. La jerarquía y el filtro por KPI **no rompen** el swap HTMX (`#bandeja-live`).

### Detalle (`/casos/{id}`)

4. **Banner de próximo paso (HÉROE, full-width, arriba)** — franja bajo el título, **dinámica según estado real**:
   - Con campos faltantes → tono `warn`, título "Falta(n) N dato(s) para poder dictaminar este caso".
   - Datos completos, sin dictamen → tono `info`, "Datos completos — re-dictamina la cobertura para habilitar la aprobación".
   - Caso terminal (`APROBADO`/`RECHAZADO`) → tono `ok`/neutro, refleja el cierre (no propone acción).
   Se arma de `recomendacion` (ya P1-safe, valida `PALABRAS_PROHIBIDAS`) + el conteo de faltantes. **Nunca** usa
   verbos de decisión del copiloto (P1). Reemplaza la card de recomendación enterrada en la columna derecha.
5. **Tabla "Datos del siniestro" fusionada (extracción + corrección en una)** — una sola tabla
   `Campo / Valor+evidencia / Confianza` construida de `caso.extraccion.campos`:
   - Filas **presentes**: **solo-lectura** — valor (mono) + evidencia citada del aviso (itálica, `border-left`
     brand) + barra de confianza con color por umbral (`≥0.9` ok · `0.7–0.9` warn · `<0.7` bad). No traen input.
   - Filas **ausentes**: fondo warn tenue, tag `REQUERIDO`, **input editable**; confianza "—". Los inputs se
     **generan de los campos ausentes reales** (no 4 hardcodeados). Al enviar y volver con valor humano → la fila
     muestra el valor + evidencia "Capturado por el analista (origen: humano)".
   - **Decisión de producto:** solo los ausentes son editables (fiel al handoff). El form de corrección envía
     **únicamente los campos antes ausentes**; los presentes conservan su valor y confianza de extracción sin
     tocarse. El endpoint `/corregir` ya maneja este caso con seguridad.
   - **Pie:** firma + botón "Corregir y re-dictaminar" que hace **POST al endpoint de corrección existente**
     (re-dictamen **determinístico**, P2 — nota visible: "La cobertura la re-calcula el motor determinístico,
     no el LLM"). El botón se **deshabilita mientras haya faltantes**.
6. **Checklist "Para aprobar se requiere"** (en el panel de decisión) — 3 ítems con check verde / círculo hueco:
   Verificación de fidelidad · Datos del siniestro completos (N/total) · Cobertura dictaminada. **Passive**,
   derivado de `verificador` + faltantes + `caso.dictamen` en `vista_caso.py` (nuevo view-model, sin dominio).
7. **Correo recibido colapsable** — el `aviso_redactado` pasa a `<details>` (colapsado por defecto) con chevron;
   conserva el tag "PII redactada" (P5).
8. **Regla de habilitación (P1-safe)** — "Aprobar dictamen" y "Corregir y re-dictaminar" quedan **deshabilitados
   mientras `faltantes > 0`**; "Rechazar caso" **siempre disponible**. El deshabilitado es **azúcar de UX**: el
   gate real sigue siendo `hitl` en el servidor (valida `aprobado_por`). No se crea ningún camino terminal nuevo.

## 4. Restricciones e invariantes (no negociables)

- **ADR-001 (server-rendered):** la edición y el re-dictamen van por **round-trip POST**; el motor determinístico
  recalcula (P2). El atributo `disabled` de los botones y el conteo de faltantes se **calculan en el servidor**
  (Jinja2, del contexto). El único JS admitido es HTMX (live refresh ya existente) y, a lo sumo, un reflejo
  cosmético del `disabled` al teclear — **prohibido** cualquier cálculo de faltantes/habilitación/cobertura o
  validación de "¿puedo aprobar?" en el cliente. El estado que gobierna la UI es siempre el del servidor.
- **P1 (HITL):** el copiloto prepara; el humano firma. El banner/checklist describen el **paso del humano**, nunca
  deciden. Rechazar siempre disponible.
- **P2 (cobertura determinística):** ningún re-dictamen desde el cliente; la cita de cláusula se muestra **literal**.
- **P7 (demo honesta):** todo se renderiza del `Caso` real. Los datos del prototipo (nombres, tokens, costos) son
  ilustrativos y **no se copian**; si un dato falta, se dice "no disponible".
- **No regresión:** se conservan bandeja en vivo, notificaciones/toasts, resumen del copiloto y feed de actividad.
- **Solo `dashboard/`:** no toca `rules/` (P2) ni `orchestrator/` (P4).

## 5. Fuera de alcance (esta Unit)

- **Panel de trazas** y **Nuevo aviso** — funcionan y quedan como están (posible pulido cosmético en otra Unit).
- Ningún cambio de contratos Pydantic, del motor de reglas ni del orquestador.

## 6. Verificación (tests fail-closed)

- **P1:** aserción de que ningún botón/endpoint del detalle alcanza estado terminal sin `aprobado_por`; el
  view-model del banner/checklist no emite `PALABRAS_PROHIBIDAS` (reusa el guard de `recomendacion`).
- **Habilitación:** con faltantes>0, el markup de "Aprobar" y "Re-dictaminar" trae el atributo/clase `disabled`;
  con faltantes==0, no.
- **Bandeja:** el filtro por KPI produce el mismo conjunto que el chip de estado equivalente; el swap HTMX
  preserva la jerarquía de filas.
- **P7:** el detalle no muestra ningún literal del prototipo (nombres/tokens demo) que no venga del `Caso`.
- **No regresión:** la suite base (`make test`) sigue verde; el poller/live y las notificaciones intactos.

## 7. Notas para el CÓMO (Bolt) — no vinculantes

Archivos previstos (todos en `backend/app/dashboard/`): `templates/bandeja.html`, `templates/detalle.html`,
`static/style.css`, `vista_caso.py` (nuevo view-model del checklist + `faltantes` públicos), y `c11.py`
(pasar `faltantes` + checklist al `_detalle_context`). **Endpoint de corrección confirmado (Unit F1):**
`POST /casos/{caso_id}/corregir` en `backend/app/api/hitl_actions.py:42` → llama al `motor_cobertura`
(re-dictamen determinístico, P2), no terminal, ya registrado en `main.py` con tests. Sin backend de dominio nuevo.
