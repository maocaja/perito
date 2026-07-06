# Mapa Historia → Unidad — Perito

> Traza cada historia a su unidad, con componentes, principios y estrato de eval. Cobertura **18/18**.

| Historia | Unidad | Componente(s) | Principios | Estrato eval | 🔒 |
|---|---|---|---|---|---|
| H-16 Generador sintético + fraude inyectado | **U1** | CT1 synthetic | P7 | infra (habilita todos) | 🔒 |
| H-17 Tool contracts tipados + validación | **U1** | contracts, C-all | P3 | infra | 🔒 |
| H-01 Ingesta multimodal + caso | **U2** | C1 intake | P3 | happy, documento-sucio | — |
| H-02 Extracción + contrato + evidencia | **U2** | C2 extractor | P3 | happy | 🔒 |
| H-03 Verificación adversarial | **U2** | C3 verifier | P4 | campos-faltantes, documento-sucio | 🔒 |
| H-04 Grounding + candidatas | **U2** | C4 policy_lookup, C10 | P3, P4 | poliza-no-encontrada | 🔒 |
| H-06 No inventar campo faltante | **U2** (+U4⚑) | C2 extractor / C7 escala | P4 | campos-faltantes | 🔒 |
| H-07 Motor R1-R5 (LLM no decide) | **U3** | C5 coverage_rules | **P2** | happy, cobertura-negativa | 🔒 |
| H-08 Cobertura negativa + cita | **U3** | C5, C10 | P2, P3 | cobertura-negativa | 🔒 |
| H-09 Fraude explicable + evidencia | **U3** | C6 fraud_signals | **P6** | fraude | 🔒 |
| H-10 Fraude solo sugiere | **U3** | C6 | **P1, P6** | fraude, red-team | 🔒 |
| H-05 Terminación acotada + escala | **U4** | C7 orchestrator | **P4** | poliza-no-encontrada, campos-faltantes | 🔒 |
| H-11 Bandeja + estados + persistencia | **U4** | C8 hitl | P1 | happy | — |
| H-12 Aprobar/corregir/rechazar + aprobado_por | **U4** | C8 hitl | **P1** | happy | 🔒 |
| H-13 Correcciones como dato de eval | **U4** | C8, C9 | P3 | happy, observabilidad | — |
| H-14 Traza por nodo + costo + replay | **U5** | C9 observability | P3 | observabilidad | — |
| H-15 Evals por estrato + versionado + PIA | **U5** | C9 | P3, P5 | todos (SOAT diferido) | 🔒 |
| H-18 Red-team inyección + sesgo + PII | **U5** | C-all (test) | **P1, P5, P6** | red-team | 🔒 |

## Resumen por unidad
| Unidad | # Historias | Historias | Estratos que cubre |
|---|---|---|---|
| U1 Fundaciones & Contratos | 2 | H-16, H-17 | infra |
| U2 Extracción·Verif·Grounding | 5 | H-01/02/03/04/06 | happy, campos-faltantes, poliza-no-encontrada, documento-sucio |
| U3 Cobertura·Fraude | 4 | H-07/08/09/10 | cobertura-negativa, fraude, happy |
| U4 Orquestación·Terminación·HITL | 4 | H-05/11/12/13 | poliza-no-encontrada, campos-faltantes, happy, observabilidad |
| U5 Observabilidad·Evals·Red-team | 3 | H-14/15/18 | observabilidad, red-team, todos |

## Verificación
- **Cobertura de historias**: 18/18 ✅
- **Cobertura de principios**: P1 (U3,U4,U5) · P2 (U3) · P3 (U1,U2,U3,U4,U5) · P4 (U2,U4) · P5 (U5) · P6 (U3,U5) · P7 (U1). Todos presentes. ✅
- **Cobertura de estratos**: happy · campos-faltantes · poliza-no-encontrada · cobertura-negativa · fraude · documento-sucio · observabilidad · infra · red-team. SOAT **diferido** (RF-27.1). ✅
- **Historias 🔒 fail-closed**: 14 (consistente con `stories.md`).
- **Dependencia de comportamiento**: H-06 anotada U2(+U4⚑) — su fail-closed se ejercita con U4.
