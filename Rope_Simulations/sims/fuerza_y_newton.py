"""
Módulo 01 · ¿Qué es un Newton?

Para alguien sin física. Una sola pantalla con tres controles que cuentan
una historia:

  1. El peso de algo es una FUERZA (en Newtons).      peso = masa × gravedad
  2. Si cae desde una altura, gana velocidad.         v = √(2·g·h)
  3. Si lo frenás de golpe, la fuerza se multiplica.  F = m·(g + v/t)

La barra de comparación muestra "tu peso" y "el golpe al frenar" sobre la
misma escala, para ver de un vistazo cómo frenar rápido dispara la fuerza
hacia lo que rompe una cuerda.
"""

import math
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox
from matplotlib.patches import FancyBboxPatch
from config import COLORS, G, NFPA_WORK_LOAD, ROPE_STATIC_MBS, apply_mpl_style
from physics import weight_kn, impact_velocity
from registry import simulation

# Referencias cotidianas para dar intuición de "cuánta fuerza es" (en Newtons).
REFERENCIAS = [
    (1.0,                     'Una manzana  (~0.1 kg)',          COLORS['accent']),
    (98.0,                    'Mochila escolar  (10 kg)',        COLORS['info']),
    (687.0,                   'Una persona  (70 kg)',            COLORS['rope']),
    (1570.0,                  'Rescatista + paciente  (160 kg)', COLORS['secondary']),
    (NFPA_WORK_LOAD * 1000,   'Carga máxima de trabajo (cuerda)', COLORS['warning']),
    (ROPE_STATIC_MBS * 1000,  'Lo que ROMPE la cuerda',          COLORS['danger']),
]


def _draw_answer(ax, mass_kg):
    """Panel izquierdo: el peso, grande y en palabras simples."""
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    F_N = mass_kg * G
    kN = weight_kn(mass_kg)
    manzanas = max(1, round(F_N))

    ax.text(0.5, 0.96, 'El peso de…', ha='center', va='center',
            fontsize=13, color=COLORS['text'])

    box = FancyBboxPatch((0.34, 0.78), 0.32, 0.11,
                         boxstyle='round,pad=0.01',
                         facecolor=COLORS['panel'],
                         edgecolor=COLORS['primary'], linewidth=2)
    ax.add_patch(box)
    ax.text(0.5, 0.835, f'{mass_kg:.0f} kg', ha='center', va='center',
            fontsize=21, fontweight='bold', color=COLORS['primary'])

    ax.annotate('', xy=(0.5, 0.66), xytext=(0.5, 0.77),
                arrowprops=dict(arrowstyle='-|>', color=COLORS['danger'],
                                lw=3, mutation_scale=22))
    ax.text(0.55, 0.71, 'tira hacia abajo', ha='left', va='center',
            fontsize=10, color=COLORS['danger'])

    ax.text(0.5, 0.52, f'{F_N:,.0f} N', ha='center', va='center',
            fontsize=44, fontweight='bold', color=COLORS['primary'])
    ax.text(0.5, 0.39, f'=  {kN:.2f} kN', ha='center', va='center',
            fontsize=22, fontweight='bold', color=COLORS['accent'])

    ax.text(0.5, 0.25,
            f'peso  =  masa × gravedad\n{mass_kg:.0f} kg  ×  9.81  =  {F_N:,.0f} N',
            ha='center', va='center', fontsize=12, color=COLORS['text'],
            linespacing=1.6)
    ax.text(0.5, 0.07, f'Es como colgar unas {manzanas:,} manzanas.',
            ha='center', va='center', fontsize=11, fontstyle='italic',
            color=COLORS['rope'])


def _draw_reference(ax, mass_kg, F_imp_N):
    """Panel derecho: comparación de fuerzas, con 'tu peso' y 'el golpe'."""
    ax.clear()
    F_N = mass_kg * G

    labels = [r[1] for r in REFERENCIAS]
    values = [r[0] for r in REFERENCIAS]
    colors = [r[2] for r in REFERENCIAS]
    y = list(range(len(REFERENCIAS)))

    ax.barh(y, values, color=colors, alpha=0.85, height=0.55, zorder=2)
    for yi, val in zip(y, values):
        txt = f'{val/1000:.0f} kN' if val >= 1000 else f'{val:.0f} N'
        ax.text(val * 1.18, yi, txt, va='center', ha='left',
                fontsize=9, color=COLORS['text'])

    # Marcador del peso en reposo
    ax.axvline(F_N, color=COLORS['primary'], lw=2, ls='--', zorder=4)
    ax.text(F_N, len(REFERENCIAS) - 0.3, ' tu peso',
            color=COLORS['primary'], fontsize=10, fontweight='bold',
            ha='center', va='bottom')

    # Marcador del golpe al frenar (solo si es notablemente mayor)
    if F_imp_N > F_N * 1.08:
        ax.axvline(F_imp_N, color=COLORS['danger'], lw=2, ls='--', zorder=4)
        ax.text(F_imp_N, -0.45, 'el golpe\nal frenar',
                color=COLORS['danger'], fontsize=9, fontweight='bold',
                ha='center', va='top', linespacing=1.1)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xscale('log')
    ax.set_xlim(0.7, 80000)
    ax.set_ylim(-0.7, len(REFERENCIAS) - 0.1)
    ax.set_title('¿Cuánta fuerza es eso?  Compárala:',
                 fontsize=13, fontweight='bold', color=COLORS['primary'], pad=10)
    ax.tick_params(axis='x', labelbottom=False)
    ax.grid(axis='x', alpha=0.12)


@simulation(backend='mpl', order=1,
            title='¿Qué es un Newton?',
            description='El peso es una fuerza; caída y golpe al frenar.')
def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(15, 8.6))
    fig.suptitle('¿Qué es un Newton?',
                 fontsize=24, fontweight='bold', color=COLORS['primary'], y=0.965)
    fig.text(0.5, 0.905,
             'El Newton (N) mide la FUERZA. El peso es una fuerza; '
             'al caer y frenar de golpe, esa fuerza se multiplica.',
             ha='center', fontsize=12.5, color=COLORS['text'])

    # Paneles grandes (el espacio liberado por los controles compactos)
    ax_answer = fig.add_axes([0.03, 0.34, 0.40, 0.52])
    ax_ref = fig.add_axes([0.55, 0.34, 0.42, 0.52])

    # Dos frases-consecuencia (caída y frenado), debajo de los paneles
    txt_fall = fig.text(0.5, 0.275, '', ha='center', fontsize=13,
                        color=COLORS['rope'])
    txt_brake = fig.text(0.5, 0.235, '', ha='center', fontsize=13,
                         color=COLORS['danger'], fontweight='bold')

    # ── Controles compactos, agrupados abajo-izquierda ────────────────
    fig.add_artist(FancyBboxPatch(
        (0.06, 0.025), 0.42, 0.165, boxstyle='round,pad=0.006',
        transform=fig.transFigure, facecolor=COLORS['panel'],
        edgecolor=COLORS['grid'], lw=1.2, alpha=0.55, zorder=0))
    fig.text(0.085, 0.158, 'Controles', fontsize=11, fontweight='bold',
             color=COLORS['primary'])

    # Sliders cortos; al lado, una casilla editable (arrastrar O escribir)
    SLW, TBX = 0.165, 0.385
    ax_m = fig.add_axes([0.205, 0.125, SLW, 0.026])
    ax_h = fig.add_axes([0.205, 0.085, SLW, 0.026])
    ax_t = fig.add_axes([0.205, 0.045, SLW, 0.026])
    sl_mass = Slider(ax_m, 'Peso (kg)', 1, 250, valinit=70,
                     valstep=1, color=COLORS['primary'])
    sl_h = Slider(ax_h, 'Altura (m)', 0, 10, valinit=2,
                  valstep=0.5, color=COLORS['rope'])
    sl_t = Slider(ax_t, 'Frenar (s)', 0.1, 2.0, valinit=0.5,
                  valstep=0.1, color=COLORS['danger'])
    for sl in (sl_mass, sl_h, sl_t):
        sl.label.set_size(10.5)
        sl.valtext.set_visible(False)   # lo reemplaza la casilla editable

    ax_tb_m = fig.add_axes([TBX, 0.125, 0.06, 0.026])
    ax_tb_h = fig.add_axes([TBX, 0.085, 0.06, 0.026])
    ax_tb_t = fig.add_axes([TBX, 0.045, 0.06, 0.026])
    tb_mass = TextBox(ax_tb_m, '', initial='70',  color=COLORS['bg'], hovercolor='#14241a')
    tb_h    = TextBox(ax_tb_h, '', initial='2',   color=COLORS['bg'], hovercolor='#14241a')
    tb_t    = TextBox(ax_tb_t, '', initial='0.5', color=COLORS['bg'], hovercolor='#14241a')
    for tb, c in ((tb_mass, COLORS['primary']), (tb_h, COLORS['rope']),
                  (tb_t, COLORS['danger'])):
        tb.text_disp.set_color(c)
        tb.text_disp.set_fontsize(11)

    _sync = {'busy': False}

    def update(_=None):
        m, h, t = sl_mass.val, sl_h.val, sl_t.val
        v = impact_velocity(h)
        F_imp_N = m * (G + (v / t if v > 0 else 0.0))
        factor = F_imp_N / (m * G)

        _draw_answer(ax_answer, m)
        _draw_reference(ax_ref, m, F_imp_N)

        if v > 0:
            txt_fall.set_text(
                f'Si cae de {h:.1f} m  →  llega a {v:.1f} m/s ({v*3.6:.0f} km/h)')
            txt_brake.set_text(
                f'Si lo frenás en {t:.1f} s  →  el golpe es '
                f'{F_imp_N/1000:.2f} kN  (×{factor:.1f} su peso)')
        else:
            txt_fall.set_text('Subí "Altura" para soltarlo y ver la caída.')
            txt_brake.set_text('')

        fig.canvas.draw_idle()

    def _sync_boxes():
        _sync['busy'] = True
        tb_mass.set_val(f'{sl_mass.val:.0f}')
        tb_h.set_val(f'{sl_h.val:.1f}')
        tb_t.set_val(f'{sl_t.val:.1f}')
        _sync['busy'] = False

    def on_slider(_=None):
        _sync_boxes()      # la barra mueve la casilla
        update()

    def make_submit(slider, lo, hi):
        def _submit(text):
            if _sync['busy']:   # cambio venido de la barra, ignorar
                return
            try:
                v = float(text.replace(',', '.'))
            except ValueError:
                _sync_boxes()   # texto inválido → restaurar
                return
            slider.set_val(max(lo, min(hi, v)))   # la casilla mueve la barra
        return _submit

    for sl in (sl_mass, sl_h, sl_t):
        sl.on_changed(on_slider)
    tb_mass.on_submit(make_submit(sl_mass, 1, 250))
    tb_h.on_submit(make_submit(sl_h, 0, 10))
    tb_t.on_submit(make_submit(sl_t, 0.1, 2.0))

    fig.text(0.73, 0.105,
             '1 N ≈ una manzana\n'
             '1 kN = 1000 N\n'
             'frenar más rápido = golpe más fuerte',
             ha='center', fontsize=10, color=COLORS['text'], alpha=0.7,
             linespacing=1.7)

    update()
    plt.show()


if __name__ == '__main__':
    main()
