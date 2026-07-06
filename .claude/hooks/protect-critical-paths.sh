#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Hook: protect-critical-paths.sh  (Perito)
# Evento: PreToolUse (matcher: Edit|Write)
#
# Pide CONFIRMACIÓN EXPLÍCITA antes de editar las rutas críticas de Perito:
#   - backend/app/rules/         → motor de reglas de cobertura (P2)
#   - backend/app/orchestrator/  → capa de terminación acotada (P4)
#
# Convierte los invariantes de advisory (texto en AGENTS.md) a ENFORCED.
# Devuelve permissionDecision "ask" (no "deny"): el humano puede autorizar,
# pero el agente no edita solo. Ver .claude/rules/{coverage-determinism,termination}.md
#
# Requiere jq. Si falta, falla-abierto (exit 0) para no romper la sesión.
# ──────────────────────────────────────────────────────────────────────────

INPUT="$(cat)"

# Sin jq no podemos parsear el input → no bloqueamos (un hook no debe romper la sesión)
command -v jq >/dev/null 2>&1 || exit 0

FILE="$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')"
[ -z "$FILE" ] && exit 0

case "$FILE" in
  *backend/app/rules/*)
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "ask",
        permissionDecisionReason: "Ruta crítica: motor de reglas de cobertura (P2). La cobertura es determinística y afecta dictámenes a escala. Confirma explícitamente antes de editar."
      }
    }'
    exit 0
    ;;
  *backend/app/orchestrator/*)
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "ask",
        permissionDecisionReason: "Ruta crítica: capa de terminación acotada (P4). No relajar los límites de rondas/tokens. Confirma explícitamente antes de editar."
      }
    }'
    exit 0
    ;;
esac

exit 0
