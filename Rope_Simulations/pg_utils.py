"""
Helpers de dibujo para las simulaciones en Pygame.

Centraliza primitivas que cada sim reimplementaba: flechas, líneas
discontinuas, la fábrica de fuentes y la barra de controles inferior.
Requiere pygame (solo lo importan las sims pygame, no la física ni los tests).
"""

import math
import pygame


def make_fonts(spec=None):
    """
    Crea un dict de fuentes DejaVu Sans a partir de {nombre: (tam, bold)}.
    Sin argumento devuelve un juego estándar title/big/med/sm/xs.
    """
    spec = spec or {
        'title': (26, True),
        'big': (18, True),
        'med': (14, True),
        'sm': (12, False),
        'xs': (11, False),
    }
    return {
        name: pygame.font.SysFont('DejaVu Sans', size, bold=bold)
        for name, (size, bold) in spec.items()
    }


def dashed_line(surface, color, start, end, width=1, dash_len=8):
    """Línea discontinua entre start y end."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    drawing = True
    while pos < length:
        seg_end = min(pos + dash_len, length)
        if drawing:
            sx = int(start[0] + ux * pos)
            sy = int(start[1] + uy * pos)
            ex = int(start[0] + ux * seg_end)
            ey = int(start[1] + uy * seg_end)
            pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)
        pos = seg_end + dash_len / 2.0
        drawing = not drawing


def arrow(surface, color, start, end, width=3, head=8):
    """Flecha de start a end con punta triangular."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    ux, uy = dx / length, dy / length
    pygame.draw.line(surface, color,
                     (int(start[0]), int(start[1])),
                     (int(end[0]), int(end[1])), width)
    perp_x, perp_y = -uy * head, ux * head
    base_x, base_y = end[0] - ux * head, end[1] - uy * head
    pygame.draw.polygon(surface, color, [
        (int(end[0]), int(end[1])),
        (int(base_x + perp_x), int(base_y + perp_y)),
        (int(base_x - perp_x), int(base_y - perp_y)),
    ])


def control_bar(surface, font, items, palette, width, height,
                active=None, pad_x=14, pad_y=None):
    """
    Barra de controles inferior. `items` es una lista de strings.
    `active` opcional: callable(item) -> bool para resaltar en danger.
    """
    y = height - 42 if pad_y is None else pad_y
    pygame.draw.rect(surface, palette['panel'], (0, y - 8, width, 50))
    x = 12
    for item in items:
        hot = bool(active(item)) if active else False
        color = palette['danger'] if hot else palette['dark_text']
        surf = font.render(item, True, color)
        surface.blit(surf, (x, y))
        x += surf.get_width() + pad_x
