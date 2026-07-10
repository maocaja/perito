# W1 — Workbench unificada 3-columnas (shell)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R (reusa view-models de U1)

## 1. Intent

Una **sola estación** (como Cursor, para seguros): el operador nunca cambia de app ni pierde contexto. Fusiona
la bandeja y el detalle de hoy (páginas separadas) en **tres columnas** persistentes:
**izquierda = cola inteligente** (W8) · **centro = la historia del caso** (header W2, timeline W3, resumen W4,
evidencia, documentos) · **derecha = acciones + alertas + formulario pre-diligenciado** (W9).

## 2. Criterios de completitud (verificables)

1. **Ruta `/workbench`** (server-rendered, ADR-001) que renderiza las 3 columnas en una sola vista.
2. **Columna izq:** la cola (reusa `_filtrar_bandeja`/`prioridad`/`clasificar`); seleccionar un caso **carga el
   centro sin recargar toda la página** (HTMX `hx-get`/`hx-target` de la columna central).
3. **Columna centro:** slots para W2-W7/W11-W12 (empiezan con lo que hoy vive en `detalle.html`).
4. **Columna der:** slots para W5 (riesgos), W6 (health), W9 (acciones).
5. **Sin pérdida de contexto:** al actuar sobre un caso, la cola y el foco se mantienen (no navegar fuera).
6. **Bandeja/detalle actuales quedan** como rutas vivas (no romper tests) hasta migrar del todo.

## 3. Invariantes / restricciones

- **ADR-001:** server-rendered (Jinja2/HTMX), JS mínimo (selección + swaps); **cero lógica de decisión en
  cliente** (P1). Los view-models siguen **passive**.
- **P1/P2:** la estación solo **presenta**; el gate real (aprobar/rechazar) sigue en `hitl`/servidor.
- **Responsive/a11y:** la workbench mantiene foco de teclado y contraste (Vercel Web Interface Guidelines).

## 4. Fuera de alcance

- El contenido nuevo de cada panel (eso es W2-W14); W1 es **el esqueleto y el cableado HTMX**.
- Borrar bandeja/detalle (se depreca después, no en W1).

## 5. Verificación (tests fail-closed)

- `GET /workbench` responde 200 con las 3 columnas.
- Seleccionar un caso hace `hx-get` del centro (parcial) sin recargar el shell.
- Ningún JS decide cobertura/estado (aserción: no hay lógica de decisión en el cliente).
- Bandeja/detalle siguen respondiendo (retro-compat, tests actuales verde).

## 6. Notas CÓMO

Nueva ruta en `dashboard/c11.py` + plantillas `workbench.html` (+ parciales por columna) reusando
`vista_caso.py`. Estilos en `static/style.css` (grid de 3 columnas). Reusa HTMX ya presente (`htmx.min.js`).

## 7. Precisiones tras code-review (CÓMO)

- **🟠 Guard `caso.extraccion` None:** `{% for … if caso.extraccion %}` reventaba si la extracción faltaba →
  envuelto en `{% if caso.extraccion %}…{% else %}Sin datos extraídos{% endif %}`. + test dedicado.
- **🟠 P5 defensa en profundidad:** `recomendacion.titulo/texto` pasan por `|redact` (aunque hoy son genéricos).
- **UX deliberada (no bug):** el auto-refresh de la cola (`every 3s`) actualiza **solo `#wb-cola`**, NO el
  `#wb-caso` activo — recargar el caso bajo el operador mientras trabaja sería peor. La sincronización de
  estado del caso activo se maneja tras una acción (W9/W10), no por polling.
