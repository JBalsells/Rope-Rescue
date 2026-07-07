"""Router REST de utilidades: health y configuración del frontend."""

from fastapi import APIRouter

from app.core import config

router = APIRouter(prefix="/api", tags=["terrain"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config")
def frontend_config():
    """Parámetros que el frontend fija al cargar (editables desde el Makefile)."""
    return {
        "detail": min(config.FRONTEND_DETAIL, config.SURFACE_GRID_MAX),
        "water": config.FRONTEND_WATER,
    }
