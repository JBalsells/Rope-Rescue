"""Configuración central del servicio (única fuente de verdad de constantes)."""

import os

APP_NAME = "Terrain Analysis"
APP_DESC = "Análisis de terreno para rescate: superficie 3D, agua y clima sobre un mapa."

# --- Elevación de la malla 3D (open-elevation, sin API key) ---
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# Superficie 3D (malla de elevación dentro de un polígono).
SURFACE_GRID_MIN = 10
SURFACE_GRID_MAX = 120      # 120×120 ≈ 14.4k pts; más arriba la API pública se cuelga
SURFACE_GRID_DEFAULT = 100
# Suavizado de la malla 3D (media móvil separable, en celdas) para quitar los
# escalones del DEM (open-elevation da metros enteros, SRTM ~30 m) → superficie lisa.
# 0/1 = sin suavizar; 3 = suave conservando la forma; subir = más liso (redondea picos).
SURFACE_SMOOTH_WINDOW = 3
ELEV_BULK_TIMEOUT_S = 45.0  # un POST grande a open-elevation puede tardar varios seg

# Agua (ríos/lagos/mar) desde OpenStreetMap vía Overpass.
# Varios espejos: si uno falla/limita, se prueba el siguiente.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OVERPASS_TIMEOUT_S = 40.0
WATER_MAX_FEATURES = 1200

# --- Clima ---
# Proveedor conmutable (patrón Strategy/registry en services/weather.py).
# Editable desde el Makefile (TA_WEATHER_PROVIDER). Hoy: "open-meteo" (sin API key).
WEATHER_PROVIDER = os.environ.get("TA_WEATHER_PROVIDER", "open-meteo").strip().lower()
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_S = 15.0
# Cachea SOLO las condiciones (temp/viento/etc.) este tiempo; el sol se recalcula
# aparte en cada request, así "raspar" la hora del día no golpea la red.
WEATHER_TTL_S = 600
WEATHER_WIND_UNIT = "kmh"
# Magnitud del vector de luz solar en el marco ENU local (metros). Grande para
# que actúe como luz "al infinito" sobre la superficie 3D.
SUN_LIGHT_SCALE = 100_000.0
# Campo de clima espacial: grilla NxN de puntos sobre el AOI (una sola llamada
# multi-coordenada a Open-Meteo) para mostrar lluvia solo donde precipita.
# El modelo global es ~11 km, así que más densidad que eso no agrega detalle real.
WEATHER_FIELD_GRID = 6

# --- Parámetros del frontend (editables desde el Makefile vía variables de entorno) ---
# El Makefile los exporta al lanzar; aquí están los valores por defecto. Se exponen
# al navegador en GET /api/config. Ver comentarios en el Makefile.
FRONTEND_DETAIL = int(os.environ.get("TA_DETAIL", str(SURFACE_GRID_MAX)))  # resolución 3D (≤120)
FRONTEND_WATER = os.environ.get("TA_WATER", "on").strip().lower() not in ("0", "off", "false", "no")
