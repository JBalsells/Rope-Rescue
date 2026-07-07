"""
Primitivas geoespaciales puras (sin GUI, sin red).

`point_in_polygon` es la única que usa el servicio de superficie para enmascarar
la malla. Trabaja en grados lon/lat (no necesita proyección para el test de
pertenencia).
"""


def point_in_polygon(lon, lat, polygon):
    """
    ¿El punto (lon, lat) está dentro del polígono? Algoritmo de ray casting.
    `polygon` = lista de vértices (lon, lat). Puro, sin dependencias.
    """
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
