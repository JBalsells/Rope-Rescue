"""
Capa de visualización transversal — umbrales de color y estado.

Toda decisión de "verde / amarillo / rojo" sale de aquí, en UN solo lugar,
para que el código de cada sim no reimplemente sus propios umbrales.
Las funciones reciben un diccionario de paleta (config.COLORS para matplotlib
o config.PG_COLORS para pygame), así sirven a ambos backends.
"""

from config import NFPA_WORK_LOAD, ROPE_STATIC_MBS


# ── Umbrales (fracción de la carga / del MBS) ─────────────────────────
RATIO_CAUTION = 0.75   # > 75 % de la referencia → precaución
RATIO_DANGER = 1.00    # ≥ 100 % → peligroso


def lerp_color(c1, c2, t):
    """Interpolación lineal entre dos colores RGB (tuplas)."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def ratio_color(ratio, palette):
    """
    Color según un ratio carga/referencia (1.0 = referencia).
      ≤ 0.75 → accent (verde)   |   ≤ 1.0 → warning   |   > 1.0 → danger
    """
    if ratio <= RATIO_CAUTION:
        return palette['accent']
    if ratio <= RATIO_DANGER:
        return palette['warning']
    return palette['danger']


def ratio_status(ratio):
    """Etiqueta textual del estado de seguridad para un ratio."""
    if ratio <= RATIO_CAUTION:
        return 'SEGURO'
    if ratio <= RATIO_DANGER:
        return 'PRECAUCIÓN'
    return 'PELIGROSO'


def tension_color(t_kn, palette):
    """
    Color según una tensión absoluta (kN) contra los límites NFPA / MBS.
      < 0.7·NFPA → accent | < NFPA → warning | < MBS → secondary | ≥ MBS → danger
    """
    if t_kn >= ROPE_STATIC_MBS:
        return palette['danger']
    if t_kn >= NFPA_WORK_LOAD:
        return palette['secondary']
    if t_kn >= NFPA_WORK_LOAD * 0.7:
        return palette['warning']
    return palette['accent']


def v_angle_color(v_angle, palette):
    """Color según peligrosidad del ángulo V de un anclaje."""
    if v_angle > 160:
        return palette['danger']
    if v_angle > 140:
        return palette['secondary']
    if v_angle > 120:
        return palette['warning']
    return palette['accent']
