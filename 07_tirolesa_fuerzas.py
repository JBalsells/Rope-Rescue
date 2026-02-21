"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 07: Tirolesa / Línea Tensada         ║
╠══════════════════════════════════════════════════════════════════════╣
║  Análisis de fuerzas en una tirolesa (Tyrolean traverse) y         ║
║  cómo la flecha (sag) afecta dramáticamente las fuerzas en         ║
║  los anclajes.                                                       ║
║                                                                      ║
║  Fórmula clave:  T = W·L / (4·d)                                   ║
║  donde T = tensión, W = peso, L = vano, d = flecha                 ║
║                                                                      ║
║  ⚠ MENOR FLECHA = MAYOR TENSIÓN EN ANCLAJES                       ║
║                                                                      ║
║  A 2% de flecha: T = 12.5 × W  (¡12 veces el peso!)              ║
║  A 5% de flecha: T = 5.0 × W                                       ║
║  A 10% de flecha: T = 2.5 × W                                      ║
║                                                                      ║
║  Ejecutar:  python 07_tirolesa_fuerzas.py                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, NFPA_WORK_LOAD, ROPE_STATIC_MBS, apply_mpl_style


def catenary_sag(x, L, sag, load_pos_ratio=0.5):
    """
    Calcula la forma de la cuerda cargada (catenaria aproximada).
    x: posición horizontal (0 a L)
    L: longitud del vano
    sag: flecha máxima
    load_pos_ratio: posición de la carga (0-1)
    """
    load_x = L * load_pos_ratio
    y = np.where(
        x <= load_x,
        -sag * x / load_x,
        -sag * (L - x) / (L - load_x)
    )
    return y


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Fuerzas en la Tirolesa',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_tiro = fig.add_axes([0.05, 0.48, 0.55, 0.40])   # Diagrama tirolesa
    ax_crv  = fig.add_axes([0.05, 0.25, 0.55, 0.18])   # Curva flecha vs tensión
    ax_info = fig.add_axes([0.65, 0.25, 0.32, 0.63])    # Panel info

    ax_sl_span = fig.add_axes([0.15, 0.14, 0.75, 0.025])
    ax_sl_sag  = fig.add_axes([0.15, 0.09, 0.75, 0.025])
    ax_sl_load = fig.add_axes([0.15, 0.04, 0.75, 0.025])

    sl_span = Slider(ax_sl_span, 'Vano L (m)', 5, 100, valinit=30,
                     color=COLORS['primary'], valstep=1)
    sl_sag = Slider(ax_sl_sag, 'Flecha (%)', 0.5, 20, valinit=5,
                    color=COLORS['secondary'], valstep=0.1)
    sl_load = Slider(ax_sl_load, 'Carga (kg)', 10, 300, valinit=100,
                     color=COLORS['warning'], valstep=1)

    def update(_=None):
        L = sl_span.val
        sag_pct = sl_sag.val
        mass = sl_load.val

        W_kN = mass * G / 1000.0
        d = L * sag_pct / 100.0  # flecha en metros

        # Tensión en los anclajes (carga en el centro)
        # T = W * L / (4 * d) para carga puntual central
        T_kN = W_kN * L / (4.0 * d)
        T_ratio = T_kN / W_kN

        # Ángulo de la cuerda con la horizontal
        angle_deg = np.degrees(np.arctan(2 * d / L))

        # ── Diagrama de la tirolesa ───────────────────────────────────
        ax_tiro.clear()
        ax_tiro.set_xlim(-L * 0.1, L * 1.1)
        y_range = max(d * 2, L * 0.15)
        ax_tiro.set_ylim(-y_range, y_range * 0.5)
        ax_tiro.set_aspect('auto')

        # Anclajes
        for ax_pt, label in [((0, 0), 'Anclaje A'), ((L, 0), 'Anclaje B')]:
            ax_tiro.plot(*ax_pt, 'D', color=COLORS['accent'], ms=14, zorder=5)
            ax_tiro.text(ax_pt[0], y_range * 0.15, label,
                         ha='center', fontsize=10, fontweight='bold',
                         color=COLORS['accent'])

        # Cuerda con carga
        x_pts = np.linspace(0, L, 300)
        y_pts = catenary_sag(x_pts, L, d, 0.5)

        rope_color = COLORS['rope']
        if T_ratio > 10:
            rope_color = COLORS['danger']
        elif T_ratio > 5:
            rope_color = COLORS['warning']

        ax_tiro.plot(x_pts, y_pts, color=rope_color, lw=3, zorder=3)

        # Punto de carga
        load_x = L / 2
        load_y = -d
        ax_tiro.plot(load_x, load_y, 'o', color=COLORS['warning'],
                     ms=12, zorder=6)

        # Flecha de peso
        arrow_len = min(W_kN * 0.5, y_range * 0.3)
        ax_tiro.annotate(
            '', xy=(load_x, load_y - arrow_len),
            xytext=(load_x, load_y),
            arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                            lw=2.5, mutation_scale=15))
        ax_tiro.text(load_x + L * 0.03, load_y - arrow_len / 2,
                     f'W = {W_kN:.2f} kN', fontsize=10,
                     color=COLORS['danger'], fontweight='bold')

        # Flechas de tensión en anclajes
        for anchor_x, sign in [(0, 1), (L, -1)]:
            dx = sign * min(T_kN * 0.3, L * 0.15)
            dy = -sign * d * 0.3  # componente vertical
            ax_tiro.annotate(
                '', xy=(anchor_x + dx, dy),
                xytext=(anchor_x, 0),
                arrowprops=dict(arrowstyle='->', color=COLORS['info'],
                                lw=2.5, mutation_scale=15))
            ax_tiro.text(anchor_x + dx * 0.5,
                         0.05 * y_range,
                         f'T = {T_kN:.1f} kN',
                         fontsize=10, fontweight='bold',
                         color=COLORS['info'],
                         ha='center')

        # Flecha de flecha (sag)
        ax_tiro.plot([load_x, load_x], [0, -d],
                     '--', color=COLORS['warning'], lw=1.5, alpha=0.7)
        ax_tiro.text(load_x + L * 0.02, -d / 2,
                     f'd = {d:.1f} m\n({sag_pct:.1f}%)',
                     fontsize=10, color=COLORS['warning'])

        ax_tiro.set_title('Diagrama de Fuerzas en la Tirolesa',
                          fontsize=13, fontweight='bold', pad=8)
        ax_tiro.axis('off')

        # ── Curva flecha vs tensión ───────────────────────────────────
        ax_crv.clear()
        sags = np.linspace(0.5, 20, 500)
        d_vals = L * sags / 100.0
        T_vals = W_kN * L / (4.0 * d_vals)

        # Zonas
        ax_crv.axhspan(0, NFPA_WORK_LOAD, facecolor=COLORS['accent'],
                       alpha=0.05)
        ax_crv.axhspan(NFPA_WORK_LOAD, ROPE_STATIC_MBS,
                       facecolor=COLORS['warning'], alpha=0.05)
        ax_crv.axhspan(ROPE_STATIC_MBS, 100,
                       facecolor=COLORS['danger'], alpha=0.05)

        ax_crv.plot(sags, T_vals, color=COLORS['primary'], lw=2.5)
        ax_crv.axhline(NFPA_WORK_LOAD, color=COLORS['danger'], ls=':',
                       lw=1, alpha=0.6)
        ax_crv.text(18, NFPA_WORK_LOAD + 0.5, 'NFPA 13.5kN',
                    fontsize=8, color=COLORS['danger'], alpha=0.7)
        ax_crv.axhline(ROPE_STATIC_MBS, color=COLORS['danger'], ls='--',
                       lw=1, alpha=0.4)
        ax_crv.text(18, ROPE_STATIC_MBS + 0.5, 'MBS 30kN',
                    fontsize=8, color=COLORS['danger'], alpha=0.5)

        # Punto actual
        ax_crv.plot(sag_pct, T_kN, 'o', color=COLORS['warning'], ms=10,
                    zorder=5)
        ax_crv.axvline(sag_pct, color=COLORS['warning'], ls='--', lw=1,
                       alpha=0.5)

        ax_crv.set_xlabel('Flecha (%)', fontsize=11)
        ax_crv.set_ylabel('Tensión (kN)', fontsize=11)
        ax_crv.set_xlim(0.5, 20)
        ax_crv.set_ylim(0, min(max(T_vals) * 1.2, 60))
        ax_crv.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        # ── Panel informativo ─────────────────────────────────────────
        ax_info.clear()
        ax_info.axis('off')

        lines = [
            ('DATOS DEL SISTEMA', COLORS['primary'], 15, 'bold'),
            ('', '', 6, ''),
            (f'Vano:            {L:.0f} m', COLORS['text'], 12, 'normal'),
            (f'Flecha:          {d:.2f} m  ({sag_pct:.1f}%)', COLORS['warning'], 12, 'normal'),
            (f'Carga:           {mass:.0f} kg  ({W_kN:.2f} kN)', COLORS['danger'], 12, 'normal'),
            (f'Ángulo cuerda:   {angle_deg:.1f}°', COLORS['text'], 11, 'normal'),
            ('', '', 6, ''),
            ('─' * 32, COLORS['grid'], 9, ''),
            ('', '', 6, ''),
            ('RESULTADO:', COLORS['warning'], 14, 'bold'),
            (f'Tensión en cada anclaje:', COLORS['info'], 13, 'bold'),
            (f'  T = {T_kN:.2f} kN', COLORS['info'], 16, 'bold'),
            (f'  = {T_ratio:.1f} × el peso', COLORS['info'], 13, 'normal'),
            ('', '', 6, ''),
            ('─' * 32, COLORS['grid'], 9, ''),
            ('', '', 6, ''),
        ]

        # Estado de seguridad
        if T_kN > ROPE_STATIC_MBS:
            lines.append(('✗ SOBREPASA ROTURA', COLORS['danger'], 14, 'bold'))
            lines.append(('  ¡El sistema FALLARÁ!', COLORS['danger'], 12, 'bold'))
        elif T_kN > NFPA_WORK_LOAD:
            lines.append(('⚠ SUPERA CARGA DE TRABAJO', COLORS['warning'], 13, 'bold'))
            lines.append(('  Riesgo elevado.', COLORS['warning'], 11, 'normal'))
            lines.append((f'  Aumentar flecha a ≥{W_kN * L / (4 * NFPA_WORK_LOAD) / L * 100:.1f}%',
                          COLORS['warning'], 11, 'normal'))
        else:
            lines.append(('✓ DENTRO DE LÍMITES', COLORS['accent'], 14, 'bold'))
            lines.append((f'  Factor de seguridad: {ROPE_STATIC_MBS / T_kN:.1f}:1',
                          COLORS['accent'], 11, 'normal'))

        lines.extend([
            ('', '', 10, ''),
            ('─' * 32, COLORS['grid'], 9, ''),
            ('TABLA DE REFERENCIA:', COLORS['text'], 11, 'bold'),
            (f' 2% flecha → T = {W_kN * L / (4 * L * 0.02):.1f} kN ({W_kN * L / (4 * L * 0.02) / W_kN:.0f}×W)', COLORS['danger'], 10, ''),
            (f' 5% flecha → T = {W_kN * L / (4 * L * 0.05):.1f} kN ({W_kN * L / (4 * L * 0.05) / W_kN:.0f}×W)', COLORS['warning'], 10, ''),
            (f'10% flecha → T = {W_kN * L / (4 * L * 0.10):.1f} kN ({W_kN * L / (4 * L * 0.10) / W_kN:.0f}×W)', COLORS['accent'], 10, ''),
        ])

        y_pos = 0.98
        for text, color, size, weight in lines:
            if not text:
                y_pos -= 0.025
                continue
            ax_info.text(0.02, y_pos, text, fontsize=size,
                         fontweight=weight if weight else 'normal',
                         color=color, transform=ax_info.transAxes,
                         verticalalignment='top', family='monospace')
            y_pos -= 0.055 if size >= 12 else 0.04

        fig.canvas.draw_idle()

    for sl in (sl_span, sl_sag, sl_load):
        sl.on_changed(update)

    fig.text(0.5, 0.92,
             'T = W · L / (4 · d)   —   ⚠ Menos flecha = MÁS tensión. '
             'Una tirolesa "bonita y tensa" puede romper anclajes.',
             fontsize=11, ha='center', color=COLORS['danger'],
             fontweight='bold', fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
