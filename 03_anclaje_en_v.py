"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 03: Anclaje en V                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  Análisis interactivo de cómo el ángulo del anclaje en V             ║
║  afecta la fuerza en cada brazo del sistema.                         ║
║                                                                      ║
║  Fórmula clave:  F_brazo = W / (2 · cos(θ/2))                        ║
║                                                                      ║
║   θ =   0° → F = 0.50W (cada brazo lleva la mitad)                   ║
║   θ =  60° → F = 0.58W                                               ║
║   θ =  90° → F = 0.71W                                               ║
║   θ = 120° → F = 1.00W  ← ¡cada brazo carga el 100%!                ║
║   θ = 150° → F = 1.93W  ← ¡casi el doble!                           ║
║   θ → 180° → F → ∞                                                 ║
║                                                                      ║
║  Ejecutar:  python 03_anclaje_en_v.py                                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.patches import FancyArrowPatch, Polygon
from config import COLORS, G, NFPA_WORK_LOAD, apply_mpl_style


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Anclaje en V: Ángulo vs Fuerza',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_v   = fig.add_axes([0.03, 0.25, 0.38, 0.62])   # Diagrama de la V
    ax_crv = fig.add_axes([0.48, 0.25, 0.48, 0.62])   # Curva ángulo vs fuerza

    ax_sl_ang  = fig.add_axes([0.15, 0.12, 0.75, 0.025])
    ax_sl_load = fig.add_axes([0.15, 0.07, 0.75, 0.025])

    sl_angle = Slider(ax_sl_ang, 'Ángulo V (°)', 0, 175, valinit=60,
                      color=COLORS['primary'], valstep=1)
    sl_load = Slider(ax_sl_load, 'Carga (kg)', 10, 300, valinit=100,
                     color=COLORS['secondary'], valstep=1)

    def update(_=None):
        theta_deg = sl_angle.val
        mass = sl_load.val
        W_kN = mass * G / 1000.0
        theta_rad = np.radians(theta_deg)
        half_theta = theta_rad / 2.0

        # Fuerza en cada brazo
        if np.cos(half_theta) > 0.01:
            F_arm_kN = W_kN / (2.0 * np.cos(half_theta))
        else:
            F_arm_kN = 99.99
        F_ratio = F_arm_kN / W_kN

        # ── Diagrama de la V ──────────────────────────────────────────
        ax_v.clear()
        ax_v.set_xlim(-2.5, 2.5)
        ax_v.set_ylim(-2.5, 1.5)
        ax_v.set_aspect('equal')
        ax_v.axis('off')
        ax_v.set_title('Diagrama del Anclaje en V',
                       fontsize=13, fontweight='bold', pad=8)

        # Puntos de anclaje y punto central
        arm_len = 1.8
        anchor_L = (-arm_len * np.sin(half_theta), 0)
        anchor_R = (arm_len * np.sin(half_theta), 0)
        load_pt = (0, -arm_len * np.cos(half_theta))

        # Pared / línea de anclajes
        ax_v.plot([-2.3, 2.3], [0, 0], color=COLORS['anchor'], lw=3)
        ax_v.fill_between([-2.3, 2.3], [0, 0], [0.3, 0.3],
                          color=COLORS['anchor'], alpha=0.15)

        # Puntos de anclaje
        for ax_pt, label in [(anchor_L, 'A₁'), (anchor_R, 'A₂')]:
            ax_v.plot(*ax_pt, 'D', color=COLORS['accent'], markersize=12,
                      zorder=5)
            ax_v.text(ax_pt[0], ax_pt[1] + 0.2, label,
                      ha='center', fontsize=11, fontweight='bold',
                      color=COLORS['accent'])

        # Brazos de la V
        arm_color = COLORS['rope']
        if theta_deg > 120:
            arm_color = COLORS['danger']
        elif theta_deg > 90:
            arm_color = COLORS['warning']

        ax_v.plot([anchor_L[0], load_pt[0]], [anchor_L[1], load_pt[1]],
                  color=arm_color, lw=3, zorder=3)
        ax_v.plot([anchor_R[0], load_pt[0]], [anchor_R[1], load_pt[1]],
                  color=arm_color, lw=3, zorder=3)

        # Punto central (mosquetón / placa)
        ax_v.plot(*load_pt, 'o', color=COLORS['warning'], markersize=14,
                  zorder=6)

        # Flecha de carga (peso)
        arrow_len = min(W_kN * 0.6, 1.0)
        ax_v.annotate(
            '', xy=(load_pt[0], load_pt[1] - arrow_len),
            xytext=load_pt,
            arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                            lw=3, mutation_scale=20))
        ax_v.text(0, load_pt[1] - arrow_len - 0.15,
                  f'W = {W_kN:.2f} kN\n({mass:.0f} kg)',
                  ha='center', fontsize=11, fontweight='bold',
                  color=COLORS['danger'])

        # Flechas de tensión en cada brazo
        for anchor in [anchor_L, anchor_R]:
            mid_x = (anchor[0] + load_pt[0]) / 2
            mid_y = (anchor[1] + load_pt[1]) / 2
            sign = 1 if anchor[0] >= 0 else -1
            ax_v.text(mid_x + sign * 0.25, mid_y,
                      f'{F_arm_kN:.2f} kN',
                      fontsize=10, fontweight='bold', color=arm_color,
                      ha='center', va='center',
                      bbox=dict(boxstyle='round,pad=0.2',
                                facecolor=COLORS['bg'],
                                edgecolor=arm_color, alpha=0.85))

        # Arco del ángulo
        arc_r = 0.55
        arc_start = -np.pi / 2 - half_theta
        arc_end = -np.pi / 2 + half_theta
        arc_thetas = np.linspace(arc_start, arc_end, 50)
        ax_v.plot(load_pt[0] + arc_r * np.cos(arc_thetas),
                  load_pt[1] + arc_r * np.sin(arc_thetas),
                  color=COLORS['warning'], lw=1.5)
        ax_v.text(load_pt[0],
                  load_pt[1] + arc_r + 0.15,
                  f'θ = {theta_deg:.0f}°',
                  ha='center', fontsize=12, fontweight='bold',
                  color=COLORS['warning'])

        # Indicador de seguridad
        if theta_deg <= 90:
            status = '✓ SEGURO'
            st_color = COLORS['accent']
        elif theta_deg <= 120:
            status = '⚠ PRECAUCIÓN'
            st_color = COLORS['warning']
        else:
            status = '✗ PELIGROSO'
            st_color = COLORS['danger']

        ax_v.text(0, -2.3,
                  f'{status}  —  Cada brazo: {F_ratio:.1%} de la carga',
                  ha='center', fontsize=13, fontweight='bold',
                  color=st_color,
                  bbox=dict(boxstyle='round,pad=0.4',
                            facecolor=COLORS['bg'],
                            edgecolor=st_color, alpha=0.9))

        # ── Curva ángulo vs multiplicador de fuerza ───────────────────
        ax_crv.clear()
        angles = np.linspace(0, 175, 500)
        half_angles = np.radians(angles) / 2.0
        ratios = 1.0 / (2.0 * np.cos(half_angles))

        # Zonas coloreadas
        ax_crv.axhspan(0, 0.75, facecolor=COLORS['accent'], alpha=0.07)
        ax_crv.axhspan(0.75, 1.0, facecolor=COLORS['warning'], alpha=0.07)
        ax_crv.axhspan(1.0, 5.0, facecolor=COLORS['danger'], alpha=0.07)

        ax_crv.plot(angles, ratios, color=COLORS['primary'], lw=3)

        # Marcadores de referencia
        ref_angles = [0, 60, 90, 120, 150]
        for ra in ref_angles:
            hr = np.radians(ra) / 2
            rv = 1.0 / (2.0 * np.cos(hr))
            ax_crv.plot(ra, rv, 'o', color=COLORS['text'], ms=6, zorder=5)
            ax_crv.annotate(
                f'{ra}°: {rv:.2f}W',
                xy=(ra, rv), xytext=(ra + 5, rv + 0.15),
                fontsize=8, color=COLORS['text'], alpha=0.7,
                arrowprops=dict(arrowstyle='-', color=COLORS['grid'],
                                lw=0.5))

        # Línea del ángulo actual
        ax_crv.axvline(theta_deg, color=COLORS['warning'], ls='--', lw=2,
                       alpha=0.8)
        ax_crv.axhline(F_ratio, color=COLORS['warning'], ls='--', lw=1.5,
                       alpha=0.5)
        ax_crv.plot(theta_deg, F_ratio, 'o', color=COLORS['warning'],
                    ms=12, zorder=10)
        ax_crv.text(theta_deg + 3, F_ratio + 0.15,
                    f'θ={theta_deg:.0f}°\nF={F_arm_kN:.2f} kN\n({F_ratio:.1%} W)',
                    fontsize=10, fontweight='bold', color=COLORS['warning'],
                    bbox=dict(boxstyle='round', facecolor=COLORS['bg'],
                              edgecolor=COLORS['warning'], alpha=0.9))

        # Línea horizontal en 100%
        ax_crv.axhline(1.0, color=COLORS['danger'], ls=':', lw=1.5,
                       alpha=0.6)
        ax_crv.text(5, 1.05, '100% de la carga (θ = 120°)',
                    fontsize=9, color=COLORS['danger'], alpha=0.8)

        ax_crv.set_xlabel('Ángulo del anclaje en V (grados)', fontsize=12)
        ax_crv.set_ylabel('Fuerza en cada brazo / Peso total', fontsize=12)
        ax_crv.set_title('F_brazo = W / (2 · cos(θ/2))',
                         fontsize=14, fontweight='bold',
                         color=COLORS['warning'], pad=10)
        ax_crv.set_xlim(0, 175)
        ax_crv.set_ylim(0, min(F_ratio * 1.5, 5.0))
        ax_crv.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        # Etiquetas de zonas
        ax_crv.text(30, 0.55, 'ZONA SEGURA\n(< 90°)',
                    fontsize=9, color=COLORS['accent'],
                    ha='center', alpha=0.6, fontstyle='italic')
        ax_crv.text(105, 0.85, 'PRECAUCIÓN\n(90°-120°)',
                    fontsize=9, color=COLORS['warning'],
                    ha='center', alpha=0.6, fontstyle='italic')

        fig.canvas.draw_idle()

    sl_angle.on_changed(update)
    sl_load.on_changed(update)

    fig.text(0.5, 0.92,
             'REGLA DE ORO: Nunca exceder 90° en un anclaje en V. '
             'A 120° cada brazo soporta el 100% de la carga.',
             fontsize=12, ha='center', color=COLORS['danger'],
             fontweight='bold', fontstyle='italic')

    fig.text(0.02, 0.015,
             '💡 F_brazo = W / (2·cos(θ/2))  │  '
             'A 0° cada brazo lleva 50%  │  '
             'A 120° cada brazo lleva 100%  │  '
             'A 150° cada brazo lleva 193% — ¡Riesgo de fallo!',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
