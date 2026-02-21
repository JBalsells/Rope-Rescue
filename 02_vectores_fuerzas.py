"""
╔══════════════════════════════════════════════════════════════════════╗
║          FÍSICA DEL RESCATE · Módulo 02: Vectores y Fuerzas          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización interactiva de suma de vectores de fuerza             ║
║  aplicada a puntos de anclaje en rescate.                            ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • Un vector tiene magnitud Y dirección                             ║
║   • Las fuerzas se suman vectorialmente                              ║
║   • La resultante determina la carga real en un anclaje              ║
║                                                                      ║
║  Controles: Deslizadores de ángulo y magnitud para 2 fuerzas         ║
║  Ejecutar:  python 02_vectores_fuerzas.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, apply_mpl_style


def draw_anchor(ax, x, y, size=0.08):
    """Dibuja un símbolo de anclaje."""
    ax.plot(x, y, 's', color=COLORS['anchor'], markersize=14, zorder=10)
    ax.plot(x, y, 'o', color=COLORS['text'], markersize=5, zorder=11)


def draw_vector(ax, origin, angle_deg, magnitude, color, label,
                max_display=3.0):
    """Dibuja un vector de fuerza con etiqueta."""
    angle_rad = np.radians(angle_deg)
    scale = magnitude / max_display * 2.5
    dx = scale * np.cos(angle_rad)
    dy = scale * np.sin(angle_rad)

    ax.annotate(
        '', xy=(origin[0] + dx, origin[1] + dy), xytext=origin,
        arrowprops=dict(arrowstyle='->', color=color, lw=2.8,
                        mutation_scale=18))

    label_x = origin[0] + dx * 1.15
    label_y = origin[1] + dy * 1.15
    ax.text(label_x, label_y,
            f'{label}\n{magnitude:.2f} kN',
            fontsize=10, fontweight='bold', color=color,
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                      edgecolor=color, alpha=0.85))

    return dx, dy


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Vectores y Suma de Fuerzas',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_vec = fig.add_axes([0.03, 0.22, 0.50, 0.68])
    ax_info = fig.add_axes([0.58, 0.35, 0.38, 0.55])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_a1 = fig.add_axes([0.15, 0.14, 0.33, 0.025])
    ax_m1 = fig.add_axes([0.15, 0.10, 0.33, 0.025])
    ax_a2 = fig.add_axes([0.58, 0.14, 0.33, 0.025])
    ax_m2 = fig.add_axes([0.58, 0.10, 0.33, 0.025])

    sl_ang1 = Slider(ax_a1, 'Ángulo F₁ (°)', -180, 180, valinit=-120,
                     color=COLORS['info'], valstep=1)
    sl_mag1 = Slider(ax_m1, 'Magnitud F₁ (kN)', 0.1, 5.0, valinit=0.78,
                     color=COLORS['info'], valstep=0.01)
    sl_ang2 = Slider(ax_a2, 'Ángulo F₂ (°)', -180, 180, valinit=-60,
                     color=COLORS['accent'], valstep=1)
    sl_mag2 = Slider(ax_m2, 'Magnitud F₂ (kN)', 0.1, 5.0, valinit=0.78,
                     color=COLORS['accent'], valstep=0.01)

    def update(_=None):
        a1, m1 = sl_ang1.val, sl_mag1.val
        a2, m2 = sl_ang2.val, sl_mag2.val

        # ── Vectores ──────────────────────────────────────────────────
        ax_vec.clear()
        ax_vec.set_xlim(-3.5, 3.5)
        ax_vec.set_ylim(-3.5, 3.0)
        ax_vec.set_aspect('equal')
        ax_vec.grid(True, alpha=0.12)
        ax_vec.axhline(0, color=COLORS['grid'], lw=0.5)
        ax_vec.axvline(0, color=COLORS['grid'], lw=0.5)
        ax_vec.set_title('Punto de anclaje: Suma de fuerzas',
                         fontsize=13, fontweight='bold', pad=8)

        origin = (0, 0)
        draw_anchor(ax_vec, 0, 0)

        max_d = max(m1, m2, 1.5)
        dx1, dy1 = draw_vector(ax_vec, origin, a1, m1, COLORS['info'],
                               'F₁', max_d)
        dx2, dy2 = draw_vector(ax_vec, origin, a2, m2, COLORS['accent'],
                               'F₂', max_d)

        # Resultante
        rx, ry = dx1 + dx2, dy1 + dy2
        r_mag = np.sqrt(rx**2 + ry**2)
        r_mag_real = m1 * np.cos(np.radians(a1)) + m2 * np.cos(np.radians(a2))
        r_mag_real_y = m1 * np.sin(np.radians(a1)) + m2 * np.sin(np.radians(a2))
        resultant_kN = np.sqrt(
            (m1 * np.cos(np.radians(a1)) + m2 * np.cos(np.radians(a2)))**2 +
            (m1 * np.sin(np.radians(a1)) + m2 * np.sin(np.radians(a2)))**2
        )
        r_angle = np.degrees(np.arctan2(ry, rx))

        # Paralelogramo (líneas punteadas)
        ax_vec.plot([dx1, dx1 + dx2], [dy1, dy1 + dy2],
                    '--', color=COLORS['accent'], alpha=0.4, lw=1.2)
        ax_vec.plot([dx2, dx1 + dx2], [dy2, dy1 + dy2],
                    '--', color=COLORS['info'], alpha=0.4, lw=1.2)

        # Flecha resultante
        ax_vec.annotate(
            '', xy=(rx, ry), xytext=origin,
            arrowprops=dict(arrowstyle='->', color=COLORS['warning'],
                            lw=3.5, mutation_scale=22))
        ax_vec.text(rx * 1.12, ry * 1.12,
                    f'R = {resultant_kN:.2f} kN',
                    fontsize=12, fontweight='bold', color=COLORS['warning'],
                    ha='center',
                    bbox=dict(boxstyle='round,pad=0.3',
                              facecolor=COLORS['bg'],
                              edgecolor=COLORS['warning'], alpha=0.9))

        # Arco del ángulo entre F1 y F2
        angle_between = abs(a1 - a2)
        if angle_between > 180:
            angle_between = 360 - angle_between
        theta_start = min(a1, a2)
        theta_end = max(a1, a2)
        thetas = np.linspace(np.radians(theta_start),
                             np.radians(theta_end), 50)
        arc_r = 0.5
        ax_vec.plot(arc_r * np.cos(thetas), arc_r * np.sin(thetas),
                    color=COLORS['warning'], lw=1.5, alpha=0.7)
        mid_a = np.radians((a1 + a2) / 2)
        ax_vec.text(0.7 * np.cos(mid_a), 0.7 * np.sin(mid_a),
                    f'{angle_between:.0f}°',
                    fontsize=10, color=COLORS['warning'], ha='center',
                    va='center')

        for spine in ax_vec.spines.values():
            spine.set_visible(False)
        ax_vec.set_xticks([])
        ax_vec.set_yticks([])

        # ── Panel informativo ─────────────────────────────────────────
        ax_info.clear()
        ax_info.axis('off')

        info_lines = [
            ('DATOS DEL SISTEMA', COLORS['primary'], 16, 'bold'),
            ('', '', 8, ''),
            (f'Fuerza F₁:  {m1:.2f} kN  a  {a1:.0f}°', COLORS['info'], 12, 'normal'),
            (f'Fuerza F₂:  {m2:.2f} kN  a  {a2:.0f}°', COLORS['accent'], 12, 'normal'),
            ('', '', 8, ''),
            (f'Ángulo entre fuerzas:  {angle_between:.0f}°', COLORS['warning'], 12, 'bold'),
            (f'Resultante R:  {resultant_kN:.2f} kN', COLORS['warning'], 14, 'bold'),
            (f'Dirección R:  {r_angle:.1f}°', COLORS['warning'], 12, 'normal'),
            ('', '', 8, ''),
            ('─' * 35, COLORS['grid'], 9, 'normal'),
            ('', '', 6, ''),
            ('INTERPRETACIÓN PARA RESCATE:', COLORS['danger'], 13, 'bold'),
            ('', '', 4, ''),
        ]

        # Safety interpretation
        if angle_between < 60:
            safety = ('✓ Ángulo estrecho: las fuerzas se suman\n'
                      '   casi directamente. Eficiente.')
            safety_color = COLORS['accent']
        elif angle_between < 120:
            safety = ('⚠ Ángulo moderado: la resultante es\n'
                      '   menor que la suma aritmética.')
            safety_color = COLORS['warning']
        else:
            safety = ('⚠ Ángulo amplio: poca eficiencia.\n'
                      '   Las fuerzas se oponen parcialmente.')
            safety_color = COLORS['danger']

        info_lines.append((safety, safety_color, 11, 'normal'))
        info_lines.append(('', '', 8, ''))

        sum_arith = m1 + m2
        efficiency = resultant_kN / sum_arith * 100 if sum_arith > 0 else 0
        info_lines.append(
            (f'Eficiencia vectorial: {efficiency:.1f}%', COLORS['text'], 11, 'bold'))
        info_lines.append(
            (f'(|R| / (|F₁|+|F₂|) = {resultant_kN:.2f}/{sum_arith:.2f})',
             COLORS['text'], 9, 'normal'))

        y_pos = 0.97
        for text, color, size, weight in info_lines:
            if not text:
                y_pos -= 0.03
                continue
            ax_info.text(0.05, y_pos, text, fontsize=size,
                         fontweight=weight if weight else 'normal',
                         color=color, transform=ax_info.transAxes,
                         verticalalignment='top', family='monospace')
            y_pos -= 0.07 if size >= 12 else 0.05

        fig.canvas.draw_idle()

    for sl in (sl_ang1, sl_mag1, sl_ang2, sl_mag2):
        sl.on_changed(update)

    fig.text(0.02, 0.015,
             '💡 En rescate, las fuerzas nunca se suman aritméticamente. '
             'Siempre hay que considerar la dirección (vector). '
             'Esto es crítico en anclajes, desviadores y tirolesas.',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')
    fig.text(0.5, 0.045,
             'R = √(F₁² + F₂² + 2·F₁·F₂·cos θ)',
             fontsize=12, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
