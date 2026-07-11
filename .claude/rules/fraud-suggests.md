# Regla: El fraude solo sugiere (P6) — NO NEGOCIABLE

- El fraude **solo sugiere** revisión / carril SIU. **Ninguna** señal cambia `caso.estado`, deshabilita la
  firma ni bloquea — **ni la señal cross-claim con foto idéntica (distancia 0)**.
- **Toda señal lleva `confianza ∈ [0,1)`** — **nunca 1.0** (un veredicto). Un falso positivo es una
  sugerencia con confianza, no una verdad (P7).
- **Toda alerta lleva evidencia obligatoria:** `inconsistencias` no vacío (`min_length=1`, H-09 🔒). Una
  alerta sin evidencia es inválida por contrato — el fraude nunca es una afirmación sin sustento.
- La **detección es determinística** (chequeos duros, distancia de Hamming, conteos). El LLM **solo explica**
  el "por qué"; no detecta ni decide.
- El bloque C6 del orquestador es **no-escalante**: adjunta la alerta (informativa) sin transicionar estado.

**Dos niveles de garantía (no confundir):**
- **Técnica** (lo que el sistema *no puede* hacer): `AlertaFraude.confianza < 1.0` (contrato), C6 no-escalante,
  `Caso.estado` frozen (RULE-CTR-05, solo HITL transiciona).
- **Operacional:** el **humano sí** decide sobre el caso — eso es **P1/HITL**, no una violación. La regla
  constriñe al **sistema**; el operador firma.

**🚫 Prohibido:**
- Un camino donde una señal de fraude alcance un estado terminal, deshabilite la firma o bloquee el caso.
- `AlertaFraude(confianza=1.0)` o presentar el fraude como veredicto/decisión.
- Que el LLM **decida** fraude (solo explica lo que la capa determinística ya detectó).

**Verificado (fail-closed) por:** `test_u6_cross_claim.py::test_p6_foto_identica_no_cambia_estado_ni_firma`,
`test_u6_cross_claim.py::test_contrato_rechaza_confianza_1_0`, `test_validation_failclosed.py`
(evidencia obligatoria) y `test_u4_c7_orchestrator.py` (corona: el orquestador nunca produce estado terminal).

Si una tarea te llevaría a violar esto, **detente y avísame** — no lo implementes.
Contexto completo: `specs/prd.md` (Principio P6) · spec de gobernanza: `specs/aidlc/evolution/gov-rules-p5-p6.md`.
