"""
╔══════════════════════════════════════════════════════════════════════╗
║          FÍSICA DEL RESCATE · Módulo 01: ¿Qué es un Newton?          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización interactiva de F = m · a y su relación con el         ║
║  peso de cargas en sistemas de rescate con cuerdas.                  ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • 1 Newton = fuerza para acelerar 1 kg a 1 m/s²                    ║
║   • Peso (N) = masa (kg) × gravedad (9.81 m/s²)                      ║
║   • 1 kN = 1000 N  ≈  102 kg de peso                                 ║
║                                                                      ║
║  Controles: Deslizadores de masa y aceleración                       ║
║  Ejecutar:  python 01_fuerza_y_newton.py                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.patches import FancyArrowPatch, Circle
from config import COLORS, G, NFPA_WORK_LOAD, ROPE_STATIC_MBS, apply_mpl_style


def draw_person(ax, x, y, scale=1.0, color='#ECEFF1'):
    """Dibuja una figura humana simplificada."""
    s = scale
    head = Circle((x, y + 0.55 * s), 0.1 * s, fill=False,
                  edgecolor=color, linewidth=2)
    ax.add_patch(head)
    ax.plot([x, x], [y + 0.45 * s, y + 0.15 * s],
            color=color, linewidth=2)
    ax.plot([x - 0.2 * s, x + 0.2 * s],
            [y + 0.38 * s, y + 0.38 * s], color=color, linewidth=2)
    ax.plot([x, x - 0.12 * s], [y + 0.15 * s, y - 0.05 * s],
            color=color, linewidth=2)
    ax.plot([x, x + 0.12 * s], [y + 0.15 * s, y - 0.05 * s],
            color=color, linewidth=2)


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — ¿Qué es un Newton?',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)
    fig.text(0.5, 0.925,
             'F = m · a   →   1 N = 1 kg × 1 m/s²   →   Peso = m × g',
             fontsize=13, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    # ── Ejes ──────────────────────────────────────────────────────────
    ax_fig = fig.add_axes([0.03, 0.22, 0.30, 0.65])       # Figura humana
    ax_bar = fig.add_axes([0.40, 0.38, 0.55, 0.52])       # Barras comparativas
    ax_crv = fig.add_axes([0.40, 0.22, 0.55, 0.12])       # Curva F vs m

    ax_sl_m = fig.add_axes([0.15, 0.11, 0.75, 0.025])
    ax_sl_a = fig.add_axes([0.15, 0.06, 0.75, 0.025])

    sl_mass = Slider(ax_sl_m, 'Masa (kg)', 1, 250, valinit=80,
                     color=COLORS['primary'], valstep=1)
    sl_acc = Slider(ax_sl_a, 'Aceleración (m/s²)', 0.1, 30.0,
                    valinit=G, color=COLORS['secondary'], valstep=0.1)

    def update(_=None):
        m = sl_mass.val
        a = sl_acc.val
        F_N = m * a
        F_kN = F_N / 1000.0
        W_kN = m * G / 1000.0

        # ── Figura humana + flecha de fuerza ──────────────────────────
        ax_fig.clear()
        ax_fig.set_xlim(-0.8, 0.8)
        ax_fig.set_ylim(-1.2, 1.2)
        ax_fig.set_aspect('equal')
        ax_fig.axis('off')

        draw_person(ax_fig, 0, 0.3, scale=0.9)

        arrow_len = min(F_kN / 2.0, 0.95)
        arrow_len = max(arrow_len, 0.15)
        ax_fig.annotate(
            '', xy=(0, -0.1 - arrow_len), xytext=(0, -0.1),
            arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                            lw=3.5, mutation_scale=22))

        ax_fig.text(0.3, -0.1 - arrow_len / 2,
                    f'F = {F_N:,.0f} N\n  = {F_kN:.2f} kN',
                    fontsize=14, fontweight='bold', color=COLORS['danger'],
                    va='center')
        ax_fig.text(0, 1.05, f'{m:.0f} kg',
                    fontsize=16, fontweight='bold', color=COLORS['primary'],
                    ha='center')
        ax_fig.set_title('Fuerza sobre la carga',
                         fontsize=12, color=COLORS['text'], pad=5)

        # ── Barras comparativas ───────────────────────────────────────
        ax_bar.clear()

        # Fuerza de choque aproximada (caída factor 1, cuerda dinámica)
        f_shock_kN = m * G * 1.77 / 1000.0  # Aprox. con elongación 40%

        scenarios = [
            ('Tu configuración\n(F = m·a)',         F_kN,              COLORS['warning']),
            (f'Peso en reposo\n({m:.0f} kg × g)',   W_kN,              COLORS['primary']),
            ('Rescatista + paciente\n(160 kg × g)',  160 * G / 1000,    COLORS['info']),
            ('Fuerza de choque\n(caída factor 1)',   f_shock_kN,        COLORS['secondary']),
            ('Carga de trabajo\nNFPA 1983',          NFPA_WORK_LOAD,    COLORS['danger']),
            ('Rotura cuerda\nestática 11mm',         ROPE_STATIC_MBS,   COLORS['accent']),
        ]

        names = [s[0] for s in scenarios]
        vals  = [s[1] for s in scenarios]
        cols  = [s[2] for s in scenarios]

        bars = ax_bar.barh(names, vals, color=cols, height=0.55,
                           edgecolor='white', linewidth=0.3, alpha=0.88)
        for bar, v in zip(bars, vals):
            ax_bar.text(bar.get_width() + 0.25,
                        bar.get_y() + bar.get_height() / 2,
                        f'{v:.2f} kN', va='center', fontsize=10,
                        fontweight='bold', color=COLORS['text'])

        ax_bar.set_xlabel('Fuerza (kN)', fontsize=11)
        ax_bar.set_xlim(0, max(vals) * 1.25)
        ax_bar.set_title('Comparación de Fuerzas Típicas en Rescate',
                         fontsize=13, fontweight='bold', color=COLORS['text'],
                         pad=8)
        ax_bar.grid(axis='x', alpha=0.15)
        for spine in ('top', 'right'):
            ax_bar.spines[spine].set_visible(False)

        # ── Curva F vs masa ───────────────────────────────────────────
        ax_crv.clear()
        masses = np.linspace(1, 250, 300)
        forces = masses * a / 1000.0
        ax_crv.plot(masses, forces, color=COLORS['primary'], linewidth=2)
        ax_crv.axvline(m, color=COLORS['warning'], ls='--', lw=1.2, alpha=0.7)
        ax_crv.axhline(F_kN, color=COLORS['warning'], ls='--', lw=1.2, alpha=0.7)
        ax_crv.plot(m, F_kN, 'o', color=COLORS['warning'], ms=8, zorder=5)
        ax_crv.set_xlabel('Masa (kg)', fontsize=10)
        ax_crv.set_ylabel('F (kN)', fontsize=10)
        ax_crv.set_title(f'Fuerza vs Masa  (a = {a:.1f} m/s²)',
                         fontsize=10, pad=4)
        ax_crv.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        fig.canvas.draw_idle()

    sl_mass.on_changed(update)
    sl_acc.on_changed(update)

    fig.text(0.02, 0.015,
             '💡 1 Newton ≈ el peso de una manzana pequeña  │  '
             '1 kN ≈ 102 kg  │  '
             'Peso de persona 80 kg = 784.8 N = 0.785 kN  │  '
             'En rescate trabajamos en kilo-Newtons (kN)',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
