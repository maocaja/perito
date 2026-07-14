# Unit de Evolución — Workbench robusto: Summary Agent no-bloqueante + confianza legible

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟢 QUÉ definido + Bolt ejecutado (rama `feat/workbench-summary-robusto`).
> **Origen:** hallazgo en demo en vivo (`DEMO_LIVE=real`): la UI se "pegaba" y el chip "Verificación 0.20" era ilegible.

Dos work-items en un Bolt (ambos brownfield, misma superficie = workbench):
- **U-W19.1** — el **Summary Agent (W19) no debe bloquear** el workbench.
- **U-W17.x** — la **confianza del verificador** debe ser **legible** (no un `0.20` pelado).

---

## 1. Intent (el goal)

**U-W19.1.** En `demo_live=real`, abrir un caso llama a **Claude Sonnet de forma síncrona en cada render**
(`vista_caso.resumen_ejecutivo` → `summary.call_summary_agent`), y el workbench **se auto-refresca cada 3 s**.
Con la API de Anthropic sobrecargada (`OverloadedError`, 529), el SDK reintenta con backoff → cada render
bloquea el **único worker síncrono** → la navegación (Inbox) **queda en cola** y la UI se **congela**.
El Summary Agent es un *enhancement*; **nunca** debe ser un bloqueante.

**U-W17.x.** El chip "Verificación" muestra `0.20` (crudo). Un analista no sabe qué es, en qué escala, ni qué
hacer. Debe **liderar el significado** (encode-not-hide, §4 del diseño), con el % en tooltip.

## 2. Qué cierra (trazabilidad)

- **P4/robustez operativa:** el pipeline "escala/degrada en vez de colgarse"; aquí, la **capa de presentación**
  también degrada con gracia (fallback W4) **sin castigar la latencia**.
- **NFR de usabilidad del workbench** (W17/W19): la confianza es *información para decidir*, no ruido.
- No abre RF/RNF nuevos: endurece dos superficies ya existentes.

## 3. Criterios de completitud (verificables)

1. **0 llamadas nuevas al LLM por auto-refresh** de un caso **ya resumido** por el agente (caché por caso).
2. **Ante `OverloadedError` / guard fallido:** cae al fallback W4 **sin reintentos** y en **< `summary_timeout_s`**
   (default 4 s); tras un fallo, **no re-llama el LLM de ese caso por `summary_cooldown_s`** (default 20 s) →
   el auto-refresh de 3 s **deja de martillar** la API. Se **auto-cura**: pasado el cooldown (o si el caso
   cambia) vuelve a intentar el LLM.
3. **La navegación no se bloquea:** con el LLM caído, un render del caso no deja al worker colgado > timeout.
4. **U-W17.x:** el chip "Verificación" muestra **texto legible** (`Verificado` / `Revisar · N%` /
   `Sin confirmar · N%`) con el **% exacto + significado en el `title`** (tooltip); el color (`nivel`) se conserva.
5. **Tests verdes** (herméticos, sin red) que prueban caché (1 sola llamada en 2 renders), fail-fast/cooldown
   (sin reintentos, 2º render sin llamar al LLM) y la legibilidad de la confianza.

## 4. Invariantes / NFR que DEBE respetar

- **P7 (rótulo de origen):** el resumen sigue rotulando `origen ∈ {agente, base}`; el fallback W4 se marca `base`.
- **P5 (redacción):** la salida del LLM se sigue redactando (`redact_pii_spans_es_co`) — sin cambios.
- **P1/P2 (guard):** el guard fail-closed (`_guard_ok`, `PALABRAS_PROHIBIDAS`, no contradice al motor) intacto;
  **solo se cachea lo que pasó el guard** o el fallback determinístico.
- **P2 (confianza ≠ decisión):** el chip de confianza es del **verificador C3** (informativo); NO decide cobertura.
- **Sin lógica de dominio nueva:** caché + timeouts son de infraestructura de presentación; el motor,
  el orquestador y HITL **no se tocan** (rutas protegidas intactas).
- **Hermético:** con `anthropic_api_key` vacía o `"test"` → nunca toca red (igual que hoy).

## 5. Diseño breve (el CÓMO — el Bolt)

- **`app/config.py`** (3 knobs, sección U2 LLM BEHAVIOR):
  `summary_timeout_s: float = 4.0`, `summary_max_retries: int = 0`, `summary_cooldown_s: float = 20.0`.
- **`app/llm/summary.py`:**
  - **Fail-fast:** `_llm_redacta` crea `Anthropic(api_key=…, timeout=settings.summary_timeout_s,
    max_retries=settings.summary_max_retries)` → ante 529 **no hace backoff**, cae al fallback ya.
  - **Caché + cooldown** en `call_summary_agent`:
    - Clave de estado = `sha256(construir_prompt(caso))` (si el caso no cambió, el prompt no cambia → reusar).
    - `_AGENTE_CACHE[caso.id] = (clave, texto)` **sticky**: hit con misma clave → devuelve `("…","agente")`
      sin tocar el LLM (criterio #1).
    - `_BASE_COOLDOWN[caso.id] = time.monotonic()` al fallar: dentro de `summary_cooldown_s` → devuelve W4
      (`base`) **sin llamar al LLM** (criterio #2). Pasado el cooldown o si cambia la clave → reintenta.
  - Un éxito posterior **limpia** el cooldown y puebla el caché sticky (auto-cura).
- **`app/dashboard/vista_caso.py`:**
  - Helper `_conf_texto(conf) -> (valor, ayuda)`: `≥0.9 → "Verificado"` · `≥0.70 → "Revisar · N%"` ·
    `<0.70 → "Sin confirmar · N%"` (umbral = `confidence_threshold`); `ayuda` explica el significado + % + umbral.
  - `confianza_riesgo(...)`: el ítem "Verificación" usa `_conf_texto`; se añade `ayuda` a los 3 ítems del strip.
- **`app/dashboard/templates/workbench_caso.html`** (línea del `wb-strip-item`): añadir
  `title="{{ c.ayuda|default('') }}"` (tooltip encode-not-hide). Cambio de una sola línea.

## 6. Fuera de alcance

- **Generación asíncrona/background** del resumen (mover fuera del request path) — mayor; el caché+cooldown
  resuelve el freeze sin cambiar el modelo de request síncrono.
- Cambiar el comportamiento del **extractor/verificador** (su cliente Anthropic conserva sus reintentos).
- Rediseño visual del strip más allá de hacer legible la confianza.

## 7. Cómo se validará el Bolt (gate de salida)

- **Tests (ejecutan, herméticos):**
  - `test_summary_cache`: 2 renders del mismo caso (LLM mock OK) → `_llm_redacta` llamado **1 vez**.
  - `test_summary_failfast_cooldown`: `_llm_redacta` lanza `OverloadedError` → devuelve `base`; 2º render
    inmediato → `base` **sin** volver a llamar (cooldown). Cliente construido con `max_retries=0`.
  - `test_confianza_legible`: `0.20 → "Sin confirmar · 20%"` + `ayuda` no vacía; `0.95 → "Verificado"`.
- **Suite base verde** (`make test`, sin API): sin regresiones.
- **Verificación por ejecución (manual):** `DEMO_LIVE=real make run` → abrir un caso → el log **ya no** repite
  "Summary Agent falló" en cada refresh; el **Inbox responde** aunque el LLM esté lento.
- **`code-reviewer`** (foco: guard P1/P2 intacto, hermético, rutas protegidas sin tocar) → **PR**.

## 8. Decisiones

- **D1 — Fallback cacheado con cooldown (no permanente):** ante overload transitorio se muestra W4 (`base`,
  rotulado P7) y se **reintenta pasado `summary_cooldown_s`** → corta el martilleo del refresh de 3 s **y**
  se auto-cura cuando Anthropic se recupera. (Alternativa "cachear base para siempre" descartada: dejaría casos
  atrapados en W4.)
- **D2 — Fail-fast `max_retries=0`:** el resumen es *best-effort*; reintentar con backoff en el request path es
  justo lo que congela. Mejor caer al W4 (válido, determinístico) al instante.
- **D3 — Confianza: encode-not-hide:** se **lidera con el significado** (`Sin confirmar`) y el número exacto +
  umbral viven en el tooltip — coherente con §4 del diseño del workbench.

## 9. Veredicto del review (code-reviewer, incorporado)

P1–P7 intactos; guard fail-closed intacto (solo se cachea lo que pasó el guard o el fallback W4); salida del LLM
redactada; clave de caché (hash del prompt) sin PII; rutas protegidas (`rules/`, `orchestrator/`) sin tocar;
tests herméticos sin contaminación. **Ajustes incorporados:**
1. 🔴 **Caché sin cota → LRU acotado** (`OrderedDict` + `_CACHE_MAX=512`, expulsa el menos usado) — §5. Evita el
   crecimiento sin fin en un proceso largo. (Se descartó TTL/Redis: sobre-ingeniería para el demo.)
2. 🟡 **`_conf_texto` sin validar rango → clamp** `conf∈[0,1]` — un valor raro no rompe el render. (Se descartó
   `raise ValueError`: un helper de display no debe tumbar el workbench.)
3. 🟢 **Logger anti-PII** (comentario: nunca `str(e)`, solo `type(e).__name__`) y **supuesto single-worker**
   documentado (el peor caso de una carrera es una llamada LLM de más, nunca corrupción ni violación de P1;
   multi-worker → store compartido). Se descartó el `assert os.getpid()` (ruido).

Tests añadidos: `test_cache_lru_expulsa_el_mas_viejo`, `test_conf_texto_clamp_fuera_de_rango`.
