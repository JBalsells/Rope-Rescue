"""
╔══════════════════════════════════════════════════════════════════════╗
║          FÍSICA DEL RESCATE · Módulo 02: Vectores y Fuerzas          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización interactiva de suma de N vectores de fuerza           ║
║  aplicada a puntos de anclaje en rescate.                            ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • Un vector tiene magnitud Y dirección                             ║
║   • Las fuerzas se suman vectorialmente                              ║
║   • La resultante determina la carga real en un anclaje              ║
║                                                                      ║
║  Controles: Deslizadores de ángulo y magnitud para N fuerzas         ║
║             Botones para agregar o eliminar fuerzas                  ║
║  Ejecutar:  python 02_vectores_fuerzas.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from config import COLORS, apply_mpl_style

# Colores para hasta 6 vectores — gradiente fósforo verde→lima→teal→ámbar
VECTOR_COLORS = [
    '#00ff33',  # verde   - F1
    '#aaff44',  # lima     - F2
    '#00d9a0',  # teal     - F3
    '#ffcc00',  # amarillo - F4
    '#ffb000',  # ámbar    - F5
    '#ff8844',  # naranja  - F6
]

MAX_VECTORS = 6
MIN_VECTORS = 1

_SUBS = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def sub(n: int) -> str:
    return str(n).translate(_SUBS)


def draw_anchor(ax, x, y):
    ax.plot(x, y, 's', color=COLORS['anchor'], markersize=14, zorder=10)
    ax.plot(x, y, 'o', color=COLORS['text'], markersize=5, zorder=11)


def draw_vector(ax, origin, angle_deg, magnitude, color, label, scale):
    """Dibuja un vector de fuerza con etiqueta."""
    angle_rad = np.radians(angle_deg)
    dx = scale * magnitude * np.cos(angle_rad)
    dy = scale * magnitude * np.sin(angle_rad)
    ax.annotate('', xy=(origin[0] + dx, origin[1] + dy), xytext=origin,
                arrowprops=dict(arrowstyle='->', color=color, lw=2.5,
                                mutation_scale=16))
    lx = np.clip(origin[0] + dx * 1.22, -3.1, 3.1)
    ly = np.clip(origin[1] + dy * 1.22, -3.1, 2.8)
    ax.text(lx, ly, f'{label}\n{magnitude:.2f} kN',
            fontsize=9, fontweight='bold', color=color,
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                      edgecolor=color, alpha=0.85))
    return dx, dy


def build_ui(fig, vectors):
    """Construye/reconstruye toda la interfaz para N vectores."""
    fig.clf()
    n = len(vectors)

    # ── Suptitle y textos (recreados tras clf) ─────────────────────────
    fig.suptitle('Sumar fuerzas: depende del ángulo',
                 fontsize=21, fontweight='bold', color=COLORS['primary'],
                 y=0.975)
    fig.text(0.29, 0.915,
             'Cada flecha es una fuerza (cuánto tira y hacia dónde). '
             'La flecha gruesa es el total.',
             fontsize=11, ha='center', color=COLORS['text'])
    fig.text(0.02, 0.017,
             'Dos fuerzas en distinta dirección NO se suman como simples '
             'números: el ángulo entre ellas cambia el total.',
             fontsize=10, color=COLORS['text'], alpha=0.7, fontstyle='italic')
    fig.text(0.88, 0.017,
             f'Fuerzas: {n}/{MAX_VECTORS}',
             fontsize=10, ha='left', color=COLORS['primary'])

    # ── Ejes principales ───────────────────────────────────────────────
    ax_vec  = fig.add_axes([0.03, 0.08, 0.52, 0.87])
    ax_info = fig.add_axes([0.57, 0.50, 0.41, 0.43])

    # ── Constantes de layout para sliders ─────────────────────────────
    SH  = 0.024   # altura de cada slider
    GAP = 0.005   # espacio entre par ang/mag del mismo vector
    SEP = 0.009   # espacio entre grupos de vectores
    PER = 2 * SH + GAP + SEP   # altura total por vector = 0.062
    Y0  = 0.09    # y-base del primer par de sliders
    XL  = 0.620   # x izquierdo de los sliders
    WS  = 0.30    # ancho de los sliders (deja sitio a la casilla editable)

    sliders_ang = []
    sliders_mag = []

    for i in range(n):
        color     = VECTOR_COLORS[i % len(VECTOR_COLORS)]
        y_base    = Y0 + i * PER
        label_sub = sub(i + 1)

        # Slider de magnitud (inferior del par)
        ax_m = fig.add_axes([XL, y_base, WS, SH])
        sl_m = Slider(ax_m, f'F{i+1} fuerza', 0.1, 10.0,
                      valinit=vectors[i]['magnitude'], color=color,
                      valstep=0.05)
        sl_m.label.set_color(color)
        sl_m.label.set_fontsize(9.5)
        sl_m.valtext.set_color(COLORS['text'])
        sl_m.valtext.set_fontsize(8)

        # Slider de ángulo (superior del par)
        ax_a = fig.add_axes([XL, y_base + SH + GAP, WS, SH])
        sl_a = Slider(ax_a, f'F{i+1} ángulo', -180, 180,
                      valinit=vectors[i]['angle'], color=color, valstep=1)
        sl_a.label.set_color(color)
        sl_a.label.set_fontsize(9.5)
        sl_a.valtext.set_color(COLORS['text'])
        sl_a.valtext.set_fontsize(8)

        sliders_ang.append(sl_a)
        sliders_mag.append(sl_m)

    # ── Botones Agregar / Eliminar ─────────────────────────────────────
    can_add = n < MAX_VECTORS
    can_rem = n > MIN_VECTORS

    ax_add = fig.add_axes([0.572, 0.042, 0.13, 0.038])
    ax_rem = fig.add_axes([0.715, 0.042, 0.13, 0.038])

    btn_add = Button(ax_add, '+ Agregar F',
                     color=COLORS['panel'],
                     hovercolor='#1a3a1a' if can_add else COLORS['panel'])
    btn_rem = Button(ax_rem, '− Eliminar F',
                     color=COLORS['panel'],
                     hovercolor='#3a1a1a' if can_rem else COLORS['panel'])

    btn_add.label.set_color(COLORS['accent'] if can_add else COLORS['grid'])
    btn_add.label.set_fontsize(9)
    btn_rem.label.set_color(COLORS['danger'] if can_rem else COLORS['grid'])
    btn_rem.label.set_fontsize(9)

    # ── Función update ─────────────────────────────────────────────────
    def update(_=None):
        forces = [(sliders_ang[i].val, sliders_mag[i].val) for i in range(n)]

        # Componentes y resultante física
        cx = sum(m * np.cos(np.radians(a)) for a, m in forces)
        cy = sum(m * np.sin(np.radians(a)) for a, m in forces)
        R       = np.sqrt(cx**2 + cy**2)
        r_angle = np.degrees(np.arctan2(cy, cx))
        sum_arith  = sum(m for _, m in forces)
        efficiency = R / sum_arith * 100 if sum_arith > 0 else 0

        # ── Panel vectorial ────────────────────────────────────────────
        ax_vec.clear()
        ax_vec.set_xlim(-3.5, 3.5)
        ax_vec.set_ylim(-3.5, 3.0)
        ax_vec.set_aspect('equal')
        ax_vec.grid(True, alpha=0.12)
        ax_vec.axhline(0, color=COLORS['grid'], lw=0.5)
        ax_vec.axvline(0, color=COLORS['grid'], lw=0.5)
        for sp in ax_vec.spines.values():
            sp.set_visible(False)
        ax_vec.set_xticks([])
        ax_vec.set_yticks([])

        draw_anchor(ax_vec, 0, 0)

        max_m = max(m for _, m in forces) if forces else 1.5
        # Incluir R en la escala: cuando las fuerzas se alinean, la resultante
        # puede ser mayor que cualquier fuerza individual y saldría del eje.
        scale = 2.5 / max(R, max_m, 1.5)

        dx_all, dy_all = [], []
        for i, (ang, mag) in enumerate(forces):
            c = VECTOR_COLORS[i % len(VECTOR_COLORS)]
            dx, dy = draw_vector(ax_vec, (0, 0), ang, mag,
                                 c, f'F{sub(i + 1)}', scale)
            dx_all.append(dx)
            dy_all.append(dy)

        tot_dx = sum(dx_all)
        tot_dy = sum(dy_all)

        # Paralelogramo (solo con exactamente 2 vectores)
        if n == 2:
            ax_vec.plot([dx_all[0], dx_all[0] + dx_all[1]],
                        [dy_all[0], dy_all[0] + dy_all[1]],
                        '--', color=VECTOR_COLORS[1], alpha=0.4, lw=1.2)
            ax_vec.plot([dx_all[1], dx_all[0] + dx_all[1]],
                        [dy_all[1], dy_all[0] + dy_all[1]],
                        '--', color=VECTOR_COLORS[0], alpha=0.4, lw=1.2)
            # Arco del ángulo entre F1 y F2
            a1, a2 = forces[0][0], forces[1][0]
            angle_between = abs(a1 - a2)
            if angle_between > 180:
                angle_between = 360 - angle_between
            thetas = np.linspace(np.radians(min(a1, a2)),
                                 np.radians(max(a1, a2)), 50)
            ax_vec.plot(0.5 * np.cos(thetas), 0.5 * np.sin(thetas),
                        color=COLORS['warning'], lw=1.5, alpha=0.7)
            mid_a = np.radians((a1 + a2) / 2)
            ax_vec.text(0.72 * np.cos(mid_a), 0.72 * np.sin(mid_a),
                        f'{angle_between:.0f}°',
                        fontsize=10, color=COLORS['warning'],
                        ha='center', va='center')

        # Flecha resultante
        if R > 0.01:
            ax_vec.annotate('', xy=(tot_dx, tot_dy), xytext=(0, 0),
                            arrowprops=dict(arrowstyle='->',
                                            color=COLORS['warning'],
                                            lw=3.5, mutation_scale=22))
            tx = np.clip(tot_dx * 1.15, -3.1, 3.1)
            ty = np.clip(tot_dy * 1.15, -3.1, 2.7)
            ax_vec.text(tx, ty, f'R = {R:.2f} kN',
                        fontsize=12, fontweight='bold',
                        color=COLORS['warning'], ha='center',
                        bbox=dict(boxstyle='round,pad=0.3',
                                  facecolor=COLORS['bg'],
                                  edgecolor=COLORS['warning'], alpha=0.9))

        # ── Panel informativo ──────────────────────────────────────────
        ax_info.clear()
        ax_info.axis('off')

        y_pos = 0.97

        def wt(text, color, size, bold=False):
            nonlocal y_pos
            if not text:
                y_pos -= 0.016
                return
            ax_info.text(0.04, y_pos, text, fontsize=size,
                         fontweight='bold' if bold else 'normal',
                         color=color, transform=ax_info.transAxes,
                         va='top', family='monospace')
            y_pos -= 0.055 if size >= 12 else 0.043 if size >= 9 else 0.035

        wt('RESULTADO', COLORS['primary'], 13, bold=True)
        wt('', '', 0)
        for i, (ang, mag) in enumerate(forces):
            c = VECTOR_COLORS[i % len(VECTOR_COLORS)]
            wt(f'Fuerza {i+1}:  {mag:.2f} kN  hacia {ang:+.0f}°', c, 10)

        wt('', '', 0)
        wt(f'Juntas tiran con:  {R:.2f} kN', COLORS['warning'], 13, bold=True)
        wt(f'en dirección {r_angle:.0f}°', COLORS['warning'], 10)
        wt('', '', 0)
        wt('─' * 34, COLORS['grid'], 8)
        wt('', '', 0)
        wt(f'Sumando los números:        {sum_arith:.2f} kN', COLORS['text'], 10)
        wt(f'Total real (por el ángulo): {R:.2f} kN', COLORS['text'], 10)
        if sum_arith - R > 0.05:
            wt('El ángulo se "comió" parte de la fuerza.',
               COLORS['info'], 9)
        wt('', '', 0)

        if n >= 2:
            angles = [a for a, _ in forces]
            max_spread = 0
            for ii in range(len(angles)):
                for jj in range(ii + 1, len(angles)):
                    d = abs(angles[ii] - angles[jj])
                    if d > 180:
                        d = 360 - d
                    max_spread = max(max_spread, d)
            if max_spread < 60:
                wt(f'Ángulo entre ellas: {max_spread:.0f}°', COLORS['accent'], 10)
                wt('Apuntan casi igual: se suman bien.', COLORS['accent'], 9)
            elif max_spread < 120:
                wt(f'Ángulo entre ellas: {max_spread:.0f}°', COLORS['warning'], 10)
                wt('Bastante abiertas: el total baja.', COLORS['warning'], 9)
            else:
                wt(f'Ángulo entre ellas: {max_spread:.0f}°', COLORS['danger'], 10)
                wt('Casi opuestas: se cancelan entre sí.', COLORS['danger'], 9)
        else:
            wt('Agregá otra fuerza para comparar.', COLORS['grid'], 9)

        fig.canvas.draw_idle()

    # ── Callbacks de botones ───────────────────────────────────────────
    def _save_state():
        for i in range(n):
            vectors[i]['angle']     = float(sliders_ang[i].val)
            vectors[i]['magnitude'] = float(sliders_mag[i].val)

    def on_add(_):
        if n < MAX_VECTORS:
            _save_state()
            vectors.append({'angle': -90.0, 'magnitude': 0.78})
            build_ui(fig, vectors)

    def on_remove(_):
        if n > MIN_VECTORS:
            _save_state()
            vectors.pop()
            build_ui(fig, vectors)

    btn_add.on_clicked(on_add)
    btn_rem.on_clicked(on_remove)

    from controls import attach_editable_numbers
    ctrls = []
    for i in range(n):
        ctrls.append((sliders_ang[i], -180, 180, lambda v: f'{v:.0f}'))
        ctrls.append((sliders_mag[i], 0.1, 10.0, lambda v: f'{v:.2f}'))
    _ftop = Y0 + (n - 1) * PER + 2 * SH + GAP + 0.05   # alto según nº fuerzas
    attach_editable_numbers(fig, ctrls, redraw=update, box_w=0.045,
                            frame=(0.565, 0.03, 0.43, _ftop - 0.03))

    # Mantener referencias vivas para evitar que el GC desconecte los callbacks
    fig._widgets = sliders_ang + sliders_mag + [btn_add, btn_rem]

    update()


from registry import simulation


@simulation(backend='mpl', order=2,
            title='Suma vectorial de fuerzas',
            description='Resultante de N vectores en un anclaje.')
def main():
    apply_mpl_style()
    vectors = [
        {'angle': -120.0, 'magnitude': 0.78},
        {'angle':  -60.0, 'magnitude': 0.78},
    ]
    fig = plt.figure(figsize=(16, 9))
    build_ui(fig, vectors)
    plt.show()


if __name__ == '__main__':
    main()
