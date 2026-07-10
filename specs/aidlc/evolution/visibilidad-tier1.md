# Unit de Evolución — Visibilidad Tier-1 (N)

> **Tipo:** spec a nivel de cambio (brownfield) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Origen:** dictamen de los 3 expertos — "Perito no es poco agéntico; su mejor activo está escondido".

## 1. Intent

Hacer **visible en la demo lo que Perito YA hace** pero hoy no muestra: la evaluación de calidad, la
trazabilidad de cumplimiento, la latencia real y el porqué del escalamiento. Es la unidad de **mejor ROI**
(casi todo ya existe; se trata de *mostrarlo*, no de construir capacidad nueva) y la que convierte "se ve
básico" en "esto es un producto regulado-listo, con evidencia, no vibes".

## 2. Restricción dura (P7) — honestidad de cada número

Cada dato mostrado debe ser **real y correctamente rotulado**. En concreto:
- Lo **determinístico y por-caso** (trayectoria, cita de cláusula, campos con origen) se calcula en runtime y
  se muestra por caso.
- Lo del **juez Claude** (faithfulness, tool-correctness) corre **offline en CI** (`pytest -m agentic`): se
  referencia/agrega como "medido en evals de CI", **nunca** se fabrica un número por-caso en vivo.
- La **latencia** es real solo con traza (modo `real` / traza sembrada rotulada como ilustrativa).
- El **baseline "sin Perito"** es un **benchmark de industria citado**, no una medición propia.

## 3. Criterios de completitud (verificables)

1. **Verificación de trayectoria por caso (determinística, runtime)** — tarjeta en el detalle que muestra,
   de la traza + salidas reales: (a) recorrió los nodos esperados del pipeline, (b) todo campo presente tiene
   `origen` (sin campos inventados), (c) el dictamen terminal cita cláusula (RULE-CTR-03), (d) confianza C3 si
   disponible. Rotulado "Verificación de la trayectoria". Cero LLM en vivo, cero fabricación.
2. **Referencia al eval Claude-as-judge (agregado, honesto)** — una línea/sello: "Evaluado con juez Claude
   sobre golden datasets — faithfulness · tool-correctness · cita-cláusula (`pytest -m agentic`)". Si se
   persiste el resultado de la última corrida, mostrarlo **rotulado "última corrida de evals en CI"**; si no,
   solo la referencia. Nunca un score por-caso en vivo.
3. **Panel de auditoría rotulado "EU AI Act / NAIC"** — reusar `/panel` + el export JSON existente: para un
   caso, la provenance completa (campo→origen, regla→cláusula, señal→evidencia, quién firmó y cuándo) como
   **registro de auditoría exportable**, con encabezado que lo nombra como trazabilidad EU AI Act Art. 14 /
   NAIC Model Bulletin. Es packaging honesto de lo que ya existe.
4. **Latencia real por caso** — "recibido → triado en N s", calculada de la traza (`latencia_ms` por nodo) o
   del delta `timestamp_creacion→actualizacion`. Mostrar solo cuando hay traza; rotular ilustrativa si el
   modo es determinístico/preset.
5. **Confianza + razón de escalamiento explícita** — en `REQUIERE_REVISION`, mostrar la confianza y el umbral:
   "confianza C3 0.62 < umbral 0.75 → escalé a humano" (o "faltan datos: monto"). Hace visible el patrón
   confidence-gated escalation. (Requiere exponer el umbral que ya usa el verificador/orquestador.)
6. **Contador "con Perito vs sin Perito"** — tile con "triado en N s vs 4–6 min de intake manual
   (**benchmark de industria citado**)". El baseline **rotulado y con fuente**, no medición propia (P7).

## 4. Restricciones e invariantes

- **P7:** ver §2. Nada fabricado; cada número con su rótulo de origen.
- **P2:** la verificación de trayectoria NO re-decide cobertura; solo comprueba que el dictamen citó cláusula.
- **P1/P6 intactos:** es todo lectura/presentación; no cambia estados ni decisiones.
- **Solo `dashboard/`** (+ quizá exponer un umbral ya existente). No toca `rules/` ni `orchestrator/` como decisores.

## 5. Fuera de alcance

- Correr el juez Claude en vivo por caso (costo + no aplica; se usa el eval de CI).
- La carta autogenerada (Unit M) y el loop reflexivo (Unit O).

## 6. Verificación (tests fail-closed)

- **P7 latencia:** en modo determinístico/preset la latencia se rotula ilustrativa; no se muestra un número real inventado.
- **P7 eval:** no aparece un score de juez-Claude por-caso presentado como live; solo checks determinísticos + referencia a CI.
- **Trayectoria:** un caso con dictamen terminal marca "cita cláusula ✓"; uno con campo sin origen marca "sin origen".
- **Auditoría:** el export/panel incluye campo→origen, regla→cláusula y `aprobado_por` cuando existe.
- **No regresión:** el resto del dashboard intacto.

## 7. Notas para el CÓMO (Bolt)

Reusar `ReplayStore`, `calcular_metricas`, el export `/panel/export`. Nuevos view-models passive en
`vista_caso.py` (`verificacion_trayectoria`, `latencia_caso`, `razon_escalamiento`). Plantillas: `detalle.html`,
`panel.html`. Tests en `tests/test_evolution_frontend_hifi.py`. Sin backend de dominio nuevo.
