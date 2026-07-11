# W19 — Summary Agent (LLM mockeable) 🔒 P1

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1b hi-fi
> **LLM/det:** 🤖 LLM (mockeable) · **Depende de:** W4 · **Datos:** R · **🔒 P1 → OK + code-reviewer antes del CÓMO.**

## 1. Intent

Subir el "Resumen Ejecutivo" de **plantilla determinística** (W4) a un **Summary Agent** real: un agente LLM
que **escribe la historia del caso** como lo haría un compañero senior. Es el **6º agente visible** de la
orquesta (refuerza el enfoque agéntico). Mockeable en tests; real con key.

## 2. Criterios de completitud (verificables)

1. **`call_summary_agent(caso) -> str`** — LLM (Haiku/Sonnet) que redacta la narrativa desde los datos del
   caso **YA REDACTADOS** (P5). Emite un evento de traza (aparece en el Timeline W18 como agente "Resumen").
2. **🔒 Fail-closed (P1):** la salida pasa por un **guard determinístico** — sin `PALABRAS_PROHIBIDAS`, no
   decide (aprobar/rechazar/cobertura), no inventa hechos ausentes. Si el guard falla **o el LLM no está
   disponible** → cae a la **plantilla determinística de W4** (`resumen_narrativo`). Nunca rompe, nunca inventa.
3. **Mockeable:** en tests, el LLM se mockea (determinístico); sin key, usa el fallback de W4.
4. **P5:** el input al LLM va redactado (patrón de C2/triage); el output se muestra con `|redact`.

## 3. Invariantes / restricciones

- **🔒 P1:** el Summary **describe, no decide**. El guard fail-closed es obligatorio; el fallback a W4
  garantiza que siempre haya un resumen honesto.
- **P5:** redacción antes del LLM y en display.
- **P7:** si el LLM alucina un hecho ausente, el guard/fallback lo contiene (no se presenta lo inventado).
- **Costo (riesgo #2):** modelo barato por defecto; el fallback determinístico es gratis.

## 4. Fuera de alcance

- RAG sobre el expediente (eso es el copiloto conversacional W15); aquí solo la narrativa del caso.

## 5. Verificación (tests fail-closed)

- El agente redacta desde datos redactados; el input al LLM no lleva PII cruda (aserción sobre el prompt).
- Salida con `PALABRAS_PROHIBIDAS` o LLM caído → **fallback a la plantilla W4** (nunca error, nunca invención).
- Emite evento de traza → el Timeline (W18) lo muestra como agente "Resumen".
- Mock determinístico: misma entrada → salida estable en tests.

## 6. Notas CÓMO

Nuevo `llm/summary.py` (`call_summary_agent`, patrón de `extractor.py`: redacción → LLM → parse). El view-model
`resumen_narrativo` (W4) queda como **fallback**. Se llama desde el pipeline (emite traza) o el view-model.
**Toca `llm/` + narrativa mostrada al humano → P1.**

## 7. Precisiones tras code-review

- **🔴 Guard fail-closed ampliado (P1+P2):** el `PALABRAS_PROHIBIDAS` no basta — la narrativa **NO afirma el
  veredicto de cobertura por su cuenta** (eso es del motor, lo presenta W7). Si menciona cobertura, debe citar
  `dictamen.resultado` **verbatim**; menciona la severidad de `alerta_fraude` si existe (o "sin señales"); **no
  referencia campos ausentes** de `extraccion.campos`. Si el guard detecta contradicción con
  `dictamen`/`alerta_fraude`/campos, o el LLM está caído/alucina → **fallback a `resumen_narrativo` (W4)**.
  Nunca error, nunca invención, nunca decide.
- **🟡 P5 — prompt redactado explícito:** el prompt se arma de **campos estructurados YA REDACTADOS** (asegurado,
  tipo, monto, dictamen, fraude), **NO** del `aviso.texto_crudo` crudo. Test: la PII de `texto_crudo` no aparece
  en el prompt enviado al LLM.
- **Traza:** el nodo `summary_agent` ya está mapeado en el Timeline (W18); se enciende cuando el agente corra
  **en el pipeline** (emisión de traza vía Tracer). Hoy W19 corre en el view-model (display) → se muestra +
  rotula su origen, pero su nodo del Timeline queda **diferido** a la integración en el orquestador (toca P4).

### Tras el CÓMO
- **🔴 Bug P2 corregido (reviewer):** el guard usaba substring → "cubierto" matcheaba dentro de "cubierto
  parcial" y rechazaba narrativas válidas. Fix: **regex con límites de palabra, más específica primero**
  (`\bno cubierto\b` → `\bcubierto parcial\b` → `\bcubierto\b`). Test de regresión + caso sin-dictamen.
- **Diferido (reviewer, "próxima cosecha"):** (a) emitir traza del Summary Agent (necesita wiring en el
  pipeline, P4); (b) caché del resumen (hoy: hermético usa el fallback gratis; el LLM solo con key real, por
  selección de caso, no cada 3s). Ambos honestos, no bloquean.
