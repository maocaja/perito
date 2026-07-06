# Métodos de Componentes — Perito (Application Design)

> Firmas de método de alto nivel + tipos de I/O. **La lógica de negocio detallada (reglas R1-R5, política de caps) se define en Functional Design (Construction).**
> Tipos referenciados son contratos Pydantic (definición completa en Units Generation / Functional Design). Notación indicativa (Python-like).

---

## C1 · intake
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `recibir_aviso` | `(payload: AvisoCrudo) -> Caso` | Ingesta multimodal, normaliza, crea Caso en `RECIBIDO` | in: bytes/texto/PDF/img · out: Caso |
| `marcar_duplicado` | `(caso: Caso) -> Caso` | Heurística mínima de duplicado | out: Caso con flag |

## C2 · extractor  *(LLM — no autoritativo)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `extraer` | `(aviso: AvisoNormalizado) -> ExtraccionValidada` | Campos vía Claude multimodal, validados contra contrato, con origen enlazado | out: campos + spans |
| `marcar_ausente` | `(campo: str) -> CampoIncierto` | Marca faltante/incierto (no inventa) | — |

## C3 · verifier  *(LLM)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `verificar` | `(extraccion: ExtraccionValidada, aviso) -> ResultadoVerificacion` | Confirma campo↔fuente adversarialmente | out: {confirmado \| señal_no_confirma} |

## C4 · policy_lookup  *(LLM-assisted + IO)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `buscar_poliza` | `(campos: CamposClave) -> ResultadoPoliza` | Match contra base (usa policy_rag) | out: {poliza \| candidatas + "no_encontrada"} |

## C5 · coverage_rules  *(DET — función pura, autoritativo)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `dictaminar` | `(campos: CamposEstructurados, poliza: Poliza) -> Dictamen` | Aplica R1..R5 en orden; salida + regla + cláusula | out: Dictamen |
| `_r1_vigencia` … `_r5_deducible` | `(...) -> ResultadoRegla` | Reglas individuales (internas, puras) | — |
| `override_soat` | `(dictamen) -> Dictamen` | Sin R5, tope en R4 (forward-compat) | — |

> **Contrato de `Dictamen`**: `{ resultado: Enum[CUBIERTO,CUBIERTO_PARCIAL,NO_CUBIERTO,REQUIERE_REVISION], regla_aplicada: str, clausula: Clausula, deducible: Decimal>=0 }`. **Sin `clausula` → inválido** (H-08). **Sin parámetro LLM en la firma** (P2).

## C6 · fraud_signals  *(LLM)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `analizar_fraude` | `(caso: Caso) -> AlertaFraude \| None` | Razona inconsistencias, evidencia obligatoria | out: alerta con evidencia |

> **Contrato de `AlertaFraude`**: `{ severidad, inconsistencias: [Evidencia], explicacion: str }`. Sin `evidencia` → inválida (H-09). **No** produce transición de estado (P1).

## C7 · orchestrator  *(DET control-plane — dueño de P4)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `procesar` | `(caso: Caso, presupuesto: Cotas) -> ResultadoFlujo` | Secuencia nodos bajo caps | out: caso avanzado o escalado |
| `chequear_cotas` | `(estado: EstadoFlujo) -> Decision` | Rondas + tokens + detección de ciclos | out: {continuar \| escalar} |
| `escalar` | `(caso, motivo) -> Caso` | Pasa a `REQUIERE_REVISION` con bloqueo mostrado | out: Caso |
| `invocar_cobertura` | `(campos, poliza) -> Dictamen` | **Único punto que llama a `coverage_rules.dictaminar`** | — |

> **Contrato de `Cotas`**: `{ max_rondas: int, presupuesto_tokens: int }` — caps duros; `chequear_cotas` es fail-closed (H-05).

## C8 · hitl  *(DET state machine — dueño de P1)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `abrir` | `(caso) -> Caso` | `LISTO_PARA_APROBAR → EN_REVISION` | — |
| `aprobar` | `(caso, usuario: Usuario) -> Caso` | `EN_REVISION → APROBADO`, set `aprobado_por` | — |
| `rechazar` | `(caso, usuario) -> Caso` | `EN_REVISION → RECHAZADO`, set `aprobado_por` | — |
| `corregir` | `(caso, cambios, usuario) -> Caso` | Aplica corrección + registra como dato de eval | — |
| `_transicion_valida` | `(desde, hacia, actor) -> bool` | **Guardia**: terminal exige `actor=humano` | 🔒 fail-closed |

> **Regla dura**: `_transicion_valida(_, APROBADO\|RECHAZADO, actor)` retorna `False` si `actor != humano` (H-12, P1).

## C9 · observability
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `instrumentar` | `(evento: EventoNodo) -> None` | Traza por nodo (latencia/tokens/modelo/IO) | — |
| `costo_caso` | `(caso_id) -> Costo` | Costo/caso | — |
| `correr_evals` | `(estrato: Estrato) -> ReporteEval` | Harness por estrato (SOAT excluido) | — |
| `test_gate_regla` | `(cambio_regla) -> bool` | Solo activa si no rompe accuracy | 🔒 |
| `exportar_pia` | `(caso_id) -> EvidenciaPIA` | Export para auditoría (sin PII innecesaria) | P5 |

## C10 · policy_rag
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `indexar` | `(poliza: Poliza) -> None` | Indexa en pgvector | — |
| `recuperar_clausula` | `(consulta: Consulta) -> Clausula` | Cláusula aplicable para C4/C5 | — |

## CT1 · synthetic_generator  *(infra-test)*
| Método | Firma | Propósito | I/O |
|---|---|---|---|
| `generar_caso` | `(fila: FilaDataset) -> (Aviso, Poliza, GroundTruth)` | Fila → aviso es-CO + póliza + verdad | — |
| `inyectar_inconsistencia` | `(aviso, etiqueta) -> Aviso` | Si etiqueta=fraude, encoda señal detectable | 🔒 (rechaza si no encoda, H-16) |

---
**Nota**: firmas indicativas; los contratos Pydantic completos y las precondiciones/postcondiciones se detallan en Functional Design y Units Generation. Los métodos 🔒 se prueban con aserciones fail-closed.
