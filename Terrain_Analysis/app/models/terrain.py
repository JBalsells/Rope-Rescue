"""Esquemas Pydantic compartidos: el contrato de entrada/salida del API (DTOs)."""

from pydantic import BaseModel, Field


class Point(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitud en grados")
    lon: float = Field(..., ge=-180, le=180, description="Longitud en grados")
