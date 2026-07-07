"""
04_capas_termicas.py
Capas Térmicas y Plano Neutral en Incendio Estructural

Modelo de dos zonas (Two-Zone Model):
  • Zona superior (capa caliente): gases de combustión + humo
  • Zona inferior (capa fría): aire ambiente con temperatura casi normal

Física:
  • Temperatura capa superior [MQH, régimen cuasi-estático]:
        ΔT_sup = 6.85 · [Q² / (h_k · A_T · A_v · √H_v)]^(1/3)
        h_k = √(K_ρc / t_ref)  (usamos t_ref = 120 s como referencia)
  • Altura de la interfaz (modelo de Zukoski simplificado):
        h_i = H · max(0.05, 1 − 0.9 · Q/Q_FO)
  • Plano neutral (abertura, modelo de presión estática):
        h_n = h_i · [T_amb / (T_amb + ΔT_mix)]^0.5
  • Perfil de temperatura por altura (gradiente lineal en cada zona):
        T(z) = T_inf                  si z < h_i
        T(z) = T_inf + (T_sup − T_inf) · (z − h_i)/(H − h_i)  si z ≥ h_i

Zonas de peligro para bomberos (NFPA 1582):
  • T > 60 °C  → equipo SCBA obligatorio
  • T > 100 °C → riesgo de quemaduras (30 min)
  • T > 250 °C → peligro inmediato para la vida (IDLH)
  • T > 600 °C → flashover, evacuación inmediata

Controles:
  HRR (kW)              — potencia calorífica del incendio
  Área habitación (m²)  — tamaño del compartimento
  Apertura vent. (m²)   — área total de la abertura
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.widgets import Slider

from config import COLORS, FC, apply_mpl_style
from config import FLASHOVER_TEMP, ROOM_HEIGHT, K_RHO_C, DOOR_HEIGHT

# ── Parámetros fijos ──────────────────────────────────────────────────────────
H     = ROOM_HEIGHT    # 2.5 m
H_V   = DOOR_HEIGHT    # 2.0 m
T_AMB = 20.0           # °C
T_REF = 120.0          # s — tiempo de referencia para h_k cuasi-estático
SCBA_LIMIT   = 60.0    # °C — límite SCBA
BURN_LIMIT   = 100.0   # °C — quemaduras significativas
IDLH_LIMIT   = 250.0   # °C — IDLH inmediato
FLASHOVER_T  = FLASHOVER_TEMP  # 600 °C


# ── Física ────────────────────────────────────────────────────────────────────

def room_surfaces(A_floor: float) -> float:
    L = np.sqrt(A_floor)
    return 2 * A_floor + 4 * L * H


def q_flashover(A_T: float, A_v: float) -> float:
    return 7.8 * A_T + 378.0 * A_v * np.sqrt(H_V)


def upper_temp(Q: float, A_T: float, A_v: float) -> float:
    """Temperatura capa superior [°C] — MQH cuasi-estático."""
    if Q < 1.0:
        return T_AMB
    h_k   = np.sqrt(K_RHO_C / T_REF) * 1e-3   # kW/(m²·K)
    denom = h_k * A_T * A_v * np.sqrt(H_V)
    if denom < 1e-9:
        return T_AMB
    dT = 6.85 * (Q ** 2 / denom) ** (1 / 3)
    return T_AMB + min(dT, 900.0)


def interface_height(Q: float, Q_fo: float) -> float:
    ratio = min(1.0, Q / max(1.0, Q_fo))
    return H * max(0.05, 1.0 - 0.9 * ratio)


def neutral_plane_height(h_i: float, T_sup: float) -> float:
    T_s = T_sup + 273.15
    T_a = T_AMB + 273.15
    h_n = h_i * np.sqrt(T_a / T_s)
    return float(np.clip(h_n, 0.05, H_V - 0.05))


def temp_profile(z_arr: np.ndarray, h_i: float,
                 T_sup: float, T_inf: float) -> np.ndarray:
    """Perfil de temperatura por altura [°C]."""
    T = np.where(
        z_arr < h_i,
        T_inf,
        T_inf + (T_sup - T_inf) * (z_arr - h_i) / max(H - h_i, 0.01)
    )
    return T


def safe_height(T_profile: np.ndarray, z_arr: np.ndarray,
                limit: float) -> float:
    """Altura hasta la que T < limit [m]."""
    idx = np.searchsorted(T_profile, limit)
    return float(z_arr[idx]) if idx < len(z_arr) else H


# ── Sección transversal ───────────────────────────────────────────────────────

def draw_room(ax, Q: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])
    ax.axis('off')

    A_T  = room_surfaces(A_floor)
    Q_fo = q_flashover(A_T, A_v)
    T_su = upper_temp(Q, A_T, A_v)
    T_lo = T_AMB + max(0, (T_su - T_AMB) * 0.06)
    h_i  = interface_height(Q, Q_fo)
    h_n  = neutral_plane_height(h_i, T_su)

    W = 2.8
    ax.set_xlim(-0.25, W + 0.35)
    ax.set_ylim(-0.2, H + 0.6)
    ax.set_aspect('equal')

    # ── Gradiente de temperatura en la capa caliente
    # Dividir la capa superior en franjas con color progresivo
    n_strips = 30
    y_tops   = np.linspace(h_i, H, n_strips + 1)
    for k in range(n_strips):
        t_frac  = (y_tops[k] - h_i) / max(H - h_i, 0.01)
        T_strip = T_lo + (T_su - T_lo) * t_frac
        r = int(np.clip(180 + 75 * t_frac, 0, 255))
        g = int(np.clip(80  - 70 * t_frac, 0, 255))
        b = int(np.clip(20  - 15 * t_frac, 0, 255))
        alpha = 0.25 + 0.50 * t_frac
        ax.fill_between([0, W], y_tops[k], y_tops[k + 1],
                        color=(r / 255, g / 255, b / 255),
                        alpha=alpha, zorder=3)

    # Capa fría (azul tenue)
    ax.fill_between([0, W], 0, h_i,
                    color='#112244', alpha=0.30, zorder=3)

    # ── Paredes
    wc = FC['wall']
    ax.plot([0, 0],  [0, H],     color=wc, lw=3, zorder=6)
    ax.plot([0, W],  [0, 0],     color=wc, lw=3, zorder=6)
    ax.plot([0, W],  [H, H],     color=wc, lw=3, zorder=6)
    ax.plot([W, W],  [H_V, H],   color=wc, lw=3, zorder=6)
    ax.plot([W, W],  [0, 0.02],  color=wc, lw=3, zorder=6)

    # ── Llamas
    Q_ratio   = min(1.0, Q / max(1.0, Q_fo))
    flame_h   = max(0.02, min(h_i * 0.8, 0.05 + 0.55 * Q_ratio))
    for j, xc in enumerate(np.linspace(0.35, W - 0.35, 5)):
        fh  = flame_h * (0.7 + 0.3 * np.sin(j * 1.4))
        fw  = 0.09
        c1  = '#FFFF44' if T_su > FLASHOVER_T else '#FFDD00'
        c2  = '#FF2200' if T_su > FLASHOVER_T else '#FF5500'
        ax.fill([xc - fw, xc, xc + fw], [0, fh * 0.7, 0],
                color=c1, alpha=0.95, zorder=7)
        ax.fill([xc - fw * 1.5, xc, xc + fw * 1.5], [0, fh, 0],
                color=c2, alpha=0.65, zorder=7)

    # ── Interfaz (línea)
    ax.plot([0, W], [h_i, h_i], color=COLORS['warning'],
            lw=2, ls='--', alpha=0.9, zorder=8)

    # ── Plano neutral (en la abertura)
    ax.plot([W - 0.03, W + 0.03], [h_n, h_n],
            color=FC['neutral'], lw=2.5, zorder=9)

    # ── Zona SCBA (línea de seguridad)
    z_arr     = np.linspace(0, H, 500)
    T_arr     = temp_profile(z_arr, h_i, T_su, T_lo)
    z_safe    = safe_height(T_arr, z_arr, SCBA_LIMIT)
    if z_safe < H:
        ax.plot([0.05, W - 0.05], [z_safe, z_safe],
                color=COLORS['accent'], lw=1.5, ls=':', alpha=0.8, zorder=8)
        ax.text(0.1, z_safe + 0.04, f'SCBA  {z_safe:.2f} m',
                fontsize=7, color=COLORS['accent'], zorder=9)

    # ── Silueta del bombero (altura 1.8 m)
    bx = 1.0
    bh = 1.80
    # Casco
    ax.add_patch(plt.Circle((bx, bh + 0.07), 0.07,
                             color=COLORS['warning'], zorder=10, alpha=0.9))
    # Cuerpo
    ax.plot([bx, bx], [bh - 0.5, bh], color=COLORS['warning'],
            lw=5, zorder=10, alpha=0.9)
    # Piernas
    ax.plot([bx - 0.08, bx], [bh - 1.0, bh - 0.5],
            color=COLORS['warning'], lw=3, zorder=10, alpha=0.9)
    ax.plot([bx + 0.08, bx], [bh - 1.0, bh - 0.5],
            color=COLORS['warning'], lw=3, zorder=10, alpha=0.9)
    # ¿en zona peligrosa?
    T_head = temp_profile(np.array([bh]), h_i, T_su, T_lo)[0]
    head_ok = T_head < IDLH_LIMIT
    ax.text(bx, bh + 0.24,
            f'{T_head:.0f}°C',
            ha='center', fontsize=7, zorder=11,
            color=COLORS['accent'] if head_ok else COLORS['danger'])

    # ── Flechas de flujo en puerta
    if h_n > 0.12:
        ax.annotate('', xy=(W - 0.01, h_n * 0.45),
                    xytext=(W + 0.25, h_n * 0.45),
                    arrowprops=dict(arrowstyle='->', color=COLORS['info'], lw=1.5),
                    zorder=9)
    if H_V - h_n > 0.15:
        ax.annotate('', xy=(W + 0.25, h_n + (H_V - h_n) * 0.55),
                    xytext=(W - 0.01, h_n + (H_V - h_n) * 0.55),
                    arrowprops=dict(arrowstyle='->', color=FC['smoke'], lw=1.5),
                    zorder=9)

    # ── Etiquetas temperatura
    ax.text(0.1, (h_i + H) / 2,
            f'T_sup = {T_su:.0f} °C',
            fontsize=7.5, color=COLORS['text'], va='center', zorder=10,
            bbox=dict(boxstyle='round,pad=0.2', fc='#00000055', ec='none'))
    ax.text(0.1, h_i * 0.4,
            f'T_inf = {T_lo:.0f} °C',
            fontsize=7.5, color=COLORS['text'], va='center', zorder=10,
            bbox=dict(boxstyle='round,pad=0.2', fc='#00000055', ec='none'))
    ax.text(W * 0.5, h_i + 0.07, f'Interfaz  h_i = {h_i:.2f} m',
            fontsize=7.5, color=COLORS['warning'], ha='center', zorder=10)
    ax.text(-0.18, h_n, f'PN {h_n:.2f}m',
            fontsize=7, color=FC['neutral'], ha='right', va='center', zorder=10)

    ax.set_title(
        f'Sección habitación   Q = {Q:.0f} kW   Q_FO = {Q_fo:.0f} kW\n'
        f'A_floor = {A_floor:.0f} m²   A_vent = {A_v:.1f} m²',
        fontsize=8.5, color=COLORS['text'], pad=4)


# ── Perfil T(z) ───────────────────────────────────────────────────────────────

def draw_profile(ax, Q: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['bg'])

    A_T  = room_surfaces(A_floor)
    Q_fo = q_flashover(A_T, A_v)
    T_su = upper_temp(Q, A_T, A_v)
    T_lo = T_AMB + max(0, (T_su - T_AMB) * 0.06)
    h_i  = interface_height(Q, Q_fo)

    z_arr = np.linspace(0, H, 500)
    T_arr = temp_profile(z_arr, h_i, T_su, T_lo)

    # Zonas de peligro (fondo)
    ax.axvspan(0,            SCBA_LIMIT,  color=COLORS['accent'],    alpha=0.08)
    ax.axvspan(SCBA_LIMIT,   BURN_LIMIT,  color=COLORS['warning'],   alpha=0.08)
    ax.axvspan(BURN_LIMIT,   IDLH_LIMIT,  color=COLORS['secondary'], alpha=0.08)
    ax.axvspan(IDLH_LIMIT,   FLASHOVER_T, color=COLORS['danger'],    alpha=0.08)
    ax.axvspan(FLASHOVER_T,  900,         color='#440000',           alpha=0.15)

    # Líneas de umbral
    thresholds = [
        (SCBA_LIMIT,  'SCBA',     COLORS['accent'],   ':'),
        (BURN_LIMIT,  'Quemaduras', COLORS['warning'], '--'),
        (IDLH_LIMIT,  'IDLH',     COLORS['danger'],   '-.'),
        (FLASHOVER_T, 'Flashover', COLORS['danger'],  '-'),
    ]
    for T_thr, lbl, color, ls in thresholds:
        ax.axvline(T_thr, color=color, lw=1.2, ls=ls, alpha=0.7,
                   label=f'{lbl} {T_thr:.0f}°C')

    # Perfil
    ax.plot(T_arr, z_arr, color=FC['flame'], lw=2.5, zorder=5)

    # Interfaz
    ax.axhline(h_i, color=COLORS['warning'], lw=1.5, ls='--', alpha=0.8)
    ax.text(10, h_i + 0.05, f'h_i={h_i:.2f}m',
            fontsize=7.5, color=COLORS['warning'])

    # Etiquetas zonas
    ax.text(SCBA_LIMIT / 2,   H * 0.92, 'OK',    fontsize=7.5,
            color=COLORS['accent'],    ha='center')
    ax.text((SCBA_LIMIT + BURN_LIMIT) / 2, H * 0.92, 'SCBA',
            fontsize=7.5, color=COLORS['warning'], ha='center')
    ax.text((BURN_LIMIT + IDLH_LIMIT) / 2, H * 0.92, 'IDLH',
            fontsize=7.5, color=COLORS['secondary'], ha='center')
    ax.text((IDLH_LIMIT + FLASHOVER_T) / 2, H * 0.92, 'PELIGRO',
            fontsize=7.5, color=COLORS['danger'], ha='center')

    ax.set_xlabel('Temperatura (°C)', fontsize=8)
    ax.set_ylabel('Altura desde el suelo (m)', fontsize=8)
    ax.set_xlim(0, min(900, max(100, T_su * 1.15)))
    ax.set_ylim(0, H)
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc='lower right',
              facecolor=COLORS['panel'], edgecolor=COLORS['grid'])
    ax.set_title('Perfil de Temperatura T(z)', fontsize=9,
                 color=COLORS['text'], pad=3)


# ── Panel de información ──────────────────────────────────────────────────────

def draw_info(ax, Q: float, A_floor: float, A_v: float):
    ax.clear()
    ax.set_facecolor(COLORS['panel'])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    A_T  = room_surfaces(A_floor)
    Q_fo = q_flashover(A_T, A_v)
    T_su = upper_temp(Q, A_T, A_v)
    T_lo = T_AMB + max(0, (T_su - T_AMB) * 0.06)
    h_i  = interface_height(Q, Q_fo)
    h_n  = neutral_plane_height(h_i, T_su)

    z_arr = np.linspace(0, H, 500)
    T_arr = temp_profile(z_arr, h_i, T_su, T_lo)
    z_safe_scba = safe_height(T_arr, z_arr, SCBA_LIMIT)
    z_safe_burn = safe_height(T_arr, z_arr, BURN_LIMIT)

    # Fase
    if T_su >= FLASHOVER_T:
        fase, fc = '⚠ FLASHOVER', COLORS['danger']
    elif T_su >= IDLH_LIMIT:
        fase, fc = 'PELIGRO INMEDIATO', COLORS['danger']
    elif T_su >= BURN_LIMIT:
        fase, fc = 'RIESGO QUEMADURAS', COLORS['secondary']
    elif T_su >= SCBA_LIMIT:
        fase, fc = 'USO SCBA', COLORS['warning']
    else:
        fase, fc = 'SEGURO (sin SCBA)', COLORS['accent']

    rows = [
        ('T capa superior',  f'{T_su:.0f} °C',         COLORS['danger']),
        ('T capa inferior',  f'{T_lo:.0f} °C',         COLORS['info']),
        ('Interfaz h_i',     f'{h_i:.2f} m',           COLORS['warning']),
        ('Plano neutral',    f'{h_n:.2f} m',           FC['neutral']),
        ('Zona segura (SCBA)', f'{z_safe_scba:.2f} m', COLORS['accent']),
        ('Situación',        fase,                      fc),
    ]
    y = 9.2
    for label, val, color in rows:
        ax.text(0.5, y, label + ':', fontsize=7.8, color=COLORS['anchor'],
                va='center')
        ax.text(9.5, y, val, fontsize=7.8, color=color,
                va='center', ha='right', fontweight='bold')
        y -= 1.52


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Capas Térmicas y Plano Neutral — Incendio Estructural',
                 fontsize=19, fontweight='bold', color=COLORS['primary'], y=0.97)

    ax_room = fig.add_axes([0.02, 0.14, 0.42, 0.77])
    ax_prof = fig.add_axes([0.47, 0.33, 0.50, 0.57])
    ax_info = fig.add_axes([0.47, 0.14, 0.50, 0.16])

    ax_sl_q    = fig.add_axes([0.15, 0.09, 0.70, 0.025])
    ax_sl_area = fig.add_axes([0.15, 0.05, 0.70, 0.025])

    for ax_sl in (ax_sl_q, ax_sl_area):
        ax_sl.set_facecolor(COLORS['panel'])

    sl_q    = Slider(ax_sl_q,    'HRR (kW)',            100, 5000, valinit=800,
                     color=FC['flame'], valstep=50)
    sl_area = Slider(ax_sl_area, 'Área habitación (m²)',  10,   50, valinit=20,
                     color=COLORS['info'], valstep=1)

    def update(_=None):
        Q       = sl_q.val
        A_floor = sl_area.val
        A_v     = 1.5    # apertura fija (puerta estándar)
        draw_room(ax_room, Q, A_floor, A_v)
        draw_profile(ax_prof, Q, A_floor, A_v)
        draw_info(ax_info, Q, A_floor, A_v)
        fig.canvas.draw_idle()

    sl_q.on_changed(update)
    sl_area.on_changed(update)
    update()
    plt.show()


if __name__ == '__main__':
    main()
