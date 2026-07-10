# M3 — Evidence Correlator (agente nuevo) 🔒 P6

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** M agentes
> **LLM/det:** ⚙️ (correlación) + 🤖 (explica) · **Depende de:** M1, M2 · **Datos:** R
> **🔒 P6 → OK explícito + code-reviewer antes del CÓMO.**

## 1. Intent

El agente que da el **"aha" agéntico** de la narrativa: **cruza FUENTES dentro de un caso**. *"La placa ABC123
está en la foto 8 y en el correo, pero en la foto posterior se lee ABC-124"*; *"la fecha del PDF (10/07) difiere
del correo (11/07)"*; *"el nombre del correo coincide con el del SOAT"*. Correlaciona el **mismo dato desde
distintas fuentes**, sube/baja la confianza por campo y emite **inconsistencias** (a Riesgos, P6). Determinístico
detecta; el LLM explica.

## 2. Criterios de completitud (verificables)

1. **Consume campos multi-fuente** (M2: cada `CampoExtraido` con su `origen`/fuente; M1: adjuntos leídos).
2. **Correlación determinística:** para el mismo campo lógico (placa, fecha, nombre) con **≥2 fuentes**,
   compara los valores normalizados → **coinciden** (sube confianza) o **divergen** (emite inconsistencia con
   ambas fuentes citadas + confianza).
3. **Alimenta:** las inconsistencias van a **Riesgos (W5/P6)**; la confianza consolidada por campo va a
   **Información Extraída (W17)**.
4. **Emite evento de traza** → aparece en el **Timeline (W18)** como agente "Correlación de evidencia".
5. **Explicación LLM** (mockeable) del "por qué" de cada divergencia; el LLM **no detecta** (eso es
   determinístico).

## 3. Invariantes / restricciones

- **🔒 P6:** las inconsistencias **solo sugieren** ("míralo"); no cambian estado ni deciden fraude. Confianza
  ∈ [0,1) por señal.
- **P2:** no toca la decisión de cobertura (eso es el motor).
- **P5:** compara valores normalizados/huellas y cita la **fuente** (foto 8, PDF pág 3), nunca PII cruda extra.
- **P4:** correlación acotada (nº de campos × fuentes por caso); sin loops.
- **P7:** hoy LATENTE (requiere M1/M2 para tener fuentes múltiples); cableado y listo, no inventa señales sin
  fuentes reales.

## 4. Fuera de alcance

- Visión/OCR (M1); extracción rica (M2). M3 **consume** lo que ellos producen.

## 5. Verificación (tests fail-closed)

- Mismo campo en 2 fuentes con valores distintos → inconsistencia citando ambas fuentes + confianza <1.0.
- Coincidencia en 2 fuentes → sube la confianza del campo (no emite inconsistencia).
- Ninguna inconsistencia cambia `caso.estado` ni deshabilita la firma (🔒 P6, aserción).
- Sin fuentes múltiples (M1/M2 ausentes) → no inventa señales (latente).

## 6. Notas CÓMO

Nuevo `agents/evidence_correlator.py` (o `fraud/`) que agrupa campos por nombre lógico y compara por fuente.
Consume M1/M2; emite a Riesgos + confianza a W17 + evento de traza a W18. Determinístico + explicación LLM
mockeable.

## 7. Precisiones tras code-review

- **🔴 Contrato formal `Correlacion` (OVERLAY, no muta en sitio):** M3 produce un overlay separado, **no**
  reescribe `CampoExtraido.confianza`. Forma:
  `Correlacion: {campo_nombre, valores_por_fuente: dict[str,str], fuentes: list[str], coincide: bool,
  confianza_ajustada: float [0,1), inconsistencia: str | None}`. W17 consulta este overlay (si existe) además
  de `Caso.extraccion`; si no hay overlay, muestra la confianza cruda del contrato.
- **🔴 Normalización explícita:** reusa `_norm_id`/`_norm_nombre` de `policy/lookup.py` (U8) — mismo criterio
  (alfanum mayúscula para placa/cédula; casefold+colapsa para nombre). Nada de fuzzy en v1 (match exacto
  normalizado). Ante duda, P6 protege: emite inconsistencia, no decide.
- **Integración en el pipeline:** corre **después** de M1/M2 (cuando hay campos con ≥2 fuentes), junto a C6
  (informativo, no escala). Emite: (a) inconsistencias → Riesgos (W5/P6), (b) overlay de confianza → W17,
  (c) evento de traza → Timeline (W18). **Latente** sin fuentes múltiples (P7).
- **P6 confirmado passive por el reviewer:** ninguna inconsistencia cambia estado/firma.

**Ronda CÓMO (2026-07-10, P6 BLINDADO — aprobado):**
- **Integración:** corre en el poller (`_correlacionar_evidencia`) TRAS M1/M2 — **intake, no el orquestador
  protegido**; emite el evento de traza `evidence_correlator` (Timeline W18, nodo ya mapeado) y adjunta el
  overlay `Caso.correlaciones`. Fuentes: el correo (extracción M2) + cada adjunto legible (mismo extractor
  determinístico de M2 por fuente). La foto es no-legible (huella) hasta la fase visual → hoy cruza correo↔PDF.
- **Fixes del review aplicados:** constante única `CONFIANZA_DIVERGENCIA/COINCIDENCIA` en el contrato (DRY);
  `_norm_fecha` normaliza formatos de fecha (evita divergencia falsa '10/07' vs '10-7'); severidad **MEDIA**
  (no BAJA) cuando el único riesgo es una divergencia cross-fuente; test extra de no-escalamiento desde
  LISTO_PARA_APROBAR; documentado que `extraer_entidades` es reuso de M2 (determinístico, no mock).
- **P5 (verificado):** un valor `[REDACTED]` de un adjunto (M1) se excluye de la comparación → no genera
  divergencia falsa contra el valor crudo del correo; los valores citados se redactan.
- **Criterio #5 (explicación LLM):** hoy la inconsistencia es texto **determinístico** (honesto, hermético);
  la elaboración LLM es el mismo patrón mockeable de W19 y se puede capar encima — la DETECCIÓN ya es
  determinística (el LLM solo reformularía, nunca detecta). Diferido como mejora, no bloquea.
