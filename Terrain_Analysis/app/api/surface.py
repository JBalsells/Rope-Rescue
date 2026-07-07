"""Router REST para la superficie 3D del terreno dentro de un polígono."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import config
from app.models.terrain import Point
from app.services.surface import generate_surface

router = APIRouter(prefix="/api", tags=["surface"])


class SurfaceRequest(BaseModel):
    polygon: List[Point] = Field(..., min_length=3, description="Vértices del polígono (≥3)")
    grid: int = Field(config.SURFACE_GRID_DEFAULT, description="Resolución de la malla (grid×grid)")


@router.post("/surface")
def surface(req: SurfaceRequest):
    """Devuelve la malla de elevación (x, y en m; z 2D) dentro del polígono."""
    poly = [(p.lon, p.lat) for p in req.polygon]
    try:
        return generate_surface(poly, req.grid)
    except Exception as exc:
        raise HTTPException(502, f"No se pudo generar la superficie: {exc}")
