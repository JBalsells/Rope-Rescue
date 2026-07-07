"""
03_propagacion_incendio.py
Propagación del Incendio Forestal — Modelo Rothermel Simplificado

Modelos físicos:
  • Tasa de propagación (ROS):
        R = R₀ · (1 + φ_viento + φ_pendiente) / ξ_humedad
        φ_viento   = 0.12 · (U km/h)^1.3
        φ_pendiente= 5.275 · tan²(θ)
        ξ_humedad  = exp(0.115 · (M − 5))
  • Intensidad lineal de fuego (Byram, 1965):
        I_B = H · w · R / 60   [kW/m]
  • Longitud de llama (Byram, 1966):
        L_f = 0.0775 · I_B^0.46   [m]
  • Altura de la columna de humo (modelo Watson):
        H_s ≈ 235 · I_B^0.24      [m]

Controles:
  Velocidad viento  — U [km/h], en la dirección de la pendiente
  Pendiente         — θ [°]
  Humedad combustible — M [%], fuelles de 10 h
  Tipo de combustible — escalar de carga de combustible
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.widgets import Slider

from config import COLORS, FC, apply_mpl_style

# ── Combustibles ──────────────────────────────────────────────────────────────
FUEL_TYPES = {
    0: ('Pasto seco',     0.5,  17000, '#C8B560'),
    1: ('Matorral',       1.2,  18500, '#6B8E23'),
    2: ('Monte bajo',     2.0,  19000, '#4A6741'),
    3: ('Bosque (hojas)', 3.0,  19500, '#2D5016'),
}
# Tasa base de propagación por tipo de combustible (m/min, plano, sin viento, M=5%)
ROS_BASE = {0: 0.06, 1: 0.045, 2: 0.032, 3: 0.022}


# ── Física ────────────────────────────────────────────────────────────────────

def rate_of_spread(U_kph: float, slope_deg: float,
                   moisture_pct: float, fuel_idx: int) -> float:
    """Tasa de propagación [m/min]. Modelo Rothermel simplificado."""
    R0      = ROS_BASE[fuel_idx]
    phi_w   = 0.12 * (max(0.0, U_kph)) ** 1.3
    theta   = np.radians(slope_deg)
    phi_s   = 5.275 * np.tan(theta) ** 2
    xi_m    = np.exp(0.115 * (moisture_pct - 5.0))
    return max(0.001, R0 * (1.0 + phi_w + phi_s) / xi_m)


def fire_intensity(ROS: float, fuel_idx: int) -> float:
    """Intensidad lineal de Byram [kW/m]."""
    _, w, H, _ = FUEL_TYPES[fuel_idx]
    return H * w * (ROS / 60.0)     # H kJ/kg, w kg/m², ROS m/s


def flame_length(I_B: float) -> float:
    """Longitud de llama de Byram (1966) [m]."""
    return 0.0775 * max(0.0, I_B) ** 0.46


def smoke_column_height(I_B: float) -> float:
    """Altura aproximada de la columna de humo [m]."""
    return 235.0 * max(0.0, I_B) ** 0.24


def ros_category(ROS: float) -> tuple[str, str]:
    if ROS < 0.5:
        return 'BAJA', COLORS['accent']
    elif ROS < 3.0:
        return 'MODERADA', COLORS['warning']
    elif ROS < 10.0:
        return 'ALTA', COLORS['secondary']
    else:
        return 'EXTREMA — INCONTROLABLE', COLORS['danger']


# ── Diagrama de terreno ───────────────────────────────────────────────────────

def draw_terrain(ax, U_kph: float, slope_deg: float,
                 moisture_pct: float, fuel_idx: int):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])
    ax.axis('off')

    ROS   = rate_of_spread(U_kph, slope_deg, moisture_pct, fuel_idx)
    I_B   = fire_intensity(ROS, fuel_idx)
    L_f   = flame_length(I_B)
    H_s   = smoke_column_height(I_B)

    name, w, H_fuel, veg_color = FUEL_TYPES[fuel_idx]

    # ── Perfil de terreno con pendiente
    theta  = np.radians(slope_deg)
    x_len  = 3.0                     # unidades horizontales
    y_rise = x_len * np.tan(theta)

    ax.set_xlim(-0.3, x_len + 0.3)
    ax.set_ylim(-0.3, max(2.5, y_rise + 2.0))
    ax.set_aspect('equal')

    xs = np.array([0.0, x_len])
    ys = np.array([0.0, y_rise])

    # Suelo (relleno)
    ax.fill([0, x_len, x_len, 0, 0],
            [-0.3, y_rise - 0.3, -0.3, -0.3, -0.3],
            color='#3A2E0A', alpha=0.85, zorder=1)
    ax.plot(xs, ys, color='#5A4A1A', lw=2, zorder=2)

    # Vegetación (líneas verticales desde terreno)
    veg_h = 0.08 + 0.05 * (fuel_idx + 1)
    for xi in np.linspace(0.1, x_len - 0.1, 22):
        yi = xi * np.tan(theta)
        # Variar altura por posición para efecto natural
        h = veg_h * (0.8 + 0.4 * np.sin(xi * 7))
        ax.plot([xi, xi], [yi, yi + h],
                color=veg_color, lw=1.2, alpha=0.7, zorder=3)

    # ── Frente de fuego (en x=0.6)
    x_fire = 0.6
    y_fire = x_fire * np.tan(theta)

    # Zona quemada (a la izquierda del frente)
    xs_burn = np.linspace(0, x_fire, 20)
    ys_burn = xs_burn * np.tan(theta)
    ax.fill_between(xs_burn, ys_burn - 0.3, ys_burn,
                    color=FC['char'], alpha=0.6, zorder=4)

    # Llamas (escala: L_f en unidades del gráfico, máx 1.0)
    lf_px = min(1.2, 0.10 + L_f * 0.08)
    flame_centers = np.linspace(x_fire - 0.2, x_fire + 0.05, 5)
    for j, xc in enumerate(flame_centers):
        yc   = xc * np.tan(theta)
        fh   = lf_px * (0.6 + 0.4 * np.sin(j * 1.7))
        fw   = 0.07
        col1 = '#FFFF00' if I_B > 5000 else '#FFCC00'
        col2 = '#FF3300' if I_B > 5000 else '#FF6600'
        ax.fill([xc - fw, xc, xc + fw], [yc, yc + fh * 0.7, yc],
                color=col1, alpha=0.9, zorder=6)
        ax.fill([xc - fw * 1.6, xc, xc + fw * 1.6], [yc, yc + fh, yc],
                color=col2, alpha=0.65, zorder=5)

    # Columna de humo (simplificada)
    smoke_h_px = min(1.8, H_s * 0.004)
    ax.fill_betweenx(
        np.linspace(y_fire + lf_px, y_fire + lf_px + smoke_h_px, 20),
        x_fire - 0.25, x_fire + 0.25,
        color=FC['smoke'], alpha=0.30, zorder=4)

    # ── Flechas de viento
    if U_kph > 0:
        n_arrows = min(4, max(1, int(U_kph / 15)))
        for k in range(n_arrows):
            y_arr = y_rise + 0.4 + k * 0.12
            ax.annotate('', xy=(x_fire + 0.05 + 0.25 * n_arrows / 4,
                                y_arr + k * 0.04),
                        xytext=(x_fire - 0.5, y_arr + k * 0.04),
                        arrowprops=dict(arrowstyle='->', color=COLORS['primary'],
                                        lw=1.2 + k * 0.1))
        ax.text(x_fire - 0.55, y_rise + 0.55,
                f'Viento\n{U_kph:.0f} km/h',
                fontsize=7.5, color=COLORS['primary'], ha='right', va='center')

    # ── Ángulo de pendiente
    if slope_deg > 3:
        arc_x = np.linspace(0, np.radians(slope_deg), 20)
        arc_r = 0.35
        ax.plot(arc_r * np.cos(arc_x), arc_r * np.sin(arc_x),
                color=COLORS['anchor'], lw=1, alpha=0.7)
        ax.text(0.38, 0.10, f'{slope_deg:.0f}°',
                fontsize=7.5, color=COLORS['anchor'])

    # ── Etiquetas
    cat, cat_col = ros_category(ROS)
    ax.set_title(
        f'Frente de fuego — {name}\n'
        f'ROS = {ROS:.2f} m/min  |  I_B = {I_B:.0f} kW/m  |  '
        f'L_llama = {L_f:.1f} m  |  Peligrosidad: {cat}',
        fontsize=8.5, color=cat_col, pad=3)


# ── Curva ROS vs viento ───────────────────────────────────────────────────────

def draw_ros_curve(ax, U_kph: float, slope_deg: float,
                   moisture_pct: float, fuel_idx: int):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])

    U_arr = np.linspace(0, 80, 200)
    R_arr = np.array([rate_of_spread(u, slope_deg, moisture_pct, fuel_idx)
                      for u in U_arr])
    R_cur = rate_of_spread(U_kph, slope_deg, moisture_pct, fuel_idx)

    # Zonas de peligro
    ax.axhspan(0,    0.5,  color=COLORS['accent'],    alpha=0.08)
    ax.axhspan(0.5,  3.0,  color=COLORS['warning'],   alpha=0.08)
    ax.axhspan(3.0,  10.0, color=COLORS['secondary'], alpha=0.08)
    ax.axhspan(10.0, 30.0, color=COLORS['danger'],    alpha=0.10)

    ax.plot(U_arr, R_arr, color=FC['flame'], lw=2.0,
            label=f'Pendiente {slope_deg:.0f}°, M={moisture_pct:.0f}%')
    ax.axvline(U_kph, color=COLORS['primary'], lw=1.2, alpha=0.7)
    ax.plot(U_kph, R_cur, 'o', color=COLORS['primary'], ms=8, zorder=5)
    ax.annotate(f'{R_cur:.2f} m/min',
                xy=(U_kph, R_cur), xytext=(U_kph + 5, R_cur + 0.3),
                fontsize=8, color=COLORS['primary'],
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1))

    # Etiquetas de zona
    ax.text(1, 0.18, 'BAJA',   fontsize=7.5, color=COLORS['accent'],    alpha=0.8)
    ax.text(1, 1.0,  'MODERADA', fontsize=7.5, color=COLORS['warning'], alpha=0.8)
    ax.text(1, 4.5,  'ALTA',   fontsize=7.5, color=COLORS['secondary'], alpha=0.8)
    ax.text(1, 12,   'EXTREMA', fontsize=7.5, color=COLORS['danger'],   alpha=0.8)

    ax.set_xlabel('Velocidad del viento (km/h)', fontsize=8)
    ax.set_ylabel('Tasa de propagación (m/min)', fontsize=8)
    ax.set_xlim(0, 80)
    ax.set_ylim(0, max(20, R_arr.max() * 1.15))
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.5, facecolor=COLORS['panel'], edgecolor=COLORS['grid'])
    ax.set_title('ROS vs Velocidad del Viento', fontsize=9,
                 color=COLORS['text'], pad=3)


# ── Panel de Valores ──────────────────────────────────────────────────────────

def draw_values(ax, U_kph: float, slope_deg: float,
                moisture_pct: float, fuel_idx: int):
    ax.clear()
    ax.set_facecolor(COLORS['panel'])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    ROS  = rate_of_spread(U_kph, slope_deg, moisture_pct, fuel_idx)
    I_B  = fire_intensity(ROS, fuel_idx)
    L_f  = flame_length(I_B)
    H_s  = smoke_column_height(I_B)
    cat, cc = ros_category(ROS)
    name = FUEL_TYPES[fuel_idx][0]

    rows = [
        ('Combustible',       name,              COLORS['warning']),
        ('ROS',               f'{ROS:.3f} m/min',  COLORS['secondary']),
        ('Intens. Byram',     f'{I_B:.0f} kW/m',   COLORS['danger']),
        ('Long. llama',       f'{L_f:.1f} m',        FC['flame']),
        ('Col. humo',         f'{H_s:.0f} m',        FC['smoke']),
        ('Peligrosidad',      cat,               cc),
    ]
    y = 9.2
    for label, val, color in rows:
        ax.text(0.5, y, label + ':', fontsize=8, color=COLORS['anchor'],
                va='center')
        ax.text(9.5, y, val, fontsize=8, color=color,
                va='center', ha='right', fontweight='bold')
        y -= 1.50


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Propagación del Incendio Forestal — Modelo Rothermel Simplificado',
                 fontsize=18, fontweight='bold', color=COLORS['primary'], y=0.97)

    ax_terrain = fig.add_axes([0.02, 0.19, 0.42, 0.72])
    ax_ros     = fig.add_axes([0.47, 0.38, 0.50, 0.52])
    ax_vals    = fig.add_axes([0.47, 0.19, 0.50, 0.16])

    ax_sl_wind  = fig.add_axes([0.15, 0.13, 0.70, 0.025])
    ax_sl_slope = fig.add_axes([0.15, 0.09, 0.70, 0.025])
    ax_sl_moist = fig.add_axes([0.15, 0.05, 0.70, 0.025])

    for ax_sl in (ax_sl_wind, ax_sl_slope, ax_sl_moist):
        ax_sl.set_facecolor(COLORS['panel'])

    sl_wind  = Slider(ax_sl_wind,  'Viento (km/h)',          0,  80, valinit=20,
                      color=COLORS['primary'], valstep=1)
    sl_slope = Slider(ax_sl_slope, 'Pendiente (°)',           0,  45, valinit=15,
                      color=COLORS['warning'], valstep=1)
    sl_moist = Slider(ax_sl_moist, 'Humedad combustible (%)', 3,  30, valinit=8,
                      color=COLORS['info'],    valstep=1)

    # Selector de combustible usando un slider discreto (0-3)
    ax_sl_fuel = fig.add_axes([0.86, 0.36, 0.02, 0.15])
    ax_sl_fuel.set_facecolor(COLORS['panel'])
    sl_fuel = Slider(ax_sl_fuel, 'Comb.', 0, 3, valinit=0,
                     color=FC['terrain'], valstep=1, orientation='vertical')

    def update(_=None):
        U     = sl_wind.val
        theta = sl_slope.val
        M     = sl_moist.val
        fi    = int(sl_fuel.val)
        draw_terrain(ax_terrain, U, theta, M, fi)
        draw_ros_curve(ax_ros, U, theta, M, fi)
        draw_values(ax_vals, U, theta, M, fi)
        # Mostrar nombre del combustible seleccionado
        ax_sl_fuel.set_title(FUEL_TYPES[fi][0][:8], fontsize=7,
                             color=COLORS['text'])
        fig.canvas.draw_idle()

    sl_wind.on_changed(update)
    sl_slope.on_changed(update)
    sl_moist.on_changed(update)
    sl_fuel.on_changed(update)
    update()
    plt.show()


if __name__ == '__main__':
    main()
