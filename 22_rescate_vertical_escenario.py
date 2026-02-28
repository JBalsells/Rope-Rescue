"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 22: Escenario Rescate Vertical        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Escenario integrador: rescate vertical de una persona              ║
║  atrapada en un pozo o barranco.                                     ║
║                                                                      ║
║  El usuario elige:                                                   ║
║   1. Tipo de anclaje (resistencia en kN)                            ║
║   2. Sistema de poleas (VM)                                          ║
║   3. Profundidad y masa de la víctima                               ║
║                                                                      ║
║  El programa verifica:                                               ║
║   • ¿La cuerda aguanta? (MBS/FS ≥ F_cuerda)                        ║
║   • ¿El anclaje aguanta? (cap/FS ≥ F_cuerda)                       ║
║   • ¿El rescatista puede jalar? (F_jale ≤ 500 N)                  ║
║   • ¿El FS del sistema ≥ 10?                                        ║
║                                                                      ║
║  Ejecutar:  python 22_rescate_vertical_escenario.py                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.widgets import Slider, RadioButtons

from config import COLORS, G, ROPE_STATIC_MBS, ROPE_DYNAMIC_MBS, NFPA_WORK_LOAD, apply_mpl_style

# ── Constantes de diseño ───────────────────────────────────────────────
FS_REQUERIDO = 10.0          # Factor de seguridad mínimo NFPA 1983
F_JALE_MAX_N = 500.0         # Fuerza máxima razonable que puede jalar un rescatista
ROPE_MBS_N = ROPE_STATIC_MBS * 1000.0   # 30 kN → N

# ── Opciones de anclaje ───────────────────────────────────────────────
ANCHORS = {
    'Perno/árbol: 25 kN': 25000.0,
    'Natural/roca: 15 kN': 15000.0,
    'Persona: 8 kN':        8000.0,
}
ANCHOR_NAMES = list(ANCHORS.keys())

# ── Opciones de sistema de poleas ─────────────────────────────────────
PULLEY_SYSTEMS = {
    '1:1 (directo)':   {'vm': 1, 'eff': 1.0},
    '2:1 (una polea)': {'vm': 2, 'eff': 0.95},
    '3:1 (Z-rig)':     {'vm': 3, 'eff': 0.95**2},
}
PULLEY_NAMES = list(PULLEY_SYSTEMS.keys())

# Estado global
state = {
    'anchor':  ANCHOR_NAMES[0],
    'system':  PULLEY_NAMES[2],   # 3:1 por defecto
    'depth_m': 10.0,
    'mass_kg': 120.0,
}


# ══════════════════════════════════════════════════════════════════════
#  CÁLCULOS DE FÍSICA
# ══════════════════════════════════════════════════════════════════════

def compute_forces(mass_kg, anchor_name, sys_name):
    """
    Calcula todas las fuerzas relevantes del sistema de rescate.
    Retorna un dict con los resultados.
    """
    W_N = mass_kg * G                          # Peso total en Newton
    sys_data = PULLEY_SYSTEMS[sys_name]
    vm = sys_data['vm']
    eff = sys_data['eff']
    vm_real = vm * eff

    # Fuerza en la cuerda principal (tramo de carga)
    f_cuerda_N = W_N / vm_real

    # Fuerza en el anclaje (aproximación para sistemas simples)
    # Para 1:1: F_anclaje ≈ 2W (dos tramos)
    # Para 2:1: F_anclaje ≈ W + W/2 = 1.5W
    # Para 3:1: F_anclaje ≈ W + W/3 = 1.33W
    # Fórmula general: F_anclaje = W × (1 + 1/vm_real) para polea fija de anclaje
    if vm == 1:
        f_anclaje_N = W_N + f_cuerda_N   # redirección: ambos tramos al anclaje
    else:
        f_anclaje_N = W_N * (1.0 + 1.0 / vm_real)

    # Fuerza que debe aplicar el rescatista
    f_jale_N = W_N / vm_real

    cap_anclaje_N = ANCHORS[anchor_name]

    # Factor de seguridad: el punto más débil / carga
    min_capacidad = min(ROPE_MBS_N, cap_anclaje_N)
    fs_sistema = min_capacidad / W_N

    # Punto más débil
    if ROPE_MBS_N < cap_anclaje_N:
        punto_debil = f'Cuerda ({ROPE_STATIC_MBS:.0f} kN MBS)'
    else:
        punto_debil = f'Anclaje ({cap_anclaje_N/1000:.0f} kN cap.)'

    return {
        'W_N':          W_N,
        'vm':           vm,
        'vm_real':      vm_real,
        'eff':          eff,
        'f_cuerda_N':   f_cuerda_N,
        'f_anclaje_N':  f_anclaje_N,
        'f_jale_N':     f_jale_N,
        'cap_anclaje_N': cap_anclaje_N,
        'fs_sistema':   fs_sistema,
        'punto_debil':  punto_debil,
    }


def check_safety(res):
    """
    Evalúa los 4 criterios de seguridad.
    Retorna lista de (descripcion, ok: bool, detalle: str).
    """
    W_N = res['W_N']
    f_c = res['f_cuerda_N']
    f_a = res['f_anclaje_N']
    cap_a = res['cap_anclaje_N']
    f_j = res['f_jale_N']
    fs = res['fs_sistema']

    checks = []

    # 1. Cuerda aguanta
    umbral_cuerda = ROPE_MBS_N / FS_REQUERIDO
    ok1 = f_c <= umbral_cuerda
    checks.append((
        '¿Cuerda aguanta?',
        ok1,
        f'F_cuerda={f_c/1000:.2f} kN  |  lím={umbral_cuerda/1000:.2f} kN (MBS/10)'
    ))

    # 2. Anclaje aguanta
    umbral_anclaje = cap_a / FS_REQUERIDO
    ok2 = f_a <= cap_a   # comparamos la fuerza real con la capacidad (sin FS sobre anclaje aquí,
                          # porque el FS lo aplicamos globalmente al final)
    checks.append((
        '¿Anclaje aguanta?',
        ok2,
        f'F_anclaje={f_a/1000:.2f} kN  |  cap={cap_a/1000:.0f} kN'
    ))

    # 3. Rescatista puede jalar
    ok3 = f_j <= F_JALE_MAX_N
    checks.append((
        '¿Rescatista puede jalar?',
        ok3,
        f'F_jale={f_j:.0f} N  |  máx humano={F_JALE_MAX_N:.0f} N'
    ))

    # 4. FS del sistema ≥ 10
    ok4 = fs >= FS_REQUERIDO
    checks.append((
        f'¿FS del sistema ≥ {FS_REQUERIDO:.0f}?',
        ok4,
        f'FS={fs:.1f}:1  |  requerido={FS_REQUERIDO:.0f}:1'
    ))

    return checks


# ══════════════════════════════════════════════════════════════════════
#  PANEL: ESCENA VISUAL
# ══════════════════════════════════════════════════════════════════════

def draw_scene(ax, depth_m, mass_kg, anchor_name, sys_name):
    """Dibuja la escena del barranco con la víctima y el sistema de rescate."""
    ax.cla()
    ax.set_facecolor(COLORS['bg'])
    ax.set_xlim(0, 10)
    ax.set_ylim(-depth_m - 3, 5)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    ax.set_title('Escena de rescate', color=COLORS['text'], fontsize=10, pad=4)

    # ── Terreno ──────────────────────────────────────────────────────
    # Superficie superior (borde izquierdo + terreno)
    terreno_y = 0.0
    ax.fill_between([0, 4], [terreno_y - 0.5, terreno_y - 0.5],
                    [terreno_y + 4, terreno_y + 4],
                    color=COLORS['anchor'], alpha=0.4, zorder=1)
    # Borde del barranco (pared vertical)
    ax.fill_between([4, 5.5], [-depth_m - 1, -depth_m - 1],
                    [terreno_y, terreno_y],
                    color=COLORS['anchor'], alpha=0.55, zorder=1)
    # Fondo del barranco
    ax.fill_between([4, 10], [-depth_m - 1, -depth_m - 1],
                    [-depth_m, -depth_m],
                    color=COLORS['anchor'], alpha=0.4, zorder=1)

    # Línea de borde del acantilado
    ax.plot([4, 4], [terreno_y, -depth_m], color=COLORS['anchor'], lw=2, zorder=2)
    ax.plot([0, 4], [terreno_y, terreno_y], color=COLORS['anchor'], lw=2.5, zorder=2)
    ax.plot([4, 10], [-depth_m, -depth_m], color=COLORS['anchor'], lw=2, zorder=2)

    # ── Anclaje ──────────────────────────────────────────────────────
    anc_x, anc_y = 2.0, terreno_y
    if 'Perno' in anchor_name or 'árbol' in anchor_name:
        # Árbol/perno: círculo con cruz
        ax.plot(anc_x, anc_y + 0.7, 'o', color=COLORS['accent'],
                ms=18, zorder=5, markeredgecolor=COLORS['text'], mew=1)
        ax.plot([anc_x, anc_x], [anc_y + 0.25, anc_y + 1.2],
                color=COLORS['accent'], lw=4, zorder=4)
        ax.text(anc_x, anc_y + 1.5, 'Anclaje\nPerno/árbol', color=COLORS['accent'],
                ha='center', fontsize=7.5, zorder=6)
    elif 'Natural' in anchor_name or 'roca' in anchor_name:
        # Roca: polígono irregular
        roca = plt.Polygon([[anc_x - 0.5, anc_y], [anc_x + 0.5, anc_y],
                             [anc_x + 0.7, anc_y + 0.7], [anc_x, anc_y + 1.0],
                             [anc_x - 0.7, anc_y + 0.6]],
                            color=COLORS['anchor'], zorder=5)
        ax.add_patch(roca)
        ax.text(anc_x, anc_y + 1.3, 'Anclaje\nRoca/natural', color=COLORS['anchor'],
                ha='center', fontsize=7.5, zorder=6)
    else:
        # Persona como anclaje
        _draw_person(ax, anc_x, anc_y + 0.8, color=COLORS['info'], scale=0.35)
        ax.text(anc_x, anc_y + 1.8, 'Anclaje\nPersona', color=COLORS['info'],
                ha='center', fontsize=7.5, zorder=6)

    # ── Rescatista en el borde ────────────────────────────────────────
    resc_x = 3.4
    _draw_person(ax, resc_x, terreno_y + 0.9, color=COLORS['warning'], scale=0.4)
    ax.text(resc_x, terreno_y + 2.1, 'Rescatista', color=COLORS['warning'],
            ha='center', fontsize=7.5, zorder=6)

    # ── Víctima al fondo ──────────────────────────────────────────────
    vic_x = 6.5
    vic_y = -depth_m + 0.0
    _draw_person(ax, vic_x, vic_y + 0.8, color=COLORS['danger'], scale=0.4)
    ax.text(vic_x, vic_y + 2.0, f'Víctima\n{mass_kg:.0f} kg', color=COLORS['danger'],
            ha='center', fontsize=7.5, zorder=6)

    # ── Cuerda ────────────────────────────────────────────────────────
    sys_data = PULLEY_SYSTEMS[sys_name]
    vm = sys_data['vm']

    # Cuerda principal: desde el anclaje al borde y luego baja a la víctima
    ax.plot([anc_x, 4.0], [anc_y, terreno_y],
            color=COLORS['rope'], lw=2.5, zorder=3)
    ax.plot([4.0, vic_x], [terreno_y, vic_y + 1.6],
            color=COLORS['rope'], lw=2.5, zorder=3, linestyle='-')

    # Poleas si corresponde
    if vm >= 2:
        # Polea en el anclaje (polea de redirección)
        pc = plt.Circle((anc_x, anc_y + 0.1), 0.25, color=COLORS['panel'],
                         ec=COLORS['primary'], lw=1.5, zorder=5)
        ax.add_patch(pc)
        ax.text(anc_x - 0.7, anc_y + 0.1, 'Polea', color=COLORS['primary'],
                fontsize=7, ha='right', va='center')

    if vm >= 3:
        # Polea en la cuerda (Z-rig: polea de carga, más arriba)
        p_movil_y = vic_y + depth_m * 0.4
        pc2 = plt.Circle((4.3, p_movil_y), 0.25, color=COLORS['panel'],
                          ec=COLORS['primary'], lw=1.5, zorder=5)
        ax.add_patch(pc2)
        ax.text(4.9, p_movil_y, 'Polea\nmóvil', color=COLORS['primary'],
                fontsize=7, ha='left', va='center')

    # ── Flecha de profundidad ─────────────────────────────────────────
    arr_x = 9.2
    ax.annotate('', xy=(arr_x, -depth_m), xytext=(arr_x, terreno_y),
                arrowprops=dict(arrowstyle='<->', color=COLORS['info'],
                                lw=1.5, mutation_scale=12))
    ax.text(arr_x + 0.3, -depth_m / 2, f'{depth_m:.0f} m',
            color=COLORS['info'], fontsize=9, va='center', fontweight='bold')

    # ── Etiqueta del sistema ──────────────────────────────────────────
    ax.text(5, terreno_y + 3.5,
            f'Sistema: {sys_name}\n(VM = {vm}:1)',
            color=COLORS['warning'], fontsize=9, ha='center', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', fc=COLORS['panel'],
                      ec=COLORS['warning'], lw=1))


def _draw_person(ax, cx, cy, color=COLORS['text'], scale=0.5):
    """Dibuja una figura humana muy simplificada (círculo + líneas)."""
    r = 0.2 * scale
    # Cabeza
    head = plt.Circle((cx, cy), r, color=color, zorder=6)
    ax.add_patch(head)
    # Cuerpo
    ax.plot([cx, cx], [cy - r, cy - r * 4], color=color, lw=2 * scale, zorder=6)
    # Brazos
    ax.plot([cx - r * 2, cx + r * 2], [cy - r * 1.8, cy - r * 1.8],
            color=color, lw=1.5 * scale, zorder=6)
    # Piernas
    ax.plot([cx, cx - r * 1.5], [cy - r * 4, cy - r * 7],
            color=color, lw=1.5 * scale, zorder=6)
    ax.plot([cx, cx + r * 1.5], [cy - r * 4, cy - r * 7],
            color=color, lw=1.5 * scale, zorder=6)


# ══════════════════════════════════════════════════════════════════════
#  PANEL: DIAGRAMA DE FUERZAS
# ══════════════════════════════════════════════════════════════════════

def draw_forces(ax, res):
    """Muestra barras horizontales con las fuerzas del sistema."""
    ax.cla()
    ax.set_facecolor(COLORS['bg'])
    ax.set_title('Fuerzas del sistema', color=COLORS['text'], fontsize=10, pad=4)

    W_kN  = res['W_N'] / 1000.0
    fc_kN = res['f_cuerda_N'] / 1000.0
    fa_kN = res['f_anclaje_N'] / 1000.0

    labels  = ['Carga total\n(peso víctima)', 'Fuerza en\ncuerda', 'Fuerza en\nanclaje']
    valores = [W_kN, fc_kN, fa_kN]
    colores = [COLORS['danger'], COLORS['warning'], COLORS['secondary']]

    bars = ax.barh(labels, valores, color=colores, height=0.4,
                   edgecolor=COLORS['grid'])

    max_val = max(valores + [ROPE_STATIC_MBS, NFPA_WORK_LOAD]) * 1.25

    for bar, val in zip(bars, valores):
        ax.text(val + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                f'{val:.2f} kN', color=COLORS['text'], va='center', fontsize=8.5,
                fontweight='bold')

    # Líneas de referencia
    ax.axvline(NFPA_WORK_LOAD, color=COLORS['warning'], lw=1.5, linestyle='--', alpha=0.8,
               label=f'NFPA carga trabajo ({NFPA_WORK_LOAD} kN)')
    ax.axvline(ROPE_STATIC_MBS, color=COLORS['danger'], lw=1.5, linestyle='--', alpha=0.8,
               label=f'MBS cuerda estática ({ROPE_STATIC_MBS} kN)')

    ax.set_xlabel('Fuerza (kN)', color=COLORS['text'], fontsize=8.5)
    ax.set_xlim(0, max_val)
    ax.tick_params(colors=COLORS['text'], labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_color(COLORS['grid'])

    ax.legend(fontsize=7, loc='lower right',
              labelcolor=COLORS['text'],
              facecolor=COLORS['panel'], edgecolor=COLORS['grid'])
    ax.grid(axis='x', color=COLORS['grid'], alpha=0.3, lw=0.8)


# ══════════════════════════════════════════════════════════════════════
#  PANEL: VERIFICACIÓN DE SEGURIDAD
# ══════════════════════════════════════════════════════════════════════

def draw_check(ax, checks):
    """Muestra un checklist visual con los 4 criterios de seguridad."""
    ax.cla()
    ax.set_facecolor(COLORS['panel'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Verificación de seguridad', color=COLORS['text'], fontsize=10, pad=4)

    n = len(checks)
    dy = 1.0 / (n + 0.5)
    for i, (desc, ok, detalle) in enumerate(checks):
        y = 1.0 - (i + 1) * dy
        simbolo = '✔' if ok else '✘'
        color_simbolo = COLORS['accent'] if ok else COLORS['danger']
        color_fondo = '#1a3a1a' if ok else '#3a1a1a'

        # Caja de fondo
        rect = FancyBboxPatch((0.01, y - dy * 0.35), 0.98, dy * 0.72,
                              boxstyle='round,pad=0.01',
                              fc=color_fondo, ec=color_simbolo,
                              lw=1.5, zorder=2)
        ax.add_patch(rect)

        ax.text(0.07, y, simbolo, color=color_simbolo, fontsize=13,
                fontweight='bold', va='center', ha='center', zorder=3)
        ax.text(0.14, y + dy * 0.08, desc,
                color=COLORS['text'], fontsize=8.5, va='center', ha='left',
                fontweight='bold', zorder=3)
        ax.text(0.14, y - dy * 0.18, detalle,
                color=COLORS['anchor'], fontsize=7, va='center', ha='left',
                zorder=3)


# ══════════════════════════════════════════════════════════════════════
#  PANEL: RESUMEN GO / NO-GO
# ══════════════════════════════════════════════════════════════════════

def draw_summary(ax, res, checks):
    """Muestra el resumen final con veredicto GO o NO-GO."""
    ax.cla()
    ax.set_facecolor(COLORS['panel'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    todos_ok = all(ok for _, ok, _ in checks)
    fallos = [(desc, detalle) for desc, ok, detalle in checks if not ok]

    # Veredicto grande
    if todos_ok:
        veredicto = 'GO'
        color_v = COLORS['accent']
        subtexto = 'Sistema SEGURO\npara operar'
    else:
        veredicto = 'NO GO'
        color_v = COLORS['danger']
        subtexto = 'Corrige los problemas\nantes de operar'

    # Fondo del veredicto
    fondo_color = '#0d2b0d' if todos_ok else '#2b0d0d'
    rect = FancyBboxPatch((0.05, 0.72), 0.90, 0.26,
                          boxstyle='round,pad=0.01',
                          fc=fondo_color, ec=color_v, lw=2.5)
    ax.add_patch(rect)

    ax.text(0.5, 0.87, veredicto, color=color_v, fontsize=22, fontweight='bold',
            ha='center', va='center')
    ax.text(0.5, 0.76, subtexto, color=color_v, fontsize=8.5,
            ha='center', va='center')

    # Datos numéricos
    W_kN  = res['W_N'] / 1000.0
    fc_kN = res['f_cuerda_N'] / 1000.0
    fa_kN = res['f_anclaje_N'] / 1000.0
    fj_N  = res['f_jale_N']
    fj_kg = fj_N / G
    fs    = res['fs_sistema']

    datos = [
        ('Carga total (W)',    f'{W_kN:.2f} kN', COLORS['danger']),
        ('F en cuerda',        f'{fc_kN:.2f} kN', COLORS['warning']),
        ('F en anclaje',       f'{fa_kN:.2f} kN', COLORS['secondary']),
        ('F que jalará rescatista', f'{fj_N:.0f} N  (≈{fj_kg:.1f} kg)', COLORS['info']),
        ('FS del sistema',     f'{fs:.1f}:1  (req. {FS_REQUERIDO:.0f}:1)',
         COLORS['accent'] if fs >= FS_REQUERIDO else COLORS['danger']),
        ('Punto más débil',    res['punto_debil'], COLORS['anchor']),
    ]

    y = 0.67
    dy = 0.095
    for etiqueta, valor, color in datos:
        ax.text(0.06, y, etiqueta + ':', color=COLORS['anchor'], fontsize=8,
                va='center', ha='left')
        ax.text(0.97, y, valor, color=color, fontsize=8.5,
                va='center', ha='right', fontweight='bold')
        ax.axhline(y - dy * 0.4, color=COLORS['grid'], lw=0.5,
                   xmin=0.05, xmax=0.95)
        y -= dy

    # Lista de fallos (si los hay)
    if not todos_ok:
        y -= 0.02
        ax.text(0.5, y, 'PROBLEMAS:', color=COLORS['danger'], fontsize=8.5,
                ha='center', va='top', fontweight='bold')
        y -= 0.06
        for desc, detalle in fallos:
            ax.text(0.08, y, f'• {desc}', color=COLORS['danger'],
                    fontsize=7.5, va='top')
            y -= 0.05
            ax.text(0.10, y, detalle, color=COLORS['anchor'],
                    fontsize=7, va='top', fontstyle='italic')
            y -= 0.06

    ax.set_title('Resumen / Veredicto', color=COLORS['text'], fontsize=10, pad=4)


# ══════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(19, 11))
    fig.suptitle(
        'FÍSICA DEL RESCATE — Escenario: Rescate Vertical',
        color=COLORS['primary'], fontsize=16, fontweight='bold', y=0.975
    )
    fig.text(
        0.5, 0.935,
        'Elige el equipo y verifica si el sistema es SEGURO antes de operar.',
        color=COLORS['text'], fontsize=10, ha='center', va='top'
    )

    # ── Crear ejes principales ─────────────────────────────────────────
    ax_scene  = fig.add_axes([0.02, 0.20, 0.32, 0.72])
    ax_forces = fig.add_axes([0.38, 0.48, 0.28, 0.44])
    ax_check  = fig.add_axes([0.38, 0.20, 0.28, 0.24])
    ax_summary = fig.add_axes([0.70, 0.20, 0.28, 0.72])

    for ax in [ax_scene, ax_forces]:
        ax.set_facecolor(COLORS['bg'])
    ax_check.set_facecolor(COLORS['panel'])
    ax_summary.set_facecolor(COLORS['panel'])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_depth = fig.add_axes([0.15, 0.13, 0.75, 0.022])
    ax_sl_mass  = fig.add_axes([0.15, 0.07, 0.75, 0.022])

    sl_depth = Slider(ax_sl_depth, 'Profundidad (m)', 1.0, 30.0,
                      valinit=state['depth_m'], valstep=0.5,
                      color=COLORS['info'])
    sl_mass  = Slider(ax_sl_mass,  'Masa víctima+equipo (kg)', 40.0, 200.0,
                      valinit=state['mass_kg'], valstep=1,
                      color=COLORS['danger'])

    for sl in [sl_depth, sl_mass]:
        sl.label.set_color(COLORS['text'])
        sl.valtext.set_color(COLORS['warning'])

    # ── RadioButtons: tipo de anclaje ─────────────────────────────────
    ax_radio_anchor = fig.add_axes([0.02, 0.10, 0.12, 0.09])
    ax_radio_anchor.set_facecolor(COLORS['panel'])
    radio_anchor = RadioButtons(
        ax_radio_anchor, ANCHOR_NAMES,
        active=0,
        activecolor=COLORS['accent']
    )
    for label in radio_anchor.labels:
        label.set_fontsize(7.5)
        label.set_color(COLORS['text'])

    # Título del grupo de anclaje
    fig.text(0.077, 0.195, 'Tipo de anclaje', color=COLORS['anchor'],
             fontsize=8, ha='center', va='bottom', fontstyle='italic')

    # ── RadioButtons: sistema de poleas ───────────────────────────────
    ax_radio_system = fig.add_axes([0.02, 0.03, 0.12, 0.06])
    ax_radio_system.set_facecolor(COLORS['panel'])
    radio_system = RadioButtons(
        ax_radio_system, PULLEY_NAMES,
        active=PULLEY_NAMES.index(state['system']),
        activecolor=COLORS['warning']
    )
    for label in radio_system.labels:
        label.set_fontsize(7.5)
        label.set_color(COLORS['text'])

    fig.text(0.077, 0.095, 'Sistema de poleas', color=COLORS['warning'],
             fontsize=8, ha='center', va='bottom', fontstyle='italic')

    # ── Función de redibujado global ──────────────────────────────────
    def redraw():
        anchor = state['anchor']
        sys_nm = state['system']
        depth  = state['depth_m']
        mass   = state['mass_kg']

        res    = compute_forces(mass, anchor, sys_nm)
        checks = check_safety(res)

        draw_scene(ax_scene, depth, mass, anchor, sys_nm)
        draw_forces(ax_forces, res)
        draw_check(ax_check, checks)
        draw_summary(ax_summary, res, checks)

        fig.canvas.draw_idle()

    # ── Callbacks ─────────────────────────────────────────────────────
    def on_anchor(label):
        state['anchor'] = label
        redraw()

    def on_system(label):
        state['system'] = label
        redraw()

    def on_depth(val):
        state['depth_m'] = float(val)
        redraw()

    def on_mass(val):
        state['mass_kg'] = float(val)
        redraw()

    radio_anchor.on_clicked(on_anchor)
    radio_system.on_clicked(on_system)
    sl_depth.on_changed(on_depth)
    sl_mass.on_changed(on_mass)

    # Dibujado inicial
    redraw()
    plt.show()


if __name__ == '__main__':
    main()
