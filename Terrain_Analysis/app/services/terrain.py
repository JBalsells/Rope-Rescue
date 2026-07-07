"""
Elevación del terreno (capa de servicio).

Provee la elevación de una malla de puntos para la superficie 3D. La obtención es
inyectable (`elevation_fn` en `generate_surface`) para poder testear sin red.
"""

import httpx

from app.core import config


def fetch_elevations_bulk(coords):
    """
    Elevación de una malla (miles de puntos) en UN solo POST a open-elevation, con
    timeout amplio. NOTA: la API pública rate-limitea (429) requests concurrentes,
    así que NO se trocea en paralelo —un único POST grande es lo confiable y rápido—.
    Si open-elevation falla, propaga el error (el API responde 502).
    """
    locations = [{"latitude": lat, "longitude": lon} for lon, lat in coords]
    resp = httpx.post(
        config.OPEN_ELEVATION_URL,
        json={"locations": locations},
        timeout=config.ELEV_BULK_TIMEOUT_S,
    )
    resp.raise_for_status()
    return [float(r["elevation"]) for r in resp.json()["results"]]
