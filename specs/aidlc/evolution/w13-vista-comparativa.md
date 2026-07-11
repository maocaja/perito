# W13 — Vista comparativa multi-correo (mismo cliente) · **provider MOCK**

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 2
> **LLM/det:** ⚙️ det · **Depende de:** U7 (triage), U8 (entity) · **Datos:** **M** · **Invariante:** P5

## 1. Intent

Cuando llegan varios correos del mismo cliente, no quiero abrir cinco. Quiero una **vista comparativa**:
Cliente Juan Pérez → Correo 1 · Correo 2 · Correo 3 · PDF · Fotos · **Cambios detectados**. La IA me resume
todo y me dice qué cambió entre versiones.

## 2. Criterios de completitud (verificables)

1. **Agrupación por cliente/expediente:** reusa `triage` (`PERTENECE_A_CASO`) + entity resolution (U8) para
   relacionar correos. **Provider `comparativa_de(caso) -> {fuentes[], cambios[]}`** hoy **mock/sembrado**
   (rotulado P7); M1/M2 lo vuelve real.
2. **Diff de cambios detectados** entre fuentes (p.ej. "el monto cambió de X a Y", "aparece un tercero nuevo")
   — determinístico sobre los campos; mock hasta tener multi-fuente real.
3. **Vista lado a lado** de las fuentes con el resumen de diferencias.

## 3. Invariantes / restricciones

- **P5:** las fuentes se muestran redactadas; el diff referencia campos, no PII cruda.
- **P4:** la agrupación está acotada (nº de fuentes por expediente); no escanea sin cota.
- **P7:** provider mock rotulado; el clustering real depende de U8/U7 en producción.

## 4. Fuera de alcance

- Clustering difuso avanzado; resolución perfecta de expediente (empezar por U8 exacto + mock).

## 5. Verificación (tests fail-closed)

- El provider mock devuelve fuentes + cambios rotulados como demo.
- El diff no expone PII cruda (P5).
- Sin fuentes relacionadas → "un solo correo" (no fabrica comparativa).

## 6. Notas CÓMO

Provider `comparativa_de(caso)` (mock intercambiable) reusando `triage`/U8. Parcial de comparativa (vista lado
a lado) en la columna central.

## 7. Precisiones tras code-review (CÓMO)

- **Contrato `Comparativa` (TypedDict) + cotas `MAX_FUENTES`/`MAX_CAMBIOS` (P4)** — interfaz estable que
  U7/U8/M1 (clustering real) implementarán sin tocar la vista (DIP). El mock **sí** muestra la comparativa
  (objetivo de la demo), rotulado `demo`; `disponible` reflejará el conteo real cuando exista el clustering
  (`False` con < 2 correos, P7). P5: fuentes/cambios redactados en el render. CSS `.wb-comp-cambios` añadido.