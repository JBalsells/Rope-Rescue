"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 05: Elasticidad de la Cuerda     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Curvas de fuerza-elongación para diferentes tipos de cuerda.       ║
║  Comparación entre cuerdas dinámicas, semiestáticas y estáticas.    ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • Elongación: cuánto se estira la cuerda bajo carga              ║
║   • Cuerda dinámica: 25-35% elongación (absorbe energía)           ║
║   • Cuerda estática: 1-3% elongación (eficiente para izar)         ║
║   • Área bajo la curva = energía absorbida                          ║
║   • Mayor absorción de energía = menor fuerza de choque            ║
║                                                                      ║
║  Controles: Deslizador de fuerza aplicada                           ║
║  Ejecutar:  python 05_elasticidad_cuerda.py                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, apply_mpl_style


# ── Modelos de cuerda (simplificado - realista) ──────────────────
# Cada cuerda se modela con: elongación_max (%), fuerza_rotura (kN),
# y un parámetro de curvatura para la forma de la curva F vs ε.

ROPES = {
    'Dinámica 10mm\n(escalada)': {
        'color':       '#4CAF50',
        'max_elong':   35.0,     # % a rotura
        'mbs':         24.0,     # kN
        'work_elong':  8.0,      # % a carga de trabajo (80kg)
        'curve_power': 1.4,      # forma de la curva
        'style':       '-',
    },
    'Semiestática 10.5mm\n(rescate)': {
        'color':       '#FFC107',
        'max_elong':   6.0,
        'mbs':         28.0,
        'work_elong':  2.5,
        'curve_power': 1.2,
        'style':       '-',
    },
    'Estática 11mm\n(rescate/espeleología)': {
        'color':       '#F44336',
        'max_elong':   3.0,
        'mbs':         30.0,
        'work_elong':  1.0,
        'curve_power': 1.1,
        'style':       '-',
    },
    'Dyneema 8mm\n(muy baja elongación)': {
        'color':       '#2196F3',
        'max_elong':   1.5,
        'mbs':         32.0,
        'work_elong':  0.3,
        'curve_power': 1.05,
        'style':       '--',
    },
}


def rope_curve(elongation_pct, rope):
    """Genera la curva fuerza vs elongación para un tipo de cuerda."""
    e_max = rope['max_elong']
    f_max = rope['mbs']
    p = rope['curve_power']
    # Modelo: F = F_max * (ε / ε_max)^p
    normalized = np.clip(elongation_pct / e_max, 0, 1)
    return f_max * normalized ** p


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Elasticidad de la Cuerda',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)
    fig.text(0.5, 0.925,
             'La elasticidad de la cuerda es lo que te salva la vida. '
             'Absorbe energía y reduce la fuerza de choque.',
             fontsize=12, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    ax_main = fig.add_axes([0.08, 0.28, 0.52, 0.60])
    ax_energy = fig.add_axes([0.67, 0.55, 0.30, 0.33])
    ax_compare = fig.add_axes([0.67, 0.28, 0.30, 0.22])

    ax_sl = fig.add_axes([0.15, 0.10, 0.75, 0.025])
    sl_force = Slider(ax_sl, 'Fuerza aplicada (kN)', 0.1, 25.0,
                      valinit=2.0, color=COLORS['primary'], valstep=0.1)

    def update(_=None):
        F_applied = sl_force.val

        # ── Curvas principales ────────────────────────────────────────
        ax_main.clear()

        for name, rope in ROPES.items():
            elong = np.linspace(0, rope['max_elong'] * 1.05, 500)
            force = rope_curve(elong, rope)

            ax_main.plot(elong, force, color=rope['color'],
                         lw=2.5, ls=rope['style'], label=name)

            # Marcar rotura
            ax_main.plot(rope['max_elong'], rope['mbs'], 'x',
                         color=rope['color'], ms=12, mew=3)

            # Elongación a la fuerza aplicada
            if F_applied <= rope['mbs']:
                # Encontrar elongación correspondiente
                e_at_f = rope['max_elong'] * (F_applied / rope['mbs']) ** (
                    1.0 / rope['curve_power'])
                ax_main.plot(e_at_f, F_applied, 'o', color=rope['color'],
                             ms=8, zorder=5)

        # Línea de fuerza aplicada
        ax_main.axhline(F_applied, color=COLORS['warning'], ls='--', lw=1.5,
                        alpha=0.7)
        ax_main.text(0.2, F_applied + 0.5,
                     f'F = {F_applied:.1f} kN',
                     fontsize=11, color=COLORS['warning'], fontweight='bold')

        # Líneas de referencia
        ax_main.axhline(0.78, color=COLORS['text'], ls=':', lw=0.8,
                        alpha=0.4)
        ax_main.text(0.2, 0.78 + 0.3, 'Peso 80kg (0.78 kN)',
                     fontsize=8, color=COLORS['text'], alpha=0.5)

        ax_main.axhline(12.0, color=COLORS['danger'], ls=':', lw=1,
                        alpha=0.5)
        ax_main.text(0.2, 12.3, 'Límite UIAA (12 kN)',
                     fontsize=9, color=COLORS['danger'], alpha=0.7)

        ax_main.set_xlabel('Elongación (%)', fontsize=13)
        ax_main.set_ylabel('Fuerza (kN)', fontsize=13)
        ax_main.set_title('Curvas Fuerza vs Elongación',
                          fontsize=14, fontweight='bold', pad=8)
        ax_main.legend(loc='upper left', fontsize=9,
                       facecolor=COLORS['bg'], edgecolor=COLORS['grid'])
        ax_main.set_xlim(0, 40)
        ax_main.set_ylim(0, 35)
        ax_main.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_main.spines[spine].set_visible(False)

        # ── Energía absorbida (área bajo la curva) ────────────────────
        ax_energy.clear()
        energy_data = {}

        for name, rope in ROPES.items():
            short_name = name.split('\n')[0]
            if F_applied <= rope['mbs']:
                e_at_f = rope['max_elong'] * (
                    F_applied / rope['mbs']) ** (1.0 / rope['curve_power'])
                elong = np.linspace(0, e_at_f, 200)
                force = rope_curve(elong, rope)
                # Energía = integral (área bajo curva), normalizada por longitud
                # E = ∫F dε (en kN·%)
                energy = np.trapz(force, elong)
                energy_data[short_name] = energy

                ax_energy.fill_between(elong, 0, force,
                                       color=rope['color'], alpha=0.15)
                ax_energy.plot(elong, force, color=rope['color'],
                               lw=1.5, ls=rope['style'])
            else:
                energy_data[short_name] = 0

        ax_energy.set_xlabel('Elongación (%)', fontsize=9)
        ax_energy.set_ylabel('Fuerza (kN)', fontsize=9)
        ax_energy.set_title(f'Energía absorbida a {F_applied:.1f} kN\n'
                            '(área bajo la curva)',
                            fontsize=10, fontweight='bold', pad=5)
        ax_energy.grid(True, alpha=0.12)
        for spine in ('top', 'right'):
            ax_energy.spines[spine].set_visible(False)

        # ── Comparación de energía absorbida ──────────────────────────
        ax_compare.clear()
        if energy_data:
            names = list(energy_data.keys())
            values = list(energy_data.values())
            rope_colors = [ROPES[n + '\n' + list(ROPES.keys())[i].split('\n')[1]]['color']
                           if i < len(ROPES) else COLORS['text']
                           for i, n in enumerate(names)]
            # Simpler color mapping
            all_ropes = list(ROPES.values())
            rope_colors = [all_ropes[i]['color'] for i in range(len(names))]

            bars = ax_compare.barh(names, values, color=rope_colors,
                                   height=0.5, alpha=0.8)
            for bar, v in zip(bars, values):
                if v > 0:
                    ax_compare.text(
                        bar.get_width() + max(values) * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        f'{v:.1f}', va='center', fontsize=9,
                        color=COLORS['text'])

            ax_compare.set_xlabel('Energía (kN·%)', fontsize=9)
            ax_compare.set_title('Capacidad de absorción',
                                 fontsize=10, fontweight='bold', pad=5)
        ax_compare.grid(axis='x', alpha=0.12)
        for spine in ('top', 'right'):
            ax_compare.spines[spine].set_visible(False)

        fig.canvas.draw_idle()

    sl_force.on_changed(update)

    fig.text(0.02, 0.015,
             '💡 La cuerda DINÁMICA absorbe mucha más energía que la estática. '
             'Por eso se usa en escalada (caídas posibles). '
             'La cuerda ESTÁTICA se usa en rescate donde NO debe haber caídas.',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')
    fig.text(0.02, 0.04,
             '× = Punto de rotura  │  ○ = Elongación a la fuerza seleccionada',
             fontsize=9, color=COLORS['text'], alpha=0.6)

    update()
    plt.show()


if __name__ == '__main__':
    main()
