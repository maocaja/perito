# 📋 U2 Functional Design Plan — Extracción·Verificación·Grounding

**Unidad:** U2 · Extracción · Verificación · Grounding  
**Historias:** H-01, H-02, H-03, H-04, H-06  
**Depende de:** U1 (contratos, redactores PII, RAG de pólizas)  
**Entrega:** Aviso caótico → extracción verificada + señales de escala  

---

## Propósito de este Plan

Este documento estructurará el **Functional Design** de U2: modelos de negocio, reglas de verificación, flujos de datos, y decisiones arquitectónicas **antes de tocar código**.

U2 es el primer punto donde el LLM (Claude) entra al sistema. Sus invariantes:
- **P5 (PII):** LLMPayloadBuilder redacta antes de enviar al LLM (deny-by-default)
- **P4 (No-invención):** Campos faltantes se marcan `ausente=True` con `valor=None`, nunca se inventa
- **P3 (Trazabilidad):** Cada campo extraído tiene `EvidenciaOrigen` citando dónde vino

---

## Steps del Functional Design

### Step 1: Analizar Contexto de U2
- [ ] Leer historias: H-01 (ingesta), H-02 (extracción+contrato), H-03 (verificación), H-04 (grounding), H-06 (no inventar)
- [ ] Revisar contratos de U1 que U2 usa: `AvisoNormalizado`, `CampoExtraido`, `ExtraccionValidada`, `Poliza`, `ResultadoPoliza`
- [ ] Entender dependencia U2→U4: señales emitidas por U2 (no-confirma, sin-match) se escalan en U4

### Step 2: Crear Plan de Preguntas
[Véase sección "Preguntas de Clarificación" abajo]

### Step 3: Recopilar Respuestas
[Esperar a que usuario conteste todas las preguntas marcadas con `[Answer]:` ]

### Step 4-6: Generar Artefactos de Diseño
- [ ] `domain-entities.md` — Extractor, Verifier, PolicyLookup, resultados
- [ ] `business-rules.md` — RULE-EXT-01..06, RULE-VER-01..03, RULE-POL-01..02
- [ ] `business-logic-model.md` — Flujos E2E, decisiones, escenarios de error

### Step 7: Presentar a Revisión

---

## ❓ PREGUNTAS DE CLARIFICACIÓN

### P1: Modelo de Extracción (H-02)

**Contexto:** U2 recibe `AvisoNormalizado` (texto_crudo + calidad) y produce `ExtraccionValidada` (lista de `CampoExtraido`).

**P1.1:** ¿Qué campos OBLIGATORIOS debe extraer siempre?  
Ej: número_poliza, fecha_siniestro, tipo_siniestro, monto_reclamado, nombre_asegurado, ¿cédula del asegurado?

[Answer]: 

**P1.2:** ¿Hay campos OPCIONALES que pueden faltar sin que sea error?  
Ej: teléfono, email, dirección, detalles del tercero.

[Answer]: 

**P1.3:** ¿Quién decide la lista de campos esperados — hardcodeada en Extractor, o leída de configuración/schema?

[Answer]: 

**P1.4:** ¿El `CampoExtraido.confianza` (score 0-100) es devuelto por Claude, o calculado post-extracción por un heurístico?

[Answer]: 

---

### P2: Verificación (H-03 — Adversarial Check)

**Contexto:** Después de extracción, el Verifier (agente o rules) comprueba que los campos se refuerzan mutuamente (no son contradictorios). H-03 menciona "verificación adversarial".

**P2.1:** ¿Qué reglas de consistencia debe validar el Verifier?  
Ej:
- `fecha_siniestro ≤ hoy` (no siniestro futuro)
- `monto_reclamado > 0`
- `tipo_siniestro ∈ [lista válida]`
- ¿Otras?

[Answer]: 

**P2.2:** Si el Verifier rechaza un campo (lo marca como inconsistente), ¿qué hace?  
- A) Rechaza todo (escala a REQUIERE_REVISION)
- B) Marca ese campo como "inconsistente" pero continúa con otros
- C) Solicita re-extracción (loop a Claude)

[Answer]: 

**P2.3:** ¿Puede el Verifier "reparar" campos obvios (ej: normalizar formato de teléfono) o solo marca inconsistencias?

[Answer]: 

---

### P3: Grounding en Póliza (H-04 — Policy Lookup)

**Contexto:** PolicyLookup (agente LLM o búsqueda vectorial) localiza la póliza que corresponde al aviso. H-04 menciona "candidatas" (múltiples opciones).

**P3.1:** ¿Cómo se busca la póliza?  
- A) Por número_poliza exacto en BD (vía SQL)
- B) Por RAG semántico (búsqueda vectorial en Langfuse/pgvector de cláusulas)
- C) Hybrid: primero SQL, luego RAG si no encuentra
- D) Claude decide ("dada la extracción, ¿qué póliza suena?")

[Answer]: 

**P3.2:** Si encuentra múltiples candidatas, ¿cómo elige la "mejor"?  
- A) Devuelve todas → U3/U4 decide
- B) Ranking por score (similitud, fecha de vigencia)
- C) Pide confirmación al usuario (pero eso es HITL, no U2)

[Answer]: 

**P3.3:** ¿Qué retorna PolicyLookup?  
- Solo `ResultadoPoliza.encontrada=True/False` + 1 poliza
- O la estructura completa con `encontrada` + `poliza` + `candidatas: list[Poliza]` (cómo U1 define)

[Answer]: 

**P3.4:** ¿RF-10 ("no forzar match") significa que si NO encontrada, devuelve `ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])`? ¿O `candidatas` puede tener opciones "débiles"?

[Answer]: 

---

### P4: Manejo de Campos Faltantes (H-06 — "No Inventar")

**Contexto:** P4 (Terminación) y P1 (regla caso.py) garantizan que `ausente=True` ⇒ `valor=None`. H-06 refuerza esto.

**P4.1:** Cuando Claude no encuentra un campo en el texto, ¿qué sucede?  
- A) Marca `ausente=True`, `valor=None`
- B) Intenta inferencia (ej: extrae de fecha del email)
- C) Devuelve `valor="[NO_ENCONTRADO]"` como string literal

[Answer]: 

**P4.2:** ¿Si un campo OBLIGATORIO está ausente, qué hace Extractor?  
- A) Continúa (deja ausente=True)
- B) Escala a REQUIERE_REVISION (emite señal, U4 decide)
- C) Pide re-ingesta (loop)

[Answer]: 

**P4.3:** ¿El Verifier rechaza extractiones con campos obligatorios faltantes, o solo marca inconsistencias internas?

[Answer]: 

---

### P5: Señales de Escala (H-01, H-03, H-04, H-06)

**Contexto:** U2 emite señales de "no confirma" o "sin match" que U4 escalará a REQUIERE_REVISION. Esto es **fail-closed**: ante ambigüedad, escala.

**P5.1:** ¿Qué condiciones emiten una señal de escala?  
Ej:
- Extracción confusa (confianza baja globalmente)
- Verificador rechaza consistencia
- PolicyLookup: sin match exacto, múltiples candidatas, o no-encontrada
- Campos obligatorios faltantes
- Documento de calidad SUCIO

[Answer]: 

**P5.2:** ¿Cómo se codifica la señal? ¿Caso.estado = REQUIERE_REVISION + motivo, o usa un nuevo enum?

[Answer]: 

**P5.3:** ¿U2 puede "sugerir" un curso de acción (ej: "use candidata #2") o solo emite el hecho sin preferencia?

[Answer]: 

---

### P6: Integración con RAG de Pólizas (P5 PII, P3 Trazabilidad)

**Contexto:** U1 definió `RAGSchema` con tabla `rag_documents`. U2 consulta cláusulas durante Verifier/PolicyLookup.

**P6.1:** ¿Qué información del aviso (potencialmente PII) se envía al RAG/Claude?  
- A) Solo categorías desensibilizadas (ej: "tipo_siniestro=COLISION", no "auto azul de Perla García")
- B) Texto redactado por LLMPayloadBuilder (deny-by-default)
- C) Ambas: datos structured redactados + referencias a cláusulas por ID

[Answer]: 

**P6.2:** Cuando PolicyLookup cita una cláusula (resultado "se aplica exclusión según cláusula POL-123"), ¿U2 verifica esa cita o solo la reenvía a U3?

[Answer]: 

---

### P7: Arquitectura de Agentes (H-02)

**Contexto:** U2 define 3 agentes conceptuales: C2 (Extractor), C3 (Verifier), C4 (PolicyLookup). ¿Cuál es el orquestador?

**P7.1:** ¿Son agentes separados (3 funciones/clases distintas) o un único Extractor-Verificador-PolicyLookup?

[Answer]: 

**P7.2:** ¿El orquestador de U2 es U2 mismo, o U4 (LangGraph) lo orquesta todo?  
(Contexto: U4 es dueño de P4 Terminación; U2 sigue emitiendo señales, no decide.)

[Answer]: 

**P7.3:** ¿Si PolicyLookup es un agente LLM (Claude), qué modelo usamos? ¿Haiku (económico) o Sonnet (más precisión)?

[Answer]: 

---

### P8: Dependencia de U4 (Fail-Closed)

**Contexto:** U2 emite señales, pero U4 **escalará** al HITL. Este es el cierre del fail-closed de U2.

**P8.1:** ¿U2 mismo verifica que la señal sea "escalable" (ej: no deja un Caso en medio de una transacción)? ¿O U4 confía en que U2 entregó un estado válido?

[Answer]: 

---

## 🔗 Dependencias Externas Confirmadas

✅ **U1 (bloqueante):**
- Contratos: `AvisoNormalizado`, `CampoExtraido`, `ExtraccionValidada`, `Poliza`, `ResultadoPoliza`
- Redacción: `LLMPayloadBuilder` (deny-by-default P5)
- RAG: `RAGSchema`, tabla `rag_documents`
- Generador: casos sintéticos con campos variados

✅ **U2 → U4:**
- Señales escaladas a REQUIERE_REVISION
- Caso.estado controlado por HITL (U4), no por U2

❓ **U2 → U3:**
- Depende de: Extracción verificada → U3 toma `Caso.extraccion` + `Caso.poliza_match`
- Relación: U3 ejecuta R1-R5 sobre los datos de U2; U2 no conoce las reglas

---

## Próximos Pasos

1. **Recopilar respuestas** a todas las preguntas `[Answer]:` arriba
2. **Mi revisión:** verificar que las respuestas cierren ambigüedades
3. **Generar artefactos:** domain-entities.md, business-rules.md, business-logic-model.md
4. **Tu aprobación** antes de Code Generation

