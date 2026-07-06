#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# semantic-review.sh — Linter semántico headless para Perito (Lección 8)
#
# Revisa los archivos .py cambiados contra una base (default: main) usando
# `claude -p` en modo headless, con foco EXCLUSIVO en los invariantes de
# Perito y un presupuesto acotado por archivo. Pensado para pre-commit o CI.
#
# Uso:  bash scripts/semantic-review.sh [base_branch]
# Requiere: claude CLI autenticado.
# ──────────────────────────────────────────────────────────────────────────
set -e

BASE="${1:-main}"

FILES=$(git diff "$BASE" --name-only -- '*.py' 2>/dev/null || true)
if [ -z "$FILES" ]; then
  echo "Sin archivos .py cambiados vs $BASE. Nada que revisar."
  exit 0
fi

echo "Revisión semántica contra invariantes de Perito (base: $BASE)"
echo "$FILES" | while read -r file; do
  [ -f "$file" ] || continue
  echo ""
  echo "── $file ──"
  cat "$file" | claude -p \
    "Revisa este archivo del proyecto Perito. Reporta SOLO violaciones de sus invariantes:
     P1 (algún camino alcanza estado terminal sin aprobación humana),
     P2 (el LLM decide cobertura en vez del motor de reglas),
     P4 (loop sin límite de rondas/tokens),
     P5 (PII innecesaria enviada al LLM),
     inyección de prompt (input de documento mezclado con instrucciones).
     Formato: LINEA - PRINCIPIO - problema. Si no hay violaciones, responde: OK." \
    --output-format text --max-budget-usd 0.30 || true
done
