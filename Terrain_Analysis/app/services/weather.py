"""
Clima del área de análisis (capa de servicio).

Arquitectura pensada para extender:

  * Strategy  — `WeatherProvider` define el contrato; `OpenMeteoProvider` lo
                implementa contra Open-Meteo (gratis, sin API key). Cambiar de
                fuente = otra subclase, sin tocar API ni frontend.
  * Adapter   — cada proveedor normaliza SU respuesta cruda a un dict estable;
                el resto del sistema nunca ve el JSON del tercero.
  * Inyección — `fetch_weather(..., provider=...)` permite testear sin red.
  * Caché TTL — solo las CONDICIONES se cachean (cambian lento); la posición
                solar se recalcula siempre, para que raspar la hora sea barato.

La posición solar (offline, pura) vive en core/solar.py.
"""

import math
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from app.core import config
from app.core.solar import light_vector, solar_position


# --- Códigos WMO → descripción (Adapter de la condición) ---
_WMO = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna ligera", 53: "Llovizna", 55: "Llovizna intensa",
    56: "Llovizna helada", 57: "Llovizna helada intensa",
    61: "Lluvia ligera", 63: "Lluvia", 65: "Lluvia intensa",
    66: "Lluvia helada", 67: "Lluvia helada intensa",
    71: "Nieve ligera", 73: "Nieve", 75: "Nieve intensa", 77: "Granos de nieve",
    80: "Chubascos ligeros", 81: "Chubascos", 82: "Chubascos violentos",
    85: "Chubascos de nieve", 86: "Chubascos de nieve intensos",
    95: "Tormenta eléctrica", 96: "Tormenta con granizo", 99: "Tormenta con granizo fuerte",
}


def describe_wmo(code):
    if code is None:
        return None
    return _WMO.get(int(code), f"Código {code}")


def wind_uv(from_deg, speed):
    """
    Componentes (este, norte) del viento a partir de su dirección METEOROLÓGICA
    (grados DESDE donde sopla) y su rapidez. El vector apunta HACIA donde va el
    viento. Puro y testeable.
    """
    to = math.radians((float(from_deg) + 180.0) % 360.0)
    return round(math.sin(to) * speed, 3), round(math.cos(to) * speed, 3)


# ----------------------------------------------------------------------------
# Proveedores (Strategy)
# ----------------------------------------------------------------------------

class WeatherProvider(ABC):
    """Contrato de una fuente de clima. `current` devuelve un dict normalizado."""

    name = "abstract"

    @abstractmethod
    def current(self, lat, lon):
        """Condiciones actuales normalizadas (sin posición solar). Puede lanzar en error de red."""
        raise NotImplementedError

    def field(self, coords):
        """
        Precipitación/nubes/código en VARIOS puntos (lista de (lon, lat)), en el
        mismo orden. Implementación por defecto: una llamada por punto (lenta). Los
        proveedores que soportan multi-coordenada deberían sobreescribirla.
        """
        out = []
        for lon, lat in coords:
            c = self.current(lat, lon)
            out.append({"precip_mm": c.get("precip_mm"), "cloud_pct": c.get("cloud_pct"), "code": c.get("code")})
        return out


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo: forecast endpoint, sin API key. Adapta su JSON al dict normalizado."""

    name = "open-meteo"

    def current(self, lat, lon):
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "is_day", "precipitation", "weather_code", "cloud_cover",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
            ]),
            "hourly": "visibility",
            "daily": "sunrise,sunset",
            "wind_speed_unit": config.WEATHER_WIND_UNIT,
            "timezone": "auto",
            "forecast_days": 1,
        }
        r = httpx.get(config.OPEN_METEO_URL, params=params, timeout=config.WEATHER_TIMEOUT_S)
        r.raise_for_status()
        j = r.json()
        cur = j.get("current", {}) or {}
        daily = j.get("daily", {}) or {}
        units = j.get("current_units", {}) or {}
        return {
            "observed_at": cur.get("time"),
            "temp_c": cur.get("temperature_2m"),
            "feels_c": cur.get("apparent_temperature"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "precip_mm": cur.get("precipitation"),
            "cloud_pct": cur.get("cloud_cover"),
            "visibility_m": self._visibility_at(j, cur.get("time")),
            "code": cur.get("weather_code"),
            "condition": describe_wmo(cur.get("weather_code")),
            "is_day": (bool(cur.get("is_day")) if cur.get("is_day") is not None else None),
            "sunrise": (daily.get("sunrise") or [None])[0],
            "sunset": (daily.get("sunset") or [None])[0],
            "wind_speed": cur.get("wind_speed_10m"),
            "wind_gust": cur.get("wind_gusts_10m"),
            "wind_dir_deg": cur.get("wind_direction_10m"),
            "wind_unit": units.get("wind_speed_10m", "km/h"),
            "notes": [],
        }

    def field(self, coords):
        """Multi-coordenada en UNA sola request (Open-Meteo acepta lat/lon separados por coma)."""
        lats = ",".join(str(round(lat, 4)) for lon, lat in coords)
        lons = ",".join(str(round(lon, 4)) for lon, lat in coords)
        params = {
            "latitude": lats, "longitude": lons,
            "current": "precipitation,weather_code,cloud_cover",
        }
        r = httpx.get(config.OPEN_METEO_URL, params=params, timeout=config.WEATHER_TIMEOUT_S)
        r.raise_for_status()
        j = r.json()
        items = j if isinstance(j, list) else [j]   # 1 coord → objeto; N coords → lista
        out = []
        for it in items:
            cur = (it.get("current", {}) or {})
            out.append({
                "precip_mm": cur.get("precipitation"),
                "cloud_pct": cur.get("cloud_cover"),
                "code": cur.get("weather_code"),
            })
        return out

    @staticmethod
    def _visibility_at(j, t):
        """La visibilidad es horaria, no 'current': se toma la hora que coincide con `current.time`."""
        hourly = j.get("hourly", {}) or {}
        times = hourly.get("time") or []
        vals = hourly.get("visibility") or []
        if t:
            pref = t[:13]                                   # 'YYYY-MM-DDTHH'
            for i, ht in enumerate(times):
                if ht[:13] == pref and i < len(vals):
                    return vals[i]
        return vals[0] if vals else None


# --- Registro de proveedores (conmutables) ---
# Para sumar otra fuente: crear otra subclase de WeatherProvider y registrarla acá.
# El proveedor activo se elige con config.WEATHER_PROVIDER (editable desde el Makefile).
PROVIDERS = {
    OpenMeteoProvider.name: OpenMeteoProvider(),
}


def get_provider(name=None):
    """Proveedor activo. `name` explícito o el de config; cae al open-meteo si no existe."""
    return PROVIDERS.get((name or config.WEATHER_PROVIDER), PROVIDERS[OpenMeteoProvider.name])


def _empty_conditions():
    """Condiciones 'desconocidas' (provider caído): viento en calma, resto None."""
    return {
        "observed_at": None, "temp_c": None, "feels_c": None, "humidity_pct": None,
        "precip_mm": None, "cloud_pct": None, "visibility_m": None, "code": None,
        "condition": None, "is_day": None, "sunrise": None, "sunset": None,
        "wind_speed": 0.0, "wind_gust": None, "wind_dir_deg": 0.0,
        "wind_unit": "km/h", "notes": [],
    }


# --- Caché TTL de condiciones (memoización con expiración) ---
_COND_CACHE = {}   # (lat2, lon2, provider) -> (expira_monotonic, conditions)


def _conditions(provider, lat, lon, use_cache=True):
    key = (round(lat, 2), round(lon, 2), provider.name)
    now = time.monotonic()
    if use_cache:
        hit = _COND_CACHE.get(key)
        if hit and hit[0] > now:
            return hit[1]
    cond = provider.current(lat, lon)
    if use_cache:
        _COND_CACHE[key] = (now + config.WEATHER_TTL_S, cond)
    return cond


def _sun_info(lat, lon, at_utc):
    """Posición solar + parámetros de iluminación sugeridos para Plotly."""
    az, elev = solar_position(lat, lon, at_utc)
    is_up = elev > 0
    if is_up:
        # Piso de elevación: con el sol muy bajo, la luz sigue siendo lateral (sombras largas).
        ambient, diffuse, lv_elev = 0.35, 0.95, max(elev, 4.0)
    else:
        # Noche/crepúsculo: luz tenue y casi cenital para que el relieve no quede negro.
        ambient, diffuse, lv_elev = 0.22, 0.30, 8.0
    lv = light_vector(az, lv_elev, config.SUN_LIGHT_SCALE)
    return {
        "azimuth_deg": round(az, 1),
        "elevation_deg": round(elev, 1),
        "is_up": is_up,
        "light": {**lv, "ambient": ambient, "diffuse": diffuse},
    }


def fetch_weather(lat, lon, at_utc=None, provider=None, use_cache=True):
    """
    Clima del punto (lat, lon) + posición solar para `at_utc` (UTC; por defecto ahora).

    Degrada con gracia: si el proveedor falla, las condiciones quedan en None y el
    viento en calma, pero la posición solar (offline) SIEMPRE se entrega, con una
    nota explicativa. Nunca lanza por fallo del proveedor.
    """
    provider = provider or get_provider()
    at = at_utc or datetime.now(timezone.utc)

    notes = []
    try:
        cond = _conditions(provider, lat, lon, use_cache=use_cache)
    except Exception as exc:   # red caída, 429, formato inesperado, etc.
        cond = _empty_conditions()
        notes.append(f"Clima no disponible ({type(exc).__name__}); solo posición solar.")

    u, v = wind_uv(cond.get("wind_dir_deg") or 0.0, cond.get("wind_speed") or 0.0)

    return {
        "lat": lat,
        "lon": lon,
        "observed_at": cond.get("observed_at"),
        "temp_c": cond.get("temp_c"),
        "feels_c": cond.get("feels_c"),
        "humidity_pct": cond.get("humidity_pct"),
        "precip_mm": cond.get("precip_mm"),
        "cloud_pct": cond.get("cloud_pct"),
        "visibility_m": cond.get("visibility_m"),
        "code": cond.get("code"),
        "condition": cond.get("condition"),
        "is_day": cond.get("is_day"),
        "sunrise": cond.get("sunrise"),
        "sunset": cond.get("sunset"),
        "wind": {
            "speed": cond.get("wind_speed"),
            "gust": cond.get("wind_gust"),
            "dir_deg": cond.get("wind_dir_deg"),
            "unit": cond.get("wind_unit", "km/h"),
            "u": u, "v": v,
        },
        "sun": _sun_info(lat, lon, at),
        "source": provider.name,
        "notes": notes + (cond.get("notes") or []),
    }


def _bbox(polygon):
    """(sur, oeste, norte, este) del polígono."""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return min(lats), min(lons), max(lats), max(lons)


_FIELD_CACHE = {}   # (s2,w2,n2,e2,grid,provider) -> (expira_monotonic, response)


def fetch_weather_field(polygon, grid=None, provider=None, use_cache=True):
    """
    Campo de clima sobre el bbox del AOI: grilla grid×grid de puntos con
    precipitación/nubes/código en cada uno (una sola request multi-coordenada).
    Permite al frontend mostrar lluvia/efectos SOLO en los sectores afectados.
    En un AOI chico, todos los puntos caen en la misma celda del modelo (~11 km)
    y el campo resulta uniforme — el comportamiento degrada a "todo igual" solo.
    """
    provider = provider or get_provider()
    s, w, n, e = _bbox(polygon)
    if grid is None:
        # Grilla adaptativa: ~1 punto cada ~18 km, para captar lluvia localizada en
        # AOIs grandes sin perder resolución. Acotada [WEATHER_FIELD_GRID, 16].
        midlat = math.radians((n + s) / 2.0)
        span_km = max((n - s) * 111.0, (e - w) * 111.0 * math.cos(midlat))
        grid = int(round(span_km / 18.0))
    grid = max(config.WEATHER_FIELD_GRID, min(16, int(grid)))
    key = (round(s, 2), round(w, 2), round(n, 2), round(e, 2), grid, provider.name)
    now = time.monotonic()
    if use_cache:
        hit = _FIELD_CACHE.get(key)
        if hit and hit[0] > now:
            return hit[1]

    rows = cols = grid
    coords, latlon = [], []
    for r in range(rows):
        lat = n - (n - s) * (r / (rows - 1)) if rows > 1 else (n + s) / 2
        for c in range(cols):
            lon = w + (e - w) * (c / (cols - 1)) if cols > 1 else (w + e) / 2
            coords.append((lon, lat))
            latlon.append((lat, lon))

    notes = []
    try:
        data = provider.field(coords)
    except Exception as exc:
        data = [{"precip_mm": None, "cloud_pct": None, "code": None} for _ in coords]
        notes.append(f"Campo de clima no disponible ({type(exc).__name__}).")

    cells = [
        {"lat": latlon[i][0], "lon": latlon[i][1],
         "precip_mm": d.get("precip_mm"), "cloud_pct": d.get("cloud_pct"), "code": d.get("code")}
        for i, d in enumerate(data)
    ]
    res = {"cells": cells, "rows": rows, "cols": cols,
           "south": s, "west": w, "north": n, "east": e,
           "source": provider.name, "notes": notes}
    if use_cache:
        _FIELD_CACHE[key] = (now + config.WEATHER_TTL_S, res)
    return res
