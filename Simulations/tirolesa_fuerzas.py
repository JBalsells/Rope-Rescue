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


# ══════════════════════════════════════════════════════════════════════
#  Física
# ══════════════════════════════════════════════════════════════════════

def rope_length_for_sag(L, h_A, h_B, d):
    """
    Longitud de la cuerda cuando la carga está en el centro (L/2)
    con flecha d medida verticalmente desde el punto medio de la línea A-B.
    """
    y_P = (h_A + h_B) / 2.0 - d
    lPA = math.sqrt((L / 2.0) ** 2 + (y_P - h_A) ** 2)
    lPB = math.sqrt((L / 2.0) ** 2 + (y_P - h_B) ** 2)
    return lPA + lPB


def solve_load_y(x, L, h_A, h_B, S):
    """
    Bisección: encuentra y_P (altura del punto de carga) para la posición
    horizontal x, dada la longitud de cuerda fija S.

    A medida que y_P baja, la longitud aumenta.
    Buscamos y_P tal que |AP| + |PB| = S.
    """
    if x <= 0.005 * L:
        return float(h_A)
    if x >= 0.995 * L:
        return float(h_B)

    def f(y):
        return (math.sqrt(x ** 2 + (y - h_A) ** 2)
                + math.sqrt((L - x) ** 2 + (y - h_B) ** 2))

    # Límite superior: carga sobre la línea recta A-B → longitud mínima = |AB|
    t    = x / L
    y_hi = h_A * (1.0 - t) + h_B * t
    y_lo = y_hi - S          # límite inferior amplio

    for _ in range(64):
        y_mid = (y_lo + y_hi) * 0.5
        if f(y_mid) < S:
            y_hi = y_mid     # y_P demasiado alto → rope demasiado corta → bajar
        else:
            y_lo = y_mid     # y_P demasiado bajo  → rope demasiado larga → subir

    return (y_lo + y_hi) * 0.5


def compute_forces(x, L, h_A, h_B, y_P, W_kN):
    """
    Equilibrio estático en el punto de carga P = (x, y_P).
    Anclajes A = (0, h_A), B = (L, h_B).

    Ecuaciones:
      x: -T_A·x/|PA| + T_B·(L-x)/|PB| = 0
      y:  T_A·(h_A-y_P)/|PA| + T_B·(h_B-y_P)/|PB| = W

    Solución:
      T_B = W·|PB| / [(L-x)·(h_A-y_P)/x + (h_B-y_P)]
      T_A = T_B·(L-x)·|PA| / (x·|PB|)
    """
    x = max(1e-4 * L, min(x, (1 - 1e-4) * L))

    lPA = math.sqrt(x ** 2 + (y_P - h_A) ** 2)
    lPB = math.sqrt((L - x) ** 2 + (y_P - h_B) ** 2)

    denom = (L - x) * (h_A - y_P) / x + (h_B - y_P)
    if abs(denom) < 1e-9 or lPA < 1e-9 or lPB < 1e-9:
        T_A = T_B = 999.0
    else:
        T_B = W_kN * lPB / denom
        T_A = T_B * (L - x) * lPA / (x * lPB)

    # Ángulos bajo la horizontal en cada anclaje (mirando hacia la carga)
    alpha_A = math.degrees(math.atan2(h_A - y_P, x))
    alpha_B = math.degrees(math.atan2(h_B - y_P, L - x))

    # Ángulo V en el punto de carga (entre los dos segmentos)
    uA = (-x / lPA,       (h_A - y_P) / lPA)
    uB = ((L - x) / lPB,  (h_B - y_P) / lPB)
    cos_v   = max(-1.0, min(1.0, uA[0] * uB[0] + uA[1] * uB[1]))
    v_angle = math.degrees(math.acos(cos_v))

    return {
        'T_A': T_A, 'T_B': T_B, 'W': W_kN,
        'y_P': y_P, 'lPA': lPA, 'lPB': lPB,
        'alpha_A': alpha_A, 'alpha_B': alpha_B,
        'v_angle': v_angle,
    }


def rope_shape(x_arr, h_A, h_B, load_x, y_P, L):
    """Forma de la cuerda: dos segmentos rectos A→P y P→B."""
    seg_L = h_A + (y_P - h_A) * x_arr / max(load_x, 1e-6)
    seg_R = y_P + (h_B - y_P) * (x_arr - load_x) / max(L - load_x, 1e-6)
    return np.where(x_arr <= load_x, seg_L, seg_R)


# ══════════════════════════════════════════════════════════════════════
#  Interfaz
# ══════════════════════════════════════════════════════════════════════

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('FÍSICA DEL RESCATE — Fuerzas en la Tirolesa',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)

    ax_tiro = fig.add_axes([0.05, 0.50, 0.55, 0.38])
    ax_crv  = fig.add_axes([0.05, 0.30, 0.55, 0.16])
    ax_info = fig.add_axes([0.65, 0.30, 0.32, 0.58])

    ax_sl_span = fig.add_axes([0.15, 0.22, 0.75, 0.025])
    ax_sl_sag  = fig.add_axes([0.15, 0.17, 0.75, 0.025])
    ax_sl_load = fig.add_axes([0.15, 0.12, 0.75, 0.025])
    ax_sl_hA   = fig.add_axes([0.15, 0.07, 0.75, 0.025])
    ax_sl_pos  = fig.add_axes([0.15, 0.02, 0.75, 0.025])

    sl_span = Slider(ax_sl_span, 'Vano L (m)',           5,   100, valinit=30,
                     color=COLORS['primary'],   valstep=1)
    sl_sag  = Slider(ax_sl_sag,  'Flecha (%)',           0.5,  20, valinit=5,
                     color=COLORS['secondary'], valstep=0.1)
    sl_load = Slider(ax_sl_load, 'Carga (kg)',           10,  300, valinit=100,
                     color=COLORS['warning'],   valstep=1)
    sl_hA   = Slider(ax_sl_hA,   'Alt. Anclaje A (m)',   0,    50, valinit=0,
                     color=COLORS['accent'],    valstep=0.5)
    sl_pos  = Slider(ax_sl_pos,  'Posición carga (%)',   1,    99, valinit=50,
                     color=COLORS['rope'],      valstep=0.5)
    # Anclaje B fijo en 0 m

    def update(_=None):
        L       = sl_span.val
        sag_pct = sl_sag.val
        mass    = sl_load.val
        h_A     = sl_hA.val
        h_B     = 0.0
        pos_pct = sl_pos.val

        W_kN   = mass * G / 1000.0
        d      = L * sag_pct / 100.0

        # Longitud fija de la cuerda (definida por la flecha en el centro)
        S = rope_length_for_sag(L, h_A, h_B, d)

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

        y_hi   = max(h_A, h_B) + max(d * 0.5, 0.5)
        y_lo   = y_P - max(W_kN * 0.4, d * 0.3)
        y_lo   = min(y_lo, min(h_A, h_B) - d * 0.3)
        plot_h = max(y_hi - y_lo, 1.0)

        ax_tiro.set_xlim(-L * 0.12, L * 1.12)
        ax_tiro.set_ylim(y_lo, y_hi + plot_h * 0.18)
        ax_tiro.set_aspect('auto')

        # Línea de referencia A-B
        ax_tiro.plot([0, L], [h_A, h_B], '--', color=COLORS['grid'],
                     lw=1, alpha=0.4, zorder=1)

        # Anclajes
        for pt, lbl in [((0, h_A), 'Anclaje A'), ((L, h_B), 'Anclaje B')]:
            ax_tiro.plot(*pt, 'D', color=COLORS['accent'], ms=14, zorder=5)
            ax_tiro.text(pt[0], y_hi + plot_h * 0.10, lbl,
                         ha='center', fontsize=10, fontweight='bold',
                         color=COLORS['accent'])

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
            f'Diagrama de Fuerzas  —  Posición: {pos_pct:.0f}%  '
            f'(x = {load_x:.1f} m)   |   Ángulo V = {f["v_angle"]:.1f}°',
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
                    label='T_A (anclaje A)')
        ax_crv.plot(prof_pct, prof_T_B, color=COLORS['info'], lw=2.0, ls='--',
                    label='T_B (anclaje B)')
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

        ax_crv.set_xlabel('Posición en el vano (%)', fontsize=11)
        ax_crv.set_ylabel('Tensión (kN)', fontsize=11)
        ax_crv.set_xlim(0, 100)
        ax_crv.set_ylim(0, max_T_cv * 1.1)
        ax_crv.grid(True, alpha=0.15)
        for spine in ('top', 'right'):
            ax_crv.spines[spine].set_visible(False)

        # ── Panel informativo ─────────────────────────────────────────
        ax_info.clear()
        ax_info.axis('off')

        # Referencia: T_A al 50% para distintos sags
        def t_ref(sag_frac):
            S2  = rope_length_for_sag(L, h_A, h_B, L * sag_frac)
            y2  = solve_load_y(L / 2, L, h_A, h_B, S2)
            return compute_forces(L / 2, L, h_A, h_B, y2, W_kN)['T_A']

        lines = [
            ('DATOS DEL SISTEMA',  COLORS['primary'], 15, 'bold'),
            ('', '', 6, ''),
            (f'Vano:         {L:.0f} m',                      COLORS['text'],    12, 'normal'),
            (f'Flecha:       {d:.2f} m ({sag_pct:.1f}%)',     COLORS['warning'], 12, 'normal'),
            (f'Carga:        {mass:.0f} kg ({W_kN:.2f} kN)',  COLORS['danger'],  12, 'normal'),
            (f'Alt. A:       {h_A:.1f} m',                    COLORS['accent'],  11, 'normal'),
            (f'Alt. B:       0.0 m (fijo)',                    COLORS['grid'],    11, 'normal'),
            (f'Posición:     {pos_pct:.0f}%  ({load_x:.1f} m)', COLORS['text'], 11, 'normal'),
            ('', '', 2, ''),
            (f'Ángulo A:     {f["alpha_A"]:.1f}°',            COLORS['text'],    11, 'normal'),
            (f'Ángulo B:     {f["alpha_B"]:.1f}°',            COLORS['text'],    11, 'normal'),
            (f'Ángulo V:     {f["v_angle"]:.1f}°',            COLORS['warning'], 12, 'bold'),
            ('', '', 4, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('', '', 4, ''),
            ('TENSIONES:',                                     COLORS['warning'],  14, 'bold'),
            (f'T_A = {T_A_kN:.2f} kN  ({T_A_kN/W_kN:.1f}×W)', COLORS['primary'], 13, 'bold'),
            (f'T_B = {T_B_kN:.2f} kN  ({T_B_kN/W_kN:.1f}×W)', COLORS['info'],    13, 'bold'),
            ('', '', 4, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('', '', 4, ''),
        ]

        if T_max > ROPE_STATIC_MBS:
            lines += [('✗ SOBREPASA ROTURA',    COLORS['danger'],  14, 'bold'),
                      ('  ¡El sistema FALLARÁ!', COLORS['danger'],  11, 'bold')]
        elif T_max > NFPA_WORK_LOAD:
            lines += [('⚠ SUPERA CARGA TRABAJO', COLORS['warning'], 13, 'bold'),
                      ('  Riesgo elevado.',        COLORS['warning'], 11, 'normal')]
        else:
            lines += [('✓ DENTRO DE LÍMITES',    COLORS['accent'],  14, 'bold'),
                      (f'  F.S. A: {ROPE_STATIC_MBS/T_A_kN:.1f}:1', COLORS['accent'], 10, 'normal'),
                      (f'  F.S. B: {ROPE_STATIC_MBS/T_B_kN:.1f}:1', COLORS['accent'], 10, 'normal')]

        lines += [
            ('', '', 6, ''),
            ('─' * 28, COLORS['grid'], 9, ''),
            ('REF. T_A@50% por flecha:', COLORS['text'], 10, 'bold'),
            (f' 2% → {t_ref(0.02):.1f} kN', COLORS['danger'],  10, ''),
            (f' 5% → {t_ref(0.05):.1f} kN', COLORS['warning'], 10, ''),
            (f'10% → {t_ref(0.10):.1f} kN', COLORS['accent'],  10, ''),
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

    for sl in (sl_span, sl_sag, sl_load, sl_hA, sl_pos):
        sl.on_changed(update)

    fig.text(0.5, 0.92,
             '⚠ Menos flecha = MÁS tensión.   '
             'Anclaje más alto soporta MAYOR tensión.   '
             'Carga descentrada → T_A ≠ T_B.',
             fontsize=11, ha='center', color=COLORS['danger'],
             fontweight='bold', fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
