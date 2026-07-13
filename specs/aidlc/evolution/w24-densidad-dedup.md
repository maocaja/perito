# W24 — Densidad y dedup (segunda pasada de precisión)

> NO cambia arquitectura (Cola → Caso → Acción → Evidencia → Actividad). Feedback fuente: review del usuario
> tras W23 ("cada elemento en pantalla debe justificar su existencia; si un dato ya responde una pregunta en
> un lugar, no debe responder la misma en otro"). Cadencia AI-DLC: por unidad Bolt → code-reviewer → ajustar →
> bitácora → siguiente. Regla de oro (heredada): MOVER/DEDUP, no borrar el rastro; encode-not-hide.

## §1 · Principio
El estado/la señal se dice **una vez**, en su lugar autoritativo. Las copias se eliminan (no el dato canónico).
🔒P2: la cita de regla+cláusula vive en "Cobertura · por qué → Ver regla aplicada" (panel derecho) — es el
único hogar; se eliminan las COPIAS (strip, prosa), nunca la cita. 🔒P1: la firma sigue obligatoria en el
servidor; solo cambia *cuándo* se muestra. P7: sin SLA inventado (no hay due-date en el modelo; se usa
`timestamp_creacion` para "esperando hace X", real).

## §2 · Unidades

### Prioridad 0 — los 4 del usuario

**N1 · Un solo estado por pantalla.** Quitar la tarjeta "Cobertura" del strip (`confianza_riesgo`) y la línea de
cobertura de la prosa del resumen. Queda: banner (arriba) + "Cobertura · por qué" (panel derecho, con "Ver regla
aplicada"). 🔒P2: la cita NO se borra, se queda en el panel derecho.

**N2 · Resumen ejecutivo.** `resumen_narrativo`/`resumen_ejecutivo` → una línea de conteo+señal: "3 de 4 datos ·
falta 1 obligatorio ({campo}) · sin fraude · cobertura pendiente de regla." (derivado de salidas reales, P7).
Menos prosa, cero duplicación con los campos. (Decisión del usuario: conteo+señal una línea.)

**N3 · Reportes enfocado.** Aclarar "Hoy: N procesado" vs "Backlog: N"; colapsar "Garantías y trazabilidad" bajo
"✔ Cumple · Ver controles"; Tokens/Costo → `<details>` "Detalle técnico" al pie (encode-not-hide: el dato sigue,
no compite con lo operativo). (Decisión del usuario: colapsar, no borrar.)

**N4 · Cola con contexto real.** Cada card suma, además de prioridad: `razon_cola` (ya existe), señal de fraude 🕵️
destacada, y "esperando hace X" (de `timestamp_creacion`). Sin SLA falso (gap declarado, P7).

### Prioridad 1 — refinamientos

**N5 · Origen por dato.** Chip ✓ IA / ✍ Manual (+ fuente correo/PDF/foto) por campo en "Datos del siniestro"
(reusa `origen`/`fuente`/`clase`).

**N6 · Firma única en el punto de acción.** La firma deja de flotar arriba del panel derecho; aparece con la
acción terminal (Radicar/Rechazar). 🔒P1: el gate server-side se mantiene; solo cambia la posición/momento.

**N7 · Actividad colapsable.** "Actividad del caso" → últimos 4 + "Ver timeline completo" (`<details>`).

**N8 · Menos texto/badges.** "La preparación es informativa…" → tooltip; strip de señales ~25% más compacto.

**N9 · Detalles.** Documentos con icono de origen (no "Correo" repetido); "Preguntar a la IA" → "Explicar
decisión"; unir banner "Aprobado" + tarjeta "Caso radicado"; acortar "No encontrado — ingrésalo arriba".

## §3 · Reconciliación de invariantes
- **P2** — la cita de regla+cláusula se mantiene en el panel derecho ("Ver regla aplicada"); N1 elimina copias.
- **P1** — la firma sigue obligatoria (servidor); N6 solo la reposiciona al punto de acción.
- **P7** — sin SLA inventado; el resumen ejecutivo deriva de salidas reales; Tokens/Costo se colapsan, no se borran.
- **encode-not-hide** — colapsar (garantías, actividad, detalle técnico) es `<details>`, no borrado.
- ⚠️ "Regla PRE_MOTOR" NO se resucita en superficie (W23 la movió por pedido del usuario); vive tras "Ver regla".

## §4 · Orden
P0: N1 → N2 → N3 → N4. Luego P1: N5 → N9. Code-review por grupo (N1+N2 juntas por P2; N3; N4; N5–N9).

## §5 · Bitácora

### N1+N2 — Un solo estado + resumen ejecutivo
- **Bolt:** `confianza_riesgo` deja de emitir la tarjeta "Cobertura" (queda en el panel derecho, P2 intacto);
  `resumen_narrativo` → línea ejecutiva "N de M datos · [falta X obligatorio (labels)] · {fraude} · {cobertura}"
  (deriva de salidas reales, P7; sin id de regla/enum). Eyebrow "Resumen del caso" → "Resumen IA". 8 tests
  migrados (formato). Suite 623 verde. Ejemplos verificados por escenario (faltantes/feliz/negativa/fraude).
- **Decisión abierta (a revisar en navegador):** el strip [Extracción·Verificación·Fraude] y el resumen
  ejecutivo comparten señal (conteo, fraude). Se mantuvieron ambos por pedido literal del usuario (resumen
  ejecutivo + strip compacto en N8); si en la verificación visual se ve duplicado, se propone fundir.

### N3 — Reportes enfocado
- **Bolt:** `panel.html` — "Métricas de operación" → "Qué está pasando" (2 KPIs: Backlog total + % escalado);
  Tokens/Costo bajan a `<details>` "Detalle técnico" (encode-not-hide); Garantías → `<details>` "✔ Cumple ·
  Ver controles"; "Mi jornada" → "Cómo voy hoy". `_productividad.html`: "Casos procesados" → "Procesados hoy"
  (aclara Hoy vs Backlog). 2 tests migrados. Suite 623 verde.

### N4 — Cola con contexto real
- **Bolt:** la cola YA traía `hace`/`razon`/`senal_fraude`; el problema era jerarquía. `workbench.html`: acento
  lateral por carril (`wb-cr-<carril>`, urgencia escaneable), fraude 🕵️ resaltado y arriba, "🕒 esperando {hace}"
  (real, de `timestamp_actualizacion`), prioridad al pie. Sin SLA falso (gap declarado, P7). Suite 623 verde.

### Code-review lote P0 (N1–N4)
- **COMPLIANT total** — P1/P2/P5/P6/P7 + encode-not-hide verificados uno a uno. 🔒P2: la cita de regla+cláusula
  vive íntegra en el panel derecho (`explicacion_cobertura`), N1 solo quitó la copia del strip. P7: "hace X" es
  real (timestamp), sin SLA inventado; N2 no filtra id de regla ni enum. Sin hallazgos → sin 2ª pasada.

### N5 — Origen por dato (rev W24.1: la IA es invisible)
- **Bolt:** `CampoUI.manual` (True si `origen.tipo==HUMANO`); helper `icono_fuente` (📧/📄/📷/✍/📎). Filtro Jinja
  `icono_fuente`. Tests +5.
- **Revisión (feedback del usuario):** el badge "IA" por fila viola el principio "la IA desaparece del flujo
  operativo" (ruido tipo "⚡Eléctrico en cada botón"). Corregido: se muestra el **ORIGEN** del dato (📧 Correo /
  📄 SOAT / 📷 Fotos) —aporta contexto/trazabilidad—, sin rotular "IA"; la única excepción marcada es "✍ Manual"
  (lo escribió el operador), que sí cambia cómo se lee el dato. Título "Resumen IA" → **"Resumen automático"**.
  3 tests migrados. Suite 636 verde. Verificado: 0 badges "IA" por fila.

### N6 — Firma única en el punto de acción (P1)
- **Bolt:** se quitó el `#wb-firma` flotante del tope del panel; ahora la firma va CON la acción terminal
  (Radicar/Escalar) o, si la primaria abre un drawer (Preparar) o no hay primaria, dentro de "Más acciones"
  (rechazar/escalar). Macro `firma_input`; condición `firma_con_primaria = rec.accion and not drawer`. 🔒P1:
  EXACTAMENTE un `#wb-firma` por estado (verificado) y el gate REAL sigue en el servidor (usuario requerido).
  Tests +3; 1 W23 migrado (ayuda contextual). Suite 627 verde.

### N7 — Actividad colapsable
- **Bolt:** timeline → últimos 4 visibles + "Ver los N eventos anteriores" (`<details>`, macro `crono_step` DRY).
  encode-not-hide: el timeline completo sigue en el DOM.

### N8 — Menos texto/badges
- **Bolt:** "La preparación es informativa…" → tooltip (ⓘ en el header, texto en `title`); strip ~25% más
  compacto (gap/padding/min-width/font reducidos).

### N9 — Detalles
- **Bolt:** "Preguntar a la IA" → "Consultar el caso" (menos repetición de 'IA'); banner de estado + tarjeta de
  confirmación FUSIONADOS en caso terminal ("✅ Caso aprobado y radicado", una sola tarjeta); "No encontrado —
  ingrésalo arriba" → "Ingrésalo arriba" (el chip de la derecha ya dice "No encontrado", sin duplicar).
  2 tests migrados. Suite 631 verde.

### Code-review lote P1 (N5–N9)
- **COMPLIANT — listo para merge.** P1/P2/P5/P6/P7 + encode-not-hide intactos. 🔒P1/N6: exactamente UN
  `#wb-firma` por estado (LISTO/REQUIERE_REVISION con y sin faltantes/terminal — verificado) y el gate real
  sigue en el servidor (radicar sin `usuario` → 400). N5 no expone PII y no revienta (default 📎). N7/N8/N9
  colapsan/fusionan sin borrar. Sin hallazgos bloqueantes → sin 2ª pasada.
- **Hallazgo MEDIUM (UX, preexistente, NO de W24):** en casos terminales, "Más acciones" aún ofrece secundarias
  como "Solicitar documentos" (no cambian estado; el servidor no las bloquea). Anotado para una pasada futura;
  no bloquea W24.

## §6 · Cierre
W24 completa (N1–N9). Suite **636 passed**, 3 skipped. Todos los invariantes P1–P7 + encode-not-hide verdes por
code-review en dos lotes (P0 y P1). Se eliminó repetición (estado ×3 → ×1; resumen ejecutivo; firma única en el
punto de acción; banner+tarjeta fusionados) SIN borrar dato (cita de regla, tokens/costo, garantías, timeline,
% de confianza siguen a un click). Sin tocar `rules/` ni `orchestrator/`. Pendiente: commit (staged; lo decide
el usuario) + reinicio del server para revisión visual + (opcional) el MEDIUM de secundarias en terminal.
