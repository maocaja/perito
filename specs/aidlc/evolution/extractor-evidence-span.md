# Unit de Evolución — Evidencia real del extractor (span) — FLAG / backlog

> **Tipo:** spec a nivel de cambio (brownfield) · **Fase AI-DLC:** por priorizar ·
> **Estado:** 🟡 QUÉ propuesto — NO implementado. Flagueado durante el pulido UX de la Unit J.
> **Toca:** `backend/app/llm/extractor.py` (capa de extracción U2) — **fuera de `dashboard/`**.

## 1. Problema (hallazgo)

El extractor real (`extractor.py:145`) no captura el **fragmento de evidencia** del aviso: pone una
referencia fija `"extracted from redacted_texto"` en `EvidenciaOrigen.referencia` de cada campo. En el
detalle esto se veía como texto de debug en inglés en cada fila ("Valor / evidencia"). Los presets usan
`"span:{campo}"` — también técnico.

**Mitigación ya aplicada (Unit J, capa de vista):** el detalle muestra esas referencias técnicas como
"extraído del aviso" (macro `campo_evidencia` en `_macros.html`). Es un parche de presentación honesto
(el dato **sí** se extrajo del aviso redactado), pero **no** es la evidencia real enlazada.

## 2. Qué cerraría (valor)

Fortalecer **P3 (evidencia enlazada)**: que cada campo extraído cite el **span real** del aviso del que
salió, para que el analista verifique la extracción contra el texto — no una etiqueta genérica.

## 3. Criterios de completitud (verificables)

1. El extractor devuelve, por campo, el **fragmento textual** (o offsets) del aviso que sustenta el valor,
   en `EvidenciaOrigen.referencia` (o un campo dedicado), ya **redactado** (P5) antes de persistir.
2. El detalle muestra la cita real (la mitigación `campo_evidencia` deja de aplicar para el modo real).
3. **Re-verificación de evals:** el cambio del prompt/salida del extractor puede mover métricas de
   extracción → correr los evals por estrato (`pytest -m agentic`) y confirmar que no regresan.

## 4. Riesgos / notas

- Toca U2 (capa de extracción, primer punto que llama a Claude). Cambiar el prompt/salida puede afectar
  accuracy y los evals agénticos → NO es un cambio de sólo-vista.
- Mantener P5: el span citado debe pasar por `redact_pii_spans_es_co` antes de mostrarse/persistirse.
- Decidir el contrato: ¿`referencia` = texto del span, u offsets (inicio/fin) sobre el aviso redactado?
