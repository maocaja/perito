---
name: front-modernize
description: Sugiere maneras modernas de construir/estilizar el front de Perito (tecnología + estilo, al día), respetando ADR-001 (server-rendered) y P7 (demo honesta). Úsala antes de un Bolt de UI para elegir el enfoque visual y de stack. No implementa; propone y compara.
---

# front-modernize — Sugerencias modernas para el front

Skill de exploración de UI para Perito. **Propone y compara; no implementa.** El objetivo es elegir
conscientemente el enfoque de tecnología y estilo antes de un Bolt de front, sin romper los invariantes.

## Cuándo usarla
- Antes de un Bolt que cree o rehaga UI (bandeja, detalle, panel, ingesta).
- Cuando quieras refrescar el look sin caer en tool sprawl (riesgo #2 del PRD) ni contradecir ADR-001.

## Constraints que NO se negocian (encuádralos primero)
- **ADR-001:** front **server-rendered** (FastAPI + Jinja2 + HTMX), mismo origen, **sin SPA/React/CORS**.
- **P7:** es una **demo honesta** de portafolio, no producto — el esfuerzo de UI debe ser proporcional.
- **Riesgo #2 (tool sprawl):** cada dependencia nueva de front se justifica; preferir 1 archivo vendored a un build pesado.
- **Self-contained deseable:** el demo debe correr offline (vendored CSS/JS mejor que depender de CDN en vivo).

## Procedimiento
1. **Lee el stack actual** de la UI (`backend/app/dashboard/templates/` + `static/`) y el ADR-001.
2. **Propón 2-4 opciones de TECNOLOGÍA** que respeten ADR-001 (upgrades server-rendered), con trade-offs:
   esfuerzo · dependencias · look resultante · si es vendored/offline. Incluye siempre la opción "quedarse".
3. **Propón 2-3 direcciones de ESTILO** al día (para un **dashboard de operaciones de seguros**: profesional,
   data-dense, escaneable, confiable — no flashy). Cita tendencias actuales (clean/minimal, dark+light,
   cards, status badges semánticos, bento, estética fintech).
4. **Recomienda** una combinación (stack + estilo) coherente con los constraints, y di qué NO recomiendas y por qué.
5. **Ofrece un mockup visual** (Artifact HTML) con 2-3 variantes de la misma pantalla (ej. la bandeja) para
   comparar de verdad, no solo describir.
6. Si una opción contradice ADR-001/P7, **decláralo explícitamente** (no lo metas por debajo).

## Salida esperada
Una tabla de opciones (tech + estilo) con trade-offs, una recomendación justificada, y (si se pide) un
Artifact con mockups comparables. Nunca cambia código de la app: es input para decidir el Bolt.
