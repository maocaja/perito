# Unit de Evolución — Tablero agent-native del caso (I)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Construye sobre:** Unit A (dashboard C11) + Unit H (demo en vivo). Consume lo que los agentes YA producen.

## 1. Intent

Convertir el detalle del caso de un **formulario CRUD** ("sin carne") en un **tablero de copiloto agéntico**: que
el analista vea, en lenguaje plano, **qué hicieron los agentes, por qué, con cuánta confianza, y qué le preparó el
copiloto para su decisión**. Todo **armado de las salidas reales del pipeline** (extracción/verificación/dictamen/
fraude/traza) — sin inventar razonamiento, sin decidir por el humano (P1/P2). El panel de expertos (UX + agentes +
siniestros, 2026) lo marcó: hoy mostramos *outputs*, no *razonamiento*; falta el **activity feed**, el **resumen del
copiloto**, la **confianza a la vista** y el **próximo paso preparado**.

## 2. Qué cierra

- El gap "se ve como app normal/básica". Hace el producto **agent-native**: reasoning panel + activity feed +
  recomendación + strip de confianza (patrones agentic-UX 2026). El valor del HITL (confianza IA sube 16%→60% con
  validación humana) se **visibiliza** en vez de esconderse en una columna.

## 3. Criterios de completitud (verificables)

Todo se **arma en la capa de vista** (passive) a partir del `Caso` + la traza (`ReplayStore`) YA existentes:

1. **A · 🧠 Resumen del copiloto** (arriba del detalle) — briefing en **lenguaje plano** ensamblado de las salidas
   reales: qué leyó, cuántos campos extrajo (y cuáles faltan), qué confirmó el verificador (si disponible), qué
   dictaminó el motor, y si hay fraude. **El dictamen se cita LITERAL** (`dictamen.resultado + regla_aplicada +
   clausula`), sin parafrasear ni inventar explicación (P2/P7): el "por qué" es la **cláusula citada**, no un texto
   agéntico. Cero fabricación: si un dato falta, dice "no disponible".
2. **B · 📋 Actividad de los agentes** — la traza convertida en **feed legible por agente**: nombre amigable
   (`c2_extraccion` → "Extractor (Haiku) leyó el aviso"), lenguaje plano del resultado, **confianza/tiempo/tokens**,
   e íconos por nodo. Reemplaza la lista técnica. Es el "activity feed" que genera confianza.
3. **C · 📊 Confianza y riesgo** — strip de un vistazo: **extracción** (confianza media) · **verificación** (confianza
   C3) · **fraude** (severidad o "sin señales") · **cobertura** (resultado del motor). Cada uno con color semántico.
4. **D · ✅ Recomendación / próximo paso** — **preparada por el copiloto, P1-safe**: describe el **siguiente paso del
   HUMANO**, nunca decide. Ej.: LISTO → "El copiloto preparó el dictamen; revísalo y **fírmalo**"; datos faltantes →
   "Falta **monto_reclamado** → sugerencia: pedirlo al asegurado antes de decidir"; fraude → "Señal de fraude — revisa
   antes de firmar". **Formato P1-safe:** `[paso del HUMANO] + [por qué] + [dato a verificar]`. **Nunca** un estado
   terminal ni las palabras "aprobar/rechazar/admitir/cerrar" como acción del copiloto (test fail-closed, §7).
5. **E · 🔍 Hallazgos del verificador (C3)** — qué revisó y qué señaló (confianza, señales). **C3 puede FALTAR**
   (review 🔴 #1): NO se persiste en el `Caso`, solo vive en la traza (evento `c3_verificador`), y en modo
   `deterministic` puede no existir → si falta, la tarjeta muestra **"Verificación no disponible"** (P7), nunca un
   valor falso. Se lee parseando el evento (§5), no del `Caso`.
6. **Layout claro y atractivo** — jerarquía: Resumen (hero) → Confianza → Actividad + Verificador → Dictamen/Fraude →
   **Decisión humana** (HITL, ya existe). Tema claro/oscuro. No se ve como CRUD.
7. **Tests + passive:** el dashboard sigue sin importar `rules/`/`orchestrator/`; el ensamblado es presentación pura.

## 4. Invariantes / NFR

- **P1 (HITL):** la **Recomendación (D)** describe un **PASO del humano** (verificar, corregir, pedir datos, revisar
  fraude, firmar), **nunca** un estado terminal (APROBADO/RECHAZADO) ni una acción automática ni "el copiloto aprueba".
  Los estados terminales siguen exigiendo firma (ya). El copiloto **prepara**.
- **P2:** el Resumen **cita el veredicto del motor** (no lo re-deriva ni lo suaviza); la cobertura la decidió el motor.
- **P3:** el Resumen/Actividad son **trazables** — cada afirmación sale de un campo/nodo real (extracción, C3, motor,
  fraude, traza). Nada de razonamiento inventado (P7 honestidad: si no hay dato, se dice "no disponible").
- **P5:** el Resumen usa campos estructurados + el aviso **redactado**; nunca `texto_crudo` crudo.
- **Passive:** todo el ensamblado vive en la capa de vista del dashboard (`dashboard/`), sin lógica de dominio nueva,
  sin importar `rules/`/`orchestrator/`. Sin deps nuevas.

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`app/dashboard/vista_caso.py`** (nuevo, presentación pura) — funciones que arman los view-models desde el `Caso`
  + la traza: `resumen_copiloto(caso)`, `actividad_agentes(traza)`, `confianza_riesgo(caso)`, `recomendacion(caso)`,
  `hallazgos_verificador(caso, traza)`. Todo determinístico, sin LLM, sin dominio.
  - **Contratos esperados (review 🔴 #2):** `app/contracts/caso.py` (`extraccion`, `poliza_match`, `dictamen`,
    `alerta_fraude`; NO tiene `verificacion`) y `app/contracts/dictamen.py` (`resultado`, `regla_aplicada`, `clausula`,
    `deducible_calculado`). Los terminales de cobertura citan cláusula (RULE-CTR-03).
  - **C3 se lee de la TRAZA (review 🔴 #1):** parsear el evento `c3_verificador` con regex
    `confianza=([0-9.]+),\s*señales=(\d+)`. Si el evento no existe (modo `deterministic`) → `{confianza: None,
    señales: []}` y la UI muestra "Verificación no disponible". El parsing es **regex sin decisión** → sigue passive.
  - **Mapa de nombres de nodo — AMBOS esquemas (review 🟠 #5):** determinístico (`intake/extractor/policy/motor/
    fraude`, ver `seed.sembrar_traza_demo`) y real (`c2_extraccion/c3_verificador/c4_policy_lookup/c5_motor_cobertura/
    c6_fraude/orquestador_*`, ver `orchestrator/c7`). Ej.: `extractor` y `c2_extraccion` → "Extractor · Haiku leyó el
    aviso". **Fallback:** nodo sin mapear → mostrar el nombre técnico tal cual (no romper el feed).
  - **P5 por campo (review 🟡 #6):** cada `CampoExtraido.valor` se muestra con `redact_pii_spans_es_co(str(valor))`;
    el aviso ya se redacta al cargar. Nunca `texto_crudo` crudo.
- **`app/dashboard/c11.py`** — `_detalle_context` agrega esos view-models al contexto (sigue passive).
- **`app/dashboard/templates/detalle.html`** — reestructurar con las secciones A-E + CSS agent-native (tarjetas,
  iconos, strip). Reusa el HITL existente (Decisión humana).
- **`static/style.css`** — estilos de las tarjetas/feed/strip (tema-aware).
- **Reuso:** `caso.extraccion/dictamen/alerta_fraude` (C3 solo en la traza), `get_replay_store().load`, la redacción
  P5. Nada nuevo de dominio.

## 6. Fuera de alcance

- **F (opcional, decisión D3):** una **nota en lenguaje natural generada por LLM** ("El copiloto para el analista: …").
  Es output agéntico genuino pero cuesta API/caso → si se incluye, **solo en modo `real`** y cacheada por caso.
- Rediseño del **panel de cumplimiento** (`/panel`) — Unit aparte. Cambiar el pipeline/agentes. Editar `rules/`.

## 7. Cómo se validará el Bolt

- **Tests (ejecutan):** `resumen_copiloto` refleja el caso (feliz → "cobertura preparada"; faltantes → "falta monto");
  **`test_recomendacion_nunca_decide`** — `recomendacion(caso)` NUNCA contiene {"aprobado","rechazado","admitido",
  "cerrado","aprobar","rechazar"} para NINGÚN estado (aserción P1 fail-closed, rompe ruidosamente); `actividad_agentes`
  mapea nodos en **ambos** esquemas (determinístico y real) + fallback; `hallazgos_verificador` con traza sin C3 →
  "no disponible"; estructural (dashboard sigue passive). Render del detalle 200 con A-E. `make test` verde.
- **Manual:** `make run` → abrir un caso → ver Resumen + Actividad + Confianza + Recomendación; comparar feliz vs
  fraude vs datos-faltantes.
- **`code-reviewer`** (P1 recomendación no-decide, P2 cita motor, P3 sin fabricar, P5, passive) → **PR**.

## 8. Decisiones (a resolver con el usuario)

- **D1 — Alcance:** ✅ **A + B + C + D + E** (determinístico, gratis, siempre presente).
- **D2 — Base:** ✅ ensamblado **determinístico** de las salidas reales (honesto, sin costo, siempre consistente).
- **D3 — Nota LLM (F):** ✅ **diferida** (cereza posterior; primero A-E).

## 9. Panel de expertos incorporado (research 2026-07-09)

- 🎨 **UX agent-native:** reasoning panel (1-2 factores, no CoT dump) + **activity feed** en lenguaje plano → §3.A/B.
- 🤖 **Producto copiloto:** action cards "hizo X · por qué · qué puedes hacer" → §3.A/D.
- 🏥 **Siniestros/IA:** recomendación + **confianza a la vista** + validación humana visible (16%→60%) → §3.C/D.
- Fuentes: Fuselab *Agent UX 2026* · Gökhan Meriç *Designing for AI Agents* · Mantlr *10 UX patterns* · Eleken
  *Agentic UX examples* · CopilotKit *Generative UI 2026* · Microsoft *Agentic AI in Insurance* · ITL *Agentic AI Claims 2026*.

## 10. Ajustes del review incorporados (code-reviewer)

Validación a dos ojos previa al Bolt. Hallazgos plegados:

- 🔴 **#1 C3 no está en el `Caso`:** se lee de la traza (regex del evento `c3_verificador`); si falta (modo
  `deterministic`) → "Verificación no disponible" (P7) → §3.E, §5.
- 🔴 **#2 Contratos no citados:** §5 referencia `contracts/caso.py` + `contracts/dictamen.py` con sus campos.
- 🟠 **#3 P1 fraseo:** la recomendación es `[paso humano]+[por qué]+[dato]`, nunca terminal/"aprobar" → §3.D, §4, §7.
- 🟠 **#4 P2 "citar literal":** el resumen cita `resultado+regla+clausula` sin parafrasear/inventar → §3.A.
- 🟠 **#5 Nombres de nodo en ambos esquemas** (`extractor` y `c2_extraccion`, …) + fallback → §5.
- 🟡 **#6 P5 por campo:** redactar cada `valor` → §5. 🟡 **#7 parsing regex = passive** (sin decisión) → §5.
- 🟡 **#8 Test P1 fail-closed:** lista de palabras prohibidas explícita → §7.
- ✅ **Confirmados:** intent agent-native correcto para HITL, criterios A-E verificables, passive, D3 (LLM) diferida.
