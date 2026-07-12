# W22 — Content design + diseño de interacción del Workbench

> Última iteración del caso (NO rediseño de arquitectura — las 3 zonas se quedan). Fuente de verdad de las
> correcciones de lenguaje, jerarquía y "una sola acción por estado". Cadencia AI-DLC: por unidad
> QUÉ+CÓMO → Bolt → code-reviewer → ajustar → code-reviewer → bitácora §7 → siguiente.

## §1 · Intent + diagnóstico

La arquitectura (cola │ caso+evidencia │ decisión) ya está bien. El problema es **content design +
interacción**: repetición del bloqueo, lenguaje técnico en la superficie, sin una acción primaria única,
densidad en la tabla y en el panel derecho. Objetivo: que un operador nuevo entienda el flujo sin manual y
un experto sea rápido — sin que el sistema exhiba su arquitectura interna.

## §2 · Reconciliación con invariantes (regla de oro: MOVER, no borrar; label ≠ valor)

- **encode-not-hide (dura):** el rastro técnico (reglas, motor, agentes, %) NO se elimina — se **mueve** al
  nivel técnico (drawer "Ver actividad técnica" / "por qué"). La superficie por defecto es humana; el técnico
  vive a un click. Tres niveles: **operativo** (siempre) · **explicativo** (bajo demanda) · **técnico**
  (auditoría).
- **P2:** el dictamen sigue citando regla+cláusula — en el nivel técnico/"por qué", no en la superficie. La
  cita no desaparece.
- **P1:** una sola acción primaria por estado, pero Radicar/Rechazar siguen exigiendo firma; la primaria en
  estado bloqueado es NO terminal (solicitar/ingresar). El servidor sigue siendo el gate.
- **P6:** "Escalar a fraude" → "Enviar a análisis de posibles irregularidades" es solo copy; el fraude sigue
  solo-sugiere.
- **Mecanismo seguro de de-jerga:** se cambia la **etiqueta de display**, nunca el valor canónico.
  `AUTO_COLISION` sigue en el dato y el motor (P2 lo compara exacto); el operador ve "Colisión vehicular".
  Igual con `monto_reclamado` (nombre de campo intacto; label "Valor de la reclamación").

## §3 · Tabla maestra de sustitución de lenguaje

| Actual | Superficie del operador | Dónde (archivo:línea) | Nota |
|---|---|---|---|
| `Auto Colision` (título) | **Colisión vehicular** | `workbench_caso.html:12` | mapa display, enum intacto |
| `AUTO_COLISION` (campo Tipo) | **Colisión vehicular** | tabla datos | `_TIPO_LABEL` nuevo |
| `HOGAR_AGUA` | **Daño por agua (hogar)** | idem | idem |
| `Monto reclamado` (label) | **Valor de la reclamación** | `_LABEL_CAMPO` (vista_caso) | nombre de campo intacto |
| `Verificación de fidelidad` | **Coincidencia entre fuentes** | `vista_caso.py:458,779` | |
| `Cobertura dictaminada` | **Resultado de cobertura** | `vista_caso.py:465,791` | |
| `dictaminar este caso` | **evaluar el caso** | `vista_caso.py:742-743` | |
| `n/d` | **No disponible** (+ "modo sin verificador" en el de C3) | `vista_caso.py:698` | |
| `Evidence Correlator` | **Comparación de evidencias** | `workbench_caso.html:103,198` | |
| `Fuentes cruzadas` | **Información comparada** | `workbench_caso.html:198` | |
| `Motor R1-R5 · regla PRE_MOTOR · "no el LLM" · (P2)` | → **mover al nivel técnico**; superficie: el "por qué" humano | `workbench_caso.html:118,244` | encode-not-hide |
| `HEURÍSTICA` (badge carril lesionados) | **detección por texto** (o al técnico) | `workbench.html:20` | |
| `(P1)/(P2)` marcadores en copy | → quitar de superficie (quedan en el spec/técnico) | varios | |
| `Radicar caso` | **Radicar caso** + tooltip 1ª vez "Crear el expediente formal del siniestro" | `workbench_caso.html:294` | conservar (dominio) + explicar |
| `Escalar a revisión` | **Enviar a revisión especializada** | `workbench_caso.html:320` | |
| `Escalar a fraude` | **Enviar a análisis de posibles irregularidades** | `workbench_caso.html:315` | P6 intacto |
| `Corregir y recalcular` | **Guardar monto y verificar** | `workbench_caso.html:59,140` | resultado humano |

## §4 · Unidades (QUÉ + CÓMO)

### L1 · Un solo bloqueo, una sola acción primaria por estado  [Prioridad 0]
- **QUÉ:** eliminar la triple repetición del bloqueo; la recomendación **==** la acción primaria; una sola
  primaria por estado.
- **CÓMO:**
  1. **Dedup:** hoy el bloqueo se dice en el banner de estado, en el bloque `wb-revisar` ("Necesitas
     revisar — Falta 1 dato") y en `wb-reco` ("Acción recomendada"). Dejar **una** explicación completa
     (bloque de resolución central) + una **acción** en el panel; el banner queda de una línea ("Necesita
     revisión · Falta el valor de la reclamación") sin repetir el cuerpo.
  2. **recomendacion() → acción vinculada:** `vista_caso.recomendacion()` (`:729`) devuelve además
     `accion = {label, endpoint, metodo, kind}`. Mapa estado→primaria:
     - `REQUIERE_REVISION` + faltantes → **"Solicitar al asegurado"** (`/casos/{id}/solicitar_docs` o carta)
       · NO terminal. Secundaria: "Ingresar manualmente" (enfoca el form inline).
     - `REQUIERE_REVISION` sin faltantes (póliza/otro) → **"Enviar a revisión especializada"**.
     - `LISTO_PARA_APROBAR` → **"Radicar caso"** (firma P1).
     - terminal → sin primaria ("Caso resuelto").
  3. **Panel derecho** renderiza `rec.accion` como la ÚNICA primaria (eyebrow "Siguiente paso").
  4. Renombrar `Corregir y recalcular` → **"Guardar monto y verificar"** (`:59,:140`).
- **Verificación:** un solo texto de bloqueo en el HTML; la primaria del panel == `rec.accion`; P1: la
  primaria en estado bloqueado NO es terminal; Radicar sigue gateado a `LISTO_PARA_APROBAR` + firma.

### L2 · Lenguaje humano + tres niveles  [Prioridad 0]
- **QUÉ:** superficie sin jerga; nombres internos al nivel técnico; % solo donde aporta criterio.
- **CÓMO:**
  1. `_TIPO_LABEL` (nuevo, espejo de `_COBERTURA_LABEL` `:707`) + `tipo_legible(caso)`; usar en el título
     (`:12`) y el campo Tipo. Enum intacto.
  2. Aplicar la tabla §3 (labels de campo, checklist, copy). Mover "Motor R1-R5/regla/no el LLM" del pie de
     datos (`:118`) y de cobertura (`:244`) al bloque técnico "por qué" (drawer/expandible). El pie humano
     queda: "La cobertura la decide una regla de la póliza, no la IA." con "Ver regla aplicada →".
  3. **% solo en campos problemáticos:** hoy `conf ≥ 0.9 → Verificado(% tenue)`, `< 0.9 → % + revisar`
     (`:96,108-110`). Cambiar: campo `ok` → solo "Verificado" (sin %); mostrar % SOLO cuando `revisar`
     (conf baja) o divergencia M3 o valor inferido. (No inflar confianzas — es presentación.)
  4. Ortografía/acentos (Colisión, Póliza) en labels derivados.
- **Verificación:** ningún enum/interno en la superficie por defecto; el técnico sigue a un click
  (encode-not-hide); P2: la cita de regla existe en el nivel "por qué".

### L3 · Densidad: tabla de datos + panel derecho + Estado operativo  [Prioridad 0/1]
- **QUÉ:** menos ruido por fila; secundarias bajo "Más acciones"; dedup Estado operativo vs indicadores.
- **CÓMO:**
  1. **Tabla de datos** (`:96-118`): fila normal = `✓ Label · valor · Fuente` (sin estado textual ni %);
     fila que requiere atención = `⚠ Label · valor · razón corta · [Comparar fuentes]`; fila faltante =
     `● Label · No encontrado · [Ingresar] [Solicitar]` (bloque accionable).
  2. **Panel derecho** (`:276-328`): `Siguiente paso` (primaria única, L1) → `También puedes` (1–2
     secundarias relevantes al estado) → `Más acciones ▾` (disclosure `<details>`: Rechazar, Enviar a
     análisis de irregularidades, Guardar borrador, Preparar carta).
  3. **Estado operativo** (lateral) vs indicadores centrales (`confianza_riesgo`, `:690`): el centro deja
     "Preparación: N de M verificaciones"; el lateral agrupa **Pendiente / Completado** + "Ver todas".
- **Verificación:** ≤4 elementos por fila normal; todas las acciones siguen accesibles (disclosure, no
  borradas); sin duplicar las 4 tarjetas centrales con el checklist lateral.

### L4 · Cola con razón operativa  [Prioridad 1]
- **QUÉ:** cada tarjeta explica por qué está ahí, para elegir sin abrir.
- **CÓMO:** `resumen_cola` (`:321`) añade `razon` (de `recomendacion`/`senal_fraude`): "Falta el valor de la
  reclamación" / "El valor reclamado supera la suma". Render como 4ª línea de la tarjeta.
- **Verificación:** cada tarjeta con prioridad · nombre · tipo (humano) · razón.

### L5 · Confirmaciones fuertes post-acción  [Prioridad 1]
- **QUÉ:** resultado inequívoco tras radicar/rechazar/escalar/solicitar/guardar (+ nº de expediente).
- **CÓMO:** los endpoints HITL devuelven un partial de confirmación ("Caso actualizado / radicado ·
  Nº SIN-2026-… · [Siguiente caso]") en vez de solo re-render silencioso; estados carga/éxito/fallo en el
  recalcular inline.
- **Verificación:** cada acción crítica muestra un resultado con referencia cuando aplica; anunciable a
  lector de pantalla (aria-live).

### L6 · Accesibilidad + evidencia instantánea  [Prioridad 2]
- **QUÉ:** foco visible, targets ≥40–44px, texto base 14–16px, contraste, zoom 200%, click en fuente abre
  evidencia.
- **CÓMO:** ajustes CSS (focus-visible, tamaños, spacing), icono+texto+color (no solo color), aria-live en
  cambios de estado. Verificar que el click en una fila/fuente abra el visor de evidencia directo.
- **Verificación:** navegación 100% teclado; nada se oculta a 200%; foco siempre visible.

## §5 · Fuera de alcance (es tuyo, no mío)
- Prueba de 5 tareas con 5 externos + 5 operadores reales.
- Auditoría **WCAG 2.2 con herramientas** (axe/Lighthouse) y lector de pantalla real — yo mejoro el markup,
  no "certifico" el cumplimiento.

## §6 · Orden de ejecución
Prioridad 0 primero: **L1 → L2 → L3**. Luego L4 → L5 → L6. Cada unidad con doble pasada de code-reviewer
(foco: la de-jerga NO viola encode-not-hide/P2; la acción única NO viola P1).

## §7 · Bitácora

### L1 — Un solo bloqueo + una acción primaria por estado
- **Bolt:** `_accion_primaria(caso, faltantes)` + `recomendacion().accion`; panel con primaria dinámica
  (REQUIERE→solicitar/escalar NO terminal · LISTO→radicar); dedup (banner 1 línea, sin repetir el detalle en
  el panel); `Corregir y recalcular`→`Guardar y verificar`; skip de la secundaria duplicada. Tests
  `test_w22_content_design.py`; 4 migrados (Radicar ausente fuera de LISTO; copy).
- **Code-review (1ª):** APROBADA, P1–P6 intactos. 2 MEDIA de robustez → **ajustados**: (i) el fail-closed P1
  también anula `accion` (`degradado`); (ii) `_accion_primaria` explícita (Radicar SOLO en LISTO; estado
  nuevo → None).
- **Code-review (2ª):** fixes correctos, CERO violaciones. 2 brechas de coverage → **añadidas** (caso
  degradado → accion None; estado no mapeado → None). 10 tests L1 verdes; suite 578→ verde.

### L2 — Lenguaje humano + tres niveles (de-jerga)
- **Bolt:** `_TIPO_LABEL`/`_tipo_humano` (tipo humano en título+campo, enum intacto); `monto_reclamado`→"Valor de
  la reclamación"; checklist "fidelidad"→"Coincidencia entre fuentes", "dictaminada"→"Resultado de cobertura";
  health_check con labels humanos; "n/d"→"No disponible"; recomendación/resumen nombran faltantes en humano
  (no `monto_reclamado`); % SOLO en campos problemáticos (verificado → "Verificado"; el % va al `title` →
  sigue en el DOM, encode-not-hide); técnico (Motor R1-R5/regla/"no el LLM") movido a `<details>` "Ver regla
  aplicada" (P2 intacto); Evidence Correlator/Fuentes cruzadas→humano; Escalar→"Enviar a análisis de
  irregularidades / revisión especializada"; tooltip Radicar. Tests +5 L2; ~11 migrados.
- **Code-review (1ª):** CERO violaciones críticas; encode-not-hide/P2/label≠valor OK. Hallazgo HIGH: `_macros.html`
  (usado por el panel) tenía mapa de labels de campo DUPLICADO e inconsistente → **ajustado**: fuente única vía
  filtro Jinja `label_campo`.
- **Code-review (2ª):** el 🔴 reportado fue **falso positivo** (línea 545 sí dice "Valor de la reclamación";
  suite verde). Hallazgo 🟠 real: estado/cobertura también duplicados (estado DIVERGÍA: panel "Requiere
  revisión" vs Workbench "Necesita revisión") → **ajustado**: `label_estado`/`label_cobertura` como fuente
  única → panel y Workbench nombran igual. 16 tests W22; suite 587 verde.
- **Follow-up documentado:** el badge de estado del Workbench (dict `S` inline) conserva sus labels (ya
  canónicos); si se quisiera 0 duplicación, rutar también por `label_estado` — no urge (valores ya iguales).

### L3 — Densidad
- **Bolt:** panel derecho — secundarias (Rechazar/fraude/escalar/carta/guardar) bajo `<details>` "Más
  acciones"; la primaria (`rec.accion`) queda fuera, visible. Checklist "Estado operativo" — 'Pendiente'
  visible + `<details>` "Ver todas las verificaciones" (lista completa, encode-not-hide). Tabla — fila
  faltante dice "No encontrado — ingrésalo arriba" (antes "Falta"). CSS `.wb-mas`/`.wb-hc-more` (disclosures
  calmos, `list-style:none` cross-browser). Tests +3 L3.
- **Code-review:** APROBADA — CERO violaciones críticas. P1 (Rechazar sigue accesible, el humano decide),
  P6, encode-not-hide (todo en el DOM dentro de los `<details>`, nada borrado) OK. Un LOW (marker webkit) ya
  cubierto por `list-style:none`. Sin ajustes → no aplica 2ª pasada. Suite 588 verde.

### L4 — Cola con razón operativa
- **Bolt:** `razon_cola(caso)` (falta {campo humano} / "Cobertura no aplica" / "Listo para revisar"), passive
  y sin PALABRAS_PROHIBIDAS; `_cola_filas` añade `razon`; la tarjeta la renderiza + usa `tipo_humano` (antes
  el tipo crudo "Auto Colision"); el fraude sigue en su flag aparte. Tests +3.
- **Ajuste propio (durante el Bolt):** el guard passive `test_dashboard_no_muta_estado_directo` marca el
  substring `caso.estado =` — se aliasó `est = caso.estado` y se limpió el comentario que también lo contenía.
- **Code-review:** PASS — P1–P6 OK, razón passive/sin decisión, fraude aparte (sin duplicar), tipo consistente.
  2 hallazgos MENORES de estilo (comparación `.value`, dejada por consistencia; duplicación intencional). Sin
  ajustes → no 2ª pasada. Suite 591 verde.

### L5 — Confirmaciones fuertes post-acción
- **Bolt:** bloque `wb-confirm` (role=status/aria-live) SOLO en terminal → "✅ Caso radicado / ⛔ Siniestro
  rechazado" + referencia del caso + firmante redactado + "Continuar →"; indicador de carga (HTMX
  `htmx-indicator` "⟳ Guardando y re-evaluando…") + botón dim en el recálculo inline. Tests +4.
- **Code-review:** sin violaciones P1–P6. Hallazgo P7 (MEDIUM-LOW): "Expediente #" podía sonar a radicado
  oficial → **ajustado** a "Referencia del caso #" (honesto: es el id interno). Verificado por test.

### L6 — Accesibilidad + evidencia instantánea
- **Bolt:** banner de estado como región viva (`role=status`/`aria-live=polite`) → anuncia el cambio tras
  recalcular. Evidencia al click YA existía (`<button>` nativo → `hx-get /workbench/evidencia`); se blindó con
  test (+endpoint 200). Base ya buena (foco `2px`, texto 14px, `.btn` ~40px, glifo+texto+color). Tests +3.
- **Code-review:** SIN VIOLACIONES — a11y correcta, región viva sin conflicto banner/confirmación, confirma
  el fix P7 de L5. Sin ajustes → cerrado.
- **Fuera de alcance (del usuario, spec §5):** auditoría WCAG 2.2 con herramientas (axe/Lighthouse), zoom
  200%, navegación 100% teclado y lector de pantalla real, + prueba de 5 tareas con 5 usuarios.

## §8 · Cierre W22
Las 6 unidades (L1–L6) completas con la cadencia AI-DLC (Bolt → code-reviewer → ajustar → code-reviewer).
**600 tests verdes.** Cero rutas protegidas tocadas. Arquitectura de 3 zonas intacta (era content design, no
rediseño). Invariantes P1–P7 + encode-not-hide preservados (regla de oro: MOVER lo técnico, no borrar;
label ≠ valor).
