# Perito — Makefile (Unit G: showcase de un comando)
#
# Uso rápido:
#   make setup                      # crea el venv e instala deps
#   export ANTHROPIC_API_KEY=...    # (opcional) para ver los agentes reales
#   make demo                       # 4 escenarios por el pipeline real (o presets sin key)
#
# El venv es configurable:  make demo VENV=/tmp/perito-v
# Claves opcionales (export antes de correr):
#   ANTHROPIC_API_KEY                        → agentes Claude reales (si falta: presets deterministas)
#   LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY → trazas a Langfuse
#   DATABASE_URL + PERSISTENCE=postgres      → persistencia en Neon (si falta: in-memory)

VENV    ?= .venv
PY      := $(abspath $(VENV))/bin/python
PIP     := $(abspath $(VENV))/bin/pip
UVICORN := $(abspath $(VENV))/bin/uvicorn

.DEFAULT_GOAL := help
.PHONY: help setup run demo evals test

help:  ## Muestra esta ayuda
	@echo "Perito — targets disponibles:"
	@echo "  make setup   Crea el venv ($(VENV)) e instala deps (obs + evals + psycopg)"
	@echo "  make run     Levanta el dashboard (uvicorn) → http://localhost:8000/casos"
	@echo "  make demo    4 escenarios (agentes reales si hay ANTHROPIC_API_KEY; si no, presets)"
	@echo "  make demo-mail  Envía FNOL sintéticos al Gmail demo (para la demo EN VIVO; requiere DEMO_GMAIL_*)"
	@echo "  make evals   Evals agénticos (pytest -m agentic, requiere key real)"
	@echo "  make test    Suite base (LLM mockeado, sin costo)"
	@echo ""
	@echo "  venv configurable:  make demo VENV=/tmp/perito-v"

setup:  ## Crea el venv e instala las deps (idempotente)
	python3 -m venv $(VENV)
	$(PIP) install -e "./backend[dev,obs,evals]"
	$(PIP) install "psycopg[binary]"
	@echo "✓ Listo. Ahora: export tus claves (opcional) y corre 'make demo'."

run:  ## Levanta el dashboard (HTMX) en :8000
	cd backend && $(UVICORN) app.main:app --reload

demo:  ## 4 escenarios por el pipeline real (o presets sin key) + Langfuse + resumen
	cd backend && $(PY) demo_run.py

demo-mail:  ## Envía correos FNOL sintéticos al Gmail demo (~5/min, tope MAIL_TOTAL). On-demand.
	cd backend && $(PY) demo_mail.py

evals:  ## Evals agénticos (Claude-as-judge) — cuesta API, requiere key real
	cd backend && PERSISTENCE=memory $(PY) -m pytest tests/ -m agentic -q

test:  ## Suite base (sin API, sin costo) — hermético: ignora .env (memory, sin Langfuse, poller off)
	cd backend && ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY:-test} PERSISTENCE=memory LANGFUSE_PUBLIC_KEY= LANGFUSE_SECRET_KEY= DEMO_LIVE=off $(PY) -m pytest tests/ -q
