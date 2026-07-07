"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Simulación: Tirolesa con Carga Móvil        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Análisis de fuerzas en una tirolesa con anclajes a diferente       ║
║  altura y carga que se desplaza a lo largo de toda la cuerda.       ║
║                                                                      ║
║  Física:                                                             ║
║   • Cuerda inextensible de longitud fija (según sag inicial)        ║
║   • y_P en cada posición → bisección sobre longitud de cuerda       ║
║   • Equilibrio en P: T_A ≠ T_B cuando h_A ≠ 0 o x ≠ L/2          ║
║   • Ángulo V calculado por producto escalar de los segmentos        ║
║                                                                      ║
║  ⚠ MENOR FLECHA = MAYOR TENSIÓN                                    ║
║  ⚠ ANCLAJE MÁS ALTO → MAYOR TENSIÓN EN ESE ANCLAJE               ║
║  ⚠ CARGA FUERA DEL CENTRO → T_A ≠ T_B                             ║
║                                                                      ║
║  Ejecutar:  python Simulations/tirolesa_fuerzas.py                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, G, NFPA_WORK_LOAD, ROPE_STATIC_MBS, apply_mpl_style
from physics import (rope_length_for_sag, span_for_rope, solve_load_y,
                     tyrolean_forces as compute_forces)


# ══════════════════════════════════════════════════════════════════════
#  Física: rope_length_for_sag / solve_load_y / compute_forces en physics.py
#  Aquí solo queda la forma de la cuerda (depende de numpy, es de vista).
# ══════════════════════════════════════════════════════════════════════

def rope_shape(x_arr, h_A, h_B, load_x, y_P, L):
    """Forma de la cuerda: dos segmentos rectos A→P y P→B."""
    seg_L = h_A + (y_P - h_A) * x_arr / max(load_x, 1e-6)
    seg_R = y_P + (h_B - y_P) * (x_arr - load_x) / max(L - load_x, 1e-6)
    return np.where(x_arr <= load_x, seg_L, seg_R)


# ══════════════════════════════════════════════════════════════════════
#  Interfaz
# ══════════════════════════════════════════════════════════════════════

from registry import simulation


@simulation(backend='mpl', order=5,
            title='Tirolesa con carga móvil',
            description='Tensión según flecha, altura de anclaje y posición.')
def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Fuerzas en la Tirolesa',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_tiro = fig.add_axes([0.05, 0.50, 0.55, 0.38])
    ax_crv  = fig.add_axes([0.05, 0.30, 0.55, 0.16])
    ax_info = fig.add_axes([0.65, 0.30, 0.32, 0.58])

    # Controles compactos, agrupados en un recuadro abajo-izquierda
    ax_sl_span = fig.add_axes([0.22, 0.205, 0.155, 0.024])
    ax_sl_sag  = fig.add_axes([0.22, 0.165, 0.155, 0.024])
    ax_sl_load = fig.add_axes([0.22, 0.125, 0.155, 0.024])
    ax_sl_hA   = fig.add_axes([0.22, 0.085, 0.155, 0.024])
    ax_sl_pos  = fig.add_axes([0.22, 0.045, 0.155, 0.024])

    sl_span = Slider(ax_sl_span, 'Long. cuerda (m)', 10, 110, valinit=31,
                     color=COLORS['primary'],   valstep=1)
    sl_sag  = Slider(ax_sl_sag,  'Flecha d (m)', 0.3, 15, valinit=1.5,
                     color=COLORS['secondary'], valstep=0.1)
    sl_load = Slider(ax_sl_load, 'Peso (kg)', 10, 300, valinit=100,
                     color=COLORS['warning'],   valstep=1)
    sl_hA   = Slider(ax_sl_hA,   'Altura A (m)', 0, 50, valinit=0,
                     color=COLORS['accent'],    valstep=0.5)
    sl_pos  = Slider(ax_sl_pos,  'Posición (%)', 1, 99, valinit=50,
                     color=COLORS['rope'],      valstep=0.5)
    for _sl in (sl_span, sl_sag, sl_load, sl_hA, sl_pos):
        _sl.label.set_size(9.5)
    # Anclaje B fijo en 0 m

    def update(_=None):
        S       = sl_span.val          # longitud de la cuerda (entrada)
        d       = sl_sag.val           # flecha en metros (entrada directa)
        mass    = sl_load.val
        h_A     = sl_hA.val
        h_B     = 0.0
        pos_pct = sl_pos.val

        W_kN   = mass * G / 1000.0
        # La cuerda no puede ser más corta que ~2·d; acotamos la flecha
        d      = min(d, 0.48 * S)
        # Distancia entre anclajes = se CALCULA a partir de cuerda + flecha
        L      = max(span_for_rope(S, d, h_A, h_B), 1.0)

        # Posición y altura actual de la carga
        load_x = pos_pct / 100.0 * L
        y_P    = solve_load_y(load_x, L, h_A, h_B, S)

        # Fuerzas en la posición actual
        f = compute_forces(load_x, L, h_A, h_B, y_P, W_kN)
        T_A_kN = f['T_A']
        T_B_kN = f['T_B']
        T_max  = max(T_A_kN, T_B_kN)

        # ── Perfil de tensiones a lo largo del vano ───────────────────
        N = 60
        prof_pct, prof_T_A, prof_T_B = [], [], []
        for i in range(N):
            pct = (i + 0.5) / N
            xi  = pct * L
            yi  = solve_load_y(xi, L, h_A, h_B, S)
            fi  = compute_forces(xi, L, h_A, h_B, yi, W_kN)
            prof_pct.append(pct * 100)
            prof_T_A.append(fi['T_A'])
            prof_T_B.append(fi['T_B'])

        # ── Diagrama de la tirolesa ───────────────────────────────────
        ax_tiro.clear()

        # Vista FIJA: depende solo de alturas y flecha, NO de la posición de
        # la carga. Así los anclajes no "saltan" al mover la posición; solo
        # se mueven si cambia la altura. El punto más bajo es la carga al
        # centro (≈ flecha d bajo el punto medio de A-B).
        y_low_center = (h_A + h_B) / 2.0 - d
        y_hi   = max(h_A, h_B) + max(d * 0.5, 0.5)
        y_lo   = y_low_center - max(W_kN * 0.5, d * 0.4, 1.0)
        plot_h = max(y_hi - y_lo, 1.0)

        ax_tiro.set_xlim(-L * 0.12, L * 1.12)
        ax_tiro.set_ylim(y_lo, y_hi + plot_h * 0.50)   # aire arriba para la cota
        ax_tiro.set_aspect('auto')

        # Línea de referencia A-B
        ax_tiro.plot([0, L], [h_A, h_B], '--', color=COLORS['grid'],
                     lw=1, alpha=0.4, zorder=1)

        # ── Cota de distancia entre anclajes (calculada) ─────────────
        y_cota = y_hi + plot_h * 0.34
        ax_tiro.annotate('', xy=(L, y_cota), xytext=(0, y_cota),
                         arrowprops=dict(arrowstyle='<|-|>', color=COLORS['text'],
                                         lw=1.5))
        for xx, hy in [(0, h_A), (L, h_B)]:
            ax_tiro.plot([xx, xx], [hy + plot_h * 0.06, y_cota], ':',
                         color=COLORS['text'], lw=0.8, alpha=0.5)
        ax_tiro.text(L / 2.0, y_cota + plot_h * 0.05,
                     f'distancia A ↔ B = {L:.1f} m',
                     ha='center', fontsize=12, fontweight='bold',
                     color=COLORS['text'])

        # Anclajes (A en verde, B en teal — para distinguirlos claramente)
        for pt, letra, col in [((0, h_A), 'A', COLORS['primary']),
                               ((L, h_B), 'B', COLORS['info'])]:
            ax_tiro.plot(*pt, 'D', color=col, ms=18, zorder=5)
            ax_tiro.text(pt[0], pt[1], letra, ha='center', va='center',
                         fontsize=11, fontweight='bold', color=COLORS['bg'],
                         zorder=6)
            ax_tiro.text(pt[0], y_hi + plot_h * 0.12, f'Anclaje {letra}',
                         ha='center', fontsize=12, fontweight='bold', color=col)

        # Cuerda
        x_pts = np.linspace(0, L, 300)
        y_pts = rope_shape(x_pts, h_A, h_B, load_x, y_P, L)
        rope_color = (COLORS['danger']  if T_max > 10 else
                      COLORS['warning'] if T_max > 5  else
                      COLORS['rope'])
        ax_tiro.plot(x_pts, y_pts, color=rope_color, lw=3, zorder=3)

        # Punto de carga
        ax_tiro.plot(load_x, y_P, 'o', color=COLORS['warning'], ms=12, zorder=6)

        # Flecha de peso (vertical hacia abajo)
        arrow_len_W = min(W_kN * 0.4, plot_h * 0.22)
        ax_tiro.annotate(
            '', xy=(load_x, y_P - arrow_len_W),
            xytext=(load_x, y_P),
            arrowprops=dict(arrowstyle='->', color=COLORS['danger'],
                            lw=2.5, mutation_scale=15))
        ax_tiro.text(load_x + L * 0.03, y_P - arrow_len_W / 2,
                     f'W = {W_kN:.2f} kN', fontsize=10,
                     color=COLORS['danger'], fontweight='bold')

        # Flechas de tensión en anclajes (dirección exacta, tamaño proporcional)
        for anc_x, anc_y, T_anc in [(0, h_A, T_A_kN), (L, h_B, T_B_kN)]:
            a_scale = float(np.clip(T_anc * 0.3, L * 0.05, L * 0.25))
            h_scale = float(np.clip(T_anc * 0.8, 10, 30))
            lw_a    = float(np.clip(T_anc * 0.15, 1.5, 5.0))
            vx = load_x - anc_x
            vy = y_P - anc_y
            nm = math.sqrt(vx ** 2 + vy ** 2)
            if nm < 1e-6:
                continue
            dx, dy = a_scale * vx / nm, a_scale * vy / nm
            ax_tiro.annotate(
                '', xy=(anc_x + dx, anc_y + dy),
                xytext=(anc_x, anc_y),
                arrowprops=dict(arrowstyle='->', color=COLORS['info'],
                                lw=lw_a, mutation_scale=h_scale))
            ax_tiro.text(anc_x + dx * 0.5,
                         anc_y + dy * 0.5 + plot_h * 0.06,
                         f'T = {T_anc:.1f} kN',
                         fontsize=10, fontweight='bold',
                         color=COLORS['info'], ha='center')

        # Indicador de sag local (desde la línea A-B hasta la carga)
        y_line_here = h_A + (h_B - h_A) * load_x / L
        ax_tiro.plot([load_x, load_x], [y_line_here, y_P],
                     '--', color=COLORS['warning'], lw=1.5, alpha=0.7)
        ax_tiro.text(load_x + L * 0.02, (y_line_here + y_P) / 2,
                     f'd = {y_line_here - y_P:.1f} m',
                     fontsize=10, color=COLORS['warning'])

        ax_tiro.set_title(
            f'La carga está al {pos_pct:.0f}% del recorrido   '
            f'(ángulo entre los dos lados: {f["v_angle"]:.0f}°)',
            fontsize=12, fontweight='bold', pad=8)
        ax_tiro.axis('off')

        # ── Curva T_A y T_B vs posición en el vano ───────────────────
        ax_crv.clear()

        T_all    = prof_T_A + prof_T_B
        max_T_cv = min(max(max(T_all), NFPA_WORK_LOAD * 1.1, 5.0), 80.0)

        ax_crv.axhspan(0, NFPA_WORK_LOAD,
                       facecolor=COLORS['accent'], alpha=0.05)
        ax_crv.axhspan(NFPA_WORK_LOAD, ROPE_STATIC_MBS,
                       facecolor=COLORS['warning'], alpha=0.05)
        ax_crv.axhspan(ROPE_STATIC_MBS, 200,
                       facecolor=COLORS['danger'], alpha=0.05)

        ax_crv.plot(prof_pct, prof_T_A, color=COLORS['primary'], lw=2.5,
                    label='Anclaje A')
        ax_crv.plot(prof_pct, prof_T_B, color=COLORS['info'], lw=2.0, ls='--',
                    label='Anclaje B')
        ax_crv.legend(fontsize=8, loc='upper right')

        ax_crv.axhline(NFPA_WORK_LOAD, color=COLORS['danger'],
                       ls=':', lw=1, alpha=0.6)
        ax_crv.text(97, NFPA_WORK_LOAD + 0.3, 'NFPA',
                    fontsize=7, color=COLORS['danger'], alpha=0.7, ha='right')
        ax_crv.axhline(ROPE_STATIC_MBS, color=COLORS['danger'],
                       ls='--', lw=1, alpha=0.4)
        ax_crv.text(97, ROPE_STATIC_MBS + 0.3, 'MBS',
                    fontsize=7, color=COLORS['danger'], alpha=0.5, ha='right')

        # Marcadores de posición actual
        ax_crv.axvline(pos_pct, color=COLORS['warning'], ls='--', lw=1.5, alpha=0.7)
        ax_crv.plot(pos_pct, T_A_kN, 'o', color=COLORS['primary'], ms=10, zorder=5)
        ax_crv.plot(pos_pct, T_B_kN, 's', color=COLORS['info'],    ms=9,  zorder=5)

        ax_crv.set_xlabel('Posición de la carga (%)', fontsize=11)
        ax_crv.set_ylabel('Fuerza en el anclaje (kN)', fontsize=11)
        ax_crv.set_xlim(0, 100)
        ax_crv.set_ylim(0, max_T_cv * 1.1)
        ax_crv.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        # ── Panel informativo ─────────────────────────────────────────
        ax_info.clear()
        ax_info.axis('off')

        # Referencia: T en anclaje A al centro, para distintas flechas
        def t_ref(d_val):
            d2 = min(d_val, 0.48 * S)
            L2 = max(span_for_rope(S, d2, h_A, h_B), 1.0)
            y2 = solve_load_y(L2 / 2, L2, h_A, h_B, S)
            return compute_forces(L2 / 2, L2, h_A, h_B, y2, W_kN)['T_A']

        lines = [
            ('DATOS',  COLORS['primary'], 15, 'bold'),
            ('', '', 6, ''),
            (f'Long. cuerda:       {S:.0f} m',                COLORS['primary'], 12, 'normal'),
            (f'Flecha d:           {d:.2f} m',                COLORS['secondary'], 12, 'normal'),
            (f'Distancia A<->B:    {L:.1f} m (calc.)',        COLORS['text'],    12, 'bold'),
            (f'Peso:               {mass:.0f} kg ({W_kN:.2f} kN)', COLORS['danger'], 12, 'normal'),
            (f'Altura anclaje A:   {h_A:.1f} m',              COLORS['accent'],  11, 'normal'),
            (f'Altura anclaje B:   0.0 m (fijo)',              COLORS['grid'],    11, 'normal'),
            (f'Posición carga:     {pos_pct:.0f}%',            COLORS['text'],    11, 'normal'),
            ('', '', 4, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('', '', 4, ''),
            ('FUERZA EN CADA ANCLAJE:',                        COLORS['warning'], 13, 'bold'),
            (f'Anclaje A = {T_A_kN:.2f} kN  ({T_A_kN/W_kN:.1f}× el peso)', COLORS['primary'], 12, 'bold'),
            (f'Anclaje B = {T_B_kN:.2f} kN  ({T_B_kN/W_kN:.1f}× el peso)', COLORS['info'], 12, 'bold'),
            ('', '', 4, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('', '', 4, ''),
        ]

        if T_max > ROPE_STATIC_MBS:
            lines += [('✗ SE PASA DE LA ROTURA',  COLORS['danger'], 13, 'bold'),
                      ('  ¡La cuerda fallaría!',    COLORS['danger'], 11, 'bold')]
        elif T_max > NFPA_WORK_LOAD:
            lines += [('⚠ FUERZA ALTA',             COLORS['warning'], 13, 'bold'),
                      ('  Riesgo elevado.',          COLORS['warning'], 11, 'normal')]
        else:
            lines += [('✓ DENTRO DE LÍMITES SEGUROS', COLORS['accent'], 13, 'bold')]

        lines += [
            ('', '', 6, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('Con la carga al centro, segun', COLORS['text'], 10, 'bold'),
            ('la flecha de la cuerda:', COLORS['text'], 10, 'bold'),
            (f'  flecha 0.5 m -> {t_ref(0.5):.1f} kN', COLORS['danger'],  10, ''),
            (f'  flecha 1.5 m -> {t_ref(1.5):.1f} kN', COLORS['warning'], 10, ''),
            (f'  flecha 3.0 m -> {t_ref(3.0):.1f} kN', COLORS['accent'],  10, ''),
        ]

        y_pos = 0.98
        for text, color, size, weight in lines:
            if not text:
                y_pos -= 0.018
                continue
            ax_info.text(0.02, y_pos, text, fontsize=size,
                         fontweight=weight or 'normal',
                         color=color, transform=ax_info.transAxes,
                         verticalalignment='top', family='monospace')
            y_pos -= 0.048 if size >= 12 else 0.036

        fig.canvas.draw_idle()

    from controls import attach_editable_numbers
    attach_editable_numbers(fig, [
        (sl_span, 10, 110, lambda v: f'{v:.0f}'),
        (sl_sag, 0.3, 15, lambda v: f'{v:.1f}'),
        (sl_load, 10, 300, lambda v: f'{v:.0f}'),
        (sl_hA, 0, 50, lambda v: f'{v:.1f}'),
        (sl_pos, 1, 99, lambda v: f'{v:.0f}'),
    ], redraw=update, frame=(0.06, 0.02, 0.42, 0.255))

    fig.text(0.5, 0.92,
             'Cuanto MENOS cuelga la cuerda, MÁS fuerza aguanta cada anclaje. '
             'Una tirolesa muy tensa es peligrosa.',
             fontsize=11, ha='center', color=COLORS['danger'],
             fontweight='bold', fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
