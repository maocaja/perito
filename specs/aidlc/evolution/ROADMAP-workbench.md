# Programa — Claims Workbench (AI OS for Insurance Operations)

> **Program doc (mini-Inception)** · **Estado:** 🟡 propuesto · Construye SOBRE el programa FNOL (U1-U10, en `main`).
> Cada Unit tiene su **change-level spec (QUÉ)** en `specs/aidlc/evolution/w*.md`. Loop por unit:
> **Bolt → code-reviewer → ajustar**. Rutas protegidas (🔒) → OK explícito + code-reviewer antes del CÓMO.
> **Diseño de referencia:** mockup hi-fi "Claims Copilot" (marca MAPFRE). Ver [[workbench-enfoque-agentico]].

## 0. Encuadre — NO es un CRUD con IA

Perito es un **AI Workbench**: la ventana desde la que un humano **coordina una orquesta invisible de agentes
especialistas** que preparan el caso, para que decida en minutos. Como Cursor para programar. **No** "un agente
que procesa correos". La orquesta YA es real: **Intake=C0 triage (U7) · Email=C2 (`llm/extractor`) · Policy
Validation=C4 (U8)+C5 motor · Consistency&Risk=C3 verifier+C6 fraude (U6) · Summary=W4/W19 · Orquestador=C7
(caps P4 + loop reflexivo U9)**. La UI la hace visible.

**🔴 INVARIANTE DEL PROGRAMA (no negociable, "PILAS"):** **nunca se mockea un AGENTE ni su rastro.** El Timeline
muestra los pasos REALES de la traza; los campos que el extractor real produce van reales. **Solo se mockea el
DATO que aún no producimos** (adjuntos, campos ricos hasta M2, audio), siempre **rotulado `demo` (P7)**. El mock
es el dato faltante, jamás el agente. La sustancia agéntica faltante (Document AI/M1, Evidence Correlator/M3,
extracción rica/M2) se construye **real**, no como chrome.

## 1. Intent — el cambio de paradigma

Dejar de ser "un agente que procesa correos" para ser el **sistema operativo del operador de siniestros**:
una **Workbench** (una sola estación, como Cursor pero para seguros) donde el operador **nunca pierde
contexto ni cambia de app**. El correo es solo una fuente de entrada; el valor es hacer **radicalmente mejor
el trabajo diario**: cola priorizada → caso ya entendido → evidencia trazable → decisión rápida.

Diseñado alrededor del **trabajo del operador** (cola, urgencia, info incompleta, decisión rápida), NO
alrededor del expediente/formulario. La IA elimina lo repetitivo; **el humano decide** (P1 intacto).

**Ya tenemos el cerebro** (U1-U10: extracción con evidencia+confianza, verificador, motor product-aware,
fraude cross-claim, triage, entity resolution, loop reflexivo). Este programa construye **la estación** encima
y una **fundación** de adjuntos/extracción rica que desbloquea el tier documental.

## 1.5 Estrategia de completitud — **mock-first, honesto** (dirección fija, no negociable)

Regla del programa: **la Workbench muestra la visión COMPLETA desde ya.**
- **Lo que tenemos** (≈70%: evidencia+confianza, verificador, motor, fraude, prioridad, checklist, acciones
  HITL) → **real**.
- **Lo que NO tenemos** (galería de docs, evidencia-que-salta-al-PDF, conteos de adjuntos, comparativa,
  copiloto conversacional, nombre del asegurado) → **MOCK rotulado (P7)**, diseñado como **punto de
  extensión**: la UI consume una interfaz/`provider` que hoy devuelve datos **sembrados/mock** y mañana los
  reales, **sin cambiar la vista**.
- El **backend real** de esos mocks (adjuntos al pipeline, extracción rica, Postgres de huellas, IA
  conversacional) es una **Mejora futura** (Fase M) que **reemplaza el mock**, no un bloqueo.
- **Honestidad (P7):** todo mock lleva un rótulo interno (`origen="demo"`/badge sutil) para no presentarlo
  como real ni en la demo ni en el código. **De esta estrategia no nos salimos.**

## 2. NO haremos (explícito)

- ❌ 15 pantallas y cientos de campos → **una** Workbench.
- ❌ Que el LLM **decida** cobertura/fraude/estado — sigue determinístico + humano (P1/P2/P6).
- ❌ IA conversacional **funcional** en este programa → **W15 es un MOCK** (el usuario la explica en vivo; se
  rotula honestamente como no-funcional, P7).
- ❌ Conectores multi-fuente reales (WhatsApp/portal/API) — es **posicionamiento**; el intake ya es extensible.
- ❌ Redacción visual perfecta de PII en imágenes (sigue diferida a fase-2; imágenes = huella).

## 3. Units de trabajo

Datos: **R** = real (ya lo tenemos) · **M** = mock/sembrado rotulado (P7), con provider intercambiable.

| Unit | Título | Datos | Gate 🔒 | Depende de | Fase |
|---|---|---|---|---|---|
| **W1** | Workbench unificada 3-columnas (shell) | R | — (ADR-001) | — | 1 Estación |
| **W2** | Header del caso (tipo + asegurado + confianza% + tiempo est.) | R + **M** (asegurado, tiempo) | — | — | 1 |
| **W3** | Timeline visual de la IA (pasos + conteos de docs) | R + **M** (conteos) | — | — | 1 |
| **W4** | Resumen ejecutivo narrativo (prosa) | R | P1 · P5 | — | 1 |
| **W5** | Riesgos ("míralo", inconsistencias clickables) | R | 🔒 P6 | — | 1 |
| **W6** | Health Check (% completo + checklist unificado) | R | — | — | 1 |
| **W7** | Explicación "por qué" de la cobertura | R | P2 | — | 1 |
| **W8** | Cola inteligente por razón (🔴🟠🟡🟢) | R | — | — | 1 |
| **W9** | Acciones ampliadas (solicitar docs · radicar · escalar · a-fraude · borrador) | R + **M** (envío docs) | 🔒 P1 | — | 1 |
| **W10** | Flujo cero-formulario / teclado-first (ENTER → siguiente) | R | P1 | W9 | 1 |
| **W11** | Centro de documentos (galería, Extraído/Validado/Relacionado) | **M** (provider) | P5 | — | 2 Documental |
| **W12** | Evidencia clickable → salto a la fuente (visor + ancla, NotebookLM) | **M** (provider) | 🔒 P5 | W11 | 2 |
| **W13** | Vista comparativa multi-correo (mismo cliente, cambios) | **M** (provider) | P5 | — | 2 |
| **W14** | Panel de productividad del operador (hoy N · tiempo · SLA · pendientes) | R + **M** (SLA/tiempo) | — | — | 3 |
| **W15** | Copiloto conversacional contextual **(MOCK)** | **M** | P7 (rótulo) | — | 3 |
| **W16** | Rebrand MAPFRE / "Claims Copilot" (colores, sidebar navy de íconos, búsqueda, acciones color, layout 5 paneles) | R | — (ADR-001) | — | 1b Hi-fi |
| **W17** | Panel "Información Extraída" (campos reales + ricos mock, valor·confianza·**fuente**, "Ver todos (28)") | R + **M** | P5 · P3 | (M2) | 1b Hi-fi |
| **W18** | Timeline **agent-native** (un nodo por AGENTE real de la traza; tokens/confianza) | R | 🔴 no mock | — | 1b Hi-fi |
| **W19** | **Summary Agent** (LLM mockeable; upgrade de W4) — 6º agente visible | R | 🔒 P1 · P5 | — | 1b Hi-fi |
| **M1** | *(Mejora/agente)* **Document AI** — adjuntos real al pipeline + OCR/visión + contrato `Adjunto` | R | 🔒 P5 | U4 | M Agentes |
| **M2** | *(Mejora/agente)* **Extracción rica** real (asegurado/placa/vehículo/terceros + huella) | R | 🔒 P5 | M1 | M Agentes |
| **M3** | *(Agente nuevo)* **Evidence Correlator** — cruza FUENTES (placa en foto vs correo vs PDF) | R | 🔒 P6 | M1, M2 | M Agentes |

**Fase M (mejoras futuras):** M1/M2 **reemplazan los providers mock** de W2/W3/W11/W12/W13 por datos reales,
**sin tocar la UI** (misma interfaz). Desbloquean además foto-reutilizada (U6) y U8 real. No bloquean la demo.

## 4. Orden de ataque sugerido

**Fase 1** (W1 → W2…W8 → W9 → W10): la estación completa con el cerebro real + mocks puntuales rotulados.
**Fase 2** (W11 → W12 → W13): tier documental **con providers mock/sembrados** (galería, evidencia-que-salta,
comparativa) — la visión completa, honesta. **Fase 3** (W14, W15-mock). **Fase M** (M1/M2) cuando se quiera el
backend real detrás de los mocks. Cada provider mock se define con la **misma interfaz** que consumirá el real.

## 5. Invariantes del programa (heredados, no negociables)

- **P1:** la Workbench **prepara**; el humano firma. Ninguna acción nueva alcanza estado terminal sin humano.
- **P2:** la cobertura la dicta el motor R1-R5; la Workbench solo la **presenta/explica**.
- **P5:** todo lo que se muestra/persiste va redactado; los adjuntos y el visor nunca exponen PII cruda.
- **P6:** "Riesgos" solo sugiere ("míralo"); ninguna señal decide/bloquea.
- **P7:** honestidad de scope — el tiempo estimado es estimado; el copiloto conversacional es un **mock**; lo
  que no tenemos, se declara.
- **ADR-001:** server-rendered (Jinja2/HTMX), JS mínimo; cero lógica de decisión en cliente.
- **Clean Code + SOLID** (`.claude/rules/clean-code-solid.md`): nombres dicientes, funciones pequeñas (SRP),
  sin duplicación/dead code/magic numbers. **DIP es el corazón del mock-first**: cada `provider`
  (`campos_extraidos`, `documentos_de`, `ancla_evidencia`, `Correlacion`…) es una **abstracción**; mock y real
  (M1/M2/M3) son implementaciones **intercambiables** que respetan el mismo contrato (Liskov). Se verifica en
  el code-reviewer de cada unit.

## 6. Units con ruta protegida (🔒)

**W12, M1, M2 (P5)** · **W5, M3 (P6)** · **W9, W19 (P1)** → **OK explícito + code-reviewer obligatorio antes del CÓMO.**

## 7. Estado de revisión del QUÉ

**Ronda 1 (W1-W15 + M1/M2):** 0 críticos, mock-first honesta. 4 precisiones al QUÉ (W9/W10/W11/W12, ver su §7).

**Ronda 2 (hi-fi + agentes: W16-W19, M3):** 0 críticos de bloqueo; el reviewer confirmó el **blindaje agéntico**
y M3 passive (P6). Precisiones aplicadas al §7 de cada spec: **W19** (guard fail-closed ampliado — no inventa
cobertura, prompt redactado), **M3** (contrato `Correlacion` overlay + normalización reusada), **W17** (contrato
`CampoUI` + frontera real/demo por procedencia, no por confianza), **W18** (mock de conteos separado del rastro
de agentes), **W16** (config de marca centralizada + mapeo de nav a rutas reales).

El §7 "tras el CÓMO" de cada unit se completa al construirla (precisiones de implementación).
