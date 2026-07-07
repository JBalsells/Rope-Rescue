# ════════════════════════════════════════════════════════════════════
#  Física del Rescate — lanzador único de simulaciones
#
#  Todo corre dentro de un entorno virtual (.venv) que se crea solo.
#  Los targets por simulación se derivan del registro (un archivo en sims/),
#  así el Makefile nunca se desincroniza del catálogo.
#
#    make run        → instala (si hace falta) y abre el menú interactivo
#    make <key>      → levanta esa simulación (ej. make tirolesa_fuerzas)
#    make list       → lista las keys disponibles
#    make test       → corre los tests unitarios
#    make install    → solo crea el venv e instala dependencias
#    make clean      → borra cachés de Python
# ════════════════════════════════════════════════════════════════════

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
STAMP  := $(VENV)/.installed

# Catálogo de simulaciones: un módulo por archivo en sims/ (la key == nombre
# del archivo). Se deriva de los filenames, sin invocar Python al parsear.
KEYS := $(filter-out __init__,$(basename $(notdir $(wildcard sims/*.py))))

.PHONY: help run list test install clean $(KEYS)

# ── Entorno virtual (centinela): se recrea si cambian las dependencias ─
$(STAMP): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	@touch $(STAMP)

install: $(STAMP)
	@echo 'Entorno listo en $(VENV)/'

# ── Arranque principal: instala si hace falta y abre el menú ──────────
run: $(STAMP)
	@$(PY) framework.py

list: $(STAMP)
	@$(PY) framework.py --list

# Un target por cada simulación del registro: `make <key>`
$(KEYS): $(STAMP)
	@$(PY) framework.py $@

test: $(STAMP)
	@$(PY) -m pytest tests/ -q

help:
	@echo ''
	@echo '  Física del Rescate — simulaciones'
	@echo '  ─────────────────────────────────'
	@echo '  make run         instala (si hace falta) y abre el menú'
	@echo ''
	@echo '  make <key>       levanta una simulación:'
	@for k in $(KEYS); do echo "                     make $$k"; done
	@echo ''
	@echo '  make list        lista keys      make test     tests unitarios'
	@echo '  make install     solo venv+deps  make clean    borra cachés'
	@echo ''

clean:
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name '.pytest_cache' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo 'limpio.'
