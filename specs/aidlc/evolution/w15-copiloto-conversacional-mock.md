# W15 — Copiloto conversacional contextual **(MOCK)**

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 3
> **LLM/det:** — (mock) · **Depende de:** — · **Datos:** **M** · **Invariante:** P7 (rótulo honesto)

## 1. Intent

Un copiloto conversacional **contextual** (no un chat cualquiera): el operador escribe *"¿Por qué dices que
falta la licencia?"* y responde *"Encontré licencia del vehículo pero no licencia del conductor."*
**En este programa es un MOCK** — la UI y el guion; el operador (tú) lo explica en vivo. El backend real es una
mejora futura.

## 2. Criterios de completitud (verificables)

1. **UI de chat contextual** en la Workbench (panel lateral/inferior), atada al caso activo.
2. **Respuestas mock guionadas** para 3-5 preguntas frecuentes del demo (por qué falta X, por qué esta
   cobertura, qué riesgos hay), derivadas de datos reales del caso donde se pueda (faltantes, dictamen).
3. **Rótulo honesto (P7):** un badge visible "Demo / respuestas de ejemplo" — **no se presenta como IA
   funcional**. Interfaz `responder(pregunta, caso)` lista para conectar el backend real (mejora).
4. **Sin efectos:** el chat **no ejecuta acciones** ni cambia estado (solo explica).

## 3. Invariantes / restricciones

- **P7 (clave):** rotulado como mock; ni el código ni el demo lo presentan como real. Cero afirmaciones
  falsas.
- **P1/P6:** el chat **no decide** nada (no aprueba, no dictamina fraude); solo explica.
- **P5:** las respuestas mock no exponen PII cruda.

## 4. Fuera de alcance (todo lo real → mejora futura)

- LLM real con RAG sobre el expediente; ejecución de acciones desde el chat; memoria de conversación.

## 5. Verificación (tests fail-closed)

- El panel lleva el rótulo "Demo" visible.
- El chat no expone endpoints que cambien estado/cobertura (solo responde texto).
- Las respuestas mock referencian datos reales del caso donde aplica; no inventan hechos del asegurado.

## 6. Notas CÓMO

Provider `responder(pregunta, caso)` (mock guionado, interfaz estable) + parcial de chat con badge Demo. JS
mínimo (enviar/mostrar), cero backend LLM.

## 7. Precisiones tras code-review (CÓMO)

- **Reviewer: SAFE TO MERGE, P1-P7 compliant.** El copiloto SOLO explica (ruta read-only; test: no muta
  estado); rotulado `demo`; respuestas sobre datos reales (dictamen/faltantes/riesgos) + guion de licencia; P5
  redacta pregunta y respuesta (tests: 404 + PII no vuelve cruda). `responder(pregunta, caso)` = interfaz
  estable para conectar un LLM real (DIP). Límite honesto: el enrutado por palabras clave es aproximación de
  demo (el real usaría intención LLM).
