"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 08: Fuerza de Choque             ║
╠══════════════════════════════════════════════════════════════════════╣
║  Cálculo interactivo de la fuerza de impacto generada durante      ║
║  una caída, según la fórmula de Dodero.                             ║
║                                                                      ║
║  Fórmula:  F = m·g · (1 + √(1 + 2·ff / (m·g·κ)))                 ║
║  donde κ = elongación unitaria de la cuerda (m/N por m de cuerda)  ║
║                                                                      ║
║  Factores que afectan la fuerza de choque:                          ║
║   • Factor de caída (ff): más ff = más fuerza                      ║
║   • Masa: más masa = más fuerza                                     ║
║   • Elasticidad de la cuerda (κ): más elástica = menos fuerza      ║
║   • Longitud de cuerda NO afecta (solo el factor de caída)         ║
║                                                                      ║
║  Ejecutar:  python 08_fuerza_de_choque.py                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, UIAA_MAX_IMPACT, ROPE_STATIC_MBS, apply_mpl_style


# Coeficientes de elongación (κ) típicos (m/N por metro de cuerda)
# κ = elongación_relativa / fuerza = (ΔL/L) / F
ROPE_KAPPA = {
    'Dinámica (escalada)':      1.8e-4,   # ~35% elong a rotura ~24kN
    'Semiestática (rescate)':   2.5e-5,   # ~6% a rotura ~28kN
    'Estática (espeleología)':  1.2e-5,   # ~3% a rotura ~30kN
}


def impact_force(mass, ff, kappa):
    """
    Calcula la fuerza de choque usando la fórmula de Dodero.
    mass: masa (kg)
    ff: factor de caída (0-2)
    kappa: coeficiente de elongación de la cuerda (m/N·m)
    Retorna: fuerza en kN
    """
    mg = mass * G
    if kappa <= 0 or ff <= 0:
        return mg / 1000.0
    discriminant = 1 + 2 * ff / (mg * kappa)
    F = mg * (1 + np.sqrt(discriminant))
    return F / 1000.0


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Fuerza de Choque (Impacto)',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_main = fig.add_axes([0.06, 0.32, 0.42, 0.55])
    ax_mass = fig.add_axes([0.55, 0.55, 0.40, 0.32])
    ax_bar  = fig.add_axes([0.55, 0.32, 0.40, 0.18])

    ax_sl_ff   = fig.add_axes([0.15, 0.18, 0.75, 0.025])
    ax_sl_m    = fig.add_axes([0.15, 0.13, 0.75, 0.025])
    ax_sl_elong = fig.add_axes([0.15, 0.08, 0.75, 0.025])

    sl_ff = Slider(ax_sl_ff, 'Factor de caída', 0.01, 2.0, valinit=1.0,
                   color=COLORS['secondary'], valstep=0.01)
    sl_m = Slider(ax_sl_m, 'Masa (kg)', 40, 200, valinit=80,
                  color=COLORS['primary'], valstep=1)
    sl_elong = Slider(ax_sl_elong, 'Elongación cuerda (%)', 1, 40,
                      valinit=8, color=COLORS['accent'], valstep=0.5)

    def update(_=None):
        ff = sl_ff.val
        mass = sl_m.val
        elong_pct = sl_elong.val

        # Convertir elongación % a kappa
        # κ ≈ (elong/100) / (masa_ref * G) donde masa_ref = 80kg
        kappa = (elong_pct / 100.0) / (80 * G)

        F_impact_kN = impact_force(mass, ff, kappa)
        W_kN = mass * G / 1000.0

        # ── Gráfico principal: F vs factor de caída ───────────────────
        ax_main.clear()
        ff_range = np.linspace(0.01, 2.0, 300)

        for name, kp in ROPE_KAPPA.items():
            F_vals = [impact_force(mass, f, kp) for f in ff_range]
            ax_main.plot(ff_range, F_vals, lw=2.5, label=name)

        # Curva con la elongación seleccionada
        F_custom = [impact_force(mass, f, kappa) for f in ff_range]
        ax_main.plot(ff_range, F_custom, '--', color=COLORS['warning'],
                     lw=2, label=f'Seleccionada ({elong_pct:.0f}%)')

        # Punto actual
        ax_main.plot(ff, F_impact_kN, 'o', color=COLORS['warning'],
                     ms=12, zorder=10)
        ax_main.annotate(
            f'{F_impact_kN:.1f} kN',
            xy=(ff, F_impact_kN),
            xytext=(ff + 0.15, F_impact_kN + 1.5),
            fontsize=12, fontweight='bold', color=COLORS['warning'],
            arrowprops=dict(arrowstyle='->', color=COLORS['warning'], lw=1.5),
            bbox=dict(boxstyle='round', facecolor=COLORS['bg'],
                      edgecolor=COLORS['warning']))

        # Líneas de referencia
        ax_main.axhline(UIAA_MAX_IMPACT, color=COLORS['danger'], ls='--',
                        lw=1.5, alpha=0.7)
        ax_main.text(0.05, UIAA_MAX_IMPACT + 0.5,
                     f'Límite UIAA: {UIAA_MAX_IMPACT} kN',
                     fontsize=9, color=COLORS['danger'])
        ax_main.axhline(ROPE_STATIC_MBS, color=COLORS['danger'], ls=':',
                        lw=1, alpha=0.4)
        ax_main.text(0.05, ROPE_STATIC_MBS + 0.5, 'MBS cuerda: 30 kN',
                     fontsize=8, color=COLORS['danger'], alpha=0.6)

        ax_main.set_xlabel('Factor de Caída', fontsize=12)
        ax_main.set_ylabel('Fuerza de Choque (kN)', fontsize=12)
        ax_main.set_title(f'Fuerza de Choque vs Factor de Caída\n'
                          f'(masa = {mass:.0f} kg)',
                          fontsize=13, fontweight='bold', pad=8)
        ax_main.legend(fontsize=9, loc='upper left',
                       facecolor=COLORS['bg'], edgecolor=COLORS['grid'])
        ax_main.set_xlim(0, 2.0)
        ax_main.set_ylim(0, min(max(F_custom) * 1.3, 45))
        ax_main.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_main.spines[spine].set_visible(False)

        # ── Gráfico F vs Masa ─────────────────────────────────────────
        ax_mass.clear()
        masses = np.linspace(40, 200, 200)
        for name, kp in ROPE_KAPPA.items():
            F_vals = [impact_force(m, ff, kp) for m in masses]
            ax_mass.plot(masses, F_vals, lw=2, label=name)

        ax_mass.plot(mass, F_impact_kN, 'o', color=COLORS['warning'],
                     ms=10, zorder=10)
        ax_mass.axhline(UIAA_MAX_IMPACT, color=COLORS['danger'], ls='--',
                        lw=1, alpha=0.5)
        ax_mass.axvline(mass, color=COLORS['warning'], ls='--', lw=1,
                        alpha=0.5)

        ax_mass.set_xlabel('Masa (kg)', fontsize=10)
        ax_mass.set_ylabel('Fuerza de Choque (kN)', fontsize=10)
        ax_mass.set_title(f'F vs Masa (FF = {ff:.2f})',
                          fontsize=11, fontweight='bold', pad=5)
        ax_mass.legend(fontsize=8, facecolor=COLORS['bg'],
                       edgecolor=COLORS['grid'])
        ax_mass.grid(True, alpha=0.12)
        for spine in ('top', 'right'):
            ax_mass.spines[spine].set_visible(False)

        # ── Barras comparativas de fuerza de choque ───────────────────
        ax_bar.clear()
        scenarios = []
        for name, kp in ROPE_KAPPA.items():
            f = impact_force(mass, ff, kp)
            scenarios.append((name, f))

        names = [s[0] for s in scenarios]
        vals  = [s[1] for s in scenarios]
        bar_colors = [COLORS['accent'], COLORS['warning'], COLORS['danger']]

        bars = ax_bar.barh(names, vals, color=bar_colors, height=0.5,
                           alpha=0.85)
        for bar, v in zip(bars, vals):
            color = COLORS['danger'] if v > UIAA_MAX_IMPACT else COLORS['text']
            symbol = '⚠' if v > UIAA_MAX_IMPACT else ''
            ax_bar.text(bar.get_width() + 0.3,
                        bar.get_y() + bar.get_height() / 2,
                        f'{v:.1f} kN {symbol}',
                        va='center', fontsize=10, fontweight='bold',
                        color=color)

        ax_bar.axvline(UIAA_MAX_IMPACT, color=COLORS['danger'], ls='--',
                       lw=1.5, alpha=0.7)
        ax_bar.set_xlabel('Fuerza de Choque (kN)', fontsize=10)
        ax_bar.set_xlim(0, max(vals) * 1.3)
        ax_bar.set_title(f'Comparación (FF={ff:.2f}, m={mass:.0f}kg)',
                         fontsize=11, fontweight='bold', pad=5)
        ax_bar.grid(axis='x', alpha=0.12)
        for spine in ('top', 'right'):
            ax_bar.spines[spine].set_visible(False)

        fig.canvas.draw_idle()

    for sl in (sl_ff, sl_m, sl_elong):
        sl.on_changed(update)

    fig.text(0.5, 0.925,
             'F = m·g·(1 + √(1 + 2·ff / (m·g·κ)))  —  Fórmula de Dodero',
             fontsize=12, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    fig.text(0.02, 0.015,
             '💡 La fuerza de choque depende del FACTOR DE CAÍDA, no de la '
             'distancia. Una caída de 2m con 2m de cuerda (ff=1) genera '
             'la misma fuerza que una caída de 20m con 20m de cuerda (ff=1). '
             'La ELASTICIDAD de la cuerda es la que absorbe la energía.',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
