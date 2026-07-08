# Unit de Evolución — Métricas agregadas del panel de cumplimiento (F2 / H-21)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.

## 1. Intent

El panel de Cumplimiento (`/panel`) hoy solo lista trazas por caso. F2 le agrega **métricas agregadas de
operación** para que sea la "operación auditable y medible" que pide el PRD (UC5), cerrando H-21 (diferido
desde el dashboard C11).

## 2. Qué cierra

- **H-21** (métricas agregadas del panel). **UC5** (Cumplimiento/Ops: operación auditable + costo/caso).
- **P3** (trazabilidad medible: % de dictámenes que citan cláusula).

## 3. Criterios de completitud (verificables)

1. **Sección "Métricas de cumplimiento"** en `/panel`, de datos existentes (`CasoRepository` + `ReplayStore`),
   SIN ground truth. **Dividida HONESTAMENTE en dos (P7 — no confundir medición con garantía):**

   **A) MÉTRICAS MEDIDAS (operación):**
   - Volumen total + **distribución por estado** (LISTO_PARA_APROBAR / REQUIERE_REVISION / APROBADO / RECHAZADO).
   - **Distribución por dictamen** (CUBIERTO / CUBIERTO_PARCIAL / NO_CUBIERTO / REQUIERE_REVISION).
   - **Alertas de fraude por severidad** (BAJA/MEDIA/ALTA).
   - **% escalado** = casos con estado **REQUIERE_REVISION** / total (solo ese estado).
   - **Tokens totales + costo estimado** (tasa blended documentada, rotulado "estimado · no facturable").

   **B) GARANTÍAS (invariantes verificadas por validador/tests — NO métricas medidas, rotuladas como garantía):**
   - **Dictámenes terminales con cláusula: N/N** — garantía RULE-CTR-03 (el validador lo enforce; no es medición de calidad).
   - **Terminación dentro de cotas (P4):** garantía verificada por **aserción en los evals** (RNF-09), NO medida en el
     panel (el `ReplayStore` no guarda rondas/presupuesto). Se muestra como sello, no como %.

2. **Honestidad (P7):** accuracy-extracción / coverage-match / precisión-recall-fraude **NO** van aquí
   (requieren ground truth → evals T3+D). Y lo que es **garantía** (cláusula, cotas) se rotula como garantía, no
   como métrica medida. El panel = operación medida + sellos de garantía.
3. **Robustez:** con **0 casos** el panel no rompe (sin `ZeroDivisionError`; muestra 0 / "N/A").
4. **Tests:** sembrar el repo con casos conocidos (ej. 2 LISTO + 1 REQUIERE_REVISION + 1 con dictamen terminal) →
   verificar conteos/porcentajes **exactos** + que la sección aparece en el HTML de `/panel` + caso **0 casos** no
   rompe. Suite completa verde (168 + nuevos).

## 4. Invariantes / NFR

- **Dashboard passive (P1/P2):** el cómputo es **agregación de presentación** (cuenta campos ya calculados:
  `caso.estado`, `caso.dictamen`, `caso.alerta_fraude`, `token_summary`). NO importa `rules/`/`orchestrator/`,
  NO recalcula dominio, NO muta estado. Igual que los KPIs de la bandeja (patrón ya aprobado).
- **P5:** las métricas son conteos/costos — **cero PII**.
- **Sin deps nuevas.**

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`app/dashboard/c11.py::panel`** (MODIFICADO): además de `replays`, calcula un dict `metricas` a partir de
  `get_caso_repository().list()` (estados, dictámenes, cláusula, fraude, escalado) + los `replays` (tokens →
  costo estimado). Agregación pura, passive. **Guarda contra 0 casos** (sin división por cero → 0/"N/A").
- **Costo estimado:** constante documentada (ej. `COSTO_USD_POR_1M_TOKENS`, tasa blended Haiku/Sonnet) en el
  módulo del dashboard; el número se rotula **"estimado · no facturable"** en la UI.
- **`app/dashboard/templates/panel.html`** (MODIFICADO): nueva sección "Métricas de cumplimiento" arriba de las
  trazas — KPI cards + un breakdown (badges por dictamen/estado, % cláusula, fraude por severidad). Reusa el
  design system (`.kpi`, `.badge`, `k-*`).
- **`backend/tests/test_u5_c11_dashboard.py`** (o nuevo): test de los conteos/porcentajes con casos sembrados.

## 6. Fuera de alcance

- Métricas con ground truth (accuracy/coverage-match/fraude-P-R) → evals (T3+D). Series temporales / gráficos
  (solo números + barras simples). Persistencia de métricas históricas.

## 7. Cómo se validará el Bolt

- **Tests (ejecutan):** repo sembrado con N casos conocidos → los conteos/% son exactos; `/panel` 200 y muestra
  la sección. Suite completa verde (168 + nuevos).
- **Manual:** `uvicorn` → `/panel` (rol Cumplimiento) → se ven las métricas coherentes con la bandeja.
- **`code-reviewer`** (passive, sin PII, agregación no-dominio) → **PR**.

## 8. Decisiones (resueltas con el usuario)

- **D1 — Costo:** ✅ **tokens totales + costo estimado** con tasa blended documentada, rotulado "estimado".
- **D2 — Alcance:** ✅ **las 7 métricas** de §3.1.
- **D3 — Cómputo:** ✅ en el router `panel` (patrón passive de los KPIs de la bandeja).

## 9. Ajustes del review incorporados (code-reviewer)

- 🔴 **"% dentro de cotas"** → sacado de las métricas medidas; ahora es **garantía P4 verificada por aserción en
  evals** (RNF-09), mostrada como sello, no medida (el ReplayStore no guarda rondas/presupuesto) — §3.1-B.
- 🟠 **"% con cláusula"** → reencuadrado como **garantía RULE-CTR-03** (N/N, el validador lo enforce), no métrica
  de calidad — §3.1-B. 🟠 **"% escalado"** → solo `REQUIERE_REVISION` (§3.1-A).
- 🟠 **Costo** → constante documentada + rótulo "estimado · no facturable" (§5). 🔴 **División por cero** → guarda
  con 0 casos (§3.3, §5). 🟠 **Test** → casos sembrados conocidos + aserciones de conteo + HTML + caso 0 (§3.4).
- ✅ passive confirmado (patrón de los KPIs de la bandeja; test estructural sigue pasando) · cero PII.
