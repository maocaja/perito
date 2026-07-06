#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Hook: post-edit-lint.sh  (Perito)
# Evento: PostToolUse (matcher: Edit|Write)
#
# Se ejecuta automáticamente después de cada edición/escritura del agente.
# Corre lint y formato sobre el archivo afectado. Prioriza Python (ruff),
# el stack principal de Perito.
#
# Falla silencioso si no encuentra herramientas — un hook nunca debe romper
# la sesión del agente.
# ──────────────────────────────────────────────────────────────────────────

set -e

FILE_PATH="${CLAUDE_FILE_PATH:-}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"

case "$EXT" in
  py)
    # Python — stack principal de Perito
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$FILE_PATH" 2>/dev/null || true
      ruff check --fix "$FILE_PATH" 2>/dev/null || true
    elif command -v black >/dev/null 2>&1; then
      black --quiet "$FILE_PATH" 2>/dev/null || true
    fi
    ;;

  ts|tsx|js|jsx|json|md|yml|yaml|html|css)
    # Frontend / config / docs — prettier si está disponible
    if [ -f "package.json" ] && npx --no-install prettier --version >/dev/null 2>&1; then
      npx --no-install prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
    ;;

  *)
    exit 0
    ;;
esac

exit 0
