# Unit de Evolución — Evals AGÉNTICOS con DeepEval + Claude-as-judge (D)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟢 QUÉ validado (usuario + code-reviewer; ajustes P5/M incorporados). Listo para Bolt.
> **Dirección (usuario):** lo **más agéntico posible, NO determinístico** — pipeline real + LLM-as-judge.

## 1. Intent (el goal)

Evaluar el sistema como **agente real**: correr el pipeline completo (C2 Haiku + C3 Sonnet + motor + C6) sobre
avisos por estrato y **juzgar la calidad con Claude-as-judge** vía DeepEval. Mide lo que un test determinista no
puede: **¿la extracción es fiel al aviso (cero campos inventados)? ¿el agente recorrió los nodos correctos?
¿escaló cuando debía?**

## 2. Qué cierra

- **RF-27** (evals **pytest + DeepEval** por estrato; tool-correctness). **RNF-28** (nodos LLM por evals, no PBT).
- Métrica clave PRD (Seg. 10): **"campos inventados ≈ 0"** (faithfulness/hallucination por juez).

## 3. Criterios de completitud (verificables)

1. **Claude-as-judge:** `ClaudeJudge(DeepEvalBaseLLM)` sobre el SDK Anthropic (NO OpenAI), modelo `claude-sonnet-5`.
   Firma: `get_model_name()`, `load_model()`, `generate(prompt: str) -> str`, `a_generate(prompt) -> str` (async).
   Se **confirma la API exacta de DeepEval en el de-risk** (versión-específica vía context7).
2. **Pipeline REAL por estrato:** corre `orquestar_fnol` con agentes reales (sin mocks) → extracción + dictamen +
   trayectoria (nodos de la traza C9).
3. **P5 — redacción ANTES del juez (BLOCKER B1):** lo que va al juez (input/context = el aviso) se pasa por
   `redact_pii_spans_es_co(aviso.texto_crudo)`. **NUNCA aviso crudo a un LLM externo.** Verificable: un aviso con
   cédula/teléfono → el `LLMTestCase` no contiene PII cruda.
4. **Métricas (juez Claude):**
   - **HallucinationMetric / FaithfulnessMetric** (context = aviso redactado; actual_output = campos extraídos) →
     campos inventados. **Umbral Faithfulness ≥ 0.70.**
   - **ToolCorrectnessMetric** (determinista): `tools_called` = nodos reales de `tracer.get_trace_log()`;
     `expected_tools` por estrato. **Umbral ≥ 0.80.** Nodos reales (de `c7.py`):
     `c2_extraccion · c3_verificador · c4_policy_lookup · c5_motor_cobertura · c6_fraude`.
   - **G-Eval "cita cláusula"**: el dictamen terminal cita una cláusula existente de la póliza.
5. **No-determinismo con umbrales + tolerancia (M4):** por métrica un umbral fijo; **máx 2 reintentos**; el run
   registra `intentos: [..], promedio, umbral, veredicto`. Gate = `promedio ≥ umbral`, no igualdad.
6. **On-demand, FUERA del CI (M3):** marcados `@pytest.mark.agentic`, **marker registrado en `pyproject.toml`** y
   **excluido por default** (`addopts = -m "not agentic"`). La suite base (168, mockeada) queda intacta y verde
   sin API/costo. Se corren con `ANTHROPIC_API_KEY` real, a demanda.
7. **Eval runs versionados SIN PII (BLOCKER B2):** `evals/runs/<YYYY-MM-DD_HH-MM-SS>.json` con esquema
   **`{estrato, caso_id, metrica, score, umbral, veredicto, intentos}`** — **jamás** aviso/extracción crudos.

## 4. Invariantes / NFR

- **P5 (CRÍTICO):** redacción antes del juez (§3.3) + eval runs sin PII (§3.7). Único redactor.
- **Juez = Claude** (nunca OpenAI).
- **P7 (honestidad):** evals **caros + no deterministas** → on-demand, NO gate de CI (la suite mockeada es el gate
  rápido). Se solapan parcialmente con los tests del orquestador; el valor es la métrica agéntica (alucinación
  real) que RF-27 nombra. No se sobre-venden.
- **No toca dominio:** en `tests/evals/`; observan el pipeline real. P1-P6 intactos.

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`tests/evals/claude_judge.py`** (NUEVO): `ClaudeJudge(DeepEvalBaseLLM)` sobre el SDK Anthropic (`claude-sonnet-5`).
- **`tests/evals/test_agentic_evals.py`** (NUEVO, `@pytest.mark.agentic`): por estrato → corre pipeline real →
  redacta el aviso → arma `LLMTestCase(input=redactado, actual_output=extracción, context=[redactado], tools_called=nodos)`
  → evalúa con las 3 métricas (juez=ClaudeJudge) → `assert_test` con umbral + reintentos → vuelca el JSON.
- **Tabla de `expected_tools` por estrato** (nodos de la traza): happy = pipeline completo; escalados = secuencia
  corta hasta el punto de escape. Se define en el Bolt.
- **`pyproject.toml`:** registrar marker `agentic` + `addopts = "-m 'not agentic'"`; `deepeval` como extra `evals`.
- **context7** para la API real de DeepEval (`DeepEvalBaseLLM`, `LLMTestCase`, métricas, `assert_test`).
- **De-risk:** smoke de 1 estrato (ClaudeJudge responde + 1 métrica end-to-end + confirma firma DeepEval) antes de los 4.

## 6. Fuera de alcance

- **Estratos SOAT / documento-sucio / campos-faltantes** en el eval agéntico → **diferidos** (los 4: happy · fraude
  · no-cubierto · no-encontrada). OTel (B2), C2 pgvector, LangGraph (E), tablero visual de evals (F/H-21).

## 7. Cómo se validará el Bolt (gate de salida)

- **De-risk:** 1 estrato real + ClaudeJudge + 1 métrica → confirma API DeepEval + juez Claude + firma.
- **Suite base intacta:** `pytest` (default, `-m "not agentic"`) sigue **168 verde**, sin API/costo.
- **Eval agéntico (manual, con key):** `pytest -m agentic` → scores ≥ umbrales (Faithfulness ≥0.70, Tool ≥0.80),
  vuelca JSON versionado sin PII. Se pega la salida como evidencia.
- **`code-reviewer`** (P5 al juez · marker excluido · juez Claude · no toca dominio) → **PR**.

## 8. Decisiones (resueltas con el usuario)

- **D1 — Métricas:** ✅ Faithfulness/Hallucination + ToolCorrectness + G-Eval "cita cláusula".
- **D2 — Modelo juez:** ✅ `claude-sonnet-5`.
- **D3 — Dependencia:** ✅ `deepeval` (pip, extra `evals`) — con confirmación antes de instalar.
- **D4 — Estratos:** ✅ 4 (happy · fraude · no-cubierto · no-encontrada); SOAT/doc-sucio/campos-faltantes diferidos.

## 9. Ajustes del review incorporados (code-reviewer)

- 🔴 **B1 P5** → aviso redactado antes del juez (§3.3, §4). 🔴 **B2 P5** → esquema de eval runs sin PII (§3.7).
- 🟠 **M1** → tool-correctness sobre nodos reales de la traza, expected por estrato (§3.4). 🟠 **M2** → firma de
  ClaudeJudge + confirmación en de-risk (§3.1, §5). 🟠 **M3** → marker `agentic` registrado + excluido del CI (§3.6).
  🟠 **M4** → umbrales por métrica + 2 reintentos + tolerancia (§3.5). 🟠 **M5** → 4 estratos, resto diferido (§6).
