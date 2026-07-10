# W14 — Panel de productividad del operador

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 3
> **LLM/det:** ⚙️ det · **Depende de:** — · **Datos:** R + **M** (SLA/tiempo)

## 1. Intent

Todos los operadores quieren saber cómo van. *Hoy: 48 casos · Tiempo promedio 4m 12s · Errores 0 · Pendientes
17 · SLA 100%.* Eso motiva y da control sobre la cola.

## 2. Criterios de completitud (verificables)

1. **Métricas reales** que ya tenemos: casos procesados, pendientes (de la cola), % escalado, costo/caso
   (reusa `calcular_metricas`).
2. **Métricas mock/derivadas rotuladas:** tiempo promedio de revisión, SLA, "errores" (expedientes
   devueltos) — **provider `productividad(operador)`** hoy sembrado/estimado (P7); real cuando exista telemetría
   de tiempos y devoluciones.
3. **Vista de operador** (no la de cumplimiento): personal, del día, motivadora.

## 3. Invariantes / restricciones

- **P7:** las métricas que no medimos aún (tiempo real, SLA) van **rotuladas como estimadas/demo**, no como
  hechos. No inflar números.
- **P1:** informativo; no cambia el trabajo ni decide.

## 4. Fuera de alcance

- Telemetría real de tiempos por caso y devoluciones (mejora); gamificación avanzada.

## 5. Verificación (tests fail-closed)

- Las métricas reales coinciden con `calcular_metricas`/la cola.
- Las métricas mock (tiempo/SLA) llevan su rótulo; no se presentan como medidas reales.
- Pendientes = conteo real de la cola.

## 6. Notas CÓMO

Provider `productividad(operador)` (real donde hay datos, mock rotulado donde no) reusando `calcular_metricas`.
Nueva vista/panel de operador (o franja en la Workbench).

## 7. Precisiones tras code-review

_(a completar tras la revisión del QUÉ)_
