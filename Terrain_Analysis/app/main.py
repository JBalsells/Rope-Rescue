"""
Punto de entrada FastAPI (fachada): monta el API y sirve el frontend estático.

Correr en local:  uvicorn app.main:app --reload --port 8000
  - UI/mapa:  http://localhost:8000/
  - API docs: http://localhost:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.surface import router as surface_router
from app.api.terrain import router as terrain_router
from app.api.water import router as water_router
from app.api.weather import router as weather_router
from app.core import config

app = FastAPI(title=config.APP_NAME, description=config.APP_DESC)

# Rutas del API primero (tienen prioridad sobre el montaje estático en "/").
app.include_router(terrain_router)
app.include_router(surface_router)
app.include_router(water_router)
app.include_router(weather_router)

# Frontend: sirve static/ en la raíz; html=True hace que "/" devuelva index.html.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
