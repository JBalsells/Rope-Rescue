"""
Controles de matplotlib reutilizables.

`attach_editable_numbers` agrega, al lado de cada Slider ya creado, una casilla
numérica editable y los sincroniza en ambos sentidos: arrastrar la barra
actualiza la casilla, y escribir un número (Enter) mueve la barra. Un guard
evita el bucle barra→casilla→barra. Opcionalmente dibuja un recuadro
"Controles" que agrupa el conjunto.

Uso típico en una sim mpl:

    sliders = [(sl_mass, 1, 250, lambda v: f'{v:.0f}'),
               (sl_h,    0,  10, lambda v: f'{v:.1f}')]
    attach_editable_numbers(fig, sliders, redraw=update,
                            frame=(0.06, 0.02, 0.42, 0.17))
"""

from matplotlib.widgets import TextBox
from matplotlib.patches import FancyBboxPatch

from config import COLORS


def attach_editable_numbers(fig, controls, redraw, *, box_w=0.05, gap=0.01,
                            frame=None, title='Controles'):
    """
    controls: lista de (slider, vmin, vmax, fmt) — fmt(valor) -> str.
    redraw:   callable() que redibuja la simulación tras cada cambio.
    box_w/gap: ancho de la casilla y separación con el slider (coords figura).
    frame:    (x0, y0, w, h) opcional para dibujar el recuadro agrupador.
    Devuelve la lista de TextBox creados (para mantener referencias vivas).
    """
    if frame is not None:
        x0, y0, w, h = frame
        fig.add_artist(FancyBboxPatch(
            (x0, y0), w, h, boxstyle='round,pad=0.006',
            transform=fig.transFigure, facecolor=COLORS['panel'],
            edgecolor=COLORS['grid'], lw=1.2, alpha=0.55, zorder=0))
        if title:
            fig.text(x0 + 0.018, y0 + h - 0.026, title, fontsize=11,
                     fontweight='bold', color=COLORS['primary'])

    sync = {'busy': False}
    items = []
    for sl, lo, hi, fmt in controls:
        p = sl.ax.get_position()
        ax_b = fig.add_axes([p.x1 + gap, p.y0, box_w, p.height])
        tb = TextBox(ax_b, '', initial=fmt(sl.val),
                     color=COLORS['bg'], hovercolor='#14241a')
        tb.text_disp.set_color(sl.poly.get_facecolor())
        tb.text_disp.set_fontsize(11)
        sl.valtext.set_visible(False)   # la casilla reemplaza el número fijo
        items.append((sl, tb, lo, hi, fmt))

    def sync_boxes():
        sync['busy'] = True
        for sl, tb, lo, hi, fmt in items:
            tb.set_val(fmt(sl.val))
        sync['busy'] = False

    def on_slider(_=None):
        sync_boxes()          # la barra mueve la casilla
        redraw()

    def make_submit(sl, lo, hi):
        def _submit(text):
            if sync['busy']:   # cambio venido de la barra → ignorar
                return
            try:
                v = float(text.replace(',', '.'))
            except ValueError:
                sync_boxes()   # inválido → restaurar
                return
            sl.set_val(max(lo, min(hi, v)))   # la casilla mueve la barra
        return _submit

    for sl, tb, lo, hi, fmt in items:
        sl.on_changed(on_slider)
        tb.on_submit(make_submit(sl, lo, hi))

    fig._editable_boxes = [it[1] for it in items]   # evitar GC
    return fig._editable_boxes
