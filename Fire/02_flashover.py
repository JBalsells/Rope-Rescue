"""
02_flashover.py
Flashover en Compartimento — Modelo t² + Correlación MQH

Modelos físicos:
  • Crecimiento del fuego:  Q(t) = α · t²  (NFPA 72 / ISO 16733)
  • Temperatura capa alta:  ΔT_g = 6.85 · [Q² / (h_k·A_T·A_v·√H_v)]^(1/3)
        h_k(t) = √(K_ρc / t)  (régimen tiempo-corto, paredes concreto/yeso)
  • Criterio de flashover:  Q_FO = 7.8·A_T + 378·A_v·√H_v  (Thomas, 1981)

Controles:
  Tiempo [s]              — avanza el desarrollo del incendio
  Velocidad crecimiento   — lento / medio / rápido / ultrarápido
  Área habitación [m²]    — tamaño de la estancia
  Apertura ventilación [m²] — tamaño total de la abertura (puerta/ventana)
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.widgets import Slider

from config import COLORS, FC, apply_mpl_style
from config import FIRE_GROWTH, FLASHOVER_TEMP, ROOM_HEIGHT, K_RHO_C, DOOR_HEIGHT

# ── Parámetros geométricos ────────────────────────────────────────────────────
H       = ROOM_HEIGHT   # 2.5 m — altura habitación
H_V     = DOOR_HEIGHT   # 2.0 m — altura ventilación (puerta)
T_AMB   = 20.0          # °C — temperatura ambiente
T_MAX   = 900.0         # °C — máximo en escala de color


# ── Física ────────────────────────────────────────────────────────────────────

def room_surfaces(A_floor: float) -> float:
    """Área total de superficies interiores de la habitación (m²)."""
    L = np.sqrt(A_floor)
    return 2 * A_floor + 4 * L * H


def q_flashover(A_T: float, A_v: float) -> float:
    """HRR de flashover — criterio de Thomas [kW]."""
    return 7.8 * A_T + 378 * A_v * np.sqrt(H_V)


def upper_layer_temp(Q: float, t: float, A_T: float, A_v: float) -> float:
    """Temperatura de la capa superior [°C] — correlación MQH."""
    if Q < 1.0 or t < 1.0:
        return T_AMB
    h_k   = np.sqrt(K_RHO_C / t) * 1e-3   # kW/(m²·K), régimen corto
    denom = h_k * A_T * A_v * np.sqrt(H_V)
    if denom < 1e-9:
        return T_AMB
    dT = 6.85 * (Q ** 2 / denom) ** (1 / 3)
    return T_AMB + min(dT, T_MAX - T_AMB)


def lower_layer_temp(T_upper: float) -> float:
    """Temperatura de la capa inferior (aprox. media ponderada)."""
    return T_AMB + max(0, (T_upper - T_AMB) * 0.08)


def interface_height(Q: float, Q_fo: float) -> float:
    """Altura de la interfaz capas fría/caliente desde el suelo [m]."""
    ratio = min(1.0, Q / max(1.0, Q_fo))
    return H * max(0.05, 1.0 - 0.85 * ratio)


def neutral_plane(h_i: float, T_upper: float) -> float:
    """Altura del plano neutral en la abertura [m] (modelo de presión)."""
    T_u = T_upper + 273.15
    T_a = T_AMB + 273.15
    h_n = h_i * (T_a / (T_a + (T_u - T_a) * 0.5)) ** 0.5
    return np.clip(h_n, 0.05, H_V)


def temp_color(T: float) -> str:
    """Color de la capa caliente según temperatura."""
    if T < 100:
        return '#555577'
    elif T < 300:
        return '#996633'
    elif T < FLASHOVER_TEMP:
        return '#CC3300'
    else:
        return '#FF1100'


def temp_alpha(T: float) -> float:
    return float(np.clip(0.25 + 0.55 * T / 700, 0.25, 0.82))


# ── Sección transversal de la habitación ─────────────────────────────────────

def draw_room(ax, t: float, alpha: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])

    Q    = alpha * t ** 2
    A_T  = room_surfaces(A_floor)
    Q_fo = q_flashover(A_T, A_v)
    T_up = upper_layer_temp(Q, t, A_T, A_v)
    T_lo = lower_layer_temp(T_up)
    h_i  = interface_height(Q, Q_fo)
    h_n  = neutral_plane(h_i, T_up)

    # Coordenadas normalizadas: ancho=3, alto=H
    W = 3.0
    ax.set_xlim(-0.15, W + 0.15)
    ax.set_ylim(-0.15, H + 0.35)
    ax.set_aspect('equal')
    ax.axis('off')

    # ── Paredes / suelo / techo
    wall_kw = dict(color=FC['wall'], lw=2.5, zorder=5)
    ax.plot([0, 0],   [0, H], **wall_kw)         # pared izq
    ax.plot([0, W],   [0, 0], **wall_kw)         # suelo
    ax.plot([0, W],   [H, H], **wall_kw)         # techo
    ax.plot([W, W],   [H_V, H], **wall_kw)       # pared der (sobre puerta)
    ax.plot([W, W],   [0, 0.02], **wall_kw)      # pared der (bajo puerta)

    # ── Zona fría (suelo → h_i)
    ax.fill_between([0, W], h_i, H,
                    color=temp_color(T_up), alpha=temp_alpha(T_up), zorder=3)
    ax.fill_between([0, W], 0, h_i,
                    color='#111133', alpha=0.25, zorder=3)

    # ── Interfaz (línea discontinua)
    ax.plot([0, W], [h_i, h_i],
            color=COLORS['warning'], lw=1.5, ls='--', alpha=0.85, zorder=6)

    # ── Llamas (fuente de fuego en el suelo)
    flame_h = min(h_i * 0.85, 0.05 + 0.55 * (Q / max(1, Q_fo)) ** 0.5)
    flame_xs = [0.4, 0.8, 1.2, 1.6, 2.0]
    for j, xc in enumerate(flame_xs):
        fh = flame_h * (0.7 + 0.3 * np.sin(j * 1.3))
        fw = 0.12
        inner_col = '#FFFF00' if T_up > FLASHOVER_TEMP else '#FFCC00'
        outer_col = '#FF4400' if T_up > FLASHOVER_TEMP else '#FF6600'
        ax.fill([xc - fw, xc, xc + fw], [0, fh * 0.8, 0],
                color=inner_col, alpha=0.95, zorder=7)
        ax.fill([xc - fw * 1.5, xc, xc + fw * 1.5], [0, fh, 0],
                color=outer_col, alpha=0.7, zorder=7)

    # ── Flujo por la puerta (flechas)
    # Entrada de aire frío (por debajo del plano neutral)
    if h_n > 0.12:
        ax.annotate('', xy=(W - 0.01, h_n * 0.4),
                    xytext=(W + 0.12, h_n * 0.4),
                    arrowprops=dict(arrowstyle='->', color=COLORS['info'],
                                   lw=1.5), zorder=8)
        ax.text(W + 0.13, h_n * 0.4, 'aire',
                fontsize=7, color=COLORS['info'], va='center')
    # Salida de humo (por encima del plano neutral)
    if H_V - h_n > 0.15:
        ax.annotate('', xy=(W + 0.12, h_n + (H_V - h_n) * 0.6),
                    xytext=(W - 0.01, h_n + (H_V - h_n) * 0.6),
                    arrowprops=dict(arrowstyle='->', color=FC['smoke'],
                                   lw=1.5), zorder=8)
        ax.text(W + 0.13, h_n + (H_V - h_n) * 0.6, 'humo',
                fontsize=7, color=FC['smoke'], va='center')

    # ── Plano neutral
    ax.plot([W - 0.02, W + 0.02], [h_n, h_n],
            color=FC['neutral'], lw=2, zorder=9)

    # ── Anotaciones de temperatura
    ax.text(0.12, (h_i + H) / 2,
            f'T_sup\n{T_up:.0f} °C',
            fontsize=7.5, color=COLORS['text'], va='center', zorder=8,
            bbox=dict(boxstyle='round,pad=0.25', fc='#00000055', ec='none'))
    ax.text(0.12, h_i * 0.45,
            f'T_inf\n{T_lo:.0f} °C',
            fontsize=7.5, color=COLORS['text'], va='center', zorder=8,
            bbox=dict(boxstyle='round,pad=0.25', fc='#00000055', ec='none'))

    # ── Interfaz y plano neutral etiquetados
    ax.text(W * 0.5, h_i + 0.06, f'Interfaz  h={h_i:.2f} m',
            fontsize=7.5, color=COLORS['warning'], ha='center', zorder=8)
    ax.text(-0.1, h_n, f'NP\n{h_n:.2f}m',
            fontsize=6.5, color=FC['neutral'], ha='right', va='center', zorder=8)

    # ── Título del panel
    phase_str, phase_col = flashover_phase(T_up)
    ax.set_title(f'Sección habitación  —  t = {t:.0f} s     Q = {Q:.0f} kW\n'
                 f'Q_FO = {Q_fo:.0f} kW  |  {phase_str}',
                 fontsize=9, color=phase_col, pad=4)


# ── Curva T(t) ────────────────────────────────────────────────────────────────

def draw_temp_curve(ax, t_now: float, alpha: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])

    A_T  = room_surfaces(A_floor)
    Q_fo = q_flashover(A_T, A_v)

    t_arr = np.linspace(1, 600, 400)
    Q_arr = alpha * t_arr ** 2
    T_arr = np.array([upper_layer_temp(q, t, A_T, A_v)
                      for q, t in zip(Q_arr, t_arr)])
    T_lo  = np.array([lower_layer_temp(tu) for tu in T_arr])

    # Zonas sombreadas por fase
    ax.axhspan(0, 200, color='#1122AA', alpha=0.07)
    ax.axhspan(200, FLASHOVER_TEMP, color='#AA4400', alpha=0.07)
    ax.axhspan(FLASHOVER_TEMP, T_MAX, color='#CC0000', alpha=0.10)

    ax.axhline(FLASHOVER_TEMP, color=COLORS['danger'], lw=1.5,
               ls='--', alpha=0.85, label=f'Flashover {FLASHOVER_TEMP:.0f} °C')

    ax.plot(t_arr, T_arr, color=FC['flame'], lw=2.0, label='T capa superior')
    ax.plot(t_arr, T_lo,  color=COLORS['info'],    lw=1.0,
            ls=':', alpha=0.7, label='T capa inferior')

    # Cursor de tiempo actual
    Q_now = alpha * t_now ** 2
    T_now = upper_layer_temp(Q_now, t_now, A_T, A_v)
    ax.axvline(t_now, color=COLORS['primary'], lw=1.2, alpha=0.7)
    ax.plot(t_now, T_now, 'o', color=COLORS['primary'], ms=7, zorder=6)

    # Anotación de temperatura actual
    ax.annotate(f'{T_now:.0f} °C',
                xy=(t_now, T_now), xytext=(t_now + 25, T_now + 25),
                fontsize=8, color=COLORS['primary'],
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1))

    # Etiquetas de fase
    ax.text(10, 80,   'INCIPIENTE',         fontsize=7.5, color=COLORS['info'],    alpha=0.75)
    ax.text(10, 380,  'DESARROLLO',         fontsize=7.5, color=COLORS['warning'], alpha=0.75)
    ax.text(10, FLASHOVER_TEMP + 30,
                      'POST-FLASHOVER',     fontsize=7.5, color=COLORS['danger'],  alpha=0.75)

    ax.set_xlabel('Tiempo (s)', fontsize=8)
    ax.set_ylabel('Temperatura (°C)', fontsize=8)
    ax.set_xlim(0, 600)
    ax.set_ylim(0, T_MAX)
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.5, loc='upper left',
              facecolor=COLORS['panel'], edgecolor=COLORS['grid'])
    ax.set_title('Temperatura capa superior vs Tiempo', fontsize=9,
                 color=COLORS['text'], pad=3)


# ── Panel de Estado ───────────────────────────────────────────────────────────

def flashover_phase(T_up: float) -> tuple[str, str]:
    if T_up < 100:
        return 'Fase Incipiente', COLORS['info']
    elif T_up < FLASHOVER_TEMP:
        return 'Fase de Desarrollo', COLORS['warning']
    else:
        return '⚠ FLASHOVER', COLORS['danger']


def draw_info(ax, t_now: float, alpha: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['panel'])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    A_T    = room_surfaces(A_floor)
    Q_fo   = q_flashover(A_T, A_v)
    Q_now  = alpha * t_now ** 2
    T_now  = upper_layer_temp(Q_now, t_now, A_T, A_v)
    phase, pc = flashover_phase(T_now)

    # Tiempo al flashover
    if alpha > 0:
        t_fo = np.sqrt(Q_fo / alpha)
        t_remaining = t_fo - t_now
    else:
        t_fo = float('inf')
        t_remaining = float('inf')

    rows = [
        ('Q actual',       f'{Q_now:.0f} kW',        COLORS['warning']),
        ('Q flashover',    f'{Q_fo:.0f} kW',          COLORS['danger']),
        ('T capa superior',f'{T_now:.0f} °C',         COLORS['secondary']),
        ('Fase',           phase,                      pc),
        ('Tiempo al FO',
         f'{t_remaining:.0f} s' if t_remaining > 0 else 'SUPERADO',
         COLORS['danger'] if t_remaining <= 0 else COLORS['accent']),
    ]
    y = 9.2
    for label, val, color in rows:
        ax.text(0.5, y, label + ':', fontsize=8.5, color=COLORS['anchor'],
                va='center')
        ax.text(9.5, y, val, fontsize=8.5, color=color,
                va='center', ha='right', fontweight='bold')
        y -= 1.75


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Flashover en Compartimento — Modelo t²  +  Correlación MQH',
                 fontsize=19, fontweight='bold', color=COLORS['primary'], y=0.97)

    ax_room = fig.add_axes([0.02, 0.22, 0.40, 0.67])
    ax_temp = fig.add_axes([0.47, 0.42, 0.50, 0.46])
    ax_info = fig.add_axes([0.47, 0.22, 0.50, 0.17])

    ax_sl_t    = fig.add_axes([0.15, 0.16, 0.70, 0.025])
    ax_sl_grow = fig.add_axes([0.15, 0.12, 0.70, 0.025])
    ax_sl_area = fig.add_axes([0.15, 0.08, 0.70, 0.025])
    ax_sl_vent = fig.add_axes([0.15, 0.04, 0.70, 0.025])

    for ax_sl in (ax_sl_t, ax_sl_grow, ax_sl_area, ax_sl_vent):
        ax_sl.set_facecolor(COLORS['panel'])

    sl_t    = Slider(ax_sl_t,    'Tiempo (s)',         1,  600, valinit=60,
                     color=COLORS['primary'], valstep=1)
    sl_grow = Slider(ax_sl_grow, 'Crecimiento (0=lento…3=ultrarápido)',
                     0, 3, valinit=2, color=COLORS['warning'], valstep=1)
    sl_area = Slider(ax_sl_area, 'Área habitación (m²)', 10, 50, valinit=20,
                     color=COLORS['info'],    valstep=1)
    sl_vent = Slider(ax_sl_vent, 'Vent. (m²)',         0.5, 3.0, valinit=1.5,
                     color=FC['smoke'],       valstep=0.1)

    def update(_=None):
        t_now  = sl_t.val
        idx    = int(sl_grow.val)
        label, alpha = FIRE_GROWTH[idx]
        A_floor = sl_area.val
        A_v     = sl_vent.val

        # Actualizar etiqueta del slider de crecimiento
        ax_sl_grow.set_xlabel(
            f'Crecimiento: {label}  (α={alpha:.5f} kW/s²)', fontsize=8,
            color=COLORS['text'])

        draw_room(ax_room, t_now, alpha, A_floor, A_v)
        draw_temp_curve(ax_temp, t_now, alpha, A_floor, A_v)
        draw_info(ax_info, t_now, alpha, A_floor, A_v)
        fig.canvas.draw_idle()

    sl_t.on_changed(update)
    sl_grow.on_changed(update)
    sl_area.on_changed(update)
    sl_vent.on_changed(update)
    update()
    plt.show()


if __name__ == '__main__':
    main()
