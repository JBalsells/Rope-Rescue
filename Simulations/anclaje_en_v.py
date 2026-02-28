"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 03: Anclaje en V                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  Análisis interactivo de cómo el ángulo del anclaje en V             ║
║  y el ángulo de la carga afectan la fuerza en cada brazo.            ║
║                                                                      ║
║  Caso simétrico (φ=0):  F_brazo = W / (2·cos(θ/2))                  ║
║  Caso general:          T₁ = W·sin(θ/2+φ)/sin(θ)                    ║
║                         T₂ = W·sin(θ/2−φ)/sin(θ)                    ║
║                                                                      ║
║  Brazo flojo cuando |φ| ≥ θ/2  (la carga supera el brazo del V)     ║
║                                                                      ║
║  Ejecutar:  python 03_anclaje_en_v.py                                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, apply_mpl_style

# Colores fijos para identificar cada brazo en todos los paneles
C1 = '#2196F3'   # azul  — brazo izquierdo / T₁
C2 = '#4CAF50'   # verde — brazo derecho   / T₂


def arm_danger_color(T, W_kN):
    """Color del brazo según nivel de peligro de su tensión."""
    if T <= 0:
        return COLORS['grid']
    ratio = T / W_kN if W_kN > 0 else 0
    if ratio > 1.0:
        return COLORS['danger']
    elif ratio > 0.75:
        return COLORS['warning']
    return COLORS['rope']


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Anclaje en V: Ángulo vs Fuerza',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    # ── Ejes ──────────────────────────────────────────────────────────
    ax_v   = fig.add_axes([0.03, 0.26, 0.38, 0.62])
    ax_crv = fig.add_axes([0.48, 0.26, 0.48, 0.62])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_ang  = fig.add_axes([0.15, 0.16, 0.75, 0.025])
    ax_sl_load = fig.add_axes([0.15, 0.10, 0.75, 0.025])
    ax_sl_phi  = fig.add_axes([0.15, 0.04, 0.75, 0.025])

    sl_angle = Slider(ax_sl_ang, 'Ángulo V  θ (°)', 2, 175, valinit=60,
                      color=COLORS['primary'], valstep=1)
    sl_load  = Slider(ax_sl_load, 'Carga (kg)', 10, 300, valinit=100,
                      color=COLORS['secondary'], valstep=1)
    sl_phi   = Slider(ax_sl_phi, 'Ángulo carga φ (°)', -90, 90, valinit=0,
                      color=COLORS['info'], valstep=1)

    # Colorear el label del slider de φ
    sl_phi.label.set_color(COLORS['info'])

    def update(_=None):
        theta_deg = sl_angle.val
        mass      = sl_load.val
        phi_deg   = sl_phi.val

        W_kN      = mass * G / 1000.0
        theta_rad = np.radians(theta_deg)
        phi_rad   = np.radians(phi_deg)
        half      = theta_rad / 2.0
        sin_t     = np.sin(theta_rad)

        # ── Tensiones: fórmula general ─────────────────────────────────
        # T₁ = W · sin(θ/2 + φ) / sin(θ)   (brazo izquierdo)
        # T₂ = W · sin(θ/2 − φ) / sin(θ)   (brazo derecho)
        if sin_t < 0.01:   # θ ≈ 0° ó 180°: singularidad
            T1 = T2 = 99.0 * W_kN
        else:
            T1 = W_kN * np.sin(half + phi_rad) / sin_t
            T2 = W_kN * np.sin(half - phi_rad) / sin_t

        r1 = T1 / W_kN if W_kN > 0 else 0
        r2 = T2 / W_kN if W_kN > 0 else 0

        col1_arm = arm_danger_color(T1, W_kN)
        col2_arm = arm_danger_color(T2, W_kN)

        # ── Diagrama de la V ───────────────────────────────────────────
        ax_v.clear()
        ax_v.set_xlim(-2.5, 2.5)
        ax_v.set_ylim(-2.9, 1.5)
        ax_v.set_aspect('equal')
        ax_v.axis('off')
        ax_v.set_title('Diagrama del Anclaje en V',
                        fontsize=13, fontweight='bold', pad=8)

        arm_len  = 1.8
        anchor_L = (-arm_len * np.sin(half), 0)
        anchor_R = ( arm_len * np.sin(half), 0)
        load_pt  = (0, -arm_len * np.cos(half))

        # Pared
        ax_v.plot([-2.3, 2.3], [0, 0], color=COLORS['anchor'], lw=3)
        ax_v.fill_between([-2.3, 2.3], [0, 0], [0.3, 0.3],
                          color=COLORS['anchor'], alpha=0.15)

        # Puntos de anclaje
        for pt, label, c in [(anchor_L, 'A₁', C1), (anchor_R, 'A₂', C2)]:
            ax_v.plot(*pt, 'D', color=c, markersize=12, zorder=5)
            ax_v.text(pt[0], pt[1] + 0.2, label,
                      ha='center', fontsize=11, fontweight='bold', color=c)

        # Brazos (coloreados por nivel de peligro)
        ax_v.plot([anchor_L[0], load_pt[0]], [anchor_L[1], load_pt[1]],
                  color=col1_arm, lw=3.5, zorder=3)
        ax_v.plot([anchor_R[0], load_pt[0]], [anchor_R[1], load_pt[1]],
                  color=col2_arm, lw=3.5, zorder=3)

        # Punto central
        ax_v.plot(*load_pt, 'o', color=COLORS['warning'],
                  markersize=14, zorder=6)

        # ── Flecha de carga al ángulo φ ────────────────────────────────
        arrow_len = min(W_kN * 0.6, 1.0)
        arr_dx =  arrow_len * np.sin(phi_rad)
        arr_dy = -arrow_len * np.cos(phi_rad)
        tip = (load_pt[0] + arr_dx, load_pt[1] + arr_dy)

        ax_v.annotate('', xy=tip, xytext=load_pt,
                      arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                                      lw=3, mutation_scale=20))

        # Línea vertical de referencia (φ=0)
        ax_v.plot([load_pt[0], load_pt[0]],
                  [load_pt[1], load_pt[1] - arrow_len * 1.1],
                  '--', color=COLORS['grid'], lw=1, alpha=0.5)

        # Arco mostrando φ (si es significativo)
        if abs(phi_deg) > 2:
            phi_r = arrow_len * 0.45
            arc_phi = np.linspace(-np.pi / 2, -np.pi / 2 + phi_rad, 40)
            ax_v.plot(load_pt[0] + phi_r * np.cos(arc_phi),
                      load_pt[1] + phi_r * np.sin(arc_phi),
                      color=COLORS['info'], lw=1.8, alpha=0.9)
            mid_a = -np.pi / 2 + phi_rad / 2
            r_lbl = phi_r + 0.20
            ax_v.text(load_pt[0] + r_lbl * np.cos(mid_a),
                      load_pt[1] + r_lbl * np.sin(mid_a),
                      f'φ={phi_deg:+.0f}°',
                      fontsize=9, color=COLORS['info'],
                      ha='center', va='center', fontweight='bold')

        # Etiqueta de carga W
        lbl_x = np.clip(load_pt[0] + arr_dx * 1.45, -2.0, 2.0)
        lbl_y = load_pt[1] + arr_dy * 1.45
        ax_v.text(lbl_x, lbl_y,
                  f'W = {W_kN:.2f} kN\n({mass:.0f} kg)',
                  ha='center', fontsize=10, fontweight='bold',
                  color=COLORS['danger'],
                  bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['bg'],
                            edgecolor=COLORS['danger'], alpha=0.85))

        # Tensiones en cada brazo
        for anchor, T, col_arm, col_id, sign, lbl in [
                (anchor_L, T1, col1_arm, C1, -1, 'T₁'),
                (anchor_R, T2, col2_arm, C2,  1, 'T₂')]:
            mid_x = (anchor[0] + load_pt[0]) / 2
            mid_y = (anchor[1] + load_pt[1]) / 2
            note  = '  FLOJO' if T <= 0 else f'={T:.2f} kN'
            ax_v.text(mid_x + sign * 0.32, mid_y,
                      f'{lbl}{note}',
                      fontsize=9, fontweight='bold', color=col_id,
                      ha='center', va='center',
                      bbox=dict(boxstyle='round,pad=0.2',
                                facecolor=COLORS['bg'],
                                edgecolor=col_id, alpha=0.9))

        # Arco del ángulo θ del anclaje
        arc_r = 0.55
        arc_thetas = np.linspace(-np.pi / 2 - half,
                                  -np.pi / 2 + half, 50)
        ax_v.plot(load_pt[0] + arc_r * np.cos(arc_thetas),
                  load_pt[1] + arc_r * np.sin(arc_thetas),
                  color=COLORS['warning'], lw=1.5)
        ax_v.text(load_pt[0], load_pt[1] + arc_r + 0.15,
                  f'θ = {theta_deg:.0f}°',
                  ha='center', fontsize=12, fontweight='bold',
                  color=COLORS['warning'])

        # Indicador de seguridad
        slack = T1 <= 0 or T2 <= 0
        max_r = max(r1, r2)
        if slack:
            status   = '⚠ BRAZO FLOJO — SISTEMA INESTABLE'
            st_color = COLORS['danger']
        elif max_r > 1.0:
            status   = '✗ PELIGROSO'
            st_color = COLORS['danger']
        elif max_r > 0.75:
            status   = '⚠ PRECAUCIÓN'
            st_color = COLORS['warning']
        else:
            status   = '✓ SEGURO'
            st_color = COLORS['accent']

        ax_v.text(0, -2.72,
                  f'{status}\nT₁: {r1:.1%}·W  |  T₂: {r2:.1%}·W',
                  ha='center', fontsize=12, fontweight='bold',
                  color=st_color,
                  bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['bg'],
                            edgecolor=st_color, alpha=0.9))

        # ── Curva ángulo vs fuerza ─────────────────────────────────────
        ax_crv.clear()

        angles_arr  = np.linspace(2, 175, 500)
        theta_arr   = np.radians(angles_arr)
        sin_t_arr   = np.maximum(np.sin(theta_arr), 1e-6)
        half_arr    = theta_arr / 2.0

        # Curva simétrica de referencia (φ=0)
        sym_ratio = 1.0 / (2.0 * np.cos(half_arr))

        # Curvas asimétricas para el φ actual
        r1_arr = np.sin(half_arr + phi_rad) / sin_t_arr
        r2_arr = np.sin(half_arr - phi_rad) / sin_t_arr

        # Zonas coloreadas
        ax_crv.axhspan(0, 0.75, facecolor=COLORS['accent'], alpha=0.07)
        ax_crv.axhspan(0.75, 1.0, facecolor=COLORS['warning'], alpha=0.07)
        ax_crv.axhspan(1.0, 5.5, facecolor=COLORS['danger'], alpha=0.07)

        # Curva de referencia simétrica
        ax_crv.plot(angles_arr, sym_ratio,
                    color=COLORS['grid'], lw=1.5, ls='--', alpha=0.55,
                    label='Simétrico φ=0°  F=W/(2·cos θ/2)')

        # Curvas T₁ y T₂ (solo distintas de la referencia si φ≠0)
        if abs(phi_deg) > 0:
            ax_crv.plot(angles_arr, np.clip(r1_arr, 0, 5.5),
                        color=C1, lw=2.2, label=f'T₁/W  (φ={phi_deg:+.0f}°)')
            ax_crv.plot(angles_arr, np.clip(r2_arr, 0, 5.5),
                        color=C2, lw=2.2, ls=':', label=f'T₂/W  (φ={phi_deg:+.0f}°)')
        else:
            ax_crv.plot(angles_arr, sym_ratio,
                        color=COLORS['primary'], lw=2.8, label='F/W  (φ=0°)')

        # Puntos de referencia (caso simétrico)
        for ra in [0, 60, 90, 120, 150]:
            hr = np.radians(ra) / 2
            rv = 1.0 / (2.0 * np.cos(hr)) if ra > 0 else 0.5
            ax_crv.plot(ra, rv, 'o', color=COLORS['text'], ms=5, zorder=5)
            ax_crv.annotate(f'{ra}°: {rv:.2f}W',
                            xy=(ra, rv), xytext=(ra + 4, rv + 0.12),
                            fontsize=7.5, color=COLORS['text'], alpha=0.65,
                            arrowprops=dict(arrowstyle='-',
                                            color=COLORS['grid'], lw=0.5))

        # Línea vertical del ángulo actual
        ax_crv.axvline(theta_deg, color=COLORS['warning'],
                       ls='--', lw=2, alpha=0.8)

        # Marcadores del punto actual
        ax_crv.plot(theta_deg, r1, 'o', color=C1, ms=12, zorder=10,
                    label=f'T₁ actual = {T1:.2f} kN')
        ax_crv.plot(theta_deg, r2, 's', color=C2, ms=10, zorder=10,
                    label=f'T₂ actual = {T2:.2f} kN')

        # Etiqueta combinada con los valores actuales
        lx = theta_deg + 4 if theta_deg < 120 else theta_deg - 58
        ly = max(r1, r2) + 0.18
        ax_crv.text(lx, ly,
                    f'θ = {theta_deg:.0f}°   φ = {phi_deg:+.0f}°\n'
                    f'T₁ = {T1:.2f} kN  ({r1:.1%} W)\n'
                    f'T₂ = {T2:.2f} kN  ({r2:.1%} W)',
                    fontsize=9, fontweight='bold', color=COLORS['warning'],
                    bbox=dict(boxstyle='round', facecolor=COLORS['bg'],
                              edgecolor=COLORS['warning'], alpha=0.9))

        # Línea horizontal al 100 %
        ax_crv.axhline(1.0, color=COLORS['danger'], ls=':', lw=1.5, alpha=0.6)
        ax_crv.text(5, 1.05, '100 % de la carga (θ=120°, φ=0°)',
                    fontsize=9, color=COLORS['danger'], alpha=0.8)

        ax_crv.set_xlabel('Ángulo del anclaje en V  θ (grados)', fontsize=12)
        ax_crv.set_ylabel('Fuerza en brazo / Peso total', fontsize=12)
        ax_crv.set_title(
            'T₁ = W·sin(θ/2+φ)/sin θ          T₂ = W·sin(θ/2−φ)/sin θ',
            fontsize=12, fontweight='bold', color=COLORS['warning'], pad=10)
        ax_crv.set_xlim(0, 175)
        ax_crv.set_ylim(0, max(min(max_r * 1.6, 5.5), 1.5))
        ax_crv.grid(True, alpha=0.15)
        ax_crv.legend(fontsize=8.5, loc='upper left')
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        ax_crv.text(30, 0.55, 'ZONA SEGURA\n(< 90°)',
                    fontsize=9, color=COLORS['accent'],
                    ha='center', alpha=0.6, fontstyle='italic')
        ax_crv.text(105, 0.85, 'PRECAUCIÓN\n(90°-120°)',
                    fontsize=9, color=COLORS['warning'],
                    ha='center', alpha=0.6, fontstyle='italic')

        fig.canvas.draw_idle()

    sl_angle.on_changed(update)
    sl_load.on_changed(update)
    sl_phi.on_changed(update)

    fig.text(0.5, 0.92,
             'REGLA DE ORO: θ < 90° y φ < θ/2. A 120° simétrico cada brazo soporta el 100%. '
             'Si la carga sale del cono del V, un brazo pierde tensión.',
             fontsize=11, ha='center', color=COLORS['danger'],
             fontweight='bold', fontstyle='italic')

    fig.text(0.02, 0.012,
             '💡  Caso simétrico (φ=0): F=W/(2·cos θ/2)  │  '
             'Brazo flojo cuando |φ| ≥ θ/2  │  '
             'φ>0 → más carga en A₁ (izq.)  │  '
             'φ<0 → más carga en A₂ (der.)',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
