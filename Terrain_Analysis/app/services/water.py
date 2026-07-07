"""
Cuerpos de agua (ríos, lagos, mar) desde OpenStreetMap vía Overpass API.

Devuelve las geometrías en lon/lat; el frontend las proyecta y las drapea sobre
la superficie 3D. El parseo está separado de la red (`parse_overpass`) para test.
"""

import httpx

from app.core import config


def bbox_of(polygon):
    """(sur, oeste, norte, este) del polígono — orden que pide Overpass."""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return min(lats), min(lons), max(lats), max(lons)


def _classify(tags):
    if tags.get("waterway"):
        return "line"            # río/quebrada/canal
    if tags.get("natural") == "coastline":
        return "coast"           # línea de costa (mar)
    return "area"                # lago/laguna/embalse


def parse_overpass(data, max_features=None):
    """Convierte la respuesta Overpass en [{kind, coords:[[lon,lat],...]}]."""
    max_features = max_features or config.WATER_MAX_FEATURES
    feats = []
    for el in data.get("elements", []):
        if el.get("type") == "way" and el.get("geometry"):
            feats.append({
                "kind": _classify(el.get("tags", {})),
                "coords": [[g["lon"], g["lat"]] for g in el["geometry"]],
            })
        elif el.get("type") == "relation":
            for m in el.get("members", []):
                if m.get("geometry"):
                    feats.append({
                        "kind": "area",
                        "coords": [[g["lon"], g["lat"]] for g in m["geometry"]],
                    })
        if len(feats) >= max_features:
            break
    return feats


_CACHE = {}   # caché en memoria por bbox redondeado → evita reconsultar Overpass


def fetch_water(polygon):
    s, w, n, e = bbox_of(polygon)
    key = (round(s, 3), round(w, 3), round(n, 3), round(e, 3))
    if key in _CACHE:
        return _CACHE[key]

    b = f"{s},{w},{n},{e}"
    query = (
        f"[out:json][timeout:{int(config.OVERPASS_TIMEOUT_S)}];"
        "("
        f'way["natural"="water"]({b});'
        f'way["waterway"~"river|stream|canal"]({b});'
        f'way["natural"="coastline"]({b});'
        f'relation["natural"="water"]({b});'
        ");"
        "out geom;"
    )
    headers = {"User-Agent": "TerrainAnalysis/1.0 (rope-rescue terrain tool)"}

    last = None
    for url in config.OVERPASS_URLS:           # probar espejos en orden
        try:
            r = httpx.post(url, data={"data": query}, headers=headers,
                           timeout=config.OVERPASS_TIMEOUT_S + 10)
            r.raise_for_status()
            feats = parse_overpass(r.json())
            res = {"features": feats, "count": len(feats)}
            _CACHE[key] = res
            return res
        except Exception as exc:               # timeout / 429 / 504 → siguiente espejo
            last = exc
            continue
    raise last or RuntimeError("Overpass no respondió")
