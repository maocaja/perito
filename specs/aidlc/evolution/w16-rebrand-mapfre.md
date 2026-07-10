# W16 — Rebrand "Claims Copilot" (identidad visual MAPFRE)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1b hi-fi
> **LLM/det:** — (front) · **Depende de:** W1 · **Datos:** R

## 1. Intent

Que la estación se vea **tal cual el mockup hi-fi**: sobria, corporativa, **no** el look genérico de IA. Marca
**MAPFRE** (rojo de acento) + nombre **"Claims Copilot · AI"**, sidebar navy con navegación de íconos, barra de
búsqueda superior, acciones con color semántico, y la fila inferior de paneles. La estética refuerza el
mensaje: un copiloto experto, no un formulario.

## 2. Criterios de completitud (verificables)

1. **Tokens de color** nuevos (theme-aware): acento **rojo MAPFRE**, **sidebar navy** oscuro, blancos limpios,
   **confianza en verde**, acciones semánticas (Radicar verde · Solicitar azul · Escalar/Fraude morado).
2. **Marca:** logo/nombre "Claims Copilot · AI" (hoy "Perito / Admisión de siniestros"). Configurable (no
   hardcode disperso).
3. **Sidebar navy con nav de íconos:** Inbox · En Proceso · Pendientes · Radicados · Escalados · Historial ·
   Reportes · Ayuda · Colapsar (mapeados a rutas/filtros existentes; los que no existan → placeholder honesto).
4. **Barra de búsqueda superior** ("Buscar por póliza, cliente, placa, caso… ⌘K") — UI + endpoint de búsqueda
   simple sobre la cola (por póliza/tipo/caso; placa cuando exista M2).
5. **Tarjetas de cola ricas:** `#CAS-…`, nombre, tipo, `Póliza | Placa`, contadores ✉/🖼/✓% (placa/conteos
   mock hasta M1/M2, rotulados).
6. **Layout de 5 paneles inferiores** (productividad · comparativa · documentos · evidencia · historial) como
   contenedores (su contenido es W11-W15).

## 3. Invariantes / restricciones

- **ADR-001:** server-rendered, JS mínimo; solo estética/estructura, cero lógica de decisión.
- **Theme-aware:** claro/oscuro con los nuevos tokens (no romper el toggle actual).
- **P7:** "MAPFRE" es el **contexto de la demo** (marca del cliente objetivo), rotulado como tal; los datos
  de marca no se confunden con datos de caso.
- **No romper** rutas/tests actuales (bandeja/detalle/panel siguen vivos).

## 4. Fuera de alcance

- El contenido de los 5 paneles (W11-W15) y los campos ricos (W17/M2). Aquí van el marco y los colores.

## 5. Verificación (tests fail-closed)

- `/workbench` responde 200 con la marca "Claims Copilot" y el nav de íconos.
- La búsqueda superior filtra la cola por póliza/tipo/caso (test).
- El tema claro/oscuro sigue funcionando (tokens definidos en ambos).
- Tarjetas de cola muestran `#CAS`, nombre, tipo, póliza (placa/conteos rotulados si mock).

## 6. Notas CÓMO

Tokens en `static/style.css` (rojo/navy); `base.html`/`workbench.html` (marca, sidebar de íconos, búsqueda);
nuevo endpoint de búsqueda simple en `c11.py`. Config de marca centralizada.

## 7. Precisiones tras code-review

- **🟡 Config de marca centralizada:** en `config.py` — `WORKBENCH_BRAND` (env-overridable, default "perito"),
  `WORKBENCH_TITLE` ("Claims Copilot · AI"), y `WORKBENCH_SIDEBAR` (lista de `{label, icon, route}`). Las
  plantillas leen de ahí (cero hardcode disperso); "MAPFRE" es contexto de demo, rotulado.
- **Mapeo del nav a rutas EXISTENTES:** Inbox→`/workbench` · En Proceso/Pendientes/Radicados/Escalados→
  `/workbench?carril=…`|`?estado=…` (filtros de W8/bandeja) · Historial→traza (`/panel` o vista de historial)
  · Reportes→`/panel` · Ayuda→placeholder honesto. Ítems sin destino real → deshabilitados/rotulados, no falsos.

### Tras el CÓMO
- **Clean Code/SOLID ✓:** marca en un módulo único (`branding.py`, SRP), inyectada a las 2 instancias de
  templates vía `registrar()` (DRY), plantillas dependen de la abstracción (DIP). `nav_icons.get(…, '')`
  fail-closed. Acoplamiento carril/estado del sidebar declarado en comentario.
- **Bug corregido:** el helper `_coincide_busqueda` había quedado entre el decorador y `def workbench` →
  movido arriba (mismo patrón que el poller). Retro-compat: bandeja/detalle/panel/nuevo siguen 200.
