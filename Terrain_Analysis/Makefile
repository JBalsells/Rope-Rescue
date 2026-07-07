# Terrain Analysis — lanzador local (correr desde este directorio)
.PHONY: help install dev test clean

VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# ─── Parámetros configurables (editá estos valores) ─────────────────────────
DETAIL   ?= 120         # resolución de la malla 3D (entero ≤120; 70=medio, 100=alto, 120=máximo)
WATER    ?= on          # dibujar ríos/lagos/mar sobre el 3D: on | off
WEATHER  ?= open-meteo  # fuente de clima (proveedor registrado en services/weather.py)
# ────────────────────────────────────────────────────────────────────────────

help:
	@echo "make install   crea .venv e instala dependencias"
	@echo "make dev       server local con hot-reload  -> http://localhost:8000"
	@echo "make test      corre pytest"
	@echo "make clean     borra .venv y caches"
	@echo ""
	@echo "Config (editar arriba en el Makefile o pasar por línea):"
	@echo "  make dev DETAIL=120 WATER=on WEATHER=open-meteo"

install:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

dev:
	TA_DETAIL=$(DETAIL) TA_WATER=$(WATER) TA_WEATHER_PROVIDER=$(WEATHER) \
		$(VENV)/bin/uvicorn app.main:app --reload --port 8000

test:
	$(PY) -m pytest -q

clean:
	rm -rf $(VENV) .pytest_cache **/__pycache__
