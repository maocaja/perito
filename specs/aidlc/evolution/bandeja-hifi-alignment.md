# Unit de Evolución — Alinear la Bandeja al prototipo hi-fi (K)

> **Tipo:** spec a nivel de cambio (brownfield) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Construye sobre:** Unit J (rediseño hi-fi) · **Insumo:** prototipo `Perito Dashboard.html` (vista bandeja).

## 1. Intent

Acercar la **tabla de la bandeja** al prototipo hi-fi (columnas, espaciado, look de filas), **respetando
P7 (demo honesta)**: el prototipo pinta datos que **no existen** en el modelo real (nombre de asegurado,
id tipo `FNOL-2026-0142`), y esos **no se inventan**. Se alinea todo lo alineable con dato real y se
**flaguea** lo que requiere datos nuevos.

## 2. Restricción dura (P7) — lo que NO se hace

Verificado contra el modelo (`contracts/caso.py`, `contracts/poliza.py`, `contracts/extraccion.py`):
- **NO existe** nombre de asegurado/titular en `Caso`, `Poliza` ni la extracción → **no se muestra ni se
  inventa** un nombre (viola P7). Se **flaguea** su extracción como unidad futura (§6).
- El `id` del caso es **uuid** → se muestra `#uuid[:8]`; **no** se fabrica un id `FNOL-…`.
- **RAMO** no es un campo, pero se puede **derivar** de `tipo_siniestro` (dato real) — eso es honesto.

## 3. Criterios de completitud (verificables)

1. **Columnas nuevas** (espejo del prototipo, con dato real): `CASO · PÓLIZA · RAMO · ESTADO · DICTAMEN ·
   FRAUDE · MONTO`. Reemplaza el layout actual (`Caso · Siniestro · Póliza · Estado · Dictamen · Fraude ·
   Monto`).
   - **CASO**: `#uuid[:8]` (conserva el chip "recién"/hora de la demo en vivo, Unit H).
   - **PÓLIZA** (ocupa el slot visual del "Asegurado" del prototipo, misma estructura "principal + sub"):
     `numero_poliza` en negrita + `fecha_siniestro` debajo. **Sin nombre de persona** (P7). Header: "Póliza".
   - **RAMO**: ramo **derivado** de `tipo_siniestro` (ver criterio 2).
   - **ESTADO · DICTAMEN · FRAUDE · MONTO**: como hoy (badges + monto a la derecha).
2. **Ramo derivado (passive, honesto):** helper de presentación que mapea el valor de `tipo_siniestro`:
   `AUTO_*` → "Autos", `HOGAR_*` → "Hogar"; **ausente o sin match** → "—". **No hay "Vida"** (no existe en
   el dominio) — no se inventa. Cero lógica de dominio, solo agrupación de un dato real para mostrar.
3. **Look de filas como el prototipo:** filas **uniformes** — se **quita** el acento izquierdo de accionables
   y el atenuado (`opacity`) de resueltos que introdujo la Unit J; se **aumenta el alto/padding** de fila
   (más aireado). (Supersede la "jerarquía de filas" de Unit J por decisión de producto: el prototipo de
   referencia las muestra uniformes.)
4. **Se conserva** lo de Unit H/J: KPIs clicables (toggle), chips de filtro, auto-refresh HTMX
   (`#bandeja-live`), notificaciones/toasts. La alineación **no rompe** el swap HTMX.

## 4. Restricciones e invariantes

- **P7:** nada fabricado. Asegurado no se muestra; ramo se **deriva** de dato real y cae a "—" si no mapea;
  id sigue uuid.
- **P5:** no se introduce PII nueva (no se añade nombre de asegurado, que además hoy no tiene NER).
- **ADR-001:** server-rendered; sin JS nuevo (es tabla + CSS).
- **Solo `dashboard/`:** no toca contratos, `rules/` ni `orchestrator/`.

## 5. Fuera de alcance

- Cambiar el detalle, el panel o "nuevo aviso".
- Fabricar id FNOL o nombres.

## 6. FLAG — unidad futura (no en esta Unit)

**Extracción del asegurado:** para que la bandeja muestre el **nombre real del titular** (como el prototipo)
haría falta: (a) extraer `asegurado` del aviso en el extractor (U2, `app/llm/`), (b) redactarlo con **NER**
(P5 — hoy el redactor no cubre nombres, gap declarado en `security/redaction.py`), (c) re-verificar evals.
Es una unidad aparte (toca capa de extracción + seguridad), no `dashboard/`. Se documenta como backlog.

## 7. Verificación (tests fail-closed)

- **Ramo:** `AUTO_COLISION`→"Autos", `HOGAR_AGUA`→"Hogar", `tipo_siniestro` ausente/otro→"—". Sin "Vida".
- **Columnas:** la bandeja renderiza las 7 cabeceras nuevas; la col 2 muestra `numero_poliza` (no un nombre).
- **P7:** la bandeja **no** contiene ningún nombre de persona fabricado ni id `FNOL-`.
- **Filas uniformes:** el markup ya **no** trae `row-accent`/`row-muted`.
- **No regresión:** KPIs clicables, chips y `#bandeja-live` (HTMX) intactos.

## 8. Notas para el CÓMO (Bolt) — no vinculantes

Archivos: `templates/bandeja.html` (columnas + quitar clases de jerarquía), `static/style.css`
(grid de columnas nuevo, alto de fila, quitar `.row-accent*`/`.row-muted`), y un helper `ramo_de(tipo)`
(en `vista_caso.py` o `_macros.html`, passive). Reusar `campo_valor`/badges existentes. Tests en
`tests/test_evolution_frontend_hifi.py`.
