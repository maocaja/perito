# Instrucciones específicas para Claude Code — Perito

> **Source of truth del proyecto:** [`AGENTS.md`](./AGENTS.md). Léelo siempre primero.
> **Contexto profundo:** `specs/prd.md` (PRD completo, 13 segmentos + apéndices) y `docs/stack.md`.
> Este archivo añade config propia de Claude Code que no es portable a otros agentes.

---

## Cómo arrancar una sesión

1. Lee `AGENTS.md` completo.
2. Si dudas del "por qué" de una decisión, consulta `specs/prd.md` (los principios P1-P7 y el Apéndice B de vacíos declarados).
3. Revisa el último commit con `git log -1` para saber en qué estábamos.
4. Si hay cambios staged/unstaged, pregúntame qué hacer antes de tocar nada nuevo.

---

## Comportamientos esperados

**Sobre commits:**
- NO hagas commits automáticamente. Deja los cambios staged; yo decido cuándo commitear.
- Cuando te pida "commitea": Conventional Commits, mensaje en español, primera línea < 70 chars.

**Sobre cambios grandes:**
- Si un cambio toca >5 archivos, muéstrame el plan antes de implementar.
- Si una decisión arquitectónica no está en `AGENTS.md` ni en `specs/prd.md`, pregúntame antes de tomarla por mí.

**Sobre los principios no negociables (P1-P7 del PRD):**
- Si una tarea te llevaría a violar un principio (ej. hacer que el LLM decida cobertura, o quitar el HITL), **detente y avísame** — no lo implementes.

**Sobre dependencias:**
- Antes de instalar una librería, verifica si ya tenemos algo equivalente. Justifica cualquier dependencia nueva y pídeme confirmación.

**Sobre el modelo (control de costo — riesgo #2 del PRD):**
- Para exploración/lectura masiva, usa el subagente Explore (Haiku) — más barato.
- Para lógica de dominio y orquestación, Sonnet u Opus.
- Diseño por capas de Perito: Haiku para extracción, Sonnet para el grueso, Opus solo para cobertura ambigua.
- Patrón **opusplan**: Opus planifica → Sonnet ejecuta (arranca Claude con `--model opusplan`).
- `/cost` para ver el gasto de la sesión; `/clear` entre tareas no relacionadas para no arrastrar contexto caro.
- Modo headless con presupuesto: `claude -p "..." --max-budget-usd 0.30`. Ver `scripts/semantic-review.sh`.

**CI/CD:**
- `scripts/semantic-review.sh [base]` — linter semántico headless que revisa el diff contra los invariantes P1-P6 (pre-commit/CI).
- `.github/workflows/claude-review.yml` — revisión automática al comentar `@claude` en un PR (DORMIDO hasta tener remoto + secret `ANTHROPIC_API_KEY`).

---

## Reglas modulares (`.claude/rules/`)

Claude Code carga automáticamente estas reglas por tema. Son los invariantes no negociables de Perito:
- `rules/hitl.md` — **P1**: el humano decide, nunca auto-decidir.
- `rules/coverage-determinism.md` — **P2**: cobertura por reglas, no por LLM.
- `rules/termination.md` — **P4**: terminación acotada, escalar en vez de inventar.
- `rules/testing.md` — evals por estrato (pytest + DeepEval).

> Si una tarea te llevaría a violar una de estas reglas, detente y avísame.

---

## Hooks activos

Definidos en `.claude/settings.json`:
- **`PreToolUse` con matcher `Edit|Write`** → ejecuta `.claude/hooks/protect-critical-paths.sh`. Pide **confirmación explícita** (`ask`) antes de editar `backend/app/rules/` (P2) y `backend/app/orchestrator/` (P4). Convierte esos invariantes de advisory a enforced. Requiere `jq`.
- **`PostToolUse` con matcher `Edit|Write`** → ejecuta `.claude/hooks/post-edit-lint.sh` (corre `ruff format` + `ruff check --fix` sobre archivos Python; prettier sobre md/json si está disponible).

---

## Skills disponibles
Aún no hay Skills custom. (La tarea de la Estación 3 incluye crear uno propio del dominio, ej. `/check-hitl` o `/audit-coverage-rules`.)

---

## Subagentes disponibles
En `.claude/agents/`. Para invocarlos, pídelo explícitamente:
- **`code-reviewer`** (Haiku, solo lectura) — revisa buscando violaciones de P1-P6, bugs, seguridad, PII, inyección de prompt. Úsalo antes de un commit/PR.
- **`test-writer`** (Sonnet) — escribe evals por estrato con pytest + DeepEval y aserciones fail-closed de los invariantes.

Además de los integrados: **Explore** (Haiku, lectura masiva barata), **Plan** (planes), **General-purpose**.

---

## Agent Teams (para el build — experimental, opt-in)

NO activado por defecto (experimental + gasta presupuesto por teammate — riesgo #2).
Se activa manualmente cuando convenga paralelizar:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

**Cuándo usarlo:** solo en Días 2-3 del build, **después** de que los contratos Pydantic (`backend/app/models/`) estén estables — así los teammates no colisionan.

**Descomposición libre de colisiones (cada teammate en su carpeta):**
- Teammate `tools` → `backend/app/agents/` (extractor, verifier, policy_lookup, fraud_signals)
- Teammate `observability` → `backend/app/observability/` (Langfuse/OTel)
- Teammate `tests` → `backend/tests/` (evals por estrato)
- Teammate `frontend` → `frontend/` (panel)

**Hacer SOLO (el lead, no delegar):** `backend/app/rules/` (motor de cobertura, P2) y `backend/app/orchestrator/` (terminación, P4) — son las rutas críticas protegidas por el hook.

**Quality gates opcionales** (hooks): `TeammateIdle` y `TaskCompleted` con exit code 2 para devolver feedback antes de dar por terminada una tarea.

## MCPs activos
Aún no configurados. (La Estación 3 incluye instalar MCPs: PostgreSQL/Neon sería el más útil para Perito.)
