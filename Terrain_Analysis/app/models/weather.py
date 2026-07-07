"""
Esquemas Pydantic del clima: el contrato estable del API.

Estos DTOs son la "forma normalizada" (patrón Adapter): no importa de qué
proveedor venga el dato (Open-Meteo hoy, otro mañana), el frontend siempre
recibe esta misma estructura.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.terrain import Point


class WeatherRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitud del punto de interés (centro del AOI)")
    lon: float = Field(..., ge=-180, le=180, description="Longitud del punto de interés")
    at: Optional[str] = Field(
        None,
        description="Instante ISO-8601 para la posición solar (ej. '2026-06-16T17:30:00Z'). "
                    "Si se omite, se usa 'ahora'. Las condiciones meteorológicas son siempre actuales.",
    )


class WindInfo(BaseModel):
    speed: Optional[float] = Field(None, description="Rapidez del viento a 10 m")
    gust: Optional[float] = Field(None, description="Ráfaga máxima")
    dir_deg: Optional[float] = Field(None, description="Dirección METEOROLÓGICA: grados DESDE donde sopla (0=N, 90=E)")
    unit: str = Field("km/h", description="Unidad de speed/gust")
    u: float = Field(0.0, description="Componente este del viento (hacia donde sopla), misma unidad")
    v: float = Field(0.0, description="Componente norte del viento (hacia donde sopla), misma unidad")


class SunLight(BaseModel):
    x: float = Field(..., description="Componente este del vector de luz (marco ENU local, m)")
    y: float = Field(..., description="Componente norte")
    z: float = Field(..., description="Componente vertical (arriba)")
    ambient: float = Field(..., description="Luz ambiente sugerida para Plotly (0–1)")
    diffuse: float = Field(..., description="Luz difusa sugerida para Plotly (0–1)")


class SunInfo(BaseModel):
    azimuth_deg: float = Field(..., description="Azimut del sol (° desde el norte, horario)")
    elevation_deg: float = Field(..., description="Elevación del sol (° sobre el horizonte; <0 = bajo el horizonte)")
    is_up: bool = Field(..., description="¿El sol está sobre el horizonte?")
    light: SunLight


class WeatherResponse(BaseModel):
    lat: float
    lon: float
    observed_at: Optional[str] = Field(None, description="Marca de tiempo de la observación (hora local del AOI)")

    temp_c: Optional[float] = None
    feels_c: Optional[float] = Field(None, description="Sensación térmica")
    humidity_pct: Optional[float] = None
    precip_mm: Optional[float] = None
    cloud_pct: Optional[float] = None
    visibility_m: Optional[float] = Field(None, description="Visibilidad horizontal (m)")
    code: Optional[int] = Field(None, description="Código WMO de condición")
    condition: Optional[str] = Field(None, description="Descripción legible de la condición")
    is_day: Optional[bool] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None

    wind: WindInfo
    sun: SunInfo

    source: str = Field(..., description="Proveedor de datos usado")
    notes: List[str] = []


# --- Campo de clima espacial: precipitación/nubes/condición por celda del AOI ---

class WeatherFieldRequest(BaseModel):
    polygon: List[Point] = Field(..., min_length=3, description="Vértices del AOI (se usa su bbox)")
    grid: Optional[int] = Field(None, ge=2, le=16, description="Resolución de la grilla (grid×grid); None = adaptativa al tamaño del AOI")


class FieldCell(BaseModel):
    lat: float
    lon: float
    precip_mm: Optional[float] = None
    cloud_pct: Optional[float] = None
    code: Optional[int] = None


class WeatherFieldResponse(BaseModel):
    cells: List[FieldCell] = Field(..., description="Celdas en orden fila-mayor; fila 0 = norte")
    rows: int
    cols: int
    south: float
    west: float
    north: float
    east: float
    source: str
    notes: List[str] = []
