"""
01_triangulo_del_fuego.py
Triángulo (Tetraedro) del Fuego — Elementos y Métodos de Extinción

Simulación interactiva para instrucción de bomberos.
Muestra cómo cada elemento del triángulo del fuego influye en la
intensidad de combustión y qué método de extinción actúa sobre él.

Controles:
  Combustible % — cantidad de material combustible disponible
  Oxígeno %     — concentración de O₂ (aire normal = 21 %)
  Calor %       — nivel de energía térmica presente
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.widgets import Slider

from config import COLORS, FC, apply_mpl_style, MIN_COMBUSTION_O2


# ── Física ────────────────────────────────────────────────────────────────────

def calc_intensity(fuel_pct: float, o2_pct: float, heat_pct: float) -> float:
    """Intensidad de combustión [0–100 %]. Modelo pedagógico de producto."""
    f = fuel_pct / 100.0
    o = max(0.0, (o2_pct - MIN_COMBUSTION_O2) / (21.0 - MIN_COMBUSTION_O2))
    h = heat_pct / 100.0
    return round(100.0 * f * o * h, 1)


def fire_status(intens: float) -> tuple[str, str]:
    if intens == 0:
        return 'SIN COMBUSTIÓN', COLORS['anchor']
    elif intens < 20:
        return 'FUEGO INCIPIENTE', COLORS['info']
    elif intens < 55:
        return 'FUEGO EN DESARROLLO', COLORS['warning']
    elif intens < 80:
        return 'FUEGO PLENAMENTE DESARROLLADO', COLORS['secondary']
    else:
        return 'FUEGO FLASHOVER INMINENTE', COLORS['danger']


# ── Dibujo del Triángulo ──────────────────────────────────────────────────────

def draw_triangle(ax, fuel: float, oxy: float, heat: float, intens: float):
    ax.clear()
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.1, 1.35)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])

    # Vértices del triángulo equilátero (R=0.82, centrado en (0, 0.10))
    R, cx, cy = 0.82, 0.0, 0.10
    angles = [np.pi / 2,
              np.pi / 2 + 2 * np.pi / 3,
              np.pi / 2 + 4 * np.pi / 3]
    v = np.array([(cx + R * np.cos(a), cy + R * np.sin(a)) for a in angles])
    # v[0]=arriba(calor), v[1]=abajo-izq(combustible), v[2]=abajo-der(oxígeno)

    # Relleno con brillo proporcional a la intensidad
    fire_alpha = (intens / 100.0) ** 0.7 * 0.65
    fire_col = '#FF2200' if intens > 75 else '#FF7700' if intens > 35 else '#CC4400'
    tri = plt.Polygon(v, closed=True, facecolor=fire_col,
                      alpha=fire_alpha, edgecolor='none', zorder=2)
    ax.add_patch(tri)

    # Lados con brillo proporcional al nivel de cada elemento
    o_eff = max(0.0, (oxy - MIN_COMBUSTION_O2) / (21.0 - MIN_COMBUSTION_O2))
    side_data = [
        (v[0], v[1], COLORS['danger'],  heat / 100, 'CALOR'),
        (v[1], v[2], COLORS['warning'], fuel / 100, 'COMBUSTIBLE'),
        (v[2], v[0], COLORS['info'],    o_eff,       'OXÍGENO'),
    ]
    for p1, p2, color, level, _ in side_data:
        lw_glow = 5 + 16 * level
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=color, lw=lw_glow, alpha=max(0.12, level),
                solid_capstyle='round', zorder=3)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=color, lw=4, alpha=1.0,
                solid_capstyle='round', zorder=4)

    # Etiquetas en los vértices
    vx_offsets = [(0, +0.13, 'center'), (-0.18, -0.08, 'right'), (+0.18, -0.08, 'left')]
    v_labels   = ['CALOR', 'COMBUSTIBLE', 'OXÍGENO']
    v_colors   = [COLORS['danger'], COLORS['warning'], COLORS['info']]
    v_vals     = [heat, fuel, oxy]
    v_units    = ['%', '%', '%']
    for i in range(3):
        dx, dy, ha = vx_offsets[i]
        ax.text(v[i][0] + dx, v[i][1] + dy, v_labels[i],
                ha=ha, va='center', fontsize=11, fontweight='bold',
                color=v_colors[i], zorder=5)
        ax.text(v[i][0] + dx, v[i][1] + dy - 0.11, f'{v_vals[i]:.0f}{v_units[i]}',
                ha=ha, va='center', fontsize=10,
                color=v_colors[i], alpha=0.9, zorder=5)

    # Centro: bola de fuego + porcentaje de intensidad
    if intens > 0:
        glow_r = 0.08 + 0.22 * (intens / 100) ** 0.6
        glow = Circle((cx, cy), glow_r, color=FC['flame'],
                      alpha=0.65 * intens / 100, zorder=5)
        ax.add_patch(glow)

    int_color = (COLORS['danger']  if intens > 75 else
                 COLORS['secondary'] if intens > 35 else
                 COLORS['warning'] if intens > 0 else COLORS['anchor'])
    ax.text(cx, cy + 0.10, f'{intens:.0f}%', ha='center', va='center',
            fontsize=32, fontweight='bold', color=int_color, zorder=6)
    ax.text(cx, cy - 0.11, 'Intensidad', ha='center', va='center',
            fontsize=9, color=COLORS['text'], alpha=0.8, zorder=6)

    # 4° elemento: reacción en cadena
    ax.text(cx, -0.82,
            '◈  Tetraedro: + REACCIÓN EN CADENA  ◈',
            ha='center', va='center', fontsize=9,
            color=COLORS['primary'], style='italic', zorder=5)

    # Estado del fuego
    status, sc = fire_status(intens)
    ax.text(cx, 1.28, status, ha='center', va='top',
            fontsize=10, fontweight='bold', color=sc, zorder=6)


# ── Panel de Extinción ────────────────────────────────────────────────────────

def draw_extinction(ax, fuel: float, oxy: float, heat: float, intens: float):
    ax.clear()
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.8, 10.5)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])

    ax.text(5, 10.2, 'MÉTODOS DE EXTINCIÓN',
            ha='center', va='top', fontsize=13, fontweight='bold',
            color=COLORS['text'])
    ax.text(5, 9.55,
            'Eliminar cualquier vértice del tetraedro extingue el fuego',
            ha='center', va='top', fontsize=8.5,
            color=COLORS['anchor'], style='italic')

    active_fuel  = fuel < 20
    active_oxy   = oxy  < MIN_COMBUSTION_O2
    active_heat  = heat < 20

    methods = [
        (
            'RETIRAR COMBUSTIBLE',
            'Desalojo, cortafuegos, derribo controlado,\ncierre de válvulas de gas',
            COLORS['warning'], active_fuel,
            f'Combustible: {fuel:.0f} %  →  umbral extinción < 20 %',
        ),
        (
            'ELIMINAR OXÍGENO  (sufocar)',
            'Espuma, CO₂, polvo, mantas ignífugas,\ncierre de ventilación',
            COLORS['info'], active_oxy,
            f'O₂: {oxy:.1f} %  →  combustión se apaga < {MIN_COMBUSTION_O2:.0f} %',
        ),
        (
            'ENFRIAR POR DEBAJO DE T_ign',
            'Agua / chorro nebulizado, agentes\nrefrigerantes (espuma AFFF)',
            COLORS['danger'], active_heat,
            f'Calor: {heat:.0f} %  →  umbral extinción < 20 %',
        ),
        (
            'ROMPER REACCIÓN EN CADENA',
            'Halones (Halon 1301/1211), polvo BC/ABC,\ninhibidores químicos',
            COLORS['primary'], False,
            'Actúa sobre el 4° elemento — independiente de temperatura',
        ),
    ]

    for i, (title, desc, color, active, info) in enumerate(methods):
        y_top = 8.7 - i * 2.35
        bg    = color if active else COLORS['panel']
        rect  = FancyBboxPatch((0.2, y_top - 1.6), 9.6, 1.85,
                               boxstyle='round,pad=0.12',
                               edgecolor=color, linewidth=1.8,
                               facecolor=bg, alpha=0.85 if active else 0.32,
                               zorder=2)
        ax.add_patch(rect)
        ax.text(0.65, y_top - 0.35, title,
                fontsize=9.5, fontweight='bold', color=color,
                va='center', zorder=3)
        ax.text(0.65, y_top - 0.82, desc,
                fontsize=8, color=COLORS['text'],
                va='center', alpha=0.88, zorder=3)
        ax.text(0.65, y_top - 1.32, info,
                fontsize=7.5, color=COLORS['anchor'],
                va='center', zorder=3)
        if active:
            ax.text(9.7, y_top - 0.7, '✓ APLICABLE',
                    ha='right', va='center', fontsize=9.5,
                    color=COLORS['accent'], fontweight='bold', zorder=3)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Triángulo del Fuego — Elementos y Métodos de Extinción',
                 fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.97)

    ax_tri = fig.add_axes([0.02, 0.19, 0.42, 0.74])
    ax_ext = fig.add_axes([0.47, 0.19, 0.50, 0.74])
    ax_tri.set_facecolor(COLORS['bg'])
    ax_ext.set_facecolor(COLORS['bg'])

    ax_sl_fuel = fig.add_axes([0.15, 0.13, 0.70, 0.025])
    ax_sl_oxy  = fig.add_axes([0.15, 0.09, 0.70, 0.025])
    ax_sl_heat = fig.add_axes([0.15, 0.05, 0.70, 0.025])

    for ax_sl in (ax_sl_fuel, ax_sl_oxy, ax_sl_heat):
        ax_sl.set_facecolor(COLORS['panel'])

    sl_fuel = Slider(ax_sl_fuel, 'Combustible %', 0, 100, valinit=80,
                     color=COLORS['warning'], valstep=1)
    sl_oxy  = Slider(ax_sl_oxy,  'Oxígeno %',     0, 21,  valinit=21,
                     color=COLORS['info'],    valstep=0.5)
    sl_heat = Slider(ax_sl_heat, 'Calor %',       0, 100, valinit=80,
                     color=COLORS['danger'],  valstep=1)

    def update(_=None):
        fuel   = sl_fuel.val
        oxy    = sl_oxy.val
        heat   = sl_heat.val
        intens = calc_intensity(fuel, oxy, heat)
        draw_triangle(ax_tri, fuel, oxy, heat, intens)
        draw_extinction(ax_ext, fuel, oxy, heat, intens)
        fig.canvas.draw_idle()

    sl_fuel.on_changed(update)
    sl_oxy.on_changed(update)
    sl_heat.on_changed(update)
    update()
    plt.show()


if __name__ == '__main__':
    main()
