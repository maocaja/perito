# 📋 U2 NFR Requirements Plan — Extracción·Verificación·Grounding

**Unidad:** U2 · Extracción · Verificación · Grounding  
**Depende de:** Functional Design aprobado  
**Objetivo:** NFR anclados a lo que U2 realmente ejecuta (runtime, seguridad, efectividad)  

---

## Enfoque: NFR Efectivos, No Catálogo

U2 tiene **dos llamadas al LLM** (C2 Haiku + C3 Sonnet):
- Costo/latencia por extracción (RNF-02/03)
- Accuracy extracción ≥90-95% (RNF-04 métrica efectiva aquí)
- Campos inventados ≈0 (RNF-07, ahora es el trabajo real de U2)
- Efectividad redacción PII (LLMPayloadBuilder no filtra)
- Umbral de confianza para escalamiento (P4 configurable)

N/A honesto: disponibilidad/escalabilidad cloud (P7, fuera de MVP).

---

## Steps del Plan

### Step 1: Analizar Functional Design
- [ ] Revisar domain-entities.md: C2 (Haiku), C3 (Sonnet Capa 1), C3 (Código Capa 2), C4 (SQL)
- [ ] Revisar business-rules.md: RULE-EXT-01..06, RULE-VER-01..04, RULE-POL-01..03
- [ ] Revisar business-logic-model.md: Happy Path, 4 Flujos de Error, propiedades verificables

### Step 2: Crear Plan de NFR
- [ ] Identificar NFR de performance (latencia/costo de LLM)
- [ ] Identificar NFR de correctitud (accuracy extracción, no-invención)
- [ ] Identificar NFR de seguridad (efectividad PII redaction)
- [ ] Identificar NFR de fiabilidad (configurabilidad umbral)

### Step 3-4: Preguntas de Clarificación

---

## ❓ PREGUNTAS DE CLARIFICACIÓN

### P1: Performance — Latencia de Extracción (Haiku + Sonnet)

**Contexto:** U2 invoca Claude Haiku (C2) + Claude Sonnet (C3 Capa 1) secuencialmente.

**P1.1:** ¿Cuál es el objetivo de latencia end-to-end de U2?
- A) < 1 segundo (interactivo)
- B) < 5 segundos (tolerable)
- C) < 30 segundos (batch aceptable)
- D) No es crítico para MVP

[Answer]: 

**P1.2:** ¿Se mide latencia por componente (Haiku, Sonnet separados) o solo end-to-end U2?

[Answer]: 

**P1.3:** ¿Hay SLA de latencia por tipo de aviso (documento limpio vs. sucio)?

[Answer]: 

---

### P2: Performance — Costo de LLM (RNF-02/03)

**Contexto:** Haiku ~$0.8/1M tokens, Sonnet ~$3/1M tokens, Opus más caro. U2 costo total = factor de escala.

**P2.1:** ¿Cuál es el presupuesto de costo por extracción?
- A) < $0.01 (muy económico)
- B) < $0.05 (económico)
- C) < $0.10 (aceptable)
- D) No hay límite (solo usa mejor modelo)

[Answer]: 

**P2.2:** ¿Es el costo por caso una métrica de monitoreo (dashboard) o solo presupuestaria?

[Answer]: 

---

### P3: Correctitud — Accuracy de Extracción (RNF-04)

**Contexto:** "Campos extraídos correctos" — ¿qué significa? Por campo? Globalmente?

**P3.1:** ¿Cuál es el objetivo de accuracy de extracción?
- A) ≥ 90% (campos correctos por caso)
- B) ≥ 95% (muy alto)
- C) ≥ 99% (casi perfecto)
- D) Depende del campo (número_poliza ≥99%, otro ≥90%)

[Answer]: 

**P3.2:** ¿Cómo se mide accuracy?
- A) Exactitud de valor (fecha_siniestro=2026-06-15 vs ground truth)
- B) Presencia (campo presente sí/no)
- C) Ambas (presencia + exactitud)

[Answer]: 

**P3.3:** ¿Hay diferencia de accuracy esperada entre documento limpio vs. sucio?

[Answer]: 

---

### P4: Correctitud — Campos Inventados ≈ 0 (RNF-07, Métrica Efectiva U2)

**Contexto:** P4 (no-invención) ahora es efectivamente medible en U2. Haiku + Sonnet pueden alucinar.

**P4.1:** ¿Cómo se define "campo inventado"?
- A) valor ≠ None pero ausente=True en ground truth
- B) valor presente pero no aparece en aviso original
- C) Ambas (cualquiera es invención)

[Answer]: 

**P4.2:** ¿Cuál es el objetivo de tasa de invención?
- A) 0% (cero inventados, fail-closed)
- B) < 0.5% (excepcional)
- C) < 1% (muy bueno)
- D) < 5% (aceptable)

[Answer]: 

**P4.3:** ¿Se escala el caso si campos inventados > umbral, o solo se monitorea?

[Answer]: 

---

### P5: Seguridad — Efectividad de Redacción PII (C2 + C3)

**Contexto:** LLMPayloadBuilder redacta PII (deny-by-default). ¿De verdad funciona?

**P5.1:** ¿Cómo se valida que LLMPayloadBuilder está redactando?
- A) Auditoría manual (spot-check de prompts)
- B) Test automatizado (inyecta PII, verifica [REDACTED] en prompt)
- C) Inspección de logs (verificar que PII no aparece)
- D) Todas

[Answer]: 

**P5.2:** ¿Hay PII que NO debería redactarse (ej: número_poliza)?

[Answer]: 

**P5.3:** Si LLMPayloadBuilder falla (PII no redactada), ¿se escala el caso o se rechaza?

[Answer]: 

---

### P6: Fiabilidad — Umbral de Confianza Configurable (P4, RULE-EXT-03)

**Contexto:** C2 reporta confianza por campo. Si confianza < umbral → escalamiento.

**P6.1:** ¿Cuál es el umbral de confianza inicial?
- A) 30% (bajo, tolera ambigüedad)
- B) 50% (medio)
- C) 70% (alto, conservador)
- D) 90% (muy alto, casi perfecto)

[Answer]: 

**P6.2:** ¿El umbral es:
- A) Global (todos los campos)
- B) Por campo (número_poliza 90%, otro 50%)
- C) Configurable por usuario/tenant

[Answer]: 

**P6.3:** Si confianza global < umbral → ¿siempre se escala, o es signal + otras heurísticas?

[Answer]: 

---

### P7: Disponibilidad / Escalabilidad (P7 — Honesto N/A)

**Contexto:** MVP local, no cloud. ¿Pero queremos dejar puerta abierta a SLA futuro?

**P7.1:** ¿Se especifica uptime SLA para U2?
- A) Sí, 99.5% (nube estándar)
- B) Sí, 99.9% (crítico)
- C) N/A (MVP local, no SLA)

[Answer]: 

**P7.2:** ¿Se requiere failover o disaster recovery en MVP?

[Answer]: 

---

### P8: Tech Stack — LLM Models (Haiku vs Sonnet, versiones)

**Contexto:** U1 confirmó: Haiku para C2 (costo), Sonnet para C3 Capa 1 (precisión).

**P8.1:** ¿Versiones concretas de modelos?
- A) claude-3-5-haiku-20241022 (C2), claude-3-5-sonnet-20241022 (C3)
- B) Usar últimas disponibles en anthropic.Anthropic()
- C) Otra (¿cuál?)

[Answer]: 

**P8.2:** ¿Se permite cambiar modelos en producción (ej: cambiar Haiku a Sonnet)?

[Answer]: 

---

### P9: Tech Stack — Database (PostgreSQL + pgvector para RAG)

**Contexto:** U1 definió postgres + pgvector. ¿Suficiente para U2?

**P9.1:** ¿Se requiere sharding o replicación para U2?
- A) No (MVP local)
- B) Sí (preparar para escala)

[Answer]: 

**P9.2:** ¿Retention policy para logs de extracción (auditoria)?
- A) Indefinida (todos los logs)
- B) 90 días (balance costo/auditoría)
- C) 30 días

[Answer]: 

---

### P10: Observabilidad — Métricas de U2

**Contexto:** U5 tendrá evals. ¿Qué métrica es KPI de U2?

**P10.1:** ¿Cuáles son las top-3 métricas de monitoreo de U2?
1. [Answer]:
2. [Answer]:
3. [Answer]:

**P10.2:** ¿Se expone dashboard de accuracy/costo en tiempo real, o solo en evals?

[Answer]: 

---

### P11: Mantenibilidad — Trazabilidad de Decisiones (RNF-05)

**Contexto:** Cada extracción debe ser trazable a prompts + responses + modelos.

**P11.1:** ¿Se loguean completos los prompts enviados al LLM (redactados)?

[Answer]: 

**P11.2:** ¿Se almacenan tokens_used y latencia por call LLM para cost tracking?

[Answer]: 

---

## Próximos Pasos

1. **Recopilar respuestas** a todas las preguntas `[Answer]:` arriba
2. **Mi revisión:** verificar coherencia (accuracy + cost + umbral alineados)
3. **Generar artefactos:** nfr-requirements.md + tech-stack-decisions.md
4. **Tu aprobación** antes de NFR Design

