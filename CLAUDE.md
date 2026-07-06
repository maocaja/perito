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

**Sobre el modelo (control de costo):**
- Para exploración/lectura masiva, usa el subagente Explore (Haiku) — más barato.
- Para lógica de dominio y orquestación, Sonnet u Opus.
- Recuerda el diseño por capas de Perito: Haiku para extracción, Opus solo para cobertura ambigua.

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
- **`PostToolUse` con matcher `Edit|Write`** → ejecuta `.claude/hooks/post-edit-lint.sh` (corre `ruff format` + `ruff check --fix` sobre archivos Python; prettier sobre md/json si está disponible).

---

## Skills disponibles
Aún no hay Skills custom. (La tarea de la Estación 3 incluye crear uno propio del dominio, ej. `/check-hitl` o `/audit-coverage-rules`.)

---

## Subagentes disponibles
Aún no hay subagentes custom. (La Estación 3 incluye crear uno, ej. `test-writer` Sonnet o `code-reviewer` Haiku.)

---

## MCPs activos
Aún no configurados. (La Estación 3 incluye instalar MCPs: PostgreSQL/Neon sería el más útil para Perito.)
