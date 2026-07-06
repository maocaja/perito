# Perito

> Archivo de contexto cross-tool para cualquier coding agent (Claude Code, Cursor, Windsurf, Copilot, OpenCode).
> `CLAUDE.md` apunta aquí como source of truth.
> Contexto profundo: `specs/prd.md` (PRD completo) y `docs/stack.md` (decisiones de stack).

---

## 1. Contexto del negocio

**¿Qué hace este producto?**
Perito es un **copiloto agéntico de admisión y triage de siniestros de seguros (FNOL — aviso de siniestro)**. Lee un aviso caótico (correo, PDF, fotos), extrae los datos, verifica la cobertura contra la póliza con reglas determinísticas, señala inconsistencias de fraude con evidencia, y entrega un caso estructurado y explicado para que un analista humano lo apruebe. **Nunca decide solo** (human-in-the-loop).

**¿Quién es el usuario?**
El **analista de admisión/triage** de una aseguradora mediana (Colombia/LATAM). Secundarios: el líder de siniestros (comprador) y el oficial de cumplimiento (veto de confianza).

**¿Cuál es el estado actual?**
**Proyecto de portafolio** (no startup) para practicar ingeniería de sistemas agénticos. Specs completas (PRD en `specs/prd.md`), **sin código todavía**. Objetivo: MVP demostrable en ~5 días. El valor es la ingeniería (orquestación, verificación adversarial, HITL, trazabilidad, evals), no ganar mercado.

---

## 2. Arquitectura

**Stack tecnológico:**
- Lenguaje principal: **Python 3.12** (backend)
- Framework API: **FastAPI**
- Base de datos: **PostgreSQL + pgvector** (RAG sobre pólizas)
- LLM: **Claude por capas** (Anthropic API) — Haiku 4.5 (extracción barata) / Sonnet 5 (grueso) / Opus 4.8 (cobertura ambigua)
- Orquestación: **LangGraph** + una **capa de terminación acotada propia** (límites de rondas/tokens + detección de ciclos) — obligatoria
- Contratos/validación: **Pydantic**
- Observabilidad: **Langfuse (self-hosted)** + convenciones OpenTelemetry GenAI
- Evals: **DeepEval** (métricas agénticas) + **pytest** (métricas determinísticas)
- Frontend: panel mínimo (a definir — Next.js o React simple)
- Datos de demo: generador sintético es-CO sobre backbone Kaggle (infra de test, no producto)

**Estructura de carpetas (intención — se irá construyendo):**
```
backend/
├── app/
│   ├── models/          ← esquemas Pydantic (Caso, Poliza, Aviso, Dictamen) = tool contracts
│   ├── agents/          ← tools del agente: extractor, policy_lookup, coverage_rules, fraud_signals
│   ├── rules/           ← motor de reglas de cobertura R1-R5 (determinístico, NO LLM)
│   ├── orchestrator/    ← grafo LangGraph + capa de terminación acotada
│   ├── observability/   ← instrumentación Langfuse + OTel
│   └── api/             ← rutas FastAPI
└── tests/               ← pytest + DeepEval (evals por estrato)

data/                    ← generador de datos sintéticos + datasets (infra de demo)
frontend/                ← panel del analista + panel de observabilidad
docs/                    ← inputs de producto (pvb, overview, mercado, icp, critica, stack)
research/                ← deep research (validacion, critica)
specs/                   ← prd.md (el PRD completo)
```

**Decisiones de diseño no obvias:**
- **La decisión de cobertura la toma el motor de reglas (`rules/`), NUNCA el LLM.** El LLM solo alimenta los campos. (Principio P2)
- **El orquestador es dueño de la política de escalamiento y terminación.** Los tools emiten señales; el orquestador decide rendirse dentro de cotas duras. (P4)
- **Cada tool del agente tiene contrato Pydantic tipado + validación de output.**
- **El fraude es razonamiento explicable (LLM) que solo sugiere revisión, nunca bloquea** — el humano decide. No contradice P2 porque no es una decisión de corrección obligatoria. (P6)
- **Observabilidad de primera clase:** cada nodo instrumentado (latencia/tokens/modelo/IO); nada de "confía en mí" sin traza. (P3)

---

## 3. Convenciones

**Estilo de código:**
- Python formateado y linteado con **ruff** (format + check).
- Type hints obligatorios; validación de datos con Pydantic.

**Nombrado:**
- Variables y funciones: `snake_case`
- Clases / modelos Pydantic: `PascalCase`
- Constantes: `SCREAMING_SNAKE_CASE`
- Estados del caso: `SCREAMING_SNAKE_CASE` (ver máquina de estados en `specs/prd.md` Apéndice C: `RECIBIDO`, `EN_PROCESO`, `REQUIERE_REVISION`, `LISTO_PARA_APROBAR`, `EN_REVISION`, `APROBADO`, `RECHAZADO`, `ESPERANDO_INFO`, `CERRADO_SIN_ACCION`)
- Tools del agente: nombres exactos `extractor`, `policy_lookup`, `coverage_rules`, `fraud_signals`

**Commits:**
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`), mensaje en español, primera línea < 70 chars.
- Un commit = una intención lógica.

**Tests:**
- Cada función de dominio: al menos 1 happy path + 1 caso de error.
- Los evals viven en `backend/tests/` organizados por **estrato** (ver `specs/prd.md` Seg. 11): happy, campos-faltantes, poliza-no-encontrada, cobertura-negativa, fraude, SOAT, documento-sucio.
- Naming: `test_<comportamiento>_when_<condicion>`.

---

## 4. Flujo de trabajo con el agente

**Lo que QUIERO que el agente haga automáticamente:**
- Después de cada edición, correr `ruff format` + `ruff check --fix` (vía hook post-edit).
- Antes de un cambio que toque >5 archivos, mostrar un plan.
- Usar los nombres de tools/estados exactos definidos arriba.

**Lo que SIEMPRE necesita mi confirmación:**
- Instalar dependencias nuevas.
- Cambios al motor de reglas de cobertura (`rules/`) — son de corrección obligatoria.
- Tocar la capa de terminación acotada del orquestador.
- Eliminación de archivos.
- Cualquier comando con `rm`, `--force`, `--no-verify`.

**Lo que NO debe hacer:**
- Hacer que el LLM decida cobertura (viola P2).
- Quitar el human-in-the-loop o crear un camino de auto-decisión (viola P1).
- Debate multi-agente libre sin terminación acotada (viola P4).
- Commits automáticos — dejar cambios staged.
- Inventar cifras de mercado/tiempo — las cifras refutadas están en `specs/prd.md` Apéndice B.

---

## 5. Restricciones

**Archivos protegidos (nunca leer ni editar):**
- `.env`, `.env.*` — credenciales (Anthropic API key, Langfuse, DB)
- `secrets/` — cualquier cosa aquí

**Rutas que requieren máxima cautela:**
- `backend/app/rules/` — el motor de cobertura determinístico; cambios afectan dictámenes a escala.
- `backend/app/orchestrator/` — la terminación acotada es el músculo de ingeniería; no relajar los límites.

**Patrones a evitar:**
- No usar el LLM para decidir cobertura (usar el motor de reglas).
- No introducir loops sin límite de rondas/tokens.
- No enviar PII innecesaria al LLM (minimización — P5).
- No emitir un dictamen o alerta sin evidencia/traza (P3).

**Decisiones ya tomadas que no debemos reabrir (ver `specs/prd.md`):**
- Encuadre **portafolio honesto**, no producto de mercado.
- **HITL obligatorio** — el agente nunca cierra un siniestro solo.
- **Cobertura determinística por reglas**, no por LLM.
- **LangGraph + terminación acotada propia** (LangGraph es el más loop-prone; los caps los ponemos nosotros).
- **Enrutamiento al ajustador, aprendizaje/recalibración y auth real están fuera del MVP** (Won't-have).
- Cifras refutadas NO se usan (Apéndice B).

---

*Última actualización: 2026-07-06 · Mantenido por: Mauricio Cajamarca*
