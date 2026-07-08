# 📋 U2 Functional Design Plan — Extracción·Verificación·Grounding

**Unidad:** U2 · Extracción · Verificación · Grounding  
**Historias:** H-01, H-02, H-03, H-04, H-06  
**Depende de:** U1 (contratos, redactores PII, RAG de pólizas)  
**Entrega:** Aviso caótico → extracción verificada + señales de escala  

---

## ⚠️ TRAMPAS DE INVARIANTE (Respuestas Obligadas — No Negociables)

Estos 5 puntos son donde U2 puede romper P1/P2/P4/P5. Respuestas marcadas como TRAMPA.

---

## RESPUESTAS A PREGUNTAS

### P1: Modelo de Extracción (H-02)

**P1.1:** ¿Qué campos OBLIGATORIOS debe extraer siempre?

[Answer]: `número_poliza, fecha_siniestro, tipo_siniestro, monto_reclamado, nombre_asegurado, cédula_asegurado (PII)`

**Nota:** `[DECIDIDO EN U1]` — Lista derivada de lo que R1-R5 consume (U3), no inventada. Ver components.md + business-rules de U1.

---

**P1.2:** ¿Hay campos OPCIONALES que pueden faltar sin que sea error?

[Answer]: `teléfono, email, dirección, detalles_tercero`

**Nota:** `[DECIDIDO EN U1]` — Son enriquecedores, no críticos para cobertura.

---

**P1.3:** ¿Quién decide la lista de campos esperados — hardcodeada en Extractor, o leída de configuración/schema?

[Answer]: `Contrato tipado (ExtraccionValidada.campos: list[CampoExtraido]); fuente única = U1.`

**Nota:** `[DECIDIDO EN U1]` — Ver `app/contracts/extraccion.py`. No strings ad-hoc.

---

**P1.4:** ¿El `CampoExtraido.confianza` (score 0-100) es devuelto por Claude, o calculado post-extracción?

[Answer]: `Reportado por Claude por campo. Usado SOLO como señal de escalamiento (P4), NUNCA decide cobertura ni terminal.`

**Nota:** `[DECIDIDO EN U1]` — confianza es metadata, no lógica de negocio.

---

### P2: Verificación (H-03 — Adversarial Check)

**P2.1:** ¿Qué reglas de consistencia debe validar el Verifier?

[Answer]: 
```
- fecha_siniestro ≤ hoy (no siniestro futuro)
- monto_reclamado > 0
- tipo_siniestro ∈ {enum definido en U1}
- nombre_asegurado ≠ vacío
- Formato de cédula válido (si presente)
```

**NO toca:** vigencia (R1), exclusiones (R3), cobertura — eso es U3 determinístico.

**Nota:** `[TRAMPA P2]` — Si el Verifier decidiera "aplica R1 vigencia" o "aplica R3 exclusión", estaría mediando cobertura (LLM decide → viola P2). Verifier = solo **consistencia de extracción**, no **cobertura**.

---

**P2.2:** Si el Verifier rechaza un campo (lo marca como inconsistente), ¿qué hace?

[Answer]: `Marca como inconsistente + emite señal (motivo + evidencia) → U4 escala a REQUIERE_REVISION. No loop sin cap (P4), no rechaza-todo unilateral.`

**Nota:** `[DECIDIDO EN U1]` — P4 Terminación prohíbe loops sin límite.

---

**P2.3:** ¿Puede el Verifier "reparar" campos obvios (ej: normalizar formato de teléfono)?

[Answer]: `NO. Solo marca inconsistencias. No alterar valor silenciosamente (violaría P3 trazabilidad + P4 no-invención).`

**Nota:** `[DECIDIDO EN U1]` — Todo cambio debe ser auditable.

---

### P3: Grounding en Póliza (H-04 — Policy Lookup)

**P3.1:** ¿Cómo se busca la póliza?

[Answer]: 
```
A) Match determinístico por número_poliza exacto (SQL/BD)
B) Si no hay exacto → candidatas por similitud (RAG/pgvector retrieval, NO chat model)
NO opción D ("Claude decide qué póliza suena") — viola RF-10/P4
```

**Nota:** `[TRAMPA P4]` — Opción D dejaría al LLM forzar un match → violación de RF-10 (no forzar match) + P4 (RF-10 es parte de Cotas determinísticas). RAG/pgvector = **recuperar cláusulas**, no **elegir la póliza**.

---

**P3.2:** Si encuentra múltiples candidatas, ¿cómo elige la "mejor"?

[Answer]: `A) Devuelve TODAS sin promover. encontrada=False; ranking solo para orden de display en UI, NUNCA auto-seleccionar.`

**Nota:** `[TRAMPA P4]` — RULE-CTR-07 + RF-10: encontrada=False ⇒ poliza=None. Promover la "mejor" candidata automáticamente = forzar match (viola P4). El humano elige (vía U4).

---

**P3.3:** ¿Qué retorna PolicyLookup?

[Answer]: `Estructura completa ResultadoPoliza (contrato U1): encontrada, poliza, candidatas.`

**Nota:** `[DECIDIDO EN U1]` — Ver `app/contracts/poliza.py`.

---

**P3.4:** ¿RF-10 ("no forzar match") significa que si NO encontrada, devuelve candidatas vacías, o puede traer opciones "débiles"?

[Answer]: `encontrada=False ⇒ poliza=None; candidatas puede traer opciones débiles (para el humano elegir en U4).`

**Nota:** `[TRAMPA P4]` — Las candidatas son información, no decisión.

---

### P4: Manejo de Campos Faltantes (H-06 — "No Inventar")

**P4.1:** Cuando Claude no encuentra un campo en el texto, ¿qué sucede?

[Answer]: `SOLO A: ausente=True, valor=None. Nada de inferencia (opción B) ni strings literales (opción C).`

**Nota:** `[TRAMPA P4]` — Inferir de otro campo o devolver "[NO_ENCONTRADO]" = invención → viola P4/H-06/RULE-GEN-02 (no-invención).

---

**P4.2:** ¿Si un campo OBLIGATORIO está ausente, qué hace Extractor?

[Answer]: `B) Emite señal (motivo: "campo obligatorio ausente") → U4 escala a REQUIERE_REVISION. No loop (P4).`

**Nota:** `[DECIDIDO EN U1]` — P4 prohíbe loops sin cap.

---

**P4.3:** ¿El Verifier rechaza extractiones con campos obligatorios faltantes, o solo marca inconsistencias internas?

[Answer]: `Complementarios: Extractor marca "obligatorio faltante"; Verifier valida consistencia interna. Ambos → emiten señales a U4.`

**Nota:** `[DECIDIDO EN U1]` — División de responsabilidades clara.

---

### P5: Señales de Escala (H-01, H-03, H-04, H-06)

**P5.1:** ¿Qué condiciones emiten una señal de escala?

[Answer]: 
```
- Confianza global baja (threshold por definir en U2 design)
- Verifier rechaza consistencia
- PolicyLookup: sin match exacto, múltiples candidatas, o no-encontrada
- Campos obligatorios faltantes
- Documento calidad SUCIO
→ U2 emite; U4 decide escalar a REQUIERE_REVISION
```

**Nota:** `[DECIDIDO EN U1]` — Lista derivada de H-01, H-03, H-04, H-06.

---

**P5.2:** ¿Cómo se codifica la señal?

[Answer]: `U2 NO setea Caso.estado. Emite un contrato tipado (ej. SeñalEscalamiento{motivo: str, evidencia: list[EvidenciaOrigen]}). U4/hitl transiciona el estado.`

**Nota:** `[TRAMPA P1]` — RULE-CTR-05 (P1): **solo hitl/U4 muta estado**. Si U2 pone `Caso.estado=REQUIERE_REVISION`, viola el endurecimiento P1. hitl/ es el único mutador.

---

**P5.3:** ¿U2 puede "sugerir" un curso de acción (ej: "use candidata #2") o solo emite el hecho?

[Answer]: `Emite el hecho + candidatas/evidencia, SIN preferencia. "Usar candidata #2" = empujar decisión → el humano elige en U4.`

**Nota:** `[DECIDIDO EN U1]` — No confundir "información" con "preferencia".

---

### P6: Integración con RAG de Pólizas (P5 PII, P3 Trazabilidad)

**P6.1:** ¿Qué información del aviso (potencialmente PII) se envía al RAG/Claude?

[Answer]: `TODO pasa por LLMPayloadBuilder deny-by-default + refs a cláusulas por ID (no texto cruda). Nunca PII sin redactar.`

**Nota:** `[DECIDIDO EN U1]` — P5 (PII minimization). Ver `app/security/redaction.py`.

---

**P6.2:** Cuando PolicyLookup cita una cláusula (resultado "se aplica exclusión según cláusula POL-123"), ¿U2 verifica esa cita o solo la reenvía a U3?

[Answer]: `U2 recupera la cláusula por ID (R1, R3 si está en RAG). U3 es quien **aplica** la regla. U2 no valida aplicabilidad (eso es cobertura → U3).`

**Nota:** `[TRAMPA P2]` — Si U2 validara "aplica R1 vigencia" o "aplica R3 exclusión", sería mediando cobertura. U2 recupera/cita; U3 aplica (determinístico).

---

### P7: Arquitectura de Agentes (H-02)

**P7.1:** ¿Son agentes separados (3 funciones/clases) o un único Extractor-Verificador-PolicyLookup?

[Answer]: `3 componentes separados (C2 Extractor, C3 Verifier, C4 PolicyLookup) — 1:1 con components.md.`

**Nota:** `[DECIDIDO EN COMPONENTES.MD]` — Separación de concerns.

---

**P7.2:** ¿El orquestador de U2 es U2 mismo, o U4 (LangGraph) lo orquesta todo?

[Answer]: `U4 (LangGraph) orquesta (dueño P4 Terminación). Los componentes de U2 se invocan y emiten señales; no auto-orquestan escalación. Cuidado: no meter lógica de orquestación en U2.`

**Nota:** `[TRAMPA P4]` — U2 components son herramientas; U4 es el director (gestiona cotas, loops, estado). Si U2 auto-orquestra, es scope creep + riesgo de loops.

---

**P7.3:** ¿Si PolicyLookup es un agente LLM, qué modelo? Haiku vs Sonnet?

[Answer]: 
```
- Extracción (C2) = Haiku (económico, extracción simple)
- Verificación (C3) = Sonnet (adversarial, mejor reasoning)
- PolicyLookup (C4) = SQL determinístico + retrieval embedding (NO chat model)
  Al fijar IDs de modelo cargo el skill claude-api — no adivino.
```

**Nota:** `[DECIDIDO EN CLAUDE.MD]` — Cost-tiering confirmado. Ver ROADMAP_CODIFICACION.md § Model Layering.

---

### P8: Dependencia de U4 (Fail-Closed)

**P8.1:** ¿U2 mismo verifica que la señal sea "escalable" (ej: no deja un Caso en transacción)? ¿O U4 confía?

[Answer]: `U2 emite señal válida por contrato. U4 es dueño de política de escalamiento. U2 no gestiona estado/transacción — contrato invalida.`

**Nota:** `[DECIDIDO EN U1]` — Validación en la fuente (strict=True, extra="forbid", validators).

---

## 📋 Próximos Pasos

Con estas respuestas confirmadas, procedo a generar:

1. **domain-entities.md**
   - Extractor, Verifier, PolicyLookup
   - SeñalEscalamiento (contrato)
   - Relaciones con U1/U3/U4

2. **business-rules.md**
   - RULE-EXT-01..06 (extracción)
   - RULE-VER-01..03 (verificación)
   - RULE-POL-01..02 (grounding)
   - Reglas de escalamiento

3. **business-logic-model.md**
   - Flujos E2E (happy path + error paths)
   - Decisiones clave (con trampa marcada)
   - Escenarios de error

**Enfoque especial en:**
- ✅ U2 NO setea estado (solo emite señal tipada)
- ✅ U2 NO hace lógica de cobertura (Verifier = consistencia, no R1-R5)
- ✅ Todo al LLM vía LLMPayloadBuilder (P5 deny-by-default)

---

**Marca confirmada:** 5 trampas resueltas, 19 preguntas con respuestas ancladas a U1/componentes/reglas.

Generando artefactos...

