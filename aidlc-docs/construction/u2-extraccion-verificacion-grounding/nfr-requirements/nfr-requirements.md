# NFR Requirements — U2 Extracción·Verificación·Grounding

## Resumen ejecutivo

U2 ejecuta **dos llamadas LLM** (C2 Haiku + C3 Sonnet) contra aviso + redacción PII. NFRs anclados a runtime real:
- Performance: latencia/costo/caso medida, sin SLA duro MVP
- Correctitud: accuracy ≥90-95%, campos inventados ≈0% fail-closed
- Seguridad: redacción PII validada automatizada
- Fiabilidad: umbral confianza 70% configurable, escalamiento a U4
- Observabilidad: top-3 KPIs (accuracy, no-invención, costo) alimentan U5
- Mantenibilidad: trazabilidad completa (prompts redactados, tokens/latencia)

---

## Performance (RNF-02, RNF-03)

### Latencia de Extracción

| Escala | Objetivo | Notas |
|--------|----------|-------|
| C2 (Haiku) | Medido, sin SLA | Modelo más rápido; ~1-3s típico |
| C3 Capa 1 (Sonnet) | Medido, sin SLA | Confirmación adversarial; ~2-5s típico |
| C3 Capa 2 (Código) | < 100ms | Validación local determinística |
| **End-to-end U2** | Reportado por estrato | Limpio vs sucio por separado |

**Estratificación:** Medir y reportar latencia diferenciada por documento (limpio=rápido, sucio=investigación más lenta). No promediar.

### Costo por Caso (RNF-02/03)

| Línea | Costo | Notas |
|-------|-------|-------|
| Haiku C2 | $1/$5 per 1M tokens | 200K ctx; avg ~500 tokens/extracción → ~$0.0005-0.001 |
| Sonnet C3 Capa 1 | $3/$15 per 1M tokens | 1M ctx; avg ~1000 tokens/verificación → $0.003-0.015 |
| **Target por caso** | < $0.05 | Incluye overhead; medido en producción |
| **Presupuesto de tokens (P4)** | 10,000 default | Cap duro en Settings; no es SLA de costo |

**Política:** Monitorear gasto real; alertar si promedio/caso > $0.05. Presupuesto_tokens es limite P4, no restricción económica.

---

## Correctitud (RNF-04, RNF-07)

### Accuracy de Extracción (RNF-04)

| Campo | Target | Definición |
|--------|--------|-----------|
| `numero_poliza` | ≥ 99% | Exactitud valor vs ground truth; crítico para grounding |
| `fecha_siniestro` | ≥ 95% | Presencia + exactitud formato |
| `tipo_siniestro` | ≥ 90% | Enum match (AUTO_COLISION, ROBO, etc) |
| **Otros** | ≥ 90% | Presencia + exactitud |

**Medición:** Por campo + por estrato (limpio vs sucio). Reportar desglose, no promediar globalmente.

### No-Invención (RNF-07 — Fail-Closed)

| Métrica | Target | Definición | Acción |
|---------|--------|-----------|--------|
| **Campos inventados** | ≈ 0% (fail-closed) | valor ≠ None ∧ (ausente en GT ∨ no aparece en aviso) | Escala a U4 + monitorea |
| **Threshold detección** | > 1% de casos | Si detección > 1% en eval, revisar C2/C3 | Ajustar prompts |

**Estrategia:** C3 adversarial (Capa 1) intenta atrapar alucinaciones; U5 evals miden tasa real; dashboard de monitoreo (M9) traza per-caso.

---

## Seguridad (RNF-01, P5)

### Redacción PII (LLMPayloadBuilder)

| Componente | PII | No-PII | Validación |
|------------|-----|--------|-----------|
| C2 Input | cédula, nombre, dirección, teléfono → [REDACTED] | número_poliza (pasa al LLM) | Test inyecta PII, verifica [REDACTED] |
| C3 Capa 1 Input | redactado (hereda de C2) | idem | Test inyecta PII, verifica [REDACTED] |
| Logs | Prompts redactados (P3+PIA) | Nunca PII crudo | Inspección spot-check |

**Fail-closed:** Si LLMPayloadBuilder falla (PII no redactada), no se envía al LLM, se escala a REQUIERE_REVISION.

---

## Fiabilidad (RNF-06)

### Umbral de Confianza (P4, RULE-EXT-03)

- **Inicial:** 70% (conservador, escala frecuente)
- **Configurable:** Sí (app/config.py)
- **Aplicación:** Por campo (número_poliza alto, otros medio)
- **Señal:** Si confianza < umbral → SeñalEscalamiento (CONFIANZA_BAJA)
- **Decisión:** U4 escalada, no U2 unilateral

**Estrategia:** Empezar conservador (70%) → medir accuracy real → ajustar si es necesario.

---

## Observabilidad (M9, RNF-03)

### Top-3 KPIs de U2

1. **Accuracy de extracción** (por campo, limpio vs sucio) — alimenta RNF-04 evals
2. **Tasa de campos inventados** (≈0% fail-closed) — alimenta RNF-07 evals
3. **Costo + Latencia/caso** (en dashboard) — alimenta RNF-02/03 trends

### Trazabilidad (RNF-05)

- **Prompts redactados** (P3 + P5): loguear entrada redactada a LLM
- **tokens_used + latencia** por call (C2, C3 Capa 1, C3 Capa 2 determinístico)
- **SeñalEscalamiento** completa (motivo, evidencia, datos_contexto)

**Herramienta:** M9 (Langfuse) traza por nodo; U5 evals importan métricas de U2.

---

## Mantenibilidad (RNF-05)

- Prompts in-code sin secretos (templates en app/llm/)
- Model IDs en config.py (fácil cambiar sin redeploy)
- Fallback si messages.parse no está (output_config JSON schema + json.loads + validar contra Pydantic)
- Versión anthropic pinneada (verificada soporta messages.parse/output_config)

---

## N/A — Fuera de Alcance MVP

- **Disponibilidad (P7):** No aplica. MVP local sin SLA. U5 owns cloud readiness.
- **Escalabilidad (P7):** No sharding, no replicación. Single-region. U5 owns.
- **Dashboard en vivo (P10.2):** Métricas alimentan harness U5 evals, no UI live. U5 owns UI.

---

## Casos de Prueba (Estratificación)

U2 debe medirse por estrato (specs/prd.md Segmento 11):

1. **happy:** Documento limpio, extracción correcta, confianza alta
2. **campos-faltantes:** Documento incompleto, algunos ausentes=True
3. **poliza-no-encontrada:** Número_poliza no existe en BD
4. **cobertura-negativa:** Tipo siniestro no cubierto (descubierto en U3, señal en U2 si confianza baja)
5. **fraude:** Inconsistencias atrapadaspor C3 adversarial
6. **SOAT:** Documento SOAT (no aplica en MVP)
7. **documento-sucio:** OCR pobre, redacción falla, confianza baja

**Métrica:** Reportar accuracy/costo/latencia por estrato, no global.

---
