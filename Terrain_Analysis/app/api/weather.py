"""Router REST del clima: condiciones actuales + posición solar del AOI."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.weather import (
    WeatherFieldRequest, WeatherFieldResponse, WeatherRequest, WeatherResponse,
)
from app.services.weather import fetch_weather, fetch_weather_field

router = APIRouter(prefix="/api", tags=["weather"])


def _parse_at(s):
    """ISO-8601 → datetime UTC. Acepta sufijo 'Z'. None si no se envía."""
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/weather", response_model=WeatherResponse)
def weather(req: WeatherRequest):
    """Clima del punto + sol para drapear sobre el terreno (HUD, luz solar, viento 3D)."""
    try:
        at = _parse_at(req.at)
    except ValueError:
        raise HTTPException(422, "El parámetro 'at' no es ISO-8601 válido")
    try:
        return fetch_weather(req.lat, req.lon, at_utc=at)
    except Exception as exc:   # solo errores inesperados; el provider ya degrada solo
        raise HTTPException(502, f"No se pudo obtener el clima: {exc}")


@router.post("/weather/field", response_model=WeatherFieldResponse)
def weather_field(req: WeatherFieldRequest):
    """Campo de clima (precip/nubes/código por celda) para mostrar efectos por sector."""
    poly = [(p.lon, p.lat) for p in req.polygon]
    try:
        return fetch_weather_field(poly, grid=req.grid)
    except Exception as exc:
        raise HTTPException(502, f"No se pudo obtener el campo de clima: {exc}")
