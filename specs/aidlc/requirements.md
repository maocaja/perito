# Perito — Documento de Requisitos (AI-DLC Inception)

> **Depth**: Comprehensive · **Idioma**: es-CO · **Fuente**: `PRD.md` (Estación 2) + `AGENTS.md` + `.claude/rules/`
> **Extensiones activas**: Security Baseline (blocking) · Property-Based Testing (Partial).
> Fecha: 2026-07-06 · Rama: `spec/aidlc-inception`.

---

## 1. Resumen de Análisis de Intención

| Dimensión | Valoración |
|---|---|
| **User request** | Construir Perito: copiloto agéntico de admisión/triage de siniestros (FNOL) que extrae datos de avisos caóticos, valida cobertura con reglas determinísticas, señala fraude con evidencia y deja la decisión al humano (HITL). Portafolio, greenfield. Base: `PRD.md`. |
| **Request type** | New Project (greenfield). |
| **Scope estimate** | System-wide — sistema agéntico multi-módulo (M1-M10) + infra de datos + observabilidad + evals. |
| **Complexity estimate** | Complex — orquestación agéntica con terminación acotada, determinismo legal, invariantes de seguridad fail-closed, riesgo regulatorio (Habeas Data / Circular SIC). |
| **Alcance decidido (Q1=B)** | **Must completo** — los 13 Must del MoSCoW → módulos M1-M10 + infra de demo. Should/Could/Won't fuera de esta Inception. |

---

## 2. Alcance

### 2.1 En alcance (Must — 13 items del MoSCoW, PRD §8)
Generador de datos sintéticos es-CO · Ingesta multimodal · Extracción estructurada con contrato · Verificación adversarial · Grounding + manejo de "no encontrada" · Motor de reglas R1-R5 + cita de cláusula · Terminación acotada · HITL (aprobar/corregir/rechazar + persistencia) · Fraude razonado (mínimo) · Observabilidad con herramienta real (Langfuse/OTel) · Evals (extracción + coverage-match) · Tool contracts tipados + validación · Eval runs versionados.

### 2.2 Fuera de alcance (declarado)
- **Should** (siguiente iteración): SOAT, acuse redactado, tablero de evals visual, cola de SLA, fraude-vs-etiqueta-Kaggle completo.
- **Could**: versionado de reglas con test-gate, multi-usuario, más tipos de documento.
- **Won't (PRD §8)**: enrutamiento al ajustador · audio · integración real con core · agregación multi-documento · dedup robusto · aprendizaje/recalibración · **auth real** (MVP = selector de rol stub).

### 2.3 Floor de degradación (PRD §8)
Si integrar Langfuse se atrasa, el mínimo aceptable es trace JSON estructurado + panel simple. Núcleo irrenunciable declarado: Must #2-#8 + #10.

---

## 3. Requisitos Funcionales (RF)

> Cada RF traza a su módulo (M), caso de uso (UC), user journey (J) y principio no negociable (P). Ver matriz en §6.

### M1 — Ingesta (`intake`)
- **RF-01** El sistema recibe un aviso FNOL en texto, PDF o imagen y crea un **Caso** en estado `RECIBIDO`. *(UC1, J1)*
- **RF-02** Normaliza el aviso a una representación interna uniforme antes del procesamiento. *(UC1)*
- **RF-03** Marca posibles duplicados (heurística mínima; dedup robusto = Won't). *(UC1)*

### M2 — Extracción (`extractor`)
- **RF-04** Extrae campos estructurados del aviso mediante Claude multimodal, produciendo un objeto validado contra **contrato Pydantic tipado**. *(UC1, P3)*
- **RF-05** Cada campo extraído queda **enlazado a su origen** (span/página/región) para trazabilidad. *(UC1, P3)*
- **RF-06** Ante campo faltante o ilegible, el extractor **no inventa**: marca el campo como ausente/incierto. *(UC2, P4)*

### M3 — Verificación adversarial (`verifier`)
- **RF-07** Confirma la extracción contra la fuente original de forma adversarial. *(UC2, P4)*
- **RF-08** Si no puede confirmar, **emite una señal al orquestador** (no continúa a ciegas). *(UC2, P4)*

### M4 — Grounding / Policy Lookup (`policy_lookup`)
- **RF-09** Busca la póliza referida contra la base de pólizas (RAG pgvector, M10). *(UC3, J4)*
- **RF-10** Si no hay match exacto, retorna **candidatas cercanas** y señala "no encontrada" — no fuerza un match. *(UC2, J4, P4)*

### M5 — Cobertura (`coverage_rules`, DETERMINÍSTICO)
- **RF-11** Aplica las reglas **R1 Vigencia → R2 Cobertura contratada → R3 Exclusiones → R4 Límite → R5 Deducible**, en orden. *(UC3, P2)*
- **RF-12** La decisión de cobertura la toma **el motor de reglas, NUNCA el LLM**. Salidas válidas: `CUBIERTO` · `CUBIERTO_PARCIAL` · `NO_CUBIERTO` · `REQUIERE_REVISION`. *(P2 — NO NEGOCIABLE)*
- **RF-13** Cada dictamen **cita la regla aplicada y la cláusula** de la póliza. Sin regla+cláusula no hay dictamen. *(UC3, P2, P3)*
- **RF-14** Override SOAT: sin R5 (deducible), tope en R4. *(nota: SOAT como tipo completo = Should; el override se contempla en el diseño del motor)*

### M6 — Fraude razonado (`fraud_signals`)
- **RF-15** Razona inconsistencias (p. ej. fecha vs. metadato) y **emite una alerta explicable con evidencia citada**. *(UC4, P6)*
- **RF-16** El fraude **solo sugiere revisión** — nunca bloquea, niega ni decide. *(UC4, P1, P6)*

### M7 — Orquestador (`orchestrator`, LangGraph)
- **RF-17** Dirige el flujo del agente y es **dueño de la política de terminación y escalamiento**. *(UC2, P4)*
- **RF-18** Impone **límites duros**: máximo de rondas + presupuesto de tokens + detección de ciclos. *(UC2, P4 — NO NEGOCIABLE)*
- **RF-19** Ante dato faltante/ambiguo o póliza sin match, tras agotar cotas **se detiene (no loop)** y escala a `REQUIERE_REVISION` mostrando qué lo bloqueó. *(UC2, J4, P4)*

### M8 — HITL (`hitl`)
- **RF-20** Gestiona los estados del caso (ver Apéndice C del PRD) con persistencia. *(UC1, J3, P1)*
- **RF-21** El analista puede **aprobar / corregir / rechazar**; todo estado terminal (`APROBADO`/`RECHAZADO`) requiere **aprobación humana registrada** (`aprobado_por`). *(P1 — NO NEGOCIABLE)*
- **RF-22** Ningún camino de código alcanza un estado terminal sin intervención humana. *(P1 — NO NEGOCIABLE)*
- **RF-23** Las correcciones del humano se **registran como dato de eval**. *(J1, UC5)*
- **RF-24** Estado persistido tolerante a interrupción (retomar sesión sin perder trabajo). *(J3)*

### M9 — Observabilidad & Evals (`observability`)
- **RF-25** Traza por nodo (latencia, tokens, modelo, IO) con herramienta real (Langfuse/OTel) + replay. *(UC5, P3)*
- **RF-26** Costo por caso medido y reportado. *(UC5)*
- **RF-27** Harness de evals (pytest + DeepEval) **por estrato**: happy · campos-faltantes · póliza-no-encontrada · cobertura-negativa · fraude · documento-sucio. *(UC5)*
  - **RF-27.1** El estrato **SOAT** queda **diferido/placeholder** (junto con el tipo SOAT = Should): no se genera dataset de eval SOAT en esta Inception. Consistencia con Q1=B (MoSCoW estricto, riesgo #2). Se reactiva cuando SOAT entre a alcance. *(nota: el PRD §11 lo lista como estrato pero §8 lo marca Should — se resuelve a favor de §8)*
- **RF-28** **Eval runs versionados**; export de evidencia para el PIA. *(UC5, P3, P5)*

### M10 — RAG de pólizas (`policy_rag`)
- **RF-29** Indexa pólizas sintéticas con cláusulas (pgvector) y recupera la cláusula aplicable para M4/M5. *(UC3, P3)*

### Infra de demo/test (no es producto)
- **RF-30** Generador de datos sintéticos es-CO + dataset de ground truth por caso. *(riesgo #1, Día 1)*
- **RF-31** **Requisito de validez del eval de fraude**: en filas etiquetadas fraude, el generador **inyecta la inconsistencia detectable** en el documento. *(PRD §11, regla testing)*

---

## 4. Requisitos No Funcionales (RNF)

### 4.1 Rendimiento y eficiencia
- **RNF-01** Procesamiento end-to-end sin fallo ≥ 95% de los casos. *(KPI Activación)*
- **RNF-02** Costo (tokens)/caso medido; ≥ 95% de casos dentro del presupuesto de tokens. *(P4)*
- **RNF-03** Latencia end-to-end/caso medida y reportada.

### 4.2 Calidad / Correctitud
- **RNF-04** Accuracy de extracción vs. ground truth ≥ 90-95%.
- **RNF-05** Correctitud del motor de cobertura = **100% por construcción** (unit test). *(P2)*
- **RNF-06** 100% de dictámenes con cláusula citada. *(P3)*
- **RNF-07** Campos inventados ≈ 0. *(P4)*
- **RNF-08** Precisión/recall de fraude vs. etiqueta reportados con honestidad (válido solo si el doc encoda la señal). *(P6, P7)*

### 4.3 Terminación acotada (P4)
- **RNF-09** 100% de flujos terminan dentro de cotas (0 loops), verificado con aserción fail-closed.
- **RNF-10** Los caps (rondas/tokens/ciclos) los define el sistema **por encima del framework** (LangGraph loops 33.8%).

### 4.4 Seguridad (extensión Security Baseline — blocking) + Habeas Data (P5)
> Aplicabilidad detallada en §7. A nivel de requisitos se capturan como obligaciones; la verificación completa ocurre en Application Design, NFR Design y Code Generation.
- **RNF-11** **Minimización de PII**: no enviar PII innecesaria al LLM. *(P5, SECURITY-03)*
- **RNF-12** Logging estructurado con timestamp + correlation ID; **sin secretos ni PII en logs**. *(SECURITY-03)*
- **RNF-13** Validación de entrada en todo endpoint (tipos, límites de tamaño, formato, parametrización de queries). *(SECURITY-05)*
- **RNF-14** Control de acceso a nivel de aplicación deny-by-default; **selector de rol stub** en MVP (auth real = Won't) con autorización server-side por rol. *(SECURITY-08, PRD §9)*
- **RNF-15** Cifrado en tránsito (TLS) y en reposo para el almacén de casos/pólizas (Postgres/pgvector). *(SECURITY-01)*
- **RNF-16** Manejo de excepciones **fail-closed**: ante error, denegar/detener, nunca fail-open; cleanup de recursos; error handler global. *(SECURITY-15, P4)*
- **RNF-17** Cadena de suministro: dependencias pinneadas + lock file + escaneo de vulnerabilidades en CI. *(SECURITY-10)*
- **RNF-18** Integridad de datos: modificaciones críticas auditables (quién/qué/cuándo); deserialización segura de entrada no confiable. *(SECURITY-13, P3)*
- **RNF-19** Resistencia a **inyección de prompt** en el documento: el diseño no permite auto-decisión derivada del contenido del aviso. *(P1, red-team PRD §11, SECURITY-11 abuso de lógica de negocio)*

### 4.5 Trazabilidad y auditabilidad (P3)
- **RNF-20** Todo dictamen y toda alerta de fraude son trazables a su fuente citada. 100% cobertura de trazabilidad.
- **RNF-21** Export de traza completa para auditoría/PIA. *(J2, P5)*

### 4.6 Testing y Property-Based Testing (extensión PBT — Partial)
> Enforced: PBT-02, PBT-03, PBT-07, PBT-08, PBT-09. Detalle de propiedades se elabora en Functional Design (PBT-01, advisory) por unidad.
- **RNF-22** Cada función de dominio tiene ≥ 1 happy path + 1 caso de error (pytest); naming `test_<comportamiento>_when_<condicion>`.
- **RNF-23** **PBT-03 (invariantes)**: el motor R1-R5 (función pura determinística) se prueba con propiedades — p. ej. salida siempre ∈ {CUBIERTO, CUBIERTO_PARCIAL, NO_CUBIERTO, REQUIERE_REVISION}; nunca deducible < 0; nunca dictamen sin cláusula. *(P2)*
- **RNF-24** **PBT-02 (round-trip)**: contratos Pydantic serializar→deserializar = identidad; parse/format de campos estructurados. *(P3)*
- **RNF-25** **PBT-07 (generadores)**: generadores de dominio (Caso, Póliza, Aviso) que respetan restricciones de negocio, no primitivos crudos.
- **RNF-26** **PBT-08 (shrinking/seed)**: shrinking habilitado; seed logueado en fallo; PBT en CI.
- **RNF-27** **PBT-09 (framework)**: framework PBT seleccionado y documentado en tech stack (Python → **Hypothesis**), incluido como dependencia.
- **RNF-28** Los nodos LLM (no deterministas) **no** se someten a PBT de igualdad — se validan con evals por estrato + tool-correctness (DeepEval). *(coherencia con P4)*

### 4.7 Invariantes de seguridad *enforced* (aserciones fail-closed — PRD §10)
100% cobertura por reglas (P2) · 100% fraude con evidencia (P6) · 100% decisiones con aprobación humana (P1) · 100% terminación dentro de cotas (P4) · 100% trazabilidad (P3) · PII minimizada (P5). **Se testean con aserciones que rompen ruidosamente si se violan**, no solo con números de dashboard.

---

## 5. Restricciones y Supuestos
- **RES-01** Greenfield: sin código de app; AI-DLC salta reverse-engineering.
- **RES-02** Portafolio honesto (P7): nada se despliega; no presentar como "decisor" ni "quita riesgo legal"; sin cifras refutadas.
- **RES-03** Datos **sintéticos** (los reales son PII/Won't) → riesgo de métricas infladas, se declara.
- **RES-04** Stack asumido del PRD: Python/FastAPI + Postgres/pgvector + LangGraph + Claude multimodal + Langfuse/OTel + pytest/DeepEval/Hypothesis. Confirmación fina en NFR Requirements (Construction).
- **SUP-01** El dataset backbone (Kaggle) tiene los campos que las reglas necesitan — **verificación Día 0** (riesgo #1); Plan B: CUAD/pólizas sintéticas.

---

## 6. Matriz de Trazabilidad Requisito ↔ Principio (P1-P7)

| Principio | Requisitos que lo realizan |
|---|---|
| **P1 HITL** | RF-16, RF-20, RF-21, RF-22, RNF-19; invariante "100% decisiones con aprobación humana" |
| **P2 Determinismo cobertura** | RF-11, RF-12, RF-13, RF-14, RNF-05, RNF-23 |
| **P3 Trazabilidad/citas** | RF-04, RF-05, RF-13, RF-25, RF-28, RF-29, RNF-06, RNF-18, RNF-20, RNF-21 |
| **P4 No alucinar + terminación** | RF-06, RF-08, RF-10, RF-17, RF-18, RF-19, RNF-02, RNF-07, RNF-09, RNF-10, RNF-16 |
| **P5 Habeas Data/PII** | RNF-11, RNF-12, RNF-15, RF-28, RNF-21 |
| **P6 Explicabilidad fraude** | RF-15, RF-16, RNF-08 |
| **P7 Honestidad de alcance** | RES-02, RES-03, RNF-08 (reporte honesto), toda la §2.2 |

---

## 7. Compliance de Extensiones (estado en Requirements Analysis)

### 7.1 Security Baseline (blocking)
En esta etapa los requisitos **capturan** las obligaciones; la verificación de implementación se difiere a Design/Code. Estado de aplicabilidad:

| Regla | Estado en Requisitos | Nota |
|---|---|---|
| SECURITY-01 Cifrado | Capturado (RNF-15) | Postgres/pgvector. |
| SECURITY-02 Logging de intermediarios de red | N/A (sin LB/CDN/API gateway en MVP local) | Reevaluar si se despliega (no aplica: Won't). |
| SECURITY-03 Logging de aplicación | Capturado (RNF-12) | Sin PII/secretos en logs. |
| SECURITY-04 HTTP security headers | Pendiente Design | Aplica si hay UI web servida. |
| SECURITY-05 Validación de entrada | Capturado (RNF-13) | + contratos Pydantic (RF-04). |
| SECURITY-06 Least-privilege IAM | N/A (sin cloud IAM en MVP) | Reevaluar en Infra Design. |
| SECURITY-07 Red restrictiva | N/A (local) | — |
| SECURITY-08 Control de acceso app | Capturado (RNF-14) | Selector de rol stub, autorización server-side. |
| SECURITY-09 Hardening/misconfig | Pendiente Design | Errores genéricos, sin stack traces. |
| SECURITY-10 Supply chain | Capturado (RNF-17) | Lock file + scan en CI. |
| SECURITY-11 Diseño seguro | Capturado (RNF-19) | Aislar lógica crítica; abuso de inyección de prompt. |
| SECURITY-12 Auth/credenciales | N/A parcial | Auth real = Won't; aplica "no hardcoded secrets". |
| SECURITY-13 Integridad software/datos | Capturado (RNF-18) | Deserialización segura, auditoría de cambios. |
| SECURITY-14 Alerting/monitoring | Pendiente Design | Logs append-only / retención; encaja con M9. |
| SECURITY-15 Excepciones fail-safe | Capturado (RNF-16) | Fail-closed alineado con P4. |

**Findings de seguridad en esta etapa**: ninguno bloqueante — todos los requisitos de seguridad aplicables quedan capturados o correctamente marcados N/A. La verificación efectiva se hará en Application Design y Code Generation.

### 7.2 Property-Based Testing (Partial)
Enforced PBT-02 (RNF-24), PBT-03 (RNF-23), PBT-07 (RNF-25), PBT-08 (RNF-26), PBT-09 (RNF-27). PBT-01 se ejecutará en Functional Design por unidad (advisory). **Findings PBT**: ninguno bloqueante en Requisitos.

---

## 8. Resumen de Requisitos Clave
- **Espinazo agéntico**: Ingesta → Extracción (contrato) → Verificación adversarial → Grounding → Cobertura determinística R1-R5 con cita → Fraude razonado → Orquestación con terminación acotada → HITL.
- **Lo no negociable**: P1 (humano firma), P2 (cobertura por reglas, no LLM), P3 (todo citado), P4 (escalar en vez de inventar + caps duros) — todos con aserciones fail-closed.
- **Auditabilidad como diferenciador**: traza por nodo, costo/caso, evals versionados, export para PIA.
- **Disciplina de ingeniería**: contratos Pydantic tipados, PBT sobre el motor determinístico, security baseline enforced, honestidad de alcance (portafolio).
