# W21 — Perito V1: reinvención del surface del operador ("Cursor for insurance")

> **Change-level spec (QUÉ + CÓMO)** · **Estado:** 🟡 en ejecución · **Reemplaza** la IA operador-facing de W1–W20
> (la superficie, no el backend). **LLM/det:** ⚙️ det (solo UI/plantillas) · **Datos:** R · **ADR-001** vigente
> (server-rendered Jinja/HTMX, JS mínimo).
>
> **Fuente de verdad de diseño.** Manifiesto Perito V1 (jul 2026): reinventar cómo trabaja el operador de
> siniestros, no mejorar el dashboard. "Cursor for insurance", no otro sistema enterprise. Empezar de un lienzo
> en blanco: cuestionar cada layout, componente e interacción.

## 1. Intent

El operador procesa **~150 casos/día**. Hoy busca, lee, compara, copia, cambia de ventana. **Ese trabajo debe
desaparecer.** Perito ya preparó el caso antes de que el operador lo abra; el operador **nunca parte de cero** —
solo **valida y decide**. La interfaz **desaparece**: el operador no piensa "estoy usando software", piensa
"estoy revisando un caso". El caso es el centro; el chrome se calla.

**Emociones de diseño (más que UI):** al abrir → calma · al abrir un caso → lo entiende en 10 s · al revisar
evidencia → confianza · al corregir → asistido · al decidir → seguro · al terminar → productivo.

## 2. Principios (del manifiesto) — no negociables de diseño

1. **Una pregunta por pantalla/sección.** Si una sección responde varias, está mal diseñada.
2. **Carga cognitiva mínima.** Reducir, reducir, reducir. Si algo no ayuda a decidir, se elimina.
3. **Jerarquía = flujo del ojo:** `CASO → ESTADO → HISTORIA → LO QUE NECESITA ATENCIÓN → EVIDENCIA → DECISIÓN →
   SIGUIENTE`. Nada interrumpe ese flujo.
4. **Formularios que ya están completos.** Nunca "llena esto"; "la IA ya lo completó, revisa lo que necesita
   atención". Solo lo problemático es editable; lo demás se ve, en calma, resuelto.
5. **IA casi invisible.** Nunca exponer orquestación/prompts/workflows. La IA aparece solo cuando crea valor:
   explica, sugiere, avisa, compara, responde.
6. **Documentos de primera clase** (no adjuntos): evidencia. Galería tipo Notion; click en un campo abre el
   documento y la **página exacta** de la extracción. El operador nunca busca.
7. **Datos como objetos, no como Excel.** Se escanea, no se lee. `✓ Póliza · verificada` / `⚠ Fecha · falta`.
8. **Timeline humano** (08:41 correo recibido · 08:42 caso preparado…), no técnico. Lo técnico, a un click.
9. **Confianza invisible salvo que importe** (baja / fuentes en conflicto / inferida por IA); si no, "Verificado".
10. **Decisión = colega senior**, no barra de admin: una acción **recomendada** + esfuerzo estimado + **UNA**
    primaria + secundarias.
11. **Color con significado:** gris por defecto · verde listo · amarillo revisar · rojo crítico/fraude/bloqueo.
    Nada más.
12. **Teclado-first**, edición inline, sin modales innecesarios. Microinteracciones sutiles (Linear), nunca
    llamativas. Empty states premium (calmos, nunca contenedores muertos).

## 3. Invariantes heredados (P1–P7 + ADR-001) — el diseño NO los toca

- **P1 (HITL):** el operador firma; ninguna ruta alcanza terminal sin firma. La "acción recomendada" **prepara**,
  no decide.
- **P2 (cobertura):** la dicta el motor R1–R5; la UI presenta, no re-decide.
- **P4 (terminación) · P5 (PII):** el visor de evidencia nunca expone PII cruda (huella/redacción); todo texto
  mostrado pasa por el boundary redactado.
- **P6 (fraude):** solo sugiere; ninguna señal bloquea la firma ni cambia el estado.
- **P7 (honestidad):** lo que aún no producimos va rotulado (`demo`); no se promete lo que no hay.

## 4. Reconciliación con `encode-not-hide` (regla dura enforced) — declarada, no override

El manifiesto pide confianza e IA "invisibles". Se cumple **codificando en calma, no ocultando**:
- **Confianza:** alta → chip **"✓ Verificado"** con el **% presente pero tenue** (hover/expand lo revela; el
  `%` sigue en el DOM). Solo se **resalta** cuando importa (baja / conflicto multi-fuente / inferida). Cumple el
  test `test_encode_not_hide_muestra_pct_incluso_al_100` (el `%` se renderiza siempre, aunque calmado).
- **Rastro de agentes:** timeline **humano** por defecto + **"actividad técnica"** en drawer (rastro real:
  nodos/tokens). No se elimina — se **codifica** a un click. El timeline no se colapsa a una sola línea.

> Esto satisface el manifiesto (calma, IA invisible) **sin** relajar la regla. Si se quisiera el override literal
> (no renderizar el `%` en alta), sería una decisión explícita del owner, registrada aquí — **no** es el default.

## 5. Unidades (cada una = Bolt → code-reviewer → ajuste → code-reviewer → siguiente)

- **V1·0 — Fundación:** sistema de diseño (tokens calmos: gris por defecto, verde/amarillo/rojo solo con
  significado; escala tipográfica; sombras suaves; transiciones sutiles) + shell invisible (el chrome se calla; la
  cola es un riel calmo; el caso es el centro). Fuente única del lenguaje visual. **Responde:** el marco no compite
  con el caso.
- **V1·1 — Identidad + estado (¿Qué miro? ¿En qué estado?):** título del caso **enorme** + banner de estado
  grande a color (🟢 listo para firmar · 🟡 necesita revisión · 🔴 crítico). Vistazo de <3 s.
- **V1·2 — Historia ejecutiva (¿Qué pasó?):** narrativa en lenguaje natural (sobre `resumen_ejecutivo`), no
  campos. IA invisible (sin badges gritones de "agente").
- **V1·3 — Lo que necesita atención (¿Qué bloquea?):** **una** cosa dominante (el bloqueo) con corrección
  inline; el resto, en calma, "completo". Campos como objetos (✓ verificado / ⚠ falta · buscar). Confianza según
  §4.
- **V1·4 — Evidencia y documentos (¿Qué lo respalda?):** documentos de primera clase (galería Notion, previews
  grandes, hover, apertura en un click); click en un campo → documento + página exacta (reusa W12/A3, P5).
- **V1·5 — Decisión como colega senior (¿Qué hago?):** acción recomendada + esfuerzo estimado + **una** primaria
  ("Ejecutar recomendación") + secundarias (escalar/rechazar/guardar). Firma P1 intacta.
- **V1·6 — Flujo (velocidad + pulido):** timeline humano + "actividad técnica" en drawer; empty states premium;
  teclado-first (Tab/Enter/flechas/atajos); microinteracciones sutiles; auditoría de color (§principio 11).

## 6. Verificación (fail-closed, por unidad)

- **P1/P5/P6** se re-verifican en cada unidad que toque decisión/evidencia (reusan asserts de W20/W5/W6).
- **encode-not-hide (§4):** el `%` se renderiza en todo campo (incl. 100%, calmado) y el timeline no colapsa —
  test bidireccional (heredado de `test_w20_bolt2b`).
- **Una pregunta por sección:** cada sección del flujo mapea a exactamente una de las 6 preguntas (§2.3).
- **Color con significado:** verde/amarillo/rojo solo en estados con semántica (no decorativos).
- **Accesibilidad:** contraste AA; foco visible; navegación por teclado.

## 7. Notas CÓMO (para el Bolt) — solo plantillas/CSS/JS mínimo (rutas NO protegidas)

- Se reinventa la **presentación**: `workbench.html` (shell), `workbench_caso.html` (el flujo del caso), los
  parciales de drawer (evidencia/documento/actividad/comparativa), `base.html`, `style.css`. Los **view-models**
  (`vista_caso.py`) y las **rutas** (`c11.py`) son la fuente de datos: se re-presentan; se añaden helpers de
  presentación solo si hacen falta (sin lógica de decisión, DIP intacto).
- **NO** se toca `rules/` ni `orchestrator/` ni los contratos. La IA sigue preparando el caso; cambia cómo se
  muestra.
- Cadencia por unidad: **Bolt (implementa) → code-reviewer (P1/P5/P6 + encode-not-hide + Clean Code) → ajustes →
  code-reviewer → siguiente unidad.** Verificación en navegador (Playwright) por unidad.

## 8. Bitácora (code-review por unidad)

### V1·0 — Fundación (Ronda 1 + ajustes)

**Implementado:** tokens `--primary*` (ink calmo, light+dark) + escala `--fs-*` + `--transition`; de-red del chrome
global (links/foco/selección → ink) y del shell (nav activo, badge de conteo, avatar, selección de cola → calma);
variable muerta `--perito-red` eliminada; `body`→`--fs-body` + transición calma en interactivos.

**Code-review (Ronda 1):** 🟢 sin impacto P1–P7, tokens en ambos temas, a11y OK. Hallazgos de consistencia
"rojo solo crítico" — **todos aplicados:** foco de inputs (`.input:focus`) y `.wb-doc:focus-visible` → ink;
banner por defecto (tono neutral) y borde del panel de decisión → ink (ya no rojo). Además, de-red de dos
componentes foundational que saltaban a la vista: **botón primario** (`.btn-primary` → ink, `color:var(--bg)`
como on-primary para contraste en ambos temas) y **barra de preparación** (`.wb-eo-bar-fill` → ink).

**Backlog de acentos (migran con su unidad, NO se dejan en silencio):** quedan rojos `--brand` en acentos de
componentes que se rediseñan más adelante — `.chip.active`/`.wb-carril.active` (filtros, → shell/V1·3),
`.wb-link`/`.wb-drawer-trigger` (enlaces, → V1·4/V1·6), `.card.accent`/`.card-head.brand`/`.copilot-hero`
(→ sus secciones), `.wb-agente-tag` (→ V1·2), y presets/kpi de intake y panel (otras superficies). Cada unidad
de-reddea lo suyo; el objetivo final es rojo = solo crítico en todo el producto. `.wb-tiempo-num` ya se eliminó
(header viejo retirado en V1·1).

### V1·1 — Identidad + estado del caso

**Implementado:** el header pasó de una card `.wb-header` (tipo pequeño + confianza global + tiempo estimado) a
**`.wb-hero`** — título del caso **enorme** (`--fs-hero` 30px, tight) + subtítulo calmo (asegurado · producto ·
#id). Debajo, **banner de ESTADO grande** `.wb-status` de una línea, color por estado (✓ verde "Listo para
firmar" · ⚠ amarillo "Necesita revisión" · 🔒 gris "Aprobado/Rechazado"). Se retiró del header la confianza
global (invisible salvo que importe) y el tiempo estimado (irá al panel de Decisión, V1·5). El banner calmo
`.wb-banner` y el header viejo `.wb-header*`/`.wb-conf-num`/`.wb-tiempo*` se eliminaron (CSS muerto). 🔒 P6: el
banner refleja el ESTADO; el fraude no lo cambia (va como riesgo aparte).

**Tests:** `test_w2_header` migrado (`test_header_muestra_identidad_y_estado`: `wb-hero-title` + `wb-status` +
`wb-status-label`); los view-models `asegurado_de`/`tiempo_estimado` siguen vivos y testeados (`tiempo_estimado`
se rinde en V1·5). Suite afectada verde (37 tests).

**Nota de scroll (→ V1·6):** `.main` retiene `scrollTop` entre swaps HTMX; al cambiar de caso el título enorme
puede quedar bajo el topbar sticky. Pulido: reset de scroll al cargar un caso (unidad V1·6).

### V1·2 — Historia ejecutiva

**Implementado:** el "Resumen ejecutivo" (card + heading + badge `✍️ Summary Agent`/`⚙️ base`) → **`.wb-historia`**:
prosa legible (`--fs-h2`, line-height 1.65, medida ~68ch) con un eyebrow calmo "RESUMEN DEL CASO"; **la IA es
invisible** — se retiró el badge de agente. P7: ambos orígenes (LLM/base) son reales (no hay mock que rotular);
si la redactó el copiloto, una nota **sutil** "Redactado por el copiloto" lo dice, sin marketing. Se eliminó el
CSS muerto `.wb-agente-tag` (otro rojo del backlog resuelto). La historia dejó de ser una card (menos
fragmentación, más narrativa).

**Code-review (Ronda 1):** 🟢 sin críticos. 1 HIGH clean-code — `.wb-status-body` sin regla CSS (layout frágil)
→ **corregido** (`display:flex; flex-direction:column; flex:1; min-width:0`); re-review confirmó limpio.

**Tests:** `test_v1_historia_se_rinde_sin_exponer_la_ia` (prosa presente + contenido real + sin badge de IA);
`test_render_muestra_la_historia` (migrado: `wb-historia` + eyebrow, sin `wb-agente-tag`). Verde.

**Ajustes tras review (R1):** 🟢 0 críticos. a11y — eyebrow `<div>`→`<h2>` (encabezado semántico). Coherencia —
`.wb-doc:hover` rojo→ink. `tiempo_estimado` en contexto sin renderizar = intencional (→ V1·5). Re-review OK.

### V1·3 — Lo que necesita atención (campos como objetos)

**Implementado:** la `<table class="wb-campos">` (dato·confianza·fuente, sentía Excel) → **campos-OBJETO**
`.wb-field`: cada campo se escanea como `[glifo estado] · [label + valor] · [estado calmo · fuente]`. **Confianza
en calma (§4):** alta (≥0.9) → "✓ Verificado" con el `%` **tenue** (`.wb-conf-muted`, presente en el DOM);
media (0.7–0.9) → ⚠ + `%` ámbar + "revisar" + fila resaltada; baja (<0.7) → ⚠ + `%` rojo + resalte; ausente →
⚠ + "Falta" resaltado. "Lo que necesita atención salta; el resto se ve tranquilo/completo." Cada campo presente
es un `<button>` (teclado-first) con `hx-get` a su evidencia (V1·4 lo profundiza). Preservados: badge `demo`
(P7), `✓✓` validado (M3), y `.wb-conf-pct` con el `%` (encode-not-hide). CSS de tabla muerto eliminado
(`.wb-campos*`/`.wb-campo*`/`.wb-ic-*`/`.wb-conf-dot`/`table.datos`/`.row-ausente`).

**Tests:** `test_render_panel` (migrado: `wb-field-state`/`wb-field-src`), `test_workbench_caso_sin_extraccion`
("Falta" en vez de "REQUERIDO"); `test_encode_not_hide_muestra_pct_incluso_al_100` sigue verde (el `%` se rinde
aunque sea 100%, calmado). Verde.

**Code-review (R1):** 🟢 limpio, 0 hallazgos (primera pasada aprobada; sin ajustes → gate satisfecho sin
re-review redundante). El reviewer marcó `.wb-drawer-trigger` rojo como item de V1·4.

### V1·4 — Evidencia y documentos (de primera clase)

**Implementado:** la galería de adjuntos minúsculos (`.wb-doc` tiles 96px, ícono 26px) → **galería tipo Notion**:
cards de 148px con **preview grande** (`.wb-doc-preview` 96px de alto + ícono 32px), label y estado; hover con
lift calmo (`translateY(-1px)` + sombra). Cada documento es un `<button>` nativo (teclado-first: Enter/Espacio
disparan el visor sin `role`/`tabindex`/`keyup` hack). Click → visor overlay (drawer, reusa W12/A3; P5:
huella/mock, nunca media cruda). El salto campo→fuente (V1·3 lo dejó como `<button hx-get>` a la evidencia) sigue
vivo. De-red de los enlaces de drawer (`.wb-drawer-trigger`, `.wb-link` → ink) y de `estado-extraido` (azul
`--info` → gris calmo; verde solo para "validado"). CSS muerto `.wb-doc-thumb` eliminado.

**Tests:** `test_a3_wb_doc_abre_visor` migrado (`<button class="wb-doc"` en vez de `role="button"`). Verde.
Validado en navegador: galería Notion + visor abre por el botón, 0 errores de consola.

**Code-review (R1):** 🟢 "cierra sin objeciones" (0 hallazgos; P5 defensa en profundidad, a11y `<button>` nativo).

### V1·5 — Decisión como colega senior

**Implementado:** el panel "Decisión del caso" (head + firma + botones de color) → **`.wb-decidir` como colega
senior**: lidera con **`.wb-reco`** (eyebrow "Acción recomendada" + icono + `rec.titulo` + `rec.texto` + **esfuerzo
estimado** `tiempo_estimado.texto` — que salió del header en V1·1 y aterriza aquí). El copiloto **aconseja, no
decide** (P1: `rec` ya es P1-safe, sin PALABRAS_PROHIBIDAS). **Una acción PRIMARIA dominante** (Radicar, verde
`btn-lg`, gated a LISTO); las demás **secundarias calmas** (`btn-ghost`): Rechazar (rojo destructivo pero no
domina), Escalar a fraude/revisión, Solicitar documentos, Preparar carta, Guardar. Se retiraron los botones
fuera de paleta **azul `.btn-solicitar` y morado `.btn-escalar`** (color con significado). Firma compartida,
`data-confirm` (A4) y guardas P1 intactos.

**Tests:** `test_acciones_una_primaria_resto_secundario` (migrado: `btn-radicar` + `btn-ghost`, sin
`btn-solicitar`/`btn-escalar`); `test_w9_acciones` (textos de acciones) y los de `disabled>Radicar caso` siguen
verdes. 85 tests verdes.

**Code-review (R1 + R2):** 🟢 0 violaciones P1–P6. Ajustes aplicados: (1) P5 defensa en profundidad —
`recomendacion()` redacta `aprobado_por` en el boundary (`_red`); (2) magic numbers → token `--go`/`--go-strong`
(verde firmar/go). R2 aprobó y detectó una a11y BAJA (blanco sobre `#16a34a` ≈ 2.3:1) → `--go` oscurecido a
`#15803d`/`#166534` (≈4.4–6:1, AA con texto blanco).

### V1·6 — Flujo (timeline humano + pulido)

**Implementado:**
- **Cronología HUMANA:** el timeline técnico horizontal `.wb-tl-h` (nodos de agente + tokens "N tok") → `.wb-crono`
  vertical calmo: `[icono] evento [hora]`, renombrado "Lo que hizo la IA" → **"Actividad del caso"**. Los tokens
  salen de la vista por defecto; el rastro técnico REAL (nodos/tokens) vive en el drawer **"Ver actividad
  técnica →"** (encode-not-hide §4: la orquesta se ve a un click, no se oculta; la IA es invisible pero su rastro
  se codifica). CSS `.wb-tl-h*` muerto eliminado.
- **Empty state premium:** el `.wb-caso-empty` (caja punteada + texto plano) → estado calmo centrado (icono ✦ +
  "Todo bajo control" + "Perito ya lo preparó — solo tienes que revisar y decidir"). Nunca un contenedor muerto.
- **Reset de scroll al cambiar de caso** (JS): en `htmx:afterSwap` de `#wb-caso`, `.main` vuelve a top → el título
  enorme del caso nuevo queda visible (resuelve la nota de V1·1).
- **De-red final del flujo:** chips de filtro `.chip.active` y carriles `.wb-carril.active` (rojo `--brand`) →
  ink calmo. Cierra el backlog de acentos: **rojo = solo crítico en toda la Workbench.**

**Tests:** `test_encode_not_hide_timeline_no_colapsa` (migrado: `Actividad del caso` + `wb-crono-step` + "Ver
actividad técnica" accesible), `test_w18`/`test_w3_w4` migrados a `wb-crono`; de paso se corrigió un assert
pendiente de V1·2 (`test_render_resumen_narrativo`: "Resumen del caso"). Validado en navegador: cronología humana,
empty state premium, 0 errores de consola.

---

## Estado del rediseño V1

**Las 7 unidades (V1·0–V1·6) implementadas y revisadas** (cada una Bolt → code-reviewer → ajuste → re-review). El
surface del operador se reinventó de un dashboard enterprise a una **estación de decisión "Cursor for insurance"**:
Caso enorme → banner de estado → historia en prosa → datos-objeto → documentos Notion → decisión como colega
senior → cronología humana. Invariantes P1–P7 + encode-not-hide intactos (reconciliados en §4, no relajados).

**Refinamientos futuros (declarados, P7):** humanizar más las etiquetas de nodo de la cronología (`_NODOS` en
`vista_caso`: "Extractor · Haiku…" → milestone humano) — requiere tocar el view-model, se deja fuera del rediseño
puramente presentacional. Los previews de documentos son íconos hasta M1 (Document AI real).
