"""Tests del núcleo geo + superficie + agua (sin red: elevación inyectada)."""

from app.core.geo import point_in_polygon
from app.services.surface import generate_surface
from app.services.water import bbox_of, parse_overpass


# ---- point in polygon + superficie 3D ----

def test_point_in_polygon():
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]  # cuadrado
    assert point_in_polygon(5.0, 5.0, sq) is True
    assert point_in_polygon(15.0, 5.0, sq) is False
    assert point_in_polygon(-1.0, 5.0, sq) is False


def test_generate_surface_masks_outside_polygon():
    # Polígono triángulo dentro de un bbox: parte de la malla queda fuera (None).
    poly = [(-90.50, 14.60), (-90.46, 14.60), (-90.48, 14.63)]
    flat = lambda coords: [1500.0 for _ in coords]   # elevación constante (sin red)
    s = generate_surface(poly, grid=12, elevation_fn=flat)
    assert len(s["z"]) == 12 and len(s["z"][0]) == 12
    inside = sum(1 for row in s["z"] for v in row if v is not None)
    outside = sum(1 for row in s["z"] for v in row if v is None)
    assert inside > 0 and outside > 0          # hay nodos dentro y fuera
    assert s["inside"] == inside
    assert s["zmin"] == 1500.0 and s["zmax"] == 1500.0   # suavizado de constante = constante


def test_generate_surface_rectangle_no_holes():
    # Un rectángulo (== su bbox) debe llenarse entero (el inset evita huecos de borde).
    poly = [(-90.55, 14.62), (-90.50, 14.62), (-90.50, 14.57), (-90.55, 14.57)]
    flat = lambda coords: [1200.0 for _ in coords]
    s = generate_surface(poly, grid=15, elevation_fn=flat)
    holes = sum(1 for row in s["z"] for v in row if v is None)
    assert holes == 0 and s["inside"] == 15 * 15


# ---- agua (OSM/Overpass) ----

def test_bbox_of():
    poly = [(-90.50, 14.60), (-90.46, 14.63), (-90.48, 14.58)]
    s, w, n, e = bbox_of(poly)
    assert (s, w, n, e) == (14.58, -90.50, 14.63, -90.46)


def test_parse_overpass_ways_and_relations():
    data = {"elements": [
        {"type": "way", "tags": {"waterway": "river"},
         "geometry": [{"lon": -90.5, "lat": 14.6}, {"lon": -90.49, "lat": 14.61}]},
        {"type": "way", "tags": {"natural": "water"},
         "geometry": [{"lon": -90.5, "lat": 14.6}, {"lon": -90.5, "lat": 14.62}]},
        {"type": "relation", "members": [
            {"geometry": [{"lon": -90.4, "lat": 14.5}, {"lon": -90.41, "lat": 14.51}]}]},
        {"type": "node"},  # ignorado
    ]}
    feats = parse_overpass(data)
    assert len(feats) == 3
    assert feats[0]["kind"] == "line"      # waterway
    assert feats[1]["kind"] == "area"      # natural=water
    assert feats[2]["kind"] == "area"      # miembro de relación
    assert feats[0]["coords"][0] == [-90.5, 14.6]


def test_parse_overpass_respects_max():
    data = {"elements": [
        {"type": "way", "tags": {"waterway": "stream"},
         "geometry": [{"lon": 0, "lat": 0}]} for _ in range(10)]}
    assert len(parse_overpass(data, max_features=4)) == 4
