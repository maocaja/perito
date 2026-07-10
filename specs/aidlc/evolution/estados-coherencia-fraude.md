# Unit de Evolución — Coherencia de estados + prioridad por riesgo (L)

> **Tipo:** spec a nivel de cambio (brownfield) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Origen:** revisión de coherencia de escenarios (el estado "Listo p/ aprobar" choca con fraude/no-cubierto).

## 1. Intent

Arreglar una incoherencia semántica real que debilita la honestidad de la demo (P7) y roza P1: el estado
`LISTO_PARA_APROBAR` **no significa "apruébalo"** — significa *"el copiloto terminó; el humano decide
(aprobar o rechazar)"*. Pero la etiqueta **"Listo p/ aprobar"** hace que el sistema *parezca recomendar
aprobar*, lo cual contradice:
- un caso con **fraude ALTA** (preset `fraude`: `CUBIERTO_PARCIAL` + `MONTO_EXCEDE_SUMA`),
- un caso **NO_CUBIERTO** (donde el humano rechazaría, no aprobaría).

**El fraude NO cambia el estado, y eso está CORRECTO (P6):** el fraude solo sugiere, no bloquea ni decide.
El problema es la etiqueta, no el modelo de estados.

## 2. Decisiones de producto (tomadas)

- **Etiqueta:** `LISTO_PARA_APROBAR` se muestra como **"Listo para decisión"** (neutral: vale para aprobar
  o rechazar). Refuerza P1 (el copiloto prepara, no recomienda).
- **Fraude:** se mantiene **ortogonal al estado (P6 puro)**. Se hace **visible y prioritario** en la vista,
  pero **no** cambia el estado ni deshabilita nada.

## 3. Criterios de completitud (verificables)

1. **Reetiquetar el DISPLAY** de `LISTO_PARA_APROBAR` → **"Listo para decisión"** en TODAS las superficies:
   badge (`_macros.html` `estado_badge`), chip de filtro y KPI de la bandeja (hoy "Listos para aprobar" →
   **"Listos para decisión"**), y cualquier texto del detalle. **El enum interno `LISTO_PARA_APROBAR` NO
   cambia** (cero impacto en contratos, orquestador, hitl, tests de dominio) — solo el texto mostrado.
2. **El fraude sigue sin tocar el estado** (P6). No se enruta a `REQUIERE_REVISION`, no deshabilita "Aprobar".
   (La habilitación sigue gateada por `estado == LISTO_PARA_APROBAR`, no por fraude.)
3. **Señal de riesgo visible en la bandeja:** las filas con `alerta_fraude` muestran, además del badge de
   severidad, la **señal que la disparó** (chip corto: p. ej. "monto excede suma", "fecha fuera de vigencia")
   para que el operador entienda el "por qué" de un vistazo. Passive, derivado de `alerta_fraude.inconsistencias`.
4. **Cue "revisar antes de firmar":** en un caso `Listo para decisión` **con** fraude, el detalle deja claro
   (ya lo hace la `recomendacion`) que el humano debe **revisar la señal antes de firmar**. Verificar que ese
   cue sea prominente (no un asterisco).
5. **Prioridad por riesgo (no rompe el efecto "en vivo"):** en la bandeja, un realce visual lleva el ojo
   primero a los casos con fraude. El **orden primario cronológico se mantiene** (para el efecto de la demo en
   vivo "los casos van entrando"); la priorización por riesgo es **realce visual**, no reordenamiento que
   rompa las llegadas. *(Si en el CÓMO se opta por un toggle de orden por riesgo, que sea secundario.)*

## 4. Restricciones e invariantes

- **P1:** ninguna superficie presenta al copiloto como recomendando "aprobar". "Listo para decisión" es neutral.
- **P6:** el fraude solo sugiere/prioriza; **nunca** cambia el estado ni bloquea. Ortogonalidad intacta.
- **P7:** los escenarios quedan coherentes (ver §6); nada fabricado.
- **Solo `dashboard/`:** no toca el enum, `rules/`, `orchestrator/` ni `hitl/`.

## 5. Fuera de alcance

- Renombrar el **valor** del enum (sería un cambio transversal grande; innecesario — basta el display).
- Enrutar fraude ALTA a `REQUIERE_REVISION` (descartado: rozaría P6 y tocaría el orquestador).
- La carta autogenerada y los ítems de visibilidad Tier-1 (units aparte, ver roadmap).

## 6. Verificación (tests fail-closed)

- **Coherencia:** ninguna vista muestra "Listo p/ aprobar"; el badge de `LISTO_PARA_APROBAR` dice "Listo para
  decisión". El KPI/chip también.
- **P1:** no aparece la palabra "aprobar" como recomendación del sistema (solo como acción disponible del humano).
- **P6:** un caso con fraude ALTA sigue en su estado (no forzado a `REQUIERE_REVISION`); "Aprobar" sigue
  habilitado/deshabilitado por `estado`, no por fraude.
- **Señal de riesgo:** una fila con `alerta_fraude` muestra la inconsistencia disparadora.
- **No regresión:** KPIs clicables, chips, HTMX live y el orden cronológico de la bandeja intactos.

## 7. Notas para el CÓMO (Bolt)

Archivos: `templates/_macros.html` (label de `estado_badge`), `templates/bandeja.html` (KPI/chip + chip de
señal de fraude), posiblemente `vista_caso.py` (helper `senal_fraude(caso)` que resume la inconsistencia
principal), `static/style.css`. Tests en `tests/test_evolution_frontend_hifi.py`. Cero backend de dominio.
