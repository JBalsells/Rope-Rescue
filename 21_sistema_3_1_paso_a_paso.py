"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 21: Sistema 3:1 Paso a Paso          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización interactiva de sistemas de ventaja mecánica:         ║
║  1:1, 2:1, 3:1 (Z-rig) y 4:1.                                      ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • VM = Carga / Fuerza aplicada                                    ║
║   • A mayor VM, menos fuerza pero más cuerda se recorre            ║
║   • Eficiencia real: ~95% por polea (fricción)                     ║
║   • La VM real = VM_teórica × eficiencia_total                     ║
║                                                                      ║
║  Controles:                                                          ║
║   RadioButtons — seleccionar sistema                                 ║
║   Sliders — ajustar masa y distancia de jale                        ║
║                                                                      ║
║  Ejecutar:  python 21_sistema_3_1_paso_a_paso.py                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, RadioButtons
from matplotlib.patches import FancyArrowPatch

from config import COLORS, G, ROPE_STATIC_MBS, ROPE_DYNAMIC_MBS, NFPA_WORK_LOAD, apply_mpl_style

# ── Definición de los sistemas ─────────────────────────────────────────
SYSTEMS = {
    '1:1  Sin poleas':    {'vm': 1, 'pulleys': 0, 'efficiency': 1.0},
    '2:1  Una polea':     {'vm': 2, 'pulleys': 1, 'efficiency': 0.95},
    '3:1  Z-rig':         {'vm': 3, 'pulleys': 2, 'efficiency': 0.95**2},
    '4:1  Cuatro-a-uno':  {'vm': 4, 'pulleys': 3, 'efficiency': 0.95**3},
}
SYSTEM_NAMES = list(SYSTEMS.keys())

# Estado global
state = {
    'system': '3:1  Z-rig',
    'mass_kg': 80.0,
    'pull_dist_m': 1.0,
}


# ══════════════════════════════════════════════════════════════════════
#  DIAGRAMA DE POLEAS
# ══════════════════════════════════════════════════════════════════════

def draw_anchor(ax, x, y, size=0.04, label='Anclaje fijo'):
    """Dibuja un punto de anclaje como triángulo relleno."""
    tri = plt.Polygon(
        [[x, y], [x - size, y + size * 1.5], [x + size, y + size * 1.5]],
        color=COLORS['anchor'], zorder=5
    )
    ax.add_patch(tri)
    # Línea de suelo
    ax.plot([x - size * 1.5, x + size * 1.5], [y + size * 1.5, y + size * 1.5],
            color=COLORS['anchor'], lw=3, zorder=5)
    if label:
        ax.text(x, y + size * 2.2, label, color=COLORS['anchor'],
                ha='center', va='bottom', fontsize=8, fontstyle='italic')


def draw_pulley(ax, x, y, radius=0.03, label='', label_side='right'):
    """Dibuja una polea como círculo con indicador central."""
    circle = plt.Circle((x, y), radius, color=COLORS['panel'],
                         ec=COLORS['primary'], lw=2, zorder=6)
    ax.add_patch(circle)
    dot = plt.Circle((x, y), radius * 0.2, color=COLORS['primary'], zorder=7)
    ax.add_patch(dot)
    if label:
        offset_x = radius * 2.5 if label_side == 'right' else -radius * 2.5
        ha = 'left' if label_side == 'right' else 'right'
        ax.text(x + offset_x, y, label, color=COLORS['primary'],
                ha=ha, va='center', fontsize=7.5, fontstyle='italic')


def draw_load_box(ax, x, y, w=0.12, h=0.08, label=''):
    """Dibuja la carga como rectángulo con etiqueta."""
    rect = mpatches.FancyBboxPatch(
        (x - w / 2, y - h), w, h,
        boxstyle='round,pad=0.005',
        fc=COLORS['panel'], ec=COLORS['secondary'], lw=2, zorder=5
    )
    ax.add_patch(rect)
    ax.text(x, y - h / 2, label, color=COLORS['text'],
            ha='center', va='center', fontsize=9, fontweight='bold', zorder=6)


def draw_rope_arrow(ax, x1, y1, x2, y2, color=None, lw=2.5, label='', label_offset=(0.02, 0)):
    """Dibuja una cuerda con flecha de dirección en el punto medio."""
    c = color or COLORS['rope']
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                                mutation_scale=14))
    ax.plot([x1, x2], [y1, y2], color=c, lw=lw, zorder=4)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(mx, my, label, color=c, fontsize=8, ha='left', va='center')


def draw_diagram_1_1(ax, W_N):
    """Diagrama 1:1 — cuerda directa, sin poleas."""
    # Coordenadas
    anc_x, anc_y = 0.5, 0.92
    load_x, load_y = 0.5, 0.42  # tope superior de la caja

    # Anclaje
    draw_anchor(ax, anc_x, anc_y, label='Anclaje fijo')

    # Cuerda principal (carga hacia anclaje)
    ax.plot([load_x, anc_x], [load_y, anc_y - 0.06], color=COLORS['rope'], lw=3, zorder=4)

    # Flecha de dirección en la mitad de la cuerda
    mid_y = (load_y + anc_y - 0.06) / 2
    ax.annotate('', xy=(load_x, mid_y + 0.04), xytext=(load_x, mid_y - 0.04),
                arrowprops=dict(arrowstyle='->', color=COLORS['rope'], lw=2.5,
                                mutation_scale=14))

    # Carga
    draw_load_box(ax, load_x, load_y, label=f'W = {W_N:.0f} N')

    # Cuerda de jale (resaltada hacia abajo — el rescatista jala hacia abajo)
    jale_y_start = load_y - 0.08
    jale_y_end = load_y - 0.25
    ax.plot([load_x, load_x], [jale_y_start, jale_y_end],
            color=COLORS['warning'], lw=3, linestyle='--', zorder=4)
    ax.annotate('', xy=(load_x, jale_y_end), xytext=(load_x, jale_y_start),
                arrowprops=dict(arrowstyle='->', color=COLORS['warning'], lw=2.5,
                                mutation_scale=16))
    ax.text(load_x + 0.07, (jale_y_start + jale_y_end) / 2,
            f'F = W/1 = {W_N:.0f} N\n(Cuerda de jale)',
            color=COLORS['warning'], fontsize=8.5, ha='left', va='center')

    # Leyenda
    ax.text(0.5, 0.12,
            'Sin poleas: La fuerza de jale\niguala el peso de la carga.',
            color=COLORS['text'], fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', fc=COLORS['panel'],
                      ec=COLORS['grid'], lw=1))


def draw_diagram_2_1(ax, W_N):
    """Diagrama 2:1 — una polea móvil en la carga."""
    anc_x, anc_y = 0.35, 0.92
    pulley_x, pulley_y = 0.5, 0.40   # polea móvil (viaja con la carga)
    amarre_x = 0.65                   # punto de amarre de la cuerda en el anclaje
    jale_x, jale_y = 0.65, 0.92      # donde se jala

    # Anclaje
    draw_anchor(ax, anc_x, anc_y, label='Anclaje fijo')
    # Punto de amarre en pared/anclaje secundario
    ax.plot(amarre_x, anc_y, 'o', color=COLORS['anchor'], ms=10, zorder=6)
    ax.text(amarre_x, anc_y + 0.04, 'Amarre', color=COLORS['anchor'],
            ha='center', fontsize=7.5, fontstyle='italic')

    # Cuerda 1: del amarre fijo (anc_x) baja a la polea móvil
    ax.plot([anc_x, pulley_x], [anc_y - 0.06, pulley_y + 0.03],
            color=COLORS['rope'], lw=3, zorder=4)

    # Cuerda 2: de la polea móvil sube al punto de jale
    ax.plot([pulley_x, amarre_x], [pulley_y + 0.03, anc_y - 0.06],
            color=COLORS['warning'], lw=3, zorder=4)
    # Flecha en cuerda de jale
    mid_jale_x = (pulley_x + amarre_x) / 2
    mid_jale_y = (pulley_y + 0.03 + anc_y - 0.06) / 2
    ax.annotate('', xy=(amarre_x, anc_y - 0.06), xytext=(mid_jale_x, mid_jale_y),
                arrowprops=dict(arrowstyle='->', color=COLORS['warning'], lw=2.5,
                                mutation_scale=14))

    # Polea móvil
    draw_pulley(ax, pulley_x, pulley_y, label='Polea de carga', label_side='left')

    # Carga (debajo de la polea)
    draw_load_box(ax, pulley_x, pulley_y - 0.03, label=f'W = {W_N:.0f} N')

    # Etiqueta fuerza de jale
    ax.text(amarre_x + 0.05, (anc_y - 0.06 + pulley_y + 0.03) / 2,
            f'F = W/2\n= {W_N/2:.0f} N',
            color=COLORS['warning'], fontsize=8.5, ha='left', va='center')

    ax.text(0.5, 0.10,
            'La polea móvil divide la carga\nentre 2 tramos de cuerda.',
            color=COLORS['text'], fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', fc=COLORS['panel'],
                      ec=COLORS['grid'], lw=1))


def draw_diagram_3_1(ax, W_N):
    """Diagrama 3:1 — Z-rig: polea fija de anclaje + polea móvil."""
    anc_x, anc_y = 0.35, 0.92         # anclaje + polea fija
    pm_x, pm_y = 0.55, 0.47           # polea móvil (en la carga)
    amarre_x = 0.65                    # amarre de inicio de cuerda
    jale_x, jale_y = 0.72, 0.92       # extremo de jale

    # Anclaje y polea fija
    draw_anchor(ax, anc_x, anc_y, label='Anclaje fijo')
    draw_pulley(ax, anc_x, anc_y - 0.07, label='Polea de anclaje', label_side='left')

    # Amarre secundario
    ax.plot(amarre_x, anc_y, 'o', color=COLORS['anchor'], ms=10, zorder=6)
    ax.text(amarre_x, anc_y + 0.04, 'Amarre', color=COLORS['anchor'],
            ha='center', fontsize=7.5, fontstyle='italic')

    # Tramo 1: del amarre baja a la polea móvil
    ax.plot([amarre_x, pm_x], [anc_y - 0.01, pm_y + 0.03],
            color=COLORS['rope'], lw=3, zorder=4)
    # Flecha tramo 1
    m1x = (amarre_x + pm_x) / 2
    m1y = (anc_y - 0.01 + pm_y + 0.03) / 2
    ax.annotate('', xy=(pm_x, pm_y + 0.03), xytext=(m1x, m1y),
                arrowprops=dict(arrowstyle='->', color=COLORS['rope'], lw=2,
                                mutation_scale=13))

    # Tramo 2: de la polea móvil sube a la polea fija
    ax.plot([pm_x, anc_x], [pm_y + 0.03, anc_y - 0.10],
            color=COLORS['rope'], lw=3, zorder=4)
    m2x = (pm_x + anc_x) / 2
    m2y = (pm_y + 0.03 + anc_y - 0.10) / 2
    ax.annotate('', xy=(anc_x, anc_y - 0.10), xytext=(m2x, m2y),
                arrowprops=dict(arrowstyle='->', color=COLORS['rope'], lw=2,
                                mutation_scale=13))

    # Tramo 3 (jale): de la polea fija al tirador
    ax.plot([anc_x, jale_x], [anc_y - 0.10, jale_y - 0.01],
            color=COLORS['warning'], lw=3, zorder=4)
    m3x = (anc_x + jale_x) / 2
    m3y = (anc_y - 0.10 + jale_y - 0.01) / 2
    ax.annotate('', xy=(jale_x, jale_y - 0.01), xytext=(m3x, m3y),
                arrowprops=dict(arrowstyle='->', color=COLORS['warning'], lw=2.5,
                                mutation_scale=14))

    # Polea móvil
    draw_pulley(ax, pm_x, pm_y, label='Polea de carga')

    # Carga
    draw_load_box(ax, pm_x, pm_y - 0.03, label=f'W = {W_N:.0f} N')

    # Etiqueta cuerda de jale
    ax.text(jale_x + 0.04, (anc_y - 0.10 + jale_y - 0.01) / 2,
            f'Cuerda de jale\nF = W/3\n= {W_N/3:.0f} N',
            color=COLORS['warning'], fontsize=8.5, ha='left', va='center')

    ax.text(0.5, 0.10,
            'Z-rig: 3 tramos de cuerda soportan\nla carga → se necesita 1/3 de la fuerza.',
            color=COLORS['text'], fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', fc=COLORS['panel'],
                      ec=COLORS['grid'], lw=1))


def draw_diagram_4_1(ax, W_N):
    """Diagrama 4:1 — cuatro ramales."""
    anc_x, anc_y = 0.30, 0.92          # anclaje con polea fija 1
    pf2_x, pf2_y = 0.58, 0.92          # polea fija 2 (redirección)
    pm1_x, pm1_y = 0.38, 0.50          # polea móvil 1
    pm2_x, pm2_y = 0.50, 0.65          # polea móvil 2
    jale_x, jale_y = 0.75, 0.88        # extremo de jale

    # Anclajes
    draw_anchor(ax, anc_x, anc_y, label='Anclaje')
    draw_anchor(ax, pf2_x, pf2_y, label='')

    # Poleas fijas
    draw_pulley(ax, anc_x, anc_y - 0.07, label='Polea fija 1', label_side='left')
    draw_pulley(ax, pf2_x, pf2_y - 0.07, label='Polea fija 2')

    # Poleas móviles
    draw_pulley(ax, pm1_x, pm1_y, label='Móvil 1', label_side='left')
    draw_pulley(ax, pm2_x, pm2_y, label='Móvil 2')

    # Carga (centrada entre poleas móviles)
    carga_x = (pm1_x + pm2_x) / 2
    draw_load_box(ax, carga_x, min(pm1_y, pm2_y) - 0.03,
                  label=f'W = {W_N:.0f} N')

    # Cuerdas (4 tramos simplificados)
    # Tramo 1
    ax.plot([anc_x - 0.01, pm1_x - 0.01], [anc_y - 0.01, pm1_y + 0.03],
            color=COLORS['rope'], lw=2.5, zorder=4)
    # Tramo 2
    ax.plot([pm1_x + 0.01, anc_x + 0.01], [pm1_y + 0.03, anc_y - 0.10],
            color=COLORS['rope'], lw=2.5, zorder=4)
    # Tramo 3
    ax.plot([anc_x + 0.01, pm2_x - 0.01], [anc_y - 0.10, pm2_y + 0.03],
            color=COLORS['rope'], lw=2.5, zorder=4)
    # Tramo 4 (jale)
    ax.plot([pm2_x + 0.01, pf2_x], [pm2_y + 0.03, pf2_y - 0.10],
            color=COLORS['rope'], lw=2.5, zorder=4)
    ax.plot([pf2_x, jale_x], [pf2_y - 0.10, jale_y],
            color=COLORS['warning'], lw=3, zorder=4)

    ax.annotate('', xy=(jale_x, jale_y), xytext=((pf2_x + jale_x)/2, (pf2_y - 0.10 + jale_y)/2),
                arrowprops=dict(arrowstyle='->', color=COLORS['warning'], lw=2.5,
                                mutation_scale=14))

    ax.text(jale_x + 0.02, jale_y,
            f'F = W/4\n= {W_N/4:.0f} N',
            color=COLORS['warning'], fontsize=8.5, ha='left', va='center')

    ax.text(0.5, 0.10,
            '4 ramales soportan la carga\n→ se necesita solo 1/4 de la fuerza.',
            color=COLORS['text'], fontsize=9, ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.4', fc=COLORS['panel'],
                      ec=COLORS['grid'], lw=1))


DIAGRAM_FUNCS = {
    '1:1  Sin poleas':    draw_diagram_1_1,
    '2:1  Una polea':     draw_diagram_2_1,
    '3:1  Z-rig':         draw_diagram_3_1,
    '4:1  Cuatro-a-uno':  draw_diagram_4_1,
}


# ══════════════════════════════════════════════════════════════════════
#  FUNCIONES DE ACTUALIZACIÓN DE PANELES
# ══════════════════════════════════════════════════════════════════════

def update_diagram(ax, sys_name, mass_kg):
    """Redibuja el diagrama de poleas para el sistema y masa actuales."""
    ax.cla()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])

    # Título del diagrama
    sys_data = SYSTEMS[sys_name]
    vm = sys_data['vm']
    ax.text(0.5, 0.98, f'Sistema {sys_name.strip()}',
            color=COLORS['primary'], fontsize=12, fontweight='bold',
            ha='center', va='top', transform=ax.transAxes)

    W_N = mass_kg * G
    DIAGRAM_FUNCS[sys_name](ax, W_N)


def update_compare(ax, sys_name, mass_kg):
    """Actualiza el panel de barras comparativas de fuerza."""
    ax.cla()
    ax.set_facecolor(COLORS['bg'])
    ax.set_title('Fuerza requerida', color=COLORS['text'], fontsize=10, pad=6)

    sys_data = SYSTEMS[sys_name]
    vm = sys_data['vm']
    eff = sys_data['efficiency']
    W_N = mass_kg * G

    f_sin_poleas = W_N
    f_con_sistema = W_N / (vm * eff)
    ahorro = f_sin_poleas - f_con_sistema
    pct_ahorro = ahorro / f_sin_poleas * 100 if f_sin_poleas > 0 else 0

    categorias = ['Sin poleas\n(1:1)', f'Este sistema\n({sys_name.split()[0]})']
    valores = [f_sin_poleas, f_con_sistema]
    colores = [COLORS['danger'], COLORS['accent']]

    bars = ax.barh(categorias, valores, color=colores, height=0.4,
                   edgecolor=COLORS['grid'])

    # Etiquetas en las barras
    for bar, val in zip(bars, valores):
        ax.text(val + f_sin_poleas * 0.02, bar.get_y() + bar.get_height() / 2,
                f'{val:.0f} N', color=COLORS['text'], va='center', fontsize=9,
                fontweight='bold')

    ax.set_xlabel('Fuerza (N)', color=COLORS['text'], fontsize=9)
    ax.set_xlim(0, f_sin_poleas * 1.35)
    ax.tick_params(colors=COLORS['text'], labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_color(COLORS['grid'])

    # Barra de ahorro superpuesta
    ax.barh(['Este sistema\n('+sys_name.split()[0]+')'],
            [ahorro], left=[f_con_sistema], color=COLORS['warning'],
            alpha=0.35, height=0.4)

    ax.text(f_sin_poleas * 0.65, 0.0,
            f'Ahorro: {ahorro:.0f} N  ({pct_ahorro:.0f}%)',
            color=COLORS['warning'], fontsize=8.5, va='center', fontweight='bold')
    ax.grid(axis='x', color=COLORS['grid'], alpha=0.3, lw=0.8)


def update_travel(ax, sys_name, mass_kg, pull_dist_m):
    """Actualiza el panel de relación distancia jalada vs subida."""
    ax.cla()
    ax.set_facecolor(COLORS['bg'])
    ax.set_title('Distancia jalada vs. carga subida', color=COLORS['text'],
                 fontsize=10, pad=6)

    sys_data = SYSTEMS[sys_name]
    vm = sys_data['vm']

    dist_subida = pull_dist_m / vm

    categorias = [f'Jalo: {pull_dist_m:.1f} m', f'Sube: {dist_subida:.2f} m']
    valores = [pull_dist_m, dist_subida]
    colores = [COLORS['warning'], COLORS['accent']]

    bars = ax.barh(categorias, valores, color=colores, height=0.4,
                   edgecolor=COLORS['grid'])
    for bar, val in zip(bars, valores):
        ax.text(val + pull_dist_m * 0.02, bar.get_y() + bar.get_height() / 2,
                f'{val:.2f} m', color=COLORS['text'], va='center', fontsize=9,
                fontweight='bold')

    ax.set_xlabel('Distancia (m)', color=COLORS['text'], fontsize=9)
    ax.set_xlim(0, pull_dist_m * 1.4)
    ax.tick_params(colors=COLORS['text'], labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_color(COLORS['grid'])
    ax.grid(axis='x', color=COLORS['grid'], alpha=0.3, lw=0.8)

    ax.text(pull_dist_m * 0.5, -0.6,
            f'Regla: Jalo {vm}× más cuerda de la que sube la carga.',
            color=COLORS['info'], fontsize=8, ha='center', va='center')


def update_info(ax, sys_name, mass_kg, pull_dist_m):
    """Actualiza el panel informativo con todos los datos del sistema."""
    ax.cla()
    ax.set_facecolor(COLORS['panel'])
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    sys_data = SYSTEMS[sys_name]
    vm = sys_data['vm']
    eff = sys_data['efficiency']
    W_N = mass_kg * G
    f_teorica = W_N / vm
    f_real = W_N / (vm * eff)
    vm_real = vm * eff
    equiv_kg = f_real / G

    y = 0.97
    dy = 0.082

    def txt(text, color=COLORS['text'], size=9.5, bold=False, indent=0):
        nonlocal y
        ax.text(0.05 + indent, y, text, color=color, fontsize=size,
                fontweight='bold' if bold else 'normal', va='top',
                transform=ax.transAxes)
        y -= dy

    txt('DATOS DEL SISTEMA', color=COLORS['primary'], size=11, bold=True)
    y -= 0.01
    txt(sys_name.strip(), color=COLORS['warning'], size=12, bold=True)
    y -= dy * 0.4

    # Separador
    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    txt(f'VM teórica:  {vm}:1', color=COLORS['text'], size=9.5)
    txt(f'Poleas:  {sys_data["pulleys"]}', color=COLORS['text'], size=9.5)
    txt(f'Eficiencia:  {eff*100:.1f}%', color=COLORS['text'], size=9.5)
    txt(f'VM real:  {vm_real:.2f}:1', color=COLORS['primary'], size=9.5, bold=True)

    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    txt(f'Carga (W):', color=COLORS['text'], size=9)
    txt(f'  {mass_kg:.0f} kg × {G} = {W_N:.0f} N', color=COLORS['warning'], size=9.5,
        bold=True)

    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    txt('Fuerza teórica:', color=COLORS['text'], size=9)
    txt(f'  W / VM = {W_N:.0f}/{vm} = {f_teorica:.0f} N', color=COLORS['accent'],
        size=9.5, bold=True)
    txt('Fuerza real (con fricción):', color=COLORS['text'], size=9)
    txt(f'  W / (VM×eff) = {f_real:.0f} N', color=COLORS['secondary'],
        size=9.5, bold=True)

    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    txt(f'Para levantar {mass_kg:.0f} kg', color=COLORS['text'], size=9)
    txt(f'aplicas {f_real:.0f} N', color=COLORS['accent'], size=10, bold=True)
    txt(f'(≈ {equiv_kg:.1f} kg de fuerza)', color=COLORS['accent'], size=9.5)

    y -= dy * 0.3
    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    # Distancia
    dist_subida = pull_dist_m / vm
    txt(f'Jalando {pull_dist_m:.1f} m de cuerda:', color=COLORS['text'], size=9)
    txt(f'  la carga sube {dist_subida:.2f} m', color=COLORS['info'], size=9.5, bold=True)

    y -= dy * 0.3
    ax.axhline(y, color=COLORS['grid'], lw=1, xmin=0.04, xmax=0.96)
    y -= dy * 0.6

    # Nota de eficiencia
    ax.text(0.5, max(y - 0.02, 0.02),
            'Nota: la eficiencia disminuye\ncon cada polea adicional (fricción).',
            color=COLORS['anchor'], fontsize=7.5, ha='center', va='top',
            transform=ax.transAxes, fontstyle='italic')


# ══════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(19, 11))
    fig.suptitle(
        'FÍSICA DEL RESCATE — Ventaja Mecánica Paso a Paso',
        color=COLORS['primary'], fontsize=16, fontweight='bold', y=0.97
    )
    fig.text(
        0.5, 0.93,
        '¿Cómo levantar cargas pesadas con menos esfuerzo? Las poleas multiplican la fuerza.',
        color=COLORS['text'], fontsize=10, ha='center', va='top'
    )

    # ── Crear ejes principales ─────────────────────────────────────────
    ax_diagram = fig.add_axes([0.02, 0.20, 0.40, 0.72])
    ax_compare  = fig.add_axes([0.46, 0.48, 0.25, 0.44])
    ax_travel   = fig.add_axes([0.46, 0.20, 0.25, 0.24])
    ax_info     = fig.add_axes([0.74, 0.20, 0.24, 0.72])

    # Estilo de los ejes secundarios
    for ax in [ax_diagram, ax_compare, ax_travel]:
        ax.set_facecolor(COLORS['bg'])

    ax_info.set_facecolor(COLORS['panel'])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_mass = fig.add_axes([0.15, 0.11, 0.75, 0.022])
    ax_sl_pull = fig.add_axes([0.15, 0.05, 0.75, 0.022])

    sl_mass = Slider(ax_sl_mass, 'Masa (kg)', 1, 200,
                     valinit=state['mass_kg'], valstep=1,
                     color=COLORS['primary'])
    sl_pull = Slider(ax_sl_pull, 'Dist. jale (m)', 0.0, 5.0,
                     valinit=state['pull_dist_m'], valstep=0.1,
                     color=COLORS['warning'])

    for sl in [sl_mass, sl_pull]:
        sl.label.set_color(COLORS['text'])
        sl.valtext.set_color(COLORS['warning'])

    # ── RadioButtons ──────────────────────────────────────────────────
    ax_radio = fig.add_axes([0.02, 0.03, 0.12, 0.14])
    ax_radio.set_facecolor(COLORS['panel'])
    radio = RadioButtons(
        ax_radio, SYSTEM_NAMES,
        active=SYSTEM_NAMES.index(state['system']),
        activecolor=COLORS['warning']
    )
    for label in radio.labels:
        label.set_fontsize(8.5)
        label.set_color(COLORS['text'])

    # ── Función de redibujado global ──────────────────────────────────
    def redraw():
        sys_name = state['system']
        mass_kg = state['mass_kg']
        pull_m = state['pull_dist_m']
        update_diagram(ax_diagram, sys_name, mass_kg)
        update_compare(ax_compare, sys_name, mass_kg)
        update_travel(ax_travel, sys_name, mass_kg, pull_m)
        update_info(ax_info, sys_name, mass_kg, pull_m)
        fig.canvas.draw_idle()

    # ── Callbacks ─────────────────────────────────────────────────────
    def on_system(label):
        state['system'] = label
        redraw()

    def on_mass(val):
        state['mass_kg'] = float(val)
        redraw()

    def on_pull(val):
        state['pull_dist_m'] = float(val)
        redraw()

    radio.on_clicked(on_system)
    sl_mass.on_changed(on_mass)
    sl_pull.on_changed(on_pull)

    # Dibujado inicial
    redraw()
    plt.show()


if __name__ == '__main__':
    main()
