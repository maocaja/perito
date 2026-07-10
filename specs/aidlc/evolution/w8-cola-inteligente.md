# W8 — Cola inteligente por razón (🔴🟠🟡🟢)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** ⚙️ det · **Depende de:** — · **Datos:** R

## 1. Intent

Hoy el operador ve "120 correos". Quiero ver **120 casos que la IA ya priorizó por razón**:
🔴 Lesionados (4) · 🟠 Cobertura dudosa (7) · 🟡 Documentos faltantes (18) · 🟢 Listos para radicar (91).
Empiezo por los verdes. La cola es la **columna izquierda** de la Workbench (W1).

## 2. Criterios de completitud (verificables)

1. **Agrupación determinística por razón** (no por estado crudo): un `clasificador_cola(caso)` mapea cada caso
   a un carril — 🔴 lesionados / 🟠 cobertura dudosa (dictamen NO_CUBIERTO/parcial o REQUIERE_REVISION por
   cobertura) / 🟡 documentos o campos faltantes / 🟢 listo (`LISTO_PARA_APROBAR` sin faltantes). Reusa
   `prioridad`, `faltantes`, `dictamen`, `alerta_fraude`.
2. **Conteos por carril** visibles; clic filtra la cola a ese carril (como los KPIs toggle de hoy).
3. **Orden dentro del carril** por prioridad (reusa el `orden` existente).
4. "Lesionados" usa el **provider** de extracción rica (mock rotulado hasta M2; hoy: heurística sobre el texto/
   tipo si aplica, honesta).

## 3. Invariantes / restricciones

- **P2/P1:** la priorización **no decide** cobertura ni estado; solo **ordena el trabajo**. La regla de cada
  carril es determinística y citable.
- **P7:** el carril "Lesionados" hoy es parcial (sin extracción de personas) → rotulado/heurístico, no
  sobrevendido.

## 4. Fuera de alcance

- Detección real de lesionados (M2); modelos de priorización aprendidos (empezar por reglas).

## 5. Verificación (tests fail-closed)

- Cada caso cae en exactamente un carril según la regla determinística (reproducible).
- Un caso `LISTO_PARA_APROBAR` sin faltantes ni riesgo alto → 🟢; con faltantes → 🟡.
- Los conteos por carril suman el total de la cola.

## 6. Notas CÓMO

Nuevo view-model `clasificador_cola(caso)` + agregador de conteos en `c11.py`. Reusa `_filtrar_bandeja`/
`prioridad`. Parcial de cola en la columna izquierda de `workbench.html`.

## 7. Precisiones tras code-review (CÓMO)

- **P7 heurística rotulada:** el carril 🔴 Lesionados lleva un badge "heurística" en la UI (detección por
  texto; extracción real = M2). Partición determinística y **mutuamente excluyente** (test: cada caso en 1
  carril; conteos suman el total). Terminales (APROBADO/RECHAZADO) → verde con motivo "caso cerrado".
- **Aceptado (UX menor):** deep-link a un caso fuera del carril filtrado no lo resalta; navegar dentro del
  workbench usa el parcial (la cola conserva su filtro), así que el flujo real no se ve afectado.
