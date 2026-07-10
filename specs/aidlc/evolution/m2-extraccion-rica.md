# M2 — *(Mejora)* Extracción rica real (asegurado/placa/terceros + huella) 🔒 P5

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** M (mejora)
> **LLM/det:** 🤖 · **Depende de:** M1 · **Datos:** R · **🔒 P5 → OK + code-reviewer antes del CÓMO.**

## 1. Intent

C2 hoy extrae 4 campos. Esta mejora lo lleva al **set FNOL real** (asegurado, placa, terceros, lesionados,
lugar, descripción, …) alimentado del bundle multimodal (M1). Reemplaza los **providers mock** de W2
(asegurado), W8 (lesionados), W13 (comparativa) y W12 (más anclas) por datos reales, **sin tocar las vistas**.

## 2. Criterios de completitud (verificables)

1. **Schema de extracción ampliado** (asegurado, placa, terceros, lesionados, lugar, …) con
   `origen`+`confianza` por campo (P3), y `ausente⇒valor=None` (no-invención, P4).
2. **Redacción P5** de los campos PII antes de mostrar/persistir; NER donde aplique.
3. Los providers `asegurado_de` (W2), carril "lesionados" (W8), `comparativa_de` (W13) y anclas (W12) pasan a
   **reales** con la misma interfaz.
4. **Entity resolution (U8) real:** con placa/cédula/nombre extraídos, el fallback de C4 deja de ser latente.

## 3. Invariantes / restricciones

- **🔒 P5:** los campos nuevos (cédula/placa/nombre) son PII → redacción en display/logs; regla
  `pii-minimization.md`.
- **P4:** el schema ampliado no relaja las cotas; `ausente⇒valor=None` fail-closed.
- **P2/P1:** más campos no cambian quién decide (motor + humano).

## 4. Fuera de alcance

- Extracción perfecta de relato/lesiones complejas (mejora continua); visión pesada (fase-2).

## 5. Verificación (tests fail-closed)

- Un campo no hallado → `ausente=True, valor=None` (no inventa, P4).
- La PII extraída se redacta antes de mostrarse (P5).
- W2/W8/W13/U8 funcionan con datos reales bajo la **misma interfaz** (sus tests siguen verde).

## 6. Notas CÓMO

Ampliar `FLAT_EXTRACTION_SCHEMA`/mapeo en `llm/extractor.py`; redacción de los nuevos campos; conectar los
providers reales. **Toca extractor + redacción → P5.**

## 7. Precisiones tras code-review

**Decisión de diseño (CÓMO):** los campos PII (nombre/placa/teléfono/cédula) se extraen de forma
**determinística** (regex/NER es-CO en `app/intake/entidades.py`) sobre el texto crudo — **nunca** al LLM
(el prompt de C2 va redactado, P5). Las entidades se apilan a la salida del LLM en `call_c2_extractor`. Los
providers ya cableados por DIP (`asegurado_de`, `campos_extraidos`, `_lesionados`, C4-fallback U8) pasan a
reales sin tocar las vistas.

**Ronda CÓMO (2026-07-10, aprobado con ajustes):**
- **P5 (aplicado):** `asegurado_de` redacta el nombre en el boundary (`_red`) — no oculta el nombre
  operacional, pero neutraliza un tel/email embebido; documentado el uso en memoria de la búsqueda (`c11`).
- **P4 (aplicado):** cota `MAX_TEXTO_ESCANEO=20_000` en `extraer_entidades` (acota el input no confiable).
  **ReDoS: NO presente** — medido con entradas adversarias de 50k → <10ms (regex lineales); la cota es higiene.
- **Test P5:** `test_pii_no_va_al_llm_...` verifica que el prompt del LLM no lleva la cédula cruda (pasa verde;
  el reviewer lo reportó como fallo por un problema de import en su sandbox — descartado tras re-correr).

**Alcance confirmado (diferido, honesto P7):**
- **Adjuntos → C2:** M2 extrae del cuerpo del correo; alimentar el texto de los adjuntos M1 al extractor
  (`combinar_para_extraccion` en `c7`) es un follow-up pequeño (toca el orquestador).
- **Co-ocurrencia por entidad** (`casos_por_entidad`, señal de fraude) sigue latente — es fraude cross-source,
  territorio de M3, no de M2. El criterio #4 (fallback C4 por placa/cédula) SÍ quedó real.
- **Vehículo/lugar** son best-effort determinístico (marca conocida / patrón de vía); si no calzan, caen al
  demo rotulado.
