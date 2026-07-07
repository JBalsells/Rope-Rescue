"""
Superficie 3D del terreno dentro de un polígono.

Muestrea una malla de elevación sobre el bbox del polígono, enmascara (None) los
nodos que caen fuera del polígono y proyecta lon/lat → metros locales para que la
superficie tenga proporciones reales. Devuelve x, y (1D, m) y z (2D, m) listos
para un `Surface` de Plotly.
"""

import math

from app.core import config
from app.core.geo import point_in_polygon
from app.services.terrain import fetch_elevations_bulk


def _smooth_grid(g, window):
    """Media móvil separable sobre una malla numérica: quita los escalones del DEM."""
    window = int(window)
    if window < 3:
        return g
    half = window // 2
    R = len(g)
    C = len(g[0]) if R else 0
    h = [[0.0] * C for _ in range(R)]              # paso horizontal
    for r in range(R):
        row = g[r]
        for c in range(C):
            lo, hi = max(0, c - half), min(C, c + half + 1)
            h[r][c] = sum(row[lo:hi]) / (hi - lo)
    out = [[0.0] * C for _ in range(R)]            # paso vertical
    for c in range(C):
        col = [h[r][c] for r in range(R)]
        for r in range(R):
            lo, hi = max(0, r - half), min(R, r + half + 1)
            out[r][c] = sum(col[lo:hi]) / (hi - lo)
    return out


def generate_surface(polygon, grid, elevation_fn=fetch_elevations_bulk):
    grid = max(config.SURFACE_GRID_MIN, min(config.SURFACE_GRID_MAX, int(grid)))
    R = C = grid

    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    west, east = min(lons), max(lons)
    south, north = min(lats), max(lats)

    # Inset mínimo del muestreo: si un nodo cae EXACTAMENTE sobre el borde del
    # polígono, el ray casting lo excluye y un rectángulo queda con huecos en los
    # bordes. Correrlo un epsilon hacia adentro lo deja estrictamente dentro.
    ex = (east - west) * 1e-4
    ey = (north - south) * 1e-4
    west += ex; east -= ex
    south += ey; north -= ey

    def lon_at(c):
        return west + (east - west) * c / (C - 1)

    def lat_at(r):
        return north - (north - south) * r / (R - 1)   # fila 0 = norte

    coords = [(lon_at(c), lat_at(r)) for r in range(R) for c in range(C)]
    elevs = elevation_fn(coords)
    # Malla 2D suavizada (quita escalones del DEM → superficie lisa). El enmascarado
    # por polígono se hace después sobre estos valores ya suaves.
    ge = _smooth_grid([[float(elevs[r * C + c]) for c in range(C)] for r in range(R)],
                      config.SURFACE_SMOOTH_WINDOW)

    # Proyección equirectangular local (área chica): grados → metros desde el centro.
    lat0 = (north + south) / 2.0
    lon0 = (west + east) / 2.0
    mx = 111320.0 * math.cos(math.radians(lat0))   # m por grado de longitud
    my = 110540.0                                   # m por grado de latitud

    x = [round((lon_at(c) - lon0) * mx, 1) for c in range(C)]
    y = [round((lat_at(r) - lat0) * my, 1) for r in range(R)]

    z = []
    zmin, zmax, inside = math.inf, -math.inf, 0
    for r in range(R):
        row = []
        for c in range(C):
            e = ge[r][c]
            if point_in_polygon(lon_at(c), lat_at(r), polygon):
                row.append(round(e, 1))
                zmin, zmax = min(zmin, e), max(zmax, e)
                inside += 1
            else:
                row.append(None)   # fuera del polígono → hueco en la superficie
        z.append(row)

    if inside == 0:   # polígono demasiado chico frente a la malla → sin huecos
        z = [[round(ge[r][c], 1) for c in range(C)] for r in range(R)]
        flat = [v for row in z for v in row]
        zmin, zmax, inside = min(flat), max(flat), R * C

    return {
        "x": x, "y": y, "z": z,
        "zmin": round(zmin, 1), "zmax": round(zmax, 1),
        "grid": grid, "inside": inside,
        # Parámetros de proyección (para que el frontend drapee agua sobre la malla).
        "lon0": lon0, "lat0": lat0, "mx": round(mx, 4), "my": my,
    }
