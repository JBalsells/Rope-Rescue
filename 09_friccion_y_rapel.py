"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 09: Fricción y Ecuación del Cabrestante ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización de la ecuación del cabrestante (Capstan / Euler)     ║
║  y cómo la fricción permite controlar cargas pesadas con poca      ║
║  fuerza en sistemas de rápel y descenso.                            ║
║                                                                      ║
║  Ecuación:  T_hold = T_load · e^(-μ·θ)                             ║
║  donde:                                                              ║
║   T_hold = fuerza que debe aplicar el frenador                      ║
║   T_load = fuerza de la carga                                       ║
║   μ = coeficiente de fricción                                       ║
║   θ = ángulo total de contacto (radianes)                           ║
║                                                                      ║
║  Ejecutar:  python 09_friccion_y_rapel.py                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.patches import Arc, FancyArrowPatch
from config import COLORS, G, apply_mpl_style


# Coeficientes de fricción típicos en rescate
FRICTION_COEFS = {
    'Cuerda sobre roca lisa':     0.20,
    'Cuerda sobre aluminio':      0.25,
    'Cuerda sobre acero (8/rack)': 0.30,
    'Cuerda sobre cuerda':        0.35,
    'Cuerda mojada sobre roca':   0.15,
    'Mosquetón (redirección)':    0.10,
}

# Dispositivos de descenso típicos
DEVICES = {
    'Mosquetón italiano (HMS)': {'mu': 0.25, 'wraps': 1.5},
    'Ocho (figure 8)':          {'mu': 0.30, 'wraps': 2.0},
    'Rack de barras (4 barras)': {'mu': 0.28, 'wraps': 4.0},
    'Dispositivo autoblocante':  {'mu': 0.35, 'wraps': 3.0},
    'Poste/bollard (3 vueltas)': {'mu': 0.30, 'wraps': 6.0},
}


def capstan_hold_force(load_kn, mu, wraps):
    """
    Calcula la fuerza necesaria para mantener la carga usando
    la ecuación del cabrestante.
    wraps: número de vueltas (1 vuelta = 2π radianes)
    """
    theta = wraps * 2 * np.pi
    return load_kn * np.exp(-mu * theta)


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Fricción y Ecuación del Cabrestante',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_main = fig.add_axes([0.06, 0.30, 0.42, 0.55])    # Curva principal
    ax_dev  = fig.add_axes([0.55, 0.55, 0.40, 0.30])     # Comparación dispositivos
    ax_diag = fig.add_axes([0.55, 0.30, 0.40, 0.22])     # Diagrama

    ax_sl_load = fig.add_axes([0.15, 0.17, 0.75, 0.025])
    ax_sl_mu   = fig.add_axes([0.15, 0.12, 0.75, 0.025])
    ax_sl_wrap = fig.add_axes([0.15, 0.07, 0.75, 0.025])

    sl_load = Slider(ax_sl_load, 'Carga (kg)', 10, 300, valinit=100,
                     color=COLORS['danger'], valstep=1)
    sl_mu = Slider(ax_sl_mu, 'Coef. fricción (μ)', 0.05, 0.50,
                   valinit=0.30, color=COLORS['primary'], valstep=0.01)
    sl_wrap = Slider(ax_sl_wrap, 'Vueltas de cuerda', 0.25, 8.0,
                     valinit=2.0, color=COLORS['accent'], valstep=0.25)

    def update(_=None):
        load_kg = sl_load.val
        mu = sl_mu.val
        wraps = sl_wrap.val

        load_kn = load_kg * G / 1000.0
        hold_kn = capstan_hold_force(load_kn, mu, wraps)
        hold_kg = hold_kn * 1000.0 / G
        theta_total = wraps * 2 * np.pi
        reduction_pct = (1 - hold_kn / load_kn) * 100

        # ── Curva principal: Fuerza de retención vs vueltas ───────────
        ax_main.clear()
        wraps_range = np.linspace(0.25, 8, 300)

        # Varias curvas para distintos μ
        mu_vals = [0.15, 0.25, 0.30, 0.40]
        colors_mu = [COLORS['info'], COLORS['accent'],
                     COLORS['warning'], COLORS['secondary']]
        for m, col in zip(mu_vals, colors_mu):
            F_hold = [capstan_hold_force(load_kn, m, w) for w in wraps_range]
            ax_main.plot(wraps_range, F_hold, lw=2, color=col,
                         label=f'μ = {m:.2f}')

        # Curva actual
        F_hold_current = [capstan_hold_force(load_kn, mu, w)
                          for w in wraps_range]
        ax_main.plot(wraps_range, F_hold_current, '--', lw=2.5,
                     color=COLORS['primary'],
                     label=f'Actual (μ = {mu:.2f})')

        # Punto actual
        ax_main.plot(wraps, hold_kn, 'o', color=COLORS['primary'],
                     ms=12, zorder=10)
        ax_main.annotate(
            f'{hold_kn:.3f} kN\n({hold_kg:.1f} kg)',
            xy=(wraps, hold_kn),
            xytext=(wraps + 0.5, hold_kn + load_kn * 0.1),
            fontsize=11, fontweight='bold', color=COLORS['primary'],
            arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1.5),
            bbox=dict(boxstyle='round', facecolor=COLORS['bg'],
                      edgecolor=COLORS['primary']))

        ax_main.axhline(load_kn, color=COLORS['danger'], ls=':', lw=1.5,
                        alpha=0.5)
        ax_main.text(0.3, load_kn * 1.03,
                     f'Carga total: {load_kn:.2f} kN ({load_kg:.0f} kg)',
                     fontsize=9, color=COLORS['danger'])

        ax_main.set_xlabel('Vueltas de cuerda', fontsize=12)
        ax_main.set_ylabel('Fuerza de retención (kN)', fontsize=12)
        ax_main.set_title('Fuerza necesaria para frenar la carga',
                          fontsize=13, fontweight='bold', pad=8)
        ax_main.legend(fontsize=9, facecolor=COLORS['bg'],
                       edgecolor=COLORS['grid'])
        ax_main.set_xlim(0.25, 8)
        ax_main.set_ylim(0, load_kn * 1.15)
        ax_main.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_main.spines[spine].set_visible(False)

        # ── Comparación de dispositivos ───────────────────────────────
        ax_dev.clear()
        dev_names = []
        dev_forces = []
        dev_colors = []

        sorted_devs = sorted(DEVICES.items(),
                             key=lambda x: capstan_hold_force(
                                 load_kn, x[1]['mu'], x[1]['wraps']),
                             reverse=True)

        color_cycle = [COLORS['info'], COLORS['accent'], COLORS['warning'],
                       COLORS['secondary'], COLORS['primary']]
        for i, (name, dev) in enumerate(sorted_devs):
            f_hold = capstan_hold_force(load_kn, dev['mu'], dev['wraps'])
            dev_names.append(name)
            dev_forces.append(f_hold)
            dev_colors.append(color_cycle[i % len(color_cycle)])

        bars = ax_dev.barh(dev_names, dev_forces, color=dev_colors,
                           height=0.5, alpha=0.85)
        for bar, v in zip(bars, dev_forces):
            v_kg = v * 1000 / G
            ax_dev.text(bar.get_width() + max(dev_forces) * 0.03,
                        bar.get_y() + bar.get_height() / 2,
                        f'{v:.3f} kN ({v_kg:.1f} kg)',
                        va='center', fontsize=9, color=COLORS['text'])

        ax_dev.set_xlabel('Fuerza de retención (kN)', fontsize=10)
        ax_dev.set_title(f'Dispositivos de descenso ({load_kg:.0f} kg)',
                         fontsize=11, fontweight='bold', pad=5)
        ax_dev.set_xlim(0, max(dev_forces) * 1.5)
        ax_dev.grid(axis='x', alpha=0.12)
        for spine in ('top', 'right'):
            ax_dev.spines[spine].set_visible(False)

        # ── Diagrama visual del cabrestante ───────────────────────────
        ax_diag.clear()
        ax_diag.set_xlim(-2, 2)
        ax_diag.set_ylim(-1.5, 1.5)
        ax_diag.set_aspect('equal')
        ax_diag.axis('off')

        # Cilindro/poste
        circle = plt.Circle((0, 0), 0.5, fill=True,
                             facecolor=COLORS['anchor'], edgecolor=COLORS['text'],
                             linewidth=2, alpha=0.7)
        ax_diag.add_patch(circle)
        ax_diag.text(0, 0, f'μ={mu:.2f}', ha='center', va='center',
                     fontsize=10, color=COLORS['text'], fontweight='bold')

        # Cuerda entrando (carga)
        ax_diag.annotate(
            '', xy=(-0.5, -0.3), xytext=(-1.8, -1.0),
            arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                            lw=2.5, mutation_scale=15))
        ax_diag.text(-1.8, -1.2, f'CARGA\n{load_kn:.2f} kN',
                     fontsize=10, fontweight='bold', color=COLORS['danger'],
                     ha='center')

        # Cuerda saliendo (frenador)
        ax_diag.annotate(
            '', xy=(0.5, -0.3), xytext=(1.8, -1.0),
            arrowprops=dict(arrowstyle='->', color=COLORS['accent'],
                            lw=2.5, mutation_scale=15))
        ax_diag.text(1.8, -1.2, f'RETENCIÓN\n{hold_kn:.3f} kN\n({hold_kg:.1f} kg)',
                     fontsize=10, fontweight='bold', color=COLORS['accent'],
                     ha='center')

        # Vueltas indicadas
        ax_diag.text(0, 0.9, f'{wraps:.1f} vueltas = {np.degrees(theta_total):.0f}°',
                     ha='center', fontsize=11, color=COLORS['warning'],
                     fontweight='bold')
        ax_diag.text(0, 1.2, f'Reducción: {reduction_pct:.1f}%',
                     ha='center', fontsize=12, color=COLORS['primary'],
                     fontweight='bold')

        ax_diag.set_title('Diagrama del Cabrestante',
                          fontsize=11, fontweight='bold', pad=5)

        fig.canvas.draw_idle()

    for sl in (sl_load, sl_mu, sl_wrap):
        sl.on_changed(update)

    fig.text(0.5, 0.925,
             'T_hold = T_load · e^(−μ·θ)  —  '
             'La fricción es tu amiga: permite controlar toneladas con las manos.',
             fontsize=12, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    fig.text(0.02, 0.015,
             '💡 Con 3 vueltas en un poste (μ=0.3): necesitas solo el 0.3% '
             'de la carga. Para 100kg, sostienes con ~300 gramos de fuerza. '
             'Así funcionan los dispositivos de descenso y aseguramiento.',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
