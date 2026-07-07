"""Router REST para cuerpos de agua (OSM/Overpass) dentro del polígono."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.terrain import Point
from app.services.water import fetch_water

router = APIRouter(prefix="/api", tags=["water"])


class WaterRequest(BaseModel):
    polygon: List[Point] = Field(..., min_length=3)


@router.post("/water")
def water(req: WaterRequest):
    """Devuelve ríos/lagos/mar (lon/lat) del bbox del polígono, para drapear en 3D."""
    poly = [(p.lon, p.lat) for p in req.polygon]
    try:
        return fetch_water(poly)
    except Exception as exc:
        raise HTTPException(502, f"No se pudo obtener el agua: {exc}")
