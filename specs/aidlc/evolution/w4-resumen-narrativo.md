# W4 — Resumen ejecutivo narrativo (prosa)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** ⚙️ (plantilla) · **Depende de:** — · **Datos:** R

## 1. Intent

No un formulario: una **historia**. *"Ayer a las 8:20 pm el asegurado impactó otro vehículo. No hubo
lesionados. Vehículo Mazda CX5, placa ABC123. Póliza vigente, cobertura Todo Riesgo. Se adjuntan 8
fotografías, denuncia, licencia, SOAT. No aparece tarjeta de propiedad."* Eso me ahorra cinco minutos.

## 2. Criterios de completitud (verificables)

1. **Narrativa en prosa** compuesta **determinísticamente** desde los datos del caso (extracción, dictamen,
   checklist de documentos, faltantes) — reusa `resumen_copiloto`, `checklist_documentos`, `faltantes`,
   `_label_cobertura`. Plantilla de frases, no generación libre.
2. **Cierra con lo que FALTA** ("No aparece tarjeta de propiedad") desde `faltantes`/`checklist_documentos`.
3. Campos aún no extraídos (placa, hora) usan el **provider** de W2/M2 (mock rotulado hasta que sean reales).
4. Se muestra al tope de la columna central, bajo el header (W2).

## 3. Invariantes / restricciones

- **P1:** la narrativa **describe**, no decide — **cero `PALABRAS_PROHIBIDAS`** (mismo guardrail que
  `recomendacion`); fail-closed a texto neutro si se colara una palabra de decisión.
- **P5:** el resumen usa datos ya redactados; no expone PII cruda.
- **P7:** no inventa hechos; los campos ausentes se nombran como ausentes, no se rellenan.

## 4. Fuera de alcance

- Generación libre por LLM (para reproducibilidad y P1 se usa plantilla determinística; un modo LLM-redactor
  mockeable queda como mejora).

## 5. Verificación (tests fail-closed)

- El resumen nunca contiene `PALABRAS_PROHIBIDAS` (aserción, como `recomendacion`).
- Menciona los documentos faltantes reales del caso.
- Un dato ausente no aparece inventado (P7).

## 6. Notas CÓMO

Nuevo view-model `resumen_narrativo(caso)` en `vista_caso.py` (plantilla determinística sobre datos existentes).
Parcial en la columna central.

## 7. Precisiones tras code-review (CÓMO)

- **🔴 P5 defensa en profundidad:** `resumen_narrativo` compone con `_red()` (nombre del asegurado + monto) →
  devuelve prosa **ya redactada**, no solo el `|redact` del template. Test: una cédula en el asegurado real
  (M2) no aparece cruda en la prosa. + guard P1 `PALABRAS_PROHIBIDAS` confirmado.
