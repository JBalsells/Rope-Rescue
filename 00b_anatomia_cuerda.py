"""
╔══════════════════════════════════════════════════════════════════════╗
║     FÍSICA DEL RESCATE · Módulo 00b: Anatomía de la Cuerda          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización de la estructura interna kernmantle y comparación     ║
║  de comportamiento entre cuerdas estática, semiestática y dinámica. ║
║                                                                      ║
║  Fisica de elongacion:                                               ║
║   e_estatica    = min(F/MBS * 2,  2)  %                             ║
║   e_semiestatica= min(F/MBS * 6,  6)  %                             ║
║   e_dinamica    = min(F/MBS * 40, 40) %                             ║
║                                                                      ║
║  Controles: Carga (kN) · Masa (kg)                                   ║
║  Ejecutar:  python 00b_anatomia_cuerda.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider
from matplotlib.patches import FancyBboxPatch, Circle
from config import COLORS, G, ROPE_STATIC_MBS, ROPE_DYNAMIC_MBS, NFPA_WORK_LOAD, apply_mpl_style


# ── Constantes de los tipos de cuerda ─────────────────────────────────

TIPOS_CUERDA = [
    {
        'nombre':     'Estatica',
        'subtitulo':  '11 mm  EN 1891-A',
        'color':      COLORS['secondary'],
        'mbs':        ROPE_STATIC_MBS,       # kN
        'elong_max':  2.0,                   # % a MBS
        'factor':     2.0,                   # e = F/MBS * factor
        'absorcion':  'Baja',
        'uso':        'Rappel, rescate,\nizar victimas',
        'ejemplo':    'Beal Antipodes',
    },
    {
        'nombre':     'Semiestatica',
        'subtitulo':  '10.5 mm  EN 1891-B',
        'color':      COLORS['warning'],
        'mbs':        28.0,                  # kN (tipica)
        'elong_max':  6.0,                   # %
        'factor':     6.0,
        'absorcion':  'Media',
        'uso':        'Espeleologia,\nrescate mixto',
        'ejemplo':    'Petzl Conga',
    },
    {
        'nombre':     'Dinamica',
        'subtitulo':  '10 mm  EN 892',
        'color':      COLORS['accent'],
        'mbs':        ROPE_DYNAMIC_MBS,      # kN
        'elong_max':  40.0,                  # %
        'factor':     40.0,
        'absorcion':  'Alta',
        'uso':        'Escalada deportiva,\nfactor de caida',
        'ejemplo':    'Mammut Infinity',
    },
]

# Posiciones de las 3 columnas en el panel central (en datos de ax_comp)
COL_XS = [0.18, 0.50, 0.82]

# Altura fija del anclaje y longitud de referencia de la cuerda en pantalla
ANCLAJE_Y = 0.92
CUERDA_L0 = 0.55    # longitud visual base de la cuerda


# ── Dibujo de la seccion transversal kernmantle ───────────────────────

def _draw_seccion_transversal(ax, carga_kN):
    """Dibuja la seccion transversal de una cuerda kernmantle."""
    ax.clear()
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Seccion Transversal\n(cuerda kernmantle)',
                 fontsize=11, fontweight='bold', color=COLORS['text'], pad=6)

    # ── Funda exterior (mantle) ────────────────────────────────────────
    # Bajo carga, la funda se comprime ligeramente (efecto visual)
    deform = min(carga_kN / ROPE_STATIC_MBS * 0.08, 0.08)
    mantle = Circle((0, 0), 1.0 - deform,
                    facecolor=COLORS['rope'], edgecolor='white',
                    linewidth=2.5, alpha=0.9)
    ax.add_patch(mantle)

    # ── Alma (kern): ~12 filamentos en disposicion circular + centro ────
    filament_r = 0.13          # radio de cada filamento
    orbit_r    = 0.56          # orbita de los filamentos exteriores
    n_outer    = 11

    # Filamentos exteriores
    for i in range(n_outer):
        ang = 2 * np.pi * i / n_outer
        fx = orbit_r * np.cos(ang)
        fy = orbit_r * np.sin(ang)
        # Color varia ligeramente con la carga para dar sensacion de tension
        tension_alpha = 0.7 + min(carga_kN / ROPE_STATIC_MBS * 0.3, 0.3)
        fil = Circle((fx, fy), filament_r,
                     facecolor='white', edgecolor='#BDBDBD',
                     linewidth=1.2, alpha=tension_alpha)
        ax.add_patch(fil)

    # Filamento central
    fil_centro = Circle((0, 0), filament_r * 1.1,
                        facecolor='#E0E0E0', edgecolor='#9E9E9E',
                        linewidth=1.2, alpha=0.85)
    ax.add_patch(fil_centro)

    # ── Anotaciones con flechas ────────────────────────────────────────
    # Flecha a la funda
    ax.annotate('Funda (mantle)\n30-40% resistencia',
                xy=(0.72, 0.72), xytext=(1.05, 0.90),
                fontsize=8.5, color=COLORS['rope'], fontweight='bold',
                ha='left', va='center',
                arrowprops=dict(arrowstyle='->', color=COLORS['rope'],
                                lw=1.5, connectionstyle='arc3,rad=-0.2'))

    # Flecha al alma
    ax.annotate('Alma (kern)\n60-70% resistencia',
                xy=(0.40, 0.0), xytext=(0.90, -0.82),
                fontsize=8.5, color='white', fontweight='bold',
                ha='left', va='center',
                arrowprops=dict(arrowstyle='->', color='white',
                                lw=1.5, connectionstyle='arc3,rad=0.3'))

    # Indicador de carga aplicada (circulo exterior que "aprieta")
    if carga_kN > 0.5:
        frac = min(carga_kN / ROPE_STATIC_MBS, 1.0)
        tension_circle = Circle((0, 0), 1.02 - deform,
                                facecolor='none',
                                edgecolor=_color_carga(carga_kN),
                                linewidth=3.5 * (0.5 + frac),
                                alpha=0.6, linestyle='--')
        ax.add_patch(tension_circle)


def _color_carga(carga_kN):
    """Devuelve color segun el nivel de carga."""
    if carga_kN < 10.0:
        return COLORS['accent']
    elif carga_kN < 20.0:
        return COLORS['warning']
    else:
        return COLORS['danger']


def _estado_cuerda(carga_kN):
    """Devuelve (texto, color) del estado de la cuerda."""
    if carga_kN < 10.0:
        return 'OK — Carga segura', COLORS['accent']
    elif carga_kN < 20.0:
        return 'PRECAUCION — Carga elevada', COLORS['warning']
    else:
        return 'PELIGRO — Cerca del limite', COLORS['danger']


# ── Dibujo del panel de comparacion de tipos ──────────────────────────

def _elongacion(tipo, carga_kN):
    """Calcula elongacion visual en porcentaje."""
    mbs = tipo['mbs']
    if mbs <= 0:
        return 0.0
    frac = carga_kN / mbs
    return min(frac * tipo['factor'], tipo['elong_max'])


def _draw_comparacion(ax, masa_kg, carga_kN):
    """
    Dibuja 3 columnas (estatica / semiestatica / dinamica) con:
    - Anclaje arriba
    - Cuerda estirada visualmente
    - Masa colgando
    - Etiqueta de elongacion
    - Barra de energia absorbida
    """
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_title('Comparacion visual: elongacion bajo carga',
                 fontsize=11, fontweight='bold', color=COLORS['text'], pad=6)

    peso_N  = masa_kg * G
    peso_kN = peso_N / 1000.0
    # Si se proporciono una carga externa (slider de kN), usarla para elongacion
    # Si no, usar el peso de la masa
    F_para_elong = carga_kN if carga_kN > 0 else peso_kN

    for i, tipo in enumerate(TIPOS_CUERDA):
        cx = COL_XS[i]
        color = tipo['color']

        # Etiqueta de tipo (arriba)
        ax.text(cx, 0.98, tipo['nombre'],
                ha='center', va='top',
                fontsize=11, fontweight='bold', color=color)
        ax.text(cx, 0.94, tipo['subtitulo'],
                ha='center', va='top',
                fontsize=8, color=COLORS['text'], alpha=0.60)

        # Anclaje (triangulo apuntando arriba)
        anc_y = ANCLAJE_Y - 0.04
        tri_xs = [cx - 0.055, cx + 0.055, cx]
        tri_ys = [anc_y,       anc_y,      anc_y + 0.045]
        ax.fill(tri_xs, tri_ys, color=COLORS['anchor'], zorder=5)
        ax.plot(tri_xs + [tri_xs[0]], tri_ys + [tri_ys[0]],
                color='white', lw=1.2, zorder=6)

        # Calcular elongacion
        elong_pct = _elongacion(tipo, F_para_elong)

        # Longitud visual de la cuerda (CUERDA_L0 estirada segun elongacion)
        # Se escala para que sea visualmente llamativo pero caber en el panel
        elong_visual_factor = elong_pct / tipo['elong_max'] if tipo['elong_max'] > 0 else 0
        l_estirada = CUERDA_L0 * (1.0 + elong_visual_factor * 0.55)

        rope_y_top = anc_y
        rope_y_bot = rope_y_top - l_estirada

        # Dibujar cuerda
        ax.plot([cx, cx], [rope_y_bot, rope_y_top],
                color=color, lw=5.5, solid_capstyle='round',
                alpha=0.88, zorder=3)

        # Masa (rectangulo)
        masa_h = 0.062
        masa_w = 0.095
        masa_rect = FancyBboxPatch(
            (cx - masa_w / 2, rope_y_bot - masa_h),
            masa_w, masa_h,
            boxstyle='round,pad=0.005',
            facecolor=color, edgecolor='white', linewidth=1.5,
            alpha=0.9, zorder=4
        )
        ax.add_patch(masa_rect)
        ax.text(cx, rope_y_bot - masa_h / 2,
                f'{masa_kg:.0f} kg',
                ha='center', va='center',
                fontsize=8, fontweight='bold', color='white', zorder=5)

        # Etiqueta de elongacion (al lado de la cuerda)
        ax.text(cx + 0.085, (rope_y_top + rope_y_bot) / 2,
                f'{elong_pct:.1f}%',
                ha='left', va='center',
                fontsize=9, fontweight='bold', color=color)

        # Flecha de elongacion (doble flecha indicando estiramiento)
        if elong_pct > 0.2:
            ax.annotate('', xy=(cx - 0.065, rope_y_bot),
                        xytext=(cx - 0.065, rope_y_top - CUERDA_L0),
                        arrowprops=dict(arrowstyle='<->',
                                        color=color, lw=1.2, alpha=0.6,
                                        mutation_scale=10))
            ax.text(cx - 0.075, rope_y_top - CUERDA_L0 / 2,
                    f'+{elong_pct:.1f}%',
                    ha='right', va='center',
                    fontsize=7.5, color=color, alpha=0.8)

        # ── Barra de energia absorbida ─────────────────────────────────
        bar_y0 = rope_y_bot - masa_h - 0.04
        bar_max_w = 0.14
        # Energia proporcional a elong_visual_factor
        e_norm = elong_visual_factor
        bar_w = max(e_norm * bar_max_w, 0.005)

        ax.add_patch(FancyBboxPatch(
            (cx - bar_max_w / 2, bar_y0 - 0.020), bar_max_w, 0.020,
            boxstyle='round,pad=0.002',
            facecolor=COLORS['grid'], edgecolor='none', alpha=0.5
        ))
        ax.add_patch(FancyBboxPatch(
            (cx - bar_max_w / 2, bar_y0 - 0.020), bar_w, 0.020,
            boxstyle='round,pad=0.002',
            facecolor=color, edgecolor='none', alpha=0.80
        ))
        ax.text(cx, bar_y0 - 0.032,
                f'Absorcion: {tipo["absorcion"]}',
                ha='center', va='top',
                fontsize=7.5, color=color)

    # ── Peso aplicado en texto central ────────────────────────────────
    ax.text(0.50, 0.06,
            f'Masa: {masa_kg:.0f} kg  |  Fuerza: {F_para_elong:.2f} kN',
            ha='center', va='bottom',
            fontsize=10, fontweight='bold', color=COLORS['text'],
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=COLORS['panel'],
                      edgecolor=COLORS['grid'], lw=1.2, alpha=0.9))


# ── Dibujo de la tabla comparativa ────────────────────────────────────

def _draw_tabla(ax):
    """Dibuja tabla fija de comparacion de tipos de cuerda."""
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # Cabecera
    headers = ['Caracteristica', 'Estatica', 'Semiestatica', 'Dinamica']
    col_xs  = [0.02, 0.30, 0.56, 0.78]
    col_colors = [COLORS['text'], COLORS['secondary'], COLORS['warning'], COLORS['accent']]

    y_header = 0.95
    for j, (hdr, cx_h, hc) in enumerate(zip(headers, col_xs, col_colors)):
        ax.text(cx_h, y_header, hdr,
                ha='left', va='top',
                fontsize=9, fontweight='bold', color=hc)

    # Linea separadora
    ax.plot([0.01, 0.99], [y_header - 0.07, y_header - 0.07],
            color=COLORS['grid'], lw=1.2, alpha=0.8)

    # Filas de datos
    filas = [
        ('MBS tipica',
         f'{ROPE_STATIC_MBS:.0f} kN', '28 kN', f'{ROPE_DYNAMIC_MBS:.0f} kN'),
        ('Elongacion',
         '< 2%', '2-6%', '20-40%'),
        ('Absorcion energia',
         'Baja', 'Media', 'Alta'),
        ('Factor de caida',
         'NO apto', 'Maximo 1', 'Hasta 2'),
        ('Uso principal',
         'Rescate/rappel', 'Espeleologia', 'Escalada'),
        ('Ejemplo',
         'Beal Antipodes', 'Petzl Conga', 'Mammut Infinity'),
    ]

    y = y_header - 0.12
    for k, (feat, val_e, val_s, val_d) in enumerate(filas):
        # Fondo alternado
        if k % 2 == 0:
            bg = FancyBboxPatch(
                (0.01, y - 0.04), 0.98, 0.075,
                boxstyle='round,pad=0.002',
                facecolor=COLORS['panel'], edgecolor='none', alpha=0.55
            )
            ax.add_patch(bg)

        row_vals = [feat, val_e, val_s, val_d]
        row_cols = [COLORS['text']] + [t['color'] for t in TIPOS_CUERDA]
        for j, (cx_h, val, rc) in enumerate(zip(col_xs, row_vals, row_cols)):
            bold = (j > 0)
            ax.text(cx_h, y, val,
                    ha='left', va='center',
                    fontsize=8.5, fontweight='bold' if bold else 'normal',
                    color=rc, alpha=0.95 if bold else 0.80)
        y -= 0.118

    ax.set_title('Tabla comparativa de tipos de cuerda',
                 fontsize=10, fontweight='bold', color=COLORS['text'], pad=6)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle('FISICA DEL RESCATE — Anatomia de la Cuerda',
                 fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.977)
    fig.text(0.5, 0.935,
             'Cuerda kernmantle: nucleo (kern) + funda (mantle).  '
             'Cada tipo tiene un comportamiento elastico muy diferente.',
             fontsize=11, ha='center', color=COLORS['warning'], fontstyle='italic')

    # ── Ejes principales ──────────────────────────────────────────────
    # Panel izquierdo: seccion transversal
    ax_sec  = fig.add_axes([0.02, 0.22, 0.26, 0.68])
    ax_sec.set_facecolor(COLORS['panel'])
    for sp in ax_sec.spines.values():
        sp.set_edgecolor(COLORS['grid'])

    # Panel central: comparacion de tipos
    ax_comp = fig.add_axes([0.31, 0.22, 0.38, 0.68])
    ax_comp.set_facecolor(COLORS['panel'])
    for sp in ax_comp.spines.values():
        sp.set_edgecolor(COLORS['grid'])

    # Panel derecho: tabla comparativa
    ax_tabla = fig.add_axes([0.71, 0.22, 0.27, 0.68])
    ax_tabla.set_facecolor(COLORS['panel'])
    for sp in ax_tabla.spines.values():
        sp.set_edgecolor(COLORS['grid'])

    # ── Sliders ───────────────────────────────────────────────────────
    # Slider de carga (kN) — panel izquierdo
    ax_sl_kN = fig.add_axes([0.04, 0.12, 0.22, 0.022])
    sl_kN = Slider(ax_sl_kN, 'Carga (kN)', 0.0, 30.0,
                   valinit=5.0, color=COLORS['primary'], valstep=0.5)
    sl_kN.valtext.set_fontsize(10)

    # Slider de masa (kg) — panel central
    ax_sl_m = fig.add_axes([0.34, 0.12, 0.34, 0.022])
    sl_masa = Slider(ax_sl_m, 'Masa (kg)', 1.0, 200.0,
                     valinit=80.0, color=COLORS['secondary'], valstep=1.0)
    sl_masa.valtext.set_fontsize(10)

    # ── Texto de estado de la cuerda (debajo del slider kN) ───────────
    estado_text = fig.text(0.15, 0.065, '',
                           ha='center', va='center',
                           fontsize=11, fontweight='bold',
                           color=COLORS['accent'],
                           bbox=dict(boxstyle='round,pad=0.35',
                                     facecolor=COLORS['bg'],
                                     edgecolor=COLORS['accent'],
                                     lw=2.0, alpha=0.0))

    # ── Update ────────────────────────────────────────────────────────
    def update(_=None):
        carga_kN = float(sl_kN.val)
        masa_kg  = float(sl_masa.val)

        # Panel izquierdo: seccion transversal
        _draw_seccion_transversal(ax_sec, carga_kN)

        # Texto de estado
        texto_est, color_est = _estado_cuerda(carga_kN)
        estado_text.set_text(texto_est)
        estado_text.set_color(color_est)
        bp = estado_text.get_bbox_patch()
        if bp is not None:
            bp.set_edgecolor(color_est)
            bp.set_alpha(0.92)

        # Panel central: comparacion visual
        _draw_comparacion(ax_comp, masa_kg, carga_kN)

        # Panel derecho: tabla (estatica, solo se dibuja una vez)
        _draw_tabla(ax_tabla)

        fig.canvas.draw_idle()

    sl_kN.on_changed(update)
    sl_masa.on_changed(update)

    # ── Etiquetas de sliders ──────────────────────────────────────────
    fig.text(0.04, 0.160,
             'Carga sobre la cuerda estatica (seccion transversal):',
             fontsize=8.5, color=COLORS['primary'], alpha=0.80)
    fig.text(0.34, 0.160,
             'Masa colgando en el sistema de comparacion:',
             fontsize=8.5, color=COLORS['secondary'], alpha=0.80)

    # ── Nota al pie ───────────────────────────────────────────────────
    fig.text(0.02, 0.018,
             'MBS = Minimum Breaking Strength  |  '
             'Elongacion e = min(F/MBS * factor, max)  |  '
             'La elongacion dinamica absorbe energia y reduce la fuerza de choque  |  '
             'Nunca usar cuerda estatica en escalada con caidas posibles',
             fontsize=8.5, color=COLORS['text'], alpha=0.50, fontstyle='italic')

    # Dibujo inicial
    update()
    plt.show()


if __name__ == '__main__':
    main()
