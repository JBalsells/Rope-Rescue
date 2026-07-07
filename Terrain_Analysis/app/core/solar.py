"""
Posición solar y vector de luz — el "físico del sol" de este servicio.

Matemática pura de astronomía de posición (sin red, sin GUI), análoga a geo.py.
Dado lat/lon y un instante UTC calcula el azimut y la elevación del sol; y
traduce esa dirección a un vector de luz en el marco local ENU (x=este, y=norte,
z=arriba) que Plotly usa para iluminar la superficie 3D (`lightposition`).

Se aísla aquí para poder testearlo y para que mañana otra capa lo reutilice
(sombras proyectadas, ventana de luz para planificar una búsqueda SAR, etc.).
"""

import math
from datetime import timezone


def _julian_day(dt_utc):
    """Día juliano (con fracción) de un datetime. Se normaliza a UTC si trae tz."""
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc)
    y, m = dt_utc.year, dt_utc.month
    day = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24.0
    if m <= 2:                       # ene/feb cuentan como meses 13/14 del año previo
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4               # corrección gregoriana
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524.5


def solar_position(lat, lon, dt_utc):
    """
    Azimut (° desde el norte, sentido horario) y elevación (° sobre el horizonte)
    del sol para (lat, lon) en el instante `dt_utc`.

    Algoritmo de baja precisión NOAA/USNO (~0.01°): más que suficiente para
    iluminar el relieve y orientar sombras. Elevación negativa = sol bajo el
    horizonte (noche/crepúsculo).
    """
    d = _julian_day(dt_utc) - 2451545.0                         # días desde J2000.0

    L = (280.460 + 0.9856474 * d) % 360.0                       # longitud media (°)
    g = math.radians((357.528 + 0.9856003 * d) % 360.0)         # anomalía media
    lam = math.radians((L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0)  # long. eclíptica
    eps = math.radians(23.439 - 0.0000004 * d)                  # oblicuidad de la eclíptica

    decl = math.asin(math.sin(eps) * math.sin(lam))             # declinación solar
    ra_deg = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))) % 360.0  # asc. recta

    gmst = (280.46061837 + 360.98564736629 * d) % 360.0         # sidéreo medio de Greenwich (°)
    lmst = (gmst + lon) % 360.0                                 # sidéreo local (°)
    h = math.radians(lmst - ra_deg)                             # ángulo horario

    phi = math.radians(lat)
    elev = math.asin(math.sin(phi) * math.sin(decl) +
                     math.cos(phi) * math.cos(decl) * math.cos(h))
    # Azimut desde el SUR (positivo hacia el oeste) → se gira a "desde el norte, horario".
    az_s = math.atan2(math.sin(h), math.cos(h) * math.sin(phi) - math.tan(decl) * math.cos(phi))
    az = (math.degrees(az_s) + 180.0) % 360.0
    return az, math.degrees(elev)


def light_vector(az_deg, elev_deg, scale=1.0):
    """
    Dirección del sol como vector en el marco local ENU (x=este, y=norte, z=arriba),
    multiplicado por `scale`. Es la `lightposition` que espera Plotly: la luz llega
    desde esa posición hacia la superficie.
    """
    a = math.radians(az_deg)
    e = math.radians(elev_deg)
    return {
        "x": round(math.cos(e) * math.sin(a) * scale, 1),
        "y": round(math.cos(e) * math.cos(a) * scale, 1),
        "z": round(math.sin(e) * scale, 1),
    }
