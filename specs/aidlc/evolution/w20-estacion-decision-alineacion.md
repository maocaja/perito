# W20 — Estación de decisión: alineación con el panel UX (cierre Fase 0/1/2)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1b Hi-fi (declutter)
> **LLM/det:** ⚙️ det (solo UI/plantillas) · **Depende de:** W1–W19 (en rama `feat/workbench-fase-m`) · **Datos:** R
> **Diseño de referencia:** panel UX de 3 especialidades (UX Researcher · Product Designer · AI-first/confianza),
> julio 2026 → convertir el "dashboard completo" en una **estación de decisión** enfocada en el bloqueo actual y
> la siguiente acción, con evidencia bajo demanda.

## 1. Intent

El operador debe **entender el caso en <15 s, identificar el bloqueo y ejecutar la siguiente acción** sin
recorrer varios bloques. El eje es un flujo: **Entender → Revisar → Corregir → Decidir → Radicar → Siguiente**.

**Ya aterrizado (Fase 0/1/2, validado en navegador — este spec lo formaliza retroactivamente):**
- **Fase 0 · declutter:** tabla única de datos (fusiona "Datos del siniestro" + "Información extraída"),
  confianza codificada por campo, health-check compacto.
- **Fase 1 · drawers:** `<dialog>` nativo a la derecha (HTMX) para evidencia, actividad por agente y comparativa.
- **Fase 2 · corrección inline:** form "Corregir y recalcular" con firma (P1); el servidor re-corre C4 + motor
  (P2) y re-pinta sin recarga; origen `HUMANO` auditable; nunca alcanza estado terminal.

Este spec define **lo que aún NO está alineado** con el panel (brechas A1–A5) y **registra las divergencias
deliberadas** (B) para que no se "corrijan" rompiendo un invariante.

## 2. Criterios de completitud (verificables) — las brechas A1–A5

| # | El panel pide | Realidad actual (evidencia) | Naturaleza |
|---|---|---|---|
| **A1** | Sacar **Productividad** de la Workbench (a Reportes/"Mi jornada") | Embebida en `workbench.html` (franja inferior) | ⚠️ **Override W14 · DECIDIDO: sacar a Reportes** |
| **A2** | Bloque **"Necesitas revisar"** dominante, con el campo editable embebido, justo bajo el encabezado | No existe; hay banner de próximo paso + `<details>` "Corregir datos" más abajo | ➕ Re-composición de W4/W5/hitl-corregir |
| **A3** | **Documentos abren visor overlay** ("Usar este valor") al hacer click | `.wb-doc` (`workbench_caso.html:120`) sin `hx-get`; solo hay evidencia **por campo** (W12) | ➕ Extiende W11/W12 |
| **A4** | **Confirmación antes de acciones sensibles** (radicar/escalar) | 5 `<form method=post>` que envían directo (`workbench_caso.html:228-250`) | ➕ Extiende W9 |
| **A5** | **Unificar** Health + Cobertura + Riesgos en "estado operativo"; health como barra "4 de 5 verificaciones" | 3 tarjetas separadas a la derecha; health titulado "Health check %" | ⚠️ **Override W5/W6/W7 · DECIDIDO: fusionar los 3** |
| **A6** | **Una sola superficie de operador** — sin páginas duplicadas | `bandeja.html` (`/`,`/casos`) y `detalle.html` (`/casos/{id}`) conviven como board/caso paralelos; `base.html:65` manda "Analista"→`/casos` | 🔴 **Duplicado · DECIDIDO: board→Bolt-1; detalle→Bolt-2 (port-first)** |
| **A7** | **Portar capacidades exclusivas de `detalle`** antes de borrarlo: **Rechazar** (→RECHAZADO) y **Carta** autogenerada | La Workbench no tiene Rechazar (solo radicar/escalar) ni Carta; viven solo en `detalle.html`/`cartas.py` | 🔴 **P1 (rechazar) + feature (carta) · portar al panel de Decisión** |

**Definición de "hecho" por brecha:**
- **A1** — la Workbench **no** muestra productividad; vive en Reportes / vista "Mi jornada". **(DECIDIDO: override W14
  — actualizar `w14-productividad.md` a "vista de operador, fuera de la Workbench".)**
- **A2** — cuando el caso tiene un bloqueo (póliza no hallada / cobertura en revisión / dato faltante), un bloque
  héroe **"Necesitas revisar"** lo enuncia y ofrece el campo editable + acciones **in situ**; al corregir, el
  bloque cambia a resuelto sin buscar en el panel derecho.
- **A3** — click en un documento abre el drawer con visor + evidencia + "Usar este valor"; reusa el drawer de W12.
- **A4** — radicar/escalar/a-fraude piden confirmación explícita (diálogo nativo) antes del POST; la firma (P1) sigue.
- **A5** — un solo bloque **"Estado operativo"** con preparación (barra "N de M") + cobertura (por qué) + riesgos
  como una sola narrativa; riesgos sigue **condicional** (solo si hay, P6). **(DECIDIDO: override W5/W6/W7 —
  actualizar sus specs a "presentación unificada, contrato de datos intacto".)**
- **A6** — la Workbench (`/workbench`) es la **única** superficie del operador. **(DECIDIDO: port-first — el
  board se consolida en Bolt-1; `detalle` se borra en Bolt-2 tras portar sus capacidades exclusivas, ver A7.)**
  - **Bolt-1 (board):** eliminar `bandeja.html` + rutas GET `/`, `/casos`; `/` → **redirect a `/workbench`**.
    Corregir `base.html:65` "Analista" → `/workbench`. Migrar redirects de `ingest.py:70,82` (`POST /nuevo`,
    preset) → `/workbench?...&caso_id={id}`. **`detalle` se conserva** (custodia carta+rechazar).
  - **Bolt-2 (caso):** tras A7, eliminar `detalle.html` + ruta `/casos/{id}` + `aprobar`/`rechazar` legacy
    (`c11.py:374-401`) + `corregir` legacy (`hitl_actions.py:117-133`); migrar el redirect de `cartas.py:146`.
  - **Se CONSERVAN:** las 5 rutas POST de acción (`radicar/escalar/enviar_fraude/solicitar_docs/guardar_borrador`)
    — ya redirigen a `/workbench` vía `_volver` (`hitl_actions.py:156`).
  - **Se conservan (revisado a fondo, NO duplican):** `/panel` = Cumplimiento/gobernanza (EU AI Act Art. 14 /
    NAIC, trazas + Export PIA) **y** "Reportes/Historial" del analista → **hogar de Productividad (A1)**;
    `/nuevo` = utilidad de ingest para demo.
  - **A1 aterriza aquí:** Productividad se mueve de la Workbench a **`/panel`** (donde el nav "Reportes" ya apunta).
  - **Tests:** 67 refs a `/casos` en 10 archivos → Bolt-1 migra los de board; Bolt-2 los de detalle/acciones.

- **A7** — antes de borrar `detalle` (Bolt-2), portar al **panel de Decisión** de la Workbench:
  - **Rechazar** (→ `RECHAZADO`, `hitl.rechazar`): acción firmada (P1) — hoy la Workbench solo aprueba/escala,
    no puede rechazar. Es una brecha **P1** (el humano debe poder negar, no solo aprobar).
  - **Carta autogenerada** (`preparar_carta`/`enviar_carta`, `cartas.py`): generar borrador + enviar firmado (P1).
    Se integra como acción/drawer del panel de Decisión, reusando `tipo_carta`/`plantilla_carta`/`pulir_prosa`.

## 3. Invariantes / restricciones (heredados, no negociables)

- **encode-not-hide** (regla dura del programa): la confianza y el rastro de la orquesta **se codifican, nunca se
  ocultan**. Ninguna brecha se cierra ocultando confianza o colapsando el rastro.
- **P1** (W9): las acciones siguen preparando; el humano firma; ninguna alcanza estado terminal sin humano.
  A4 **añade** fricción de confirmación, no la quita.
- **P2** (W7): la cobertura la dicta el motor; A5 solo **re-presenta**, no re-decide.
- **P5** (W12): el visor de A3 nunca expone PII cruda; huella/redacción.
- **P6** (W5): riesgos solo sugiere; A5 no puede convertir un riesgo en bloqueo/decisión.
- **ADR-001:** server-rendered (Jinja/HTMX), JS mínimo; la confirmación de A4 es diálogo nativo, sin lógica de
  decisión en cliente.

## 4. Fuera de alcance — divergencias declaradas (P7), NO tocar

Estas partes del panel **se rechazan a propósito** porque violan un invariante. Se registran aquí para que no se
"arreglen" por error:

- **B1 — "no mostrar confianza cuando es alta":** ❌ se rechaza. Perito muestra el **% en todos los campos,
  siempre** (`encode-not-hide` / P7). Ocultarla sería una regresión de transparencia.
- **B2 — "colapsar 'Lo que hizo la IA' a una sola línea":** ❌ se rechaza. El timeline **agent-native** (W18) es la
  orquesta visible, no chrome. Se mantiene condensado, no colapsado.
- **C — filtros de cola como chips `[Todos][Urgentes][Revisión][Listos]`:** equivalente ya cubierto por los
  **carriles** del nav (🔴🟠🟡🟢, W8). No se re-implementa como chips.

## 5. Decisiones (resueltas) — overrides de unidades aceptadas

- **Decisión-1 (A1): ✅ RESUELTO — override W14.** Productividad sale de la Workbench a Reportes / "Mi jornada".
  Consecuencia: actualizar `w14-productividad.md` (§4/§6) a "vista de operador, no franja en la Workbench".
- **Decisión-2 (A5): ✅ RESUELTO — override W5/W6/W7.** Se fusiona la **presentación** en un bloque "Estado
  operativo". El **contrato de datos** de cada unidad NO cambia (Health/Cobertura/Riesgos siguen calculándose
  igual); solo se unifica el render. P6 intacto: riesgos condicional, solo sugiere. Consecuencia: nota de
  override en el §7 de `w5-riesgos.md`, `w6-health-check.md`, `w7-explicacion-cobertura.md`.
- **Decisión-3 (A6): ✅ RESUELTO — borrado duro de duplicados.** `bandeja.html`/`detalle.html` y las rutas
  `/`,`/casos`,`/casos/{id}` se eliminan; `/` redirige a `/workbench`. **Revisado a fondo:** `/panel` (Cumplimiento
  + Reportes) y `/nuevo` (ingest demo) **se conservan** — no duplican la Workbench.

## 6. Verificación (tests fail-closed)

- **A1:** `test_w*`/`test_fase*` — la Workbench no renderiza "Tu productividad hoy"; sí existe en su vista destino.
- **A2:** con caso bloqueado, el HTML contiene el bloque "Necesitas revisar" con el campo editable; al corregir
  (POST `/workbench/corregir`), el bloque refleja resuelto. Estado nunca terminal (P1, reusa asserts de Fase 2).
- **A3:** click en documento → `GET` del drawer con visor; fail-closed "Sin fuente localizada" si no hay ancla (P5).
- **A4:** el POST de radicar/escalar exige confirmación; sin firma sigue rechazando (P1).
- **A5:** el estado operativo muestra preparación "N de M"; riesgos solo aparece si `inconsistencias` no vacío (P6).
- **A5 · fail-closed P6/P1 (code-review P-3):** un caso con **alerta fraude ALTA + cobertura REQUIERE_REVISION +
  health bajo** mantiene la firma habilitada y estado **no terminal** — ninguna combinación H/C/R bloquea ni decide.
- **encode-not-hide (bidireccional, code-review P-5):** ningún cambio elimina el `%` por campo NI colapsa el
  timeline, **y** todos los campos de `datos_principales`/`campos_extraidos` muestran su `%` aunque sea 100%.
- **A6:** `/casos*` responden 404/redirect a `/workbench`; `POST /nuevo` y envío de carta aterrizan en `/workbench`
  (no 404); las 5 acciones POST siguen redirigiendo a `/workbench`.

## 7. Notas CÓMO (para el Bolt — NO ejecutar aún)

- **A2–A5 (UI):** solo plantillas + CSS (ruta **no** protegida): `workbench.html`, `workbench_caso.html`,
  `style.css`, y un partial nuevo para el visor de documento (reusa `workbench_evidencia.html` / drawer de W12).
  Son **re-composición** de contexto ya calculado en `vista_caso.py` (banner, riesgos, health) — sin lógica de
  decisión nueva; DIP intacto (provider/contratos sin cambios). A4: `<dialog>` de confirmación nativo (ADR-001).
- **Bolt-1 (board · A6-board + A1):** en `c11.py` eliminar `bandeja()` (`/`,`/casos`); `/` →
  `RedirectResponse('/workbench')`. Borrar `bandeja.html`. Migrar redirects `ingest.py:70,82` →
  `/workbench?...&caso_id={id}`. `base.html:65` "Analista" → `/workbench`. Mover la franja de Productividad de
  `workbench.html` a `panel.html`. Migrar los tests de **board** (`/casos?...`, bandeja) a `/workbench`.
  **`detalle` intacto** (custodia carta+rechazar hasta A7).
- **Bolt-2 (caso · A7 + borrado detalle + A2–A5):** **primero** portar Rechazar + Carta al panel de Decisión
  (A7); **luego** borrar `detalle.html`, `detalle()`/`aprobar()`/`rechazar()` (`c11.py:363-401`), `corregir`
  legacy (`hitl_actions.py:117-133`), migrar `cartas.py:146` → `/workbench`; y la recomposición A2–A5 (Necesitas
  revisar, visor de docs, confirmación, Estado operativo). Migrar los tests de detalle/acciones.
- **Se CONSERVAN** en ambos: las 5 rutas POST de acción (`radicar/escalar/enviar_fraude/solicitar_docs/
  guardar_borrador`) — ya redirigen a `/workbench`.
- Cadencia: **Bolt → code-reviewer (P1/P5/P6 + encode-not-hide) → §8.**

## 8. Precisiones tras code-review (Ronda 1 — QUÉ)

**Veredicto:** 0 violaciones de P1/P2/P4/P5/P6 en el QUÉ. Los hallazgos son **acoplamiento de rutas** y
**precisión de verificación**, resolubles sin revertir principios. Precisiones aplicadas:

- 🔴 **P-1 (acoplamiento subestimado — CRÍTICO):** A6 solo contemplaba los redirects de `hitl_actions.py`, pero
  **3 POST más redirigen a `/casos/{id}`**: `ingest.py:70` (`POST /nuevo`), `ingest.py:82` (preset) y
  `cartas.py:146` (envío de carta). Bajo **port-first**: los 2 de `ingest` migran en **Bolt-1** (aterrizan en la
  Workbench); `cartas.py:146` y el `corregir` legacy (`hitl_actions.py:133`) migran en **Bolt-2** (siguen
  válidos mientras `detalle` viva — no rompen hasta que se borre).
- 🔴 **P-2 (claridad A6):** las **5 rutas POST de acción** (`radicar/escalar/enviar_fraude/solicitar_docs/
  guardar_borrador`, `hitl_actions.py:168-235`) **se CONSERVAN** (son acciones, no páginas) y **ya redirigen a
  `/workbench`** vía `_volver`. Solo se borra: las páginas GET (`/`,`/casos`,`/casos/{id}`) y el `corregir` legacy
  (117-133). Las rutas de acción no se mueven.
- 🟠 **P-3 (A5 · test P6 fail-closed):** añadir a §6 aserción de que un caso con **alerta ALTA + cobertura
  REQUIERE_REVISION + health bajo** sigue con firma habilitada y estado **no terminal** — la fusión de
  presentación no puede hacer que un riesgo bloquee (P6/P1).
- 🟠 **P-4 (A3 · P5 en el visor):** el visor de documentos reusa la redacción/ancla de W12 y su fail-closed
  ("Sin fuente localizada"). La redacción **visual** de imágenes sigue diferida (M1/fase 2, `gov-rules-p5-p6.md`):
  hasta entonces, huella, nunca media cruda con PII.
- 🟡 **P-5 (encode-not-hide · aserción bidireccional):** el test de §6 no solo verifica que el `%` no se elimina,
  también que **se muestra en todos los campos** de `datos_principales`/`campos_extraidos`, aunque sea 100%.
- 🔵 **P-6 (recuento de tests):** son **67 refs a `/casos` en 10 archivos** (no ~10). Plan: separar GET
  bandeja/detalle (eliminar) · asserts de ruta (migrar a `/workbench`) · POST de acción (se conservan, solo cambia
  el destino del redirect si aplica).
- ✅ **Rutas protegidas:** confirmado — W20 no toca `rules/` ni `orchestrator/`.
- ✅ **Sin duplicación oculta:** las plantillas `workbench*` son nuevas (shell + drawers), no duplican bandeja/detalle.
- 🔴 **P-7 (detalle NO es puro duplicado — hallazgo durante Bolt-1):** `detalle.html` carga 2 capacidades ausentes
  en la Workbench: **Rechazar** (→RECHAZADO, brecha **P1**) y **Carta** autogenerada. `aprobar` legacy sí es
  redundante (radicar ya llama `hitl_aprobar`). → **Re-secuenciado a port-first (A7):** el board va en Bolt-1;
  `detalle` se borra en Bolt-2 tras portar Rechazar+Carta. Evita regresión de capacidad.

### Ronda 2 — code-review de Bolt-1 (implementación board + A1)

**Veredicto:** verde. 530 tests, rutas verificadas en vivo (`/`→303 `/workbench`, `/casos`→404, Productividad
en `/panel` no en Workbench). 0 regresiones de P1/P5/P6; detalle/carta/rechazar/acciones POST intactos. Fixes
aplicados:
- ✅ **B1-fix (link roto):** `detalle.html` "Volver" apuntaba a `/casos` (ahora 404) → `/workbench?...&caso_id`.
- ✅ **B1-fix (dead code):** removidas 4 vars Jinja muertas (`is_workbench/is_bandeja/is_nuevo/is_panel`,
  `base.html`) y el CSS huérfano `.grid-bandeja*` (`style.css`).
- ⏭️ **Diferido a Bolt-2 (no rompe ahora, `detalle` vive):** migrar `cartas.py:146` y el `corregir` legacy
  (`hitl_actions.py:133`) a `/workbench`; se hará al borrar `detalle`.

### Ronda 3 — code-review de Bolt-2a (A7: portar Rechazar+Carta + borrar detalle)

**Veredicto:** verde. 526 tests. El reviewer verificó (✅) P1 (Rechazar exige firma+motivo, 409 si terminal,
solo vía `hitl.rechazar`; Carta: draft≠send, envío no muta el caso, fail-safe SMTP sin 500), P2/P7 (guardrail
`cita_intacta` intacto), P5 (drawer redactado), sin conflicto de rutas, borrado limpio de `detalle`. Verificado
en vivo: Rechazar→RECHAZADO (PRG a `/workbench`), Carta drawer preparar→enviar. Fix aplicado:
- ✅ **B2a-fix:** `test_p1_rechazar_ok` afirmaba `==200` (pasaba siguiendo el redirect) → apretado a `303` +
  `location` + estado, consistente con el sibling `radicar`.
- ✅ **detalle eliminado:** ya no hay páginas duplicadas; carta+rechazar portadas sin pérdida de capacidad (P1).

### Ronda 4 — code-review de Bolt-2b (A2–A5: recomposición de jerarquía)

**Alcance:** solo UI (plantillas Jinja/HTMX + CSS) + **una ruta GET nueva** (`/workbench/documento/{id}`, A3). NO
toca `rules/` ni `orchestrator/`. Implementado:
- **A2** — bloque héroe **"Necesitas revisar"** con el campo editable EMBEBIDO cuando el caso está bloqueado
  (`REQUIERE_REVISION`); banner calmo si no. La corrección reusa `/workbench/corregir` (firma P1, 409 si terminal,
  nunca terminal). Un solo form de corrección visible a la vez (hero XOR colapsable `LISTO_PARA_APROBAR`).
- **A3** — los documentos abren un **visor overlay** (drawer, reusa W12) vía `hx-get`; ruta nueva sirve
  etiqueta/huella/mock. Fail-closed a "Documento no encontrado" (índice inválido). P5: nunca media cruda ni el
  nombre de archivo; "Usar este valor" deshabilitado (extracción real → M1, P7).
- **A4** — confirmación **nativa** (`data-confirm` + `confirm()`) antes de radicar/rechazar/escalar/fraude; el gate
  real sigue en el servidor (P1). ADR-001: sin lógica de decisión en cliente.
- **A5** — Health+Cobertura+Riesgos fusionados en un solo bloque **"Estado operativo"**; health como barra
  **"N de M verificaciones"** (encode-not-hide, no un %). Contratos de datos intactos (W5/W6/W7 se calculan igual).

**Veredicto:** 🟢 **verde — 0 violaciones P1–P6.** El reviewer verificó (✅): P1 (radicar/rechazar/corregir exigen
firma, 409 si terminal, la confirmación A4 no sustituye el gate del servidor); P2 (cobertura sigue del motor,
"no el LLM"); P5 (visor sin media cruda ni nombre de archivo, boundary redactado); **P6/P1 fail-closed** (la fusión
A5 NO convierte alerta ALTA + cobertura REQUIERE_REVISION + health bajo en un bloqueo — la firma sigue habilitada,
el estado intacto); encode-not-hide (`%` visible en todo campo incl. 100%, timeline no colapsado); Clean Code/SOLID
(nombres dicientes, sin código muerto, DIP: el visor depende del provider `documentos_de`). "Commit seguro para
merge." Sin findings que aplicar.

**Tests (fail-closed):** `test_w20_bolt2b.py` (12) — A2 hero-vs-banner + exclusión mutua del form · A3
visor/fail-closed/404/P5-sin-nombre-crudo · A4 `data-confirm` + gate del servidor intacto · A5 fusión + barra
"N de M" + **combinación P6/P1 no bloquea** · encode-not-hide bidireccional (`%` al 100% + timeline visible).
Migrados: `test_w6_health` (Health→"Estado operativo"/barra N-de-M), `test_w5_riesgos` (fix de un assert latente
que buscaba `/aprobar`, retirado en Bolt-2a → apuntado a `/radicar`). Suite: **538 passed, 3 skipped** (`make test`).

**Validación en navegador (Playwright, server fresco):** confirmado A2 (hero "Necesitas revisar — Falta 1 dato"
con campos + firma + "Corregir y recalcular"), A5 ("Estado operativo" con barra "N de M" + cobertura P2 + riesgos
condicional), A3 (visor overlay "Denuncia Policía" con huella/mock, "Usar este valor" off, sin nombre crudo), A4
(los `confirm()` disparan), encode-not-hide (`%` en todo campo, `[REDACTED]` en PII, timeline visible). **0 errores
de consola.** Gotcha atrapado: el visor A3 dio 404 con el server **viejo** (código Python cacheado); reinicio del
proceso → ruta registrada → 200. Los templates se leían frescos, pero una ruta nueva exige reiniciar el server.
