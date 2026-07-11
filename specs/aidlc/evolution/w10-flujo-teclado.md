# W10 — Flujo cero-formulario / teclado-first (ENTER → siguiente)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** W9 · **Datos:** R · **Invariante:** P1

## 1. Intent

No llenar formularios. Jamás. Abro el caso, la IA llenó todo, **yo solo corrijo**; si no corrijo nada,
**ENTER → Radicar → siguiente**. La cola se procesa como un flujo, no como una app.

## 2. Criterios de completitud (verificables)

1. **Foco automático** en el caso activo; **atajos de teclado**: ENTER = radicar (si habilitado), E = escalar,
   C = corregir, ↓/↑ = siguiente/anterior en la cola.
2. **Siguiente-en-cola:** tras radicar/escalar, la Workbench carga el **siguiente caso del carril** sin salir
   de la estación (HTMX).
3. **Confirmación en radicar:** ENTER sobre "Radicar" pide la confirmación humana registrada (P1), no radica a
   ciegas.
4. **Descubribilidad:** los atajos se muestran (hint sutil), accesibles.

## 3. Invariantes / restricciones

- **🔒 P1:** ENTER=Radicar **no** salta el gate humano — Radicar sigue exigiendo `aprobado_por`; el atajo es
  azúcar, no un bypass. Solo habilitado en `LISTO_PARA_APROBAR`.
- **ADR-001:** JS mínimo (manejo de teclas + swaps HTMX); cero lógica de decisión en cliente.
- **A11y:** los atajos no rompen la navegación por teclado ni el foco.

## 4. Fuera de alcance

- Edición masiva/bulk; macros. Empezar por el flujo 1-caso-a-la-vez.

## 5. Verificación (tests fail-closed)

- ENTER=Radicar sobre un caso NO `LISTO_PARA_APROBAR` → no radica (deshabilitado, P1).
- Radicar por teclado sigue exigiendo `aprobado_por` (no bypass).
- Tras una acción, se carga el siguiente caso sin recargar el shell.

## 6. Notas CÓMO

JS mínimo inline (keymap) en `workbench.html` + endpoint "siguiente en carril". Reusa las acciones de W9 y el
gate de `hitl`. Hints de atajos en la UI.

## 7. Precisiones tras code-review

- **🟠 "Siguiente" respeta el carril + filtro activos:** tras radicar/escalar, el siguiente caso se toma del
  **mismo carril (W8) y filtro** que el operador tenía en la columna izquierda — no salta a otro carril. Si el
  carril queda vacío → estado **"Carril vacío"** (no carga un caso fuera de contexto). Cualquier vista abierta
  (p.ej. comparativa W13) se cierra al cargar el siguiente caso.

### Tras el CÓMO
- **🔒 P1 verificado:** el teclado es azúcar — Enter/E hacen `requestSubmit` de forms del servidor; el gate
  real (firma + estado LISTO → 409) es server-side. Test: Enter no radica un caso no-LISTO.
- **"Avanzar → siguiente":** las acciones redirigen con `avanzar=1`; la ruta carga el siguiente de la cola
  (índice+1; último → se queda; caso fuera de la cola visible → primero visible).
- **Honestidad (P7):** en esta primera versión el "siguiente" avanza sobre la **cola completa**, no sobre el
  carril filtrado (el redirect de la acción no arrastra el `carril`); la navegación por **teclado ↑↓ sí**
  respeta la cola visible/filtrada. Preservar el carril a través de la acción queda como pulido menor.
- ADR-001: `go()` retorna bool → `preventDefault` condicional; cero `fetch`/decisión en cliente.
