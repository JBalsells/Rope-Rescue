"""
╔══════════════════════════════════════════════════════════════════════╗
║    FÍSICA DEL RESCATE · Módulo 18: Ángulos Críticos del Anclaje     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Cómo el ángulo entre los brazos de un anclaje en V afecta          ║
║  dramáticamente la tensión en cada brazo.                           ║
║                                                                      ║
║  Física clave (anclaje en V simétrico):                             ║
║   T = W / (2 · cos(θ/2))                                            ║
║                                                                      ║
║   θ =   0°  → T = W/2      (ideal, 50% del peso en cada brazo)     ║
║   θ =  60°  → T ≈ 0.577·W                                          ║
║   θ =  90°  → T ≈ 0.707·W                                          ║
║   θ = 120°  → T = W        (CRÍTICO: cada brazo = peso total)      ║
║   θ = 150°  → T ≈ 1.93·W                                           ║
║   θ = 170°  → T ≈ 5.74·W                                           ║
║   θ → 180°  → T → ∞                                                ║
║                                                                      ║
║  Ejecutar:  python 18_angulos_criticos.py                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider
from config import COLORS, G, NFPA_WORK_LOAD, apply_mpl_style


# ── Constantes ────────────────────────────────────────────────────────
ANGULO_MAX_PLOT = 178          # límite del eje X en la curva (grados)
ANGULO_CRITICO  = 120          # ángulo donde T = W (cada brazo = peso)
ANGULO_SEGURO   =  60          # ángulo recomendado máximo en rescate
T_W_MAX_PLOT    =  6.0         # máximo del eje Y en la curva (T/W)

# Colores de zonas de peligro (por T/W)
ZONA_SEGURA   = COLORS['accent']   # T/W < 1
ZONA_ATENCION = COLORS['warning']  # 1 ≤ T/W < 1.5
ZONA_PELIGRO  = COLORS['secondary']  # 1.5 ≤ T/W < 3
ZONA_CRITICA  = COLORS['danger']   # T/W ≥ 3


def tension_ratio(theta_deg):
    """
    Calcula T/W para un anclaje en V simétrico.
    T/W = 1 / (2 · cos(θ/2))
    Retorna np.inf cuando cos(θ/2) ≈ 0 (θ → 180°).
    """
    half_rad = np.radians(np.asarray(theta_deg, dtype=float)) / 2.0
    cos_half  = np.cos(half_rad)
    # Evitar división por cero: se aproxima a θ = 180°
    cos_half  = np.where(np.abs(cos_half) < 1e-6,
                         np.sign(cos_half) * 1e-6, cos_half)
    return 1.0 / (2.0 * cos_half)


def color_zona(ratio):
    """Devuelve el color de peligro según el cociente T/W."""
    if ratio < 1.0:
        return ZONA_SEGURA
    elif ratio < 1.5:
        return ZONA_ATENCION
    elif ratio < 3.0:
        return ZONA_PELIGRO
    else:
        return ZONA_CRITICA


# ── Visualización geométrica del anclaje ──────────────────────────────

def dibujar_viz(ax, theta_deg, masa_kg):
    """Dibuja el anclaje en V con los brazos, la masa y las etiquetas."""
    ax.clear()
    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.45, 1.10)
    ax.set_aspect('equal')
    ax.axis('off')

    W_kN   = masa_kg * G / 1000.0
    ratio  = tension_ratio(theta_deg)
    # Limitar la ratio para el cálculo visual (evitar infinito gráfico)
    ratio_vis = min(ratio, 6.0)
    T_kN   = ratio * W_kN
    T_kN_vis = min(T_kN, W_kN * 6.0)

    half_rad = np.radians(theta_deg) / 2.0

    # Geometría: punto central (unión) abajo, anclajes arriba
    arm_len = 1.0
    join_pt = np.array([0.0, -0.30])
    anc_L   = join_pt + arm_len * np.array([-np.sin(half_rad),  np.cos(half_rad)])
    anc_R   = join_pt + arm_len * np.array([ np.sin(half_rad),  np.cos(half_rad)])

    # ── Color de fondo del ángulo según peligrosidad ──────────────────
    bg_color = (ZONA_SEGURA   if theta_deg < ANGULO_SEGURO else
                ZONA_ATENCION if theta_deg < 90            else
                ZONA_PELIGRO  if theta_deg < ANGULO_CRITICO else
                ZONA_CRITICA)

    # Arco del ángulo θ en el punto de unión
    arc_r = 0.28
    if theta_deg > 2:
        t_arc = np.linspace(np.pi / 2 - half_rad,
                             np.pi / 2 + half_rad, 80)
        ax.fill_between(
            join_pt[0] + arc_r * np.cos(t_arc),
            join_pt[1],
            join_pt[1] + arc_r * np.sin(t_arc),
            alpha=0.25, color=bg_color, zorder=1)
        ax.plot(join_pt[0] + arc_r * np.cos(t_arc),
                join_pt[1] + arc_r * np.sin(t_arc),
                color=bg_color, lw=2.0, zorder=3)

    # ── Pared o techo (barra de anclaje superior) ─────────────────────
    ax.plot([-1.3, 1.3], [anc_L[1] + 0.04, anc_R[1] + 0.04],
            color=COLORS['anchor'], lw=4, solid_capstyle='round', zorder=2)
    ax.fill_between([-1.3, 1.3],
                    [anc_L[1] + 0.04, anc_R[1] + 0.04],
                    [anc_L[1] + 0.14, anc_R[1] + 0.14],
                    color=COLORS['anchor'], alpha=0.20)

    # ── Brazos de la cuerda ───────────────────────────────────────────
    rope_color = COLORS['rope']
    ax.plot([anc_L[0], join_pt[0]], [anc_L[1], join_pt[1]],
            color=rope_color, lw=5, solid_capstyle='round', zorder=3)
    ax.plot([anc_R[0], join_pt[0]], [anc_R[1], join_pt[1]],
            color=rope_color, lw=5, solid_capstyle='round', zorder=3)

    # ── Puntos de anclaje ─────────────────────────────────────────────
    for pt, lbl in [(anc_L, 'A₁'), (anc_R, 'A₂')]:
        ax.plot(*pt, 'D', color=COLORS['anchor'], ms=14, zorder=5)
        ax.plot(*pt, 'D', color=COLORS['text'],   ms=8,  zorder=6)
        ax.text(pt[0], pt[1] + 0.10, lbl,
                ha='center', fontsize=10, fontweight='bold',
                color=COLORS['text'], zorder=7)

    # ── Punto de unión central ────────────────────────────────────────
    ax.plot(*join_pt, 'o', color=COLORS['warning'], ms=14, zorder=6)
    ax.plot(*join_pt, 'o', color=COLORS['bg'],      ms=7,  zorder=7)

    # ── Flechas de tensión en cada brazo (proporcionales a T) ─────────
    max_arr = 0.40   # longitud máxima visual de la flecha
    arr_len = min(ratio_vis / T_W_MAX_PLOT, 1.0) * max_arr
    arr_len = max(arr_len, 0.08)   # mínimo visible

    col_T = color_zona(ratio)

    # Dirección de cada brazo (desde join hacia el anclaje)
    dir_L = (anc_L - join_pt) / np.linalg.norm(anc_L - join_pt)
    dir_R = (anc_R - join_pt) / np.linalg.norm(anc_R - join_pt)

    for dir_v, sign, lab_off in [(dir_L, -1, -0.12), (dir_R, 1, 0.12)]:
        tip = join_pt + dir_v * arr_len
        ax.annotate('', xy=tuple(tip), xytext=tuple(join_pt),
                    arrowprops=dict(arrowstyle='->',
                                   color=col_T, lw=3.0, mutation_scale=18),
                    zorder=7)
        # Etiqueta T en el medio del brazo
        mid = (join_pt + join_pt + dir_v * arm_len * 0.55) / 2.0
        if not np.isinf(T_kN):
            label_T = f'T = {T_kN:.2f} kN'
        else:
            label_T = 'T → ∞'
        ax.text(mid[0] + lab_off, mid[1], label_T,
                ha='center', va='center', fontsize=8.5,
                fontweight='bold', color=col_T,
                bbox=dict(boxstyle='round,pad=0.2',
                          facecolor=COLORS['bg'],
                          edgecolor=col_T, alpha=0.88),
                zorder=8)

    # ── Caja de masa colgante ─────────────────────────────────────────
    masa_y  = join_pt[1] - 0.60
    masa_w, masa_h = 0.36, 0.22
    caja = mpatches.FancyBboxPatch(
        (-masa_w / 2, masa_y - masa_h / 2), masa_w, masa_h,
        boxstyle='round,pad=0.02',
        facecolor=COLORS['panel'], edgecolor=COLORS['danger'],
        linewidth=2, zorder=7)
    ax.add_patch(caja)

    # Cuerda hasta la caja
    ax.plot([join_pt[0], join_pt[0]],
            [join_pt[1] - 0.06, masa_y + masa_h / 2],
            color=COLORS['rope'], lw=4, zorder=4)

    ax.text(0, masa_y, f'{masa_kg:.0f} kg\n{W_kN:.2f} kN',
            ha='center', va='center', fontsize=9,
            fontweight='bold', color=COLORS['danger'], zorder=8)

    # ── Etiqueta del ángulo ───────────────────────────────────────────
    ax.text(join_pt[0], join_pt[1] + arc_r + 0.14,
            f'θ = {theta_deg:.0f}°',
            ha='center', fontsize=12, fontweight='bold',
            color=bg_color, zorder=8)

    # ── Advertencia zona peligrosa ────────────────────────────────────
    if theta_deg > ANGULO_CRITICO:
        warn_rect = mpatches.FancyBboxPatch(
            (-1.30, -1.43), 2.60, 0.34,
            boxstyle='round,pad=0.02',
            facecolor=COLORS['danger'], edgecolor=COLORS['danger'],
            linewidth=2, alpha=0.20, zorder=6)
        ax.add_patch(warn_rect)
        ax.text(0, -1.26,
                'ZONA PELIGROSA  —  CARGA SUPERA EL PESO EN CADA BRAZO',
                ha='center', va='center', fontsize=9,
                fontweight='bold', color=COLORS['danger'], zorder=9)

    ax.set_title(
        f'Anclaje en V  —  θ = {theta_deg:.0f}°  '
        f'|  T/W = {ratio:.2f}',
        fontsize=12, fontweight='bold', color=bg_color, pad=6)


# ── Curva T/W vs ángulo ───────────────────────────────────────────────

def dibujar_curva(ax, theta_deg, masa_kg):
    """Curva suave de T/W en función del ángulo, con punto destacado."""
    ax.clear()

    W_kN  = masa_kg * G / 1000.0
    ratio = tension_ratio(theta_deg)

    angulos = np.linspace(0, ANGULO_MAX_PLOT, 800)
    ratios  = tension_ratio(angulos)
    # Limitar visualmente a T_W_MAX_PLOT
    ratios_vis = np.clip(ratios, 0, T_W_MAX_PLOT)

    # ── Zonas de color de fondo ───────────────────────────────────────
    ax.axhspan(0,   1.0, facecolor=ZONA_SEGURA,   alpha=0.08)
    ax.axhspan(1.0, 1.5, facecolor=ZONA_ATENCION, alpha=0.09)
    ax.axhspan(1.5, 3.0, facecolor=ZONA_PELIGRO,  alpha=0.09)
    ax.axhspan(3.0, T_W_MAX_PLOT,
               facecolor=ZONA_CRITICA,  alpha=0.10)

    # ── Curva de T/W ─────────────────────────────────────────────────
    ax.plot(angulos, ratios_vis,
            color=COLORS['primary'], lw=2.8, zorder=4)

    # ── Líneas de referencia horizontales ────────────────────────────
    ax.axhline(1.0, color=COLORS['warning'],
               ls='--', lw=1.6, alpha=0.85, zorder=3)
    ax.text(3, 1.05,
            'T = W  (cada brazo = peso total)',
            fontsize=8, color=COLORS['warning'], va='bottom', alpha=0.90)

    # ── Línea vertical en 120° ────────────────────────────────────────
    ax.axvline(ANGULO_CRITICO, color=COLORS['danger'],
               ls=':', lw=1.5, alpha=0.75, zorder=3)
    ax.text(ANGULO_CRITICO + 1.5, T_W_MAX_PLOT * 0.90,
            f'{ANGULO_CRITICO}°',
            fontsize=9, color=COLORS['danger'], va='top',
            fontweight='bold')

    # ── Línea vertical en 60° (zona segura) ──────────────────────────
    ax.axvline(ANGULO_SEGURO, color=COLORS['accent'],
               ls=':', lw=1.2, alpha=0.65, zorder=3)
    ax.text(ANGULO_SEGURO + 1.5, T_W_MAX_PLOT * 0.90,
            f'{ANGULO_SEGURO}°',
            fontsize=9, color=COLORS['accent'], va='top')

    # ── Punto destacado del ángulo actual ─────────────────────────────
    ratio_vis_actual = min(ratio, T_W_MAX_PLOT)
    col_pt = color_zona(ratio)
    ax.plot(theta_deg, ratio_vis_actual, 'o',
            color=COLORS['warning'], ms=14, zorder=8,
            markeredgecolor=COLORS['bg'], markeredgewidth=2)
    ax.plot(theta_deg, ratio_vis_actual, 'o',
            color=col_pt, ms=8, zorder=9)

    # Líneas de cruz en el punto
    ax.axvline(theta_deg, color=COLORS['warning'],
               ls='--', lw=1.4, alpha=0.60, zorder=3)
    ax.axhline(ratio_vis_actual, color=COLORS['warning'],
               ls='--', lw=1.0, alpha=0.45, zorder=3)

    # Etiqueta flotante del punto actual
    lbl_x = theta_deg + 5 if theta_deg < 130 else theta_deg - 55
    lbl_y = ratio_vis_actual + 0.35 if ratio_vis_actual < T_W_MAX_PLOT - 0.5 else ratio_vis_actual - 0.6
    if not np.isinf(ratio):
        lbl = f'θ={theta_deg:.0f}°\nT/W = {ratio:.2f}\nT = {ratio * W_kN:.2f} kN'
    else:
        lbl = f'θ={theta_deg:.0f}°\nT → ∞'
    ax.text(lbl_x, lbl_y, lbl,
            fontsize=9, fontweight='bold', color=COLORS['warning'],
            ha='left', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=COLORS['bg'],
                      edgecolor=COLORS['warning'], alpha=0.92),
            zorder=10)

    # Etiquetas de zona
    ax.text(25,  0.55, 'SEGURO', fontsize=8, color=ZONA_SEGURA,
            ha='center', alpha=0.80, fontstyle='italic')
    ax.text(100, 0.72, 'ATENCION', fontsize=8, color=ZONA_ATENCION,
            ha='center', alpha=0.80, fontstyle='italic')
    ax.text(140, 2.0, 'PELIGRO', fontsize=8, color=ZONA_PELIGRO,
            ha='center', alpha=0.80, fontstyle='italic')
    ax.text(170, 4.5, 'CRITICO', fontsize=8, color=ZONA_CRITICA,
            ha='center', alpha=0.80, fontstyle='italic')

    ax.set_xlabel('Ángulo entre brazos (°)', fontsize=10)
    ax.set_ylabel('T / W', fontsize=10)
    ax.set_title('T/W = 1 / (2·cos(θ/2))', fontsize=11,
                 fontweight='bold', color=COLORS['warning'], pad=6)
    ax.set_xlim(0, ANGULO_MAX_PLOT)
    ax.set_ylim(0, T_W_MAX_PLOT)
    ax.grid(True, alpha=0.15)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


# ── Barras comparativas de tensión ────────────────────────────────────

def dibujar_barras(ax, theta_deg, masa_kg):
    """Barras horizontales: T en brazo, W de la carga y límite NFPA."""
    ax.clear()

    W_kN  = masa_kg * G / 1000.0
    ratio = tension_ratio(theta_deg)
    # Limitar el valor para no desvirtuar el gráfico
    T_kN  = min(ratio * W_kN, W_kN * T_W_MAX_PLOT)
    T_kN_real = ratio * W_kN

    col_T = color_zona(ratio)

    etiquetas = [
        f'T brazo  (θ={theta_deg:.0f}°)',
        f'Peso W  ({masa_kg:.0f} kg)',
        f'Límite NFPA',
    ]
    valores = [T_kN, W_kN, NFPA_WORK_LOAD]
    colores = [col_T, COLORS['info'], COLORS['danger']]

    bars = ax.barh(etiquetas, valores, color=colores,
                   alpha=0.85, height=0.55,
                   edgecolor=colores, linewidth=1.5)

    # Valores al final de cada barra
    for bar, val, col, real_val in zip(bars, valores, colores,
                                        [T_kN_real, W_kN, NFPA_WORK_LOAD]):
        label_val = real_val if not np.isinf(real_val) else float('inf')
        if np.isinf(label_val):
            txt = '∞ kN / ∞ N'
        else:
            txt = f'{real_val:.2f} kN  ({real_val * 1000:.0f} N)'
        ax.text(max(val, 0.3) + 0.2, bar.get_y() + bar.get_height() / 2,
                txt, va='center', ha='left', fontsize=8.5,
                color=col, fontweight='bold')

    ax.set_xlim(0, max(T_kN, W_kN, NFPA_WORK_LOAD) * 1.55 + 1.0)
    ax.set_xlabel('Fuerza (kN)', fontsize=9)
    ax.set_title('Comparación de fuerzas', fontsize=10,
                 fontweight='bold', color=COLORS['primary'], pad=5)
    ax.grid(True, axis='x', alpha=0.15)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)

    # Si T > NFPA, mostrar advertencia
    if T_kN_real > NFPA_WORK_LOAD and not np.isinf(T_kN_real):
        ax.text(ax.get_xlim()[1] * 0.02, 2.35,
                f'T supera NFPA en {T_kN_real - NFPA_WORK_LOAD:.2f} kN',
                fontsize=8, color=COLORS['danger'], fontweight='bold',
                va='center')


# ── Función principal ─────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(18, 10))

    # ── Títulos ───────────────────────────────────────────────────────
    fig.suptitle(
        'FÍSICA DEL RESCATE — El Ángulo de Anclaje y la Tensión en la Cuerda',
        fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.97)
    fig.text(
        0.5, 0.925,
        'T = W / (2 · cos(θ/2))   →   A mayor ángulo, MAYOR tensión en la cuerda',
        ha='center', fontsize=12, color=COLORS['warning'], style='italic')

    # ── Ejes ──────────────────────────────────────────────────────────
    ax_viz   = fig.add_axes([0.02, 0.22, 0.38, 0.68])
    ax_curve = fig.add_axes([0.44, 0.45, 0.52, 0.45])
    ax_bar   = fig.add_axes([0.44, 0.22, 0.52, 0.20])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_angle = fig.add_axes([0.15, 0.13, 0.75, 0.025])
    ax_sl_mass  = fig.add_axes([0.15, 0.07, 0.75, 0.025])

    sl_angle = Slider(
        ax_sl_angle, 'Ángulo θ entre brazos (°)',
        0, ANGULO_MAX_PLOT, valinit=60,
        color=COLORS['primary'], valstep=1)
    sl_mass  = Slider(
        ax_sl_mass, 'Masa de la carga (kg)',
        1, 200, valinit=80,
        color=COLORS['secondary'], valstep=1)

    sl_angle.label.set_color(COLORS['primary'])
    sl_angle.valtext.set_color(COLORS['primary'])
    sl_mass.label.set_color(COLORS['secondary'])
    sl_mass.valtext.set_color(COLORS['secondary'])

    def update(_=None):
        theta_deg = float(sl_angle.val)
        masa_kg   = float(sl_mass.val)

        dibujar_viz(ax_viz,   theta_deg, masa_kg)
        dibujar_curva(ax_curve, theta_deg, masa_kg)
        dibujar_barras(ax_bar,  theta_deg, masa_kg)

        fig.canvas.draw_idle()

    sl_angle.on_changed(update)
    sl_mass.on_changed(update)

    # ── Nota educativa fija ───────────────────────────────────────────
    fig.text(
        0.5, 0.018,
        'En rescate: usar angulos < 60°. Nunca superar 120° entre brazos del anclaje en V.   '
        '|   A 120° cada brazo soporta el 100% del peso.   '
        '|   A 150° cada brazo soporta casi el doble del peso.',
        ha='center', fontsize=9,
        color=COLORS['danger'], fontweight='bold', style='italic')

    fig.text(
        0.02, 0.005,
        'T = W / (2·cos(θ/2))   |   θ=0°: T=W/2 (óptimo)   |   '
        'θ=60°: T≈0.58W   |   θ=90°: T≈0.71W   |   '
        'θ=120°: T=W   |   θ=150°: T≈1.93W   |   θ→180°: T→∞',
        fontsize=8.5, color=COLORS['text'], alpha=0.55, style='italic')

    # Primer renderizado
    update()
    plt.show()


if __name__ == '__main__':
    main()
