"""
╔══════════════════════════════════════════════════════════════════════╗
║    FÍSICA DEL RESCATE · Módulo 17b: Nudos y Resistencia de la       ║
║    Cuerda                                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Los nudos siempre reducen la resistencia de la cuerda.             ║
║  Este módulo muestra cuánto se pierde con cada nudo y qué           ║
║  resistencia queda disponible para la carga.                        ║
║                                                                      ║
║  Física clave:                                                       ║
║   MBS_nudo = MBS_cuerda × (eficiencia / 100)                        ║
║   Pérdida  = MBS_cuerda − MBS_nudo                                  ║
║                                                                      ║
║  Eficiencias típicas (% del MBS de la cuerda):                      ║
║   Sin nudo        → 100 %  (referencia)                             ║
║   Nudo en ocho    →  80 %                                           ║
║   As de guía      →  75 %                                           ║
║   Pescador doble  →  70 %                                           ║
║   Mariposa alpina →  68 %                                           ║
║   Nudo simple     →  60 %                                           ║
║                                                                      ║
║  Ejecutar:  python 17b_nudos_y_resistencia.py                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import matplotlib.patheffects as pe
from matplotlib.widgets import Slider, RadioButtons
from config import COLORS, ROPE_STATIC_MBS, NFPA_WORK_LOAD, apply_mpl_style


# ── Datos de nudos ─────────────────────────────────────────────────────
# (nombre, eficiencia %, color, descripción)
KNOTS = [
    ('Sin nudo',            100, '#4CAF50', 'Referencia: resistencia total de la cuerda'),
    ('Nudo en ocho',         80, '#00BCD4', 'El más usado en rescate. Fácil de verificar.'),
    ('As de guía (Bowline)', 75, '#2196F3', 'Nudo de anclaje rápido. No usar bajo carga dinámica.'),
    ('Pescador doble',       70, '#9C27B0', 'Unión de dos cuerdas. Muy seguro y compacto.'),
    ('Mariposa alpina',      68, '#FF9800', 'Nudo de línea media. Cargable en tres direcciones.'),
    ('Nudo simple',          60, '#F44336', 'El más débil. Solo como nudo de tope de emergencia.'),
]

# Umbral mínimo recomendado de eficiencia en rescate
EFFICIENCY_MIN = 75


# ── Dibujo de diagramas de nudos ──────────────────────────────────────

def _draw_rope_segment(ax, x, y_top, y_bot, color, lw=6):
    """Dibuja un segmento de cuerda vertical (línea simple)."""
    ax.plot([x, x], [y_top, y_bot], color=color, lw=lw,
            solid_capstyle='round', zorder=3)


def _dibujar_sin_nudo(ax, color):
    """Línea recta: sin punto débil."""
    # Cuerda continua de arriba a abajo
    ax.plot([0, 0], [0.85, -0.70], color=color, lw=8,
            solid_capstyle='round', zorder=3)
    ax.text(0, 0.10, 'Sin punto\ndébil', ha='center', va='center',
            fontsize=10, color=COLORS['text'], alpha=0.70,
            style='italic')


def _dibujar_nudo_ocho(ax, color):
    """
    Dibuja la forma característica del nudo en ocho usando una curva
    paramétrica (lemniscata de Bernoulli adaptada a la vertical).
    """
    # Tramo superior de entrada (cuerda viene de arriba)
    ax.plot([0, 0], [0.88, 0.45], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Cuerpo del ocho: dos bucles usando curvas paramétricas
    t_top = np.linspace(np.pi / 2, -np.pi / 2, 120)
    r_top = 0.28
    cx_top, cy_top = 0.0, 0.20
    x_top = cx_top + r_top * np.cos(t_top) * 1.4
    y_top = cy_top + r_top * np.sin(t_top)
    ax.plot(x_top, y_top, color=color, lw=7,
            solid_capstyle='round', zorder=4)

    t_bot = np.linspace(-np.pi / 2, np.pi / 2, 120)
    r_bot = 0.28
    cx_bot, cy_bot = 0.0, -0.18
    x_bot = cx_bot - r_bot * np.cos(t_bot) * 1.4
    y_bot_arr = cy_bot + r_bot * np.sin(t_bot)
    ax.plot(x_bot, y_bot_arr, color=color, lw=7,
            solid_capstyle='round', zorder=4)

    # Punto central del ocho (cruce)
    ax.plot([0], [0.01], 'o', color=COLORS['bg'], ms=10, zorder=5)
    ax.plot([0], [0.01], 'o', color=color, ms=5, zorder=6)

    # Tramo inferior de salida
    ax.plot([0, 0], [-0.46, -0.70], color=color, lw=7,
            solid_capstyle='round', zorder=3)


def _dibujar_as_de_guia(ax, color):
    """
    Dibuja el as de guía (bowline): bucle fijo en el extremo
    con el ramal que sale por dentro y rodea el seno.
    """
    # Entrada superior
    ax.plot([0, 0], [0.88, 0.30], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Bucle del seno (círculo pequeño lateral)
    t_seno = np.linspace(0, 2 * np.pi, 120)
    r_s = 0.14
    ax.plot(0.15 + r_s * np.cos(t_seno),
            0.10 + r_s * np.sin(t_seno),
            color=color, lw=6, solid_capstyle='round', zorder=4)

    # Bucle principal (gaza)
    t_gaza = np.linspace(np.pi, 2 * np.pi, 120)
    r_g = 0.28
    ax.plot(0.0 + r_g * np.cos(t_gaza),
            -0.20 + r_g * 0.65 * np.sin(t_gaza),
            color=color, lw=6, solid_capstyle='round', zorder=4)

    # Ramal que sale hacia abajo
    ax.plot([0, 0], [-0.46, -0.70], color=color, lw=7,
            solid_capstyle='round', zorder=3)


def _dibujar_pescador_doble(ax, color):
    """
    Dibuja el nudo de pescador doble: dos grupos de vueltas
    apretadas que unen dos cabos de cuerda.
    """
    # Cabo izquierdo (entra por la izquierda)
    ax.plot([-0.45, -0.05], [0.10, 0.10], color=color, lw=7,
            solid_capstyle='round', zorder=3)
    ax.plot([-0.45, -0.05], [-0.10, -0.10], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Cuerpo del nudo: bloque central con vueltas
    for dy in [-0.22, -0.08, 0.08, 0.22]:
        ax.plot([-0.12, 0.12], [dy, dy], color=color, lw=5,
                solid_capstyle='round', zorder=4, alpha=0.85)

    # Rectángulo compacto del nudo
    rect_x = np.array([-0.18, 0.18, 0.18, -0.18, -0.18])
    rect_y = np.array([-0.30, -0.30,  0.30,  0.30, -0.30])
    ax.plot(rect_x, rect_y, color=color, lw=2.5, alpha=0.40, zorder=3)

    # Cabo derecho (sale por la derecha)
    ax.plot([0.05, 0.45], [0.10, 0.10], color=color, lw=7,
            solid_capstyle='round', zorder=3)
    ax.plot([0.05, 0.45], [-0.10, -0.10], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Etiqueta descriptiva
    ax.text(0, -0.52, 'Unión de dos cuerdas', ha='center',
            fontsize=8, color=COLORS['text'], alpha=0.60, style='italic')


def _dibujar_mariposa_alpina(ax, color):
    """
    Dibuja la mariposa alpina: nudo de línea media con bucle central
    y dos cabos laterales.
    """
    # Cabo izquierdo
    ax.plot([-0.55, -0.22], [0.05, 0.05], color=color, lw=7,
            solid_capstyle='round', zorder=3)
    # Cabo derecho
    ax.plot([0.22, 0.55], [0.05, 0.05], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Bucle central (mariposa) que cuelga hacia abajo
    t_ala = np.linspace(0, np.pi, 100)
    # Ala izquierda
    ax.plot(-0.22 + 0.22 * np.cos(t_ala),
             0.05 - 0.28 * np.sin(t_ala),
             color=color, lw=7, solid_capstyle='round', zorder=4)
    # Ala derecha
    ax.plot(0.22 - 0.22 * np.cos(t_ala),
            0.05 - 0.28 * np.sin(t_ala),
            color=color, lw=7, solid_capstyle='round', zorder=4)

    # Cuerpo central apretado (cruce)
    for dx in [-0.06, 0.0, 0.06]:
        ax.plot([dx, dx], [-0.05, 0.15], color=color, lw=5,
                solid_capstyle='round', zorder=5, alpha=0.70)

    # Punto de carga inferior del bucle
    ax.plot([0], [-0.25], 'o', color=COLORS['warning'], ms=10, zorder=6)

    ax.text(0, -0.52, 'Cargable en 3 direcciones', ha='center',
            fontsize=8, color=COLORS['text'], alpha=0.60, style='italic')


def _dibujar_nudo_simple(ax, color):
    """
    Dibuja un nudo simple (nudo de tope): bucle sencillo con el
    ramal pasando por dentro.
    """
    # Entrada superior
    ax.plot([0, 0], [0.88, 0.35], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    # Bucle del nudo simple
    t_buc = np.linspace(0, 2 * np.pi, 150)
    r_b = 0.26
    ax.plot(r_b * np.cos(t_buc) * 1.2,
            0.05 + r_b * np.sin(t_buc),
            color=color, lw=7, solid_capstyle='round', zorder=4)

    # Ramal que sale hacia abajo pasando por el bucle
    ax.plot([0.04, 0.00], [0.30, -0.22], color=color, lw=6,
            solid_capstyle='round', zorder=5)

    # Salida inferior
    ax.plot([0, 0], [-0.22, -0.70], color=color, lw=7,
            solid_capstyle='round', zorder=3)

    ax.text(0, -0.90, 'Solo como tope de emergencia', ha='center',
            fontsize=8, color=COLORS['danger'], alpha=0.80, style='italic')


# Mapa de funciones de dibujo (en el mismo orden que KNOTS)
_DRAW_FN = [
    _dibujar_sin_nudo,
    _dibujar_nudo_ocho,
    _dibujar_as_de_guia,
    _dibujar_pescador_doble,
    _dibujar_mariposa_alpina,
    _dibujar_nudo_simple,
]


def dibujar_diagrama(ax, knot_idx, mbs_kN):
    """Dibuja el diagrama del nudo seleccionado con sus anotaciones."""
    ax.clear()
    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.15, 1.10)
    ax.set_aspect('equal')
    ax.axis('off')

    nombre, efic, color, desc = KNOTS[knot_idx]
    mbs_nudo = mbs_kN * efic / 100.0

    # Fondo del panel
    rect_bg = mpatches.FancyBboxPatch(
        (-0.98, -1.13), 1.96, 2.22,
        boxstyle='round,pad=0.02',
        facecolor=COLORS['panel'], edgecolor=color,
        linewidth=2, alpha=0.40, zorder=0)
    ax.add_patch(rect_bg)

    # Punto de anclaje arriba (diamante)
    ax.plot([0], [0.90], 'D', color=COLORS['anchor'], ms=13, zorder=7)
    ax.plot([0], [0.90], 'D', color=COLORS['text'],   ms=7,  zorder=8)

    # Dibuja la forma específica del nudo
    _DRAW_FN[knot_idx](ax, color)

    # Flecha de carga hacia abajo
    ax.annotate(
        '', xy=(0, -0.95), xytext=(0, -0.73),
        arrowprops=dict(
            arrowstyle='->', color=COLORS['danger'],
            lw=3.0, mutation_scale=22))

    # Etiqueta de carga
    ax.text(0.22, -0.87, f'Carga\n{mbs_nudo:.1f} kN',
            ha='left', va='center', fontsize=8,
            color=COLORS['danger'], fontweight='bold')

    # Nombre del nudo (grande, en la parte superior)
    ax.set_title(nombre, fontsize=13, fontweight='bold',
                 color=color, pad=6)

    # Eficiencia destacada
    efic_color = (COLORS['accent']  if efic >= EFFICIENCY_MIN else
                  COLORS['warning'] if efic >= 60             else
                  COLORS['danger'])
    ax.text(0, -1.05, f'{efic}%  ({mbs_nudo:.1f} kN)',
            ha='center', va='center', fontsize=11,
            fontweight='bold', color=efic_color,
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=COLORS['bg'],
                      edgecolor=efic_color, alpha=0.90))

    # Descripción breve
    ax.text(0, -1.13, desc, ha='center', va='bottom',
            fontsize=7.5, color=COLORS['text'], alpha=0.65,
            style='italic', wrap=True)


def dibujar_barras(ax, knot_idx, mbs_kN):
    """Barras horizontales de eficiencia para los 6 nudos."""
    ax.clear()

    # Zonas de color de fondo
    ax.axvspan(0,               EFFICIENCY_MIN, facecolor=COLORS['danger'],  alpha=0.06)
    ax.axvspan(EFFICIENCY_MIN,  75,              facecolor=COLORS['warning'], alpha=0.06)
    ax.axvspan(75,              100,             facecolor=COLORS['accent'],  alpha=0.06)

    # Línea de mínimo recomendado
    ax.axvline(EFFICIENCY_MIN, color=COLORS['warning'],
               lw=1.8, ls='--', alpha=0.85, zorder=3)
    ax.text(EFFICIENCY_MIN + 0.8, 5.65,
            f'Mínimo\nrecomendado\n{EFFICIENCY_MIN}%',
            fontsize=8, color=COLORS['warning'],
            va='top', ha='left', alpha=0.90,
            bbox=dict(boxstyle='round,pad=0.2',
                      facecolor=COLORS['bg'],
                      edgecolor=COLORS['warning'], alpha=0.80))

    n = len(KNOTS)
    y_positions = np.arange(n)

    for i, (nombre, efic, color, _) in enumerate(KNOTS):
        mbs_con_nudo = mbs_kN * efic / 100.0
        selected = (i == knot_idx)

        # Borde más grueso si está seleccionado
        lw_borde = 3.5 if selected else 0.8
        alpha_b  = 1.0 if selected else 0.65

        ax.barh(y_positions[i], efic, color=color, alpha=alpha_b,
                height=0.62, edgecolor=color, linewidth=lw_borde,
                zorder=2)

        # Etiqueta al final de la barra
        ax.text(efic + 0.8, y_positions[i],
                f'{efic}%  =  {mbs_con_nudo:.1f} kN',
                va='center', ha='left', fontsize=9,
                color=color if selected else COLORS['text'],
                fontweight='bold' if selected else 'normal',
                alpha=1.0 if selected else 0.75)

        # Nombre del nudo a la izquierda (dentro de la barra si cabe)
        ax.text(-0.8, y_positions[i], nombre,
                va='center', ha='right', fontsize=9,
                color=COLORS['text'],
                fontweight='bold' if selected else 'normal',
                alpha=1.0 if selected else 0.75)

    ax.set_xlim(-1, 115)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_xlabel('Eficiencia del nudo (% del MBS)', fontsize=10,
                  color=COLORS['text'])
    ax.set_title('Eficiencia de los nudos', fontsize=12,
                 fontweight='bold', color=COLORS['primary'], pad=8)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, EFFICIENCY_MIN, 100])
    ax.set_xticklabels(['0%', '25%', '50%', f'{EFFICIENCY_MIN}%', '100%'],
                       fontsize=9)
    ax.grid(True, axis='x', alpha=0.15)
    ax.invert_yaxis()
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


def dibujar_fuerza(ax, knot_idx, mbs_kN):
    """Dos barras verticales: MBS total vs MBS con el nudo."""
    ax.clear()

    nombre, efic, color, _ = KNOTS[knot_idx]
    mbs_nudo = mbs_kN * efic / 100.0
    perdida  = mbs_kN - mbs_nudo

    # Barra gris: MBS total de la cuerda
    ax.bar(0, mbs_kN, width=0.55, color=COLORS['anchor'],
           alpha=0.80, edgecolor=COLORS['text'], linewidth=1.2,
           label=f'MBS cuerda: {mbs_kN:.1f} kN')

    # Barra coloreada: MBS con el nudo
    ax.bar(1, mbs_nudo, width=0.55, color=color,
           alpha=0.90, edgecolor=color, linewidth=1.8,
           label=f'MBS con nudo: {mbs_nudo:.1f} kN')

    # Línea NFPA
    ax.axhline(NFPA_WORK_LOAD, color=COLORS['danger'],
               ls='--', lw=1.8, alpha=0.80, zorder=4)
    ax.text(1.32, NFPA_WORK_LOAD + 0.4,
            f'NFPA\n{NFPA_WORK_LOAD} kN',
            fontsize=8, color=COLORS['danger'],
            ha='left', va='bottom', fontweight='bold')

    # Etiqueta de pérdida (entre las dos barras, en rojo)
    if perdida > 0:
        ax.annotate(
            '',
            xy=(1, mbs_nudo + 0.3),
            xytext=(1, mbs_kN - 0.3),
            arrowprops=dict(arrowstyle='<->', color=COLORS['danger'],
                            lw=2.0, mutation_scale=14))
        ax.text(1.32, (mbs_kN + mbs_nudo) / 2,
                f'Pérdida:\n{perdida:.1f} kN',
                fontsize=8.5, color=COLORS['danger'],
                fontweight='bold', ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.25',
                          facecolor=COLORS['bg'],
                          edgecolor=COLORS['danger'], alpha=0.88))

    # Valores encima de cada barra
    ax.text(0, mbs_kN + 0.5, f'{mbs_kN:.1f} kN',
            ha='center', fontsize=9, fontweight='bold',
            color=COLORS['anchor'])
    ax.text(1, mbs_nudo + 0.5, f'{mbs_nudo:.1f} kN',
            ha='center', fontsize=9, fontweight='bold', color=color)

    ax.set_xlim(-0.55, 2.0)
    ax.set_ylim(0, mbs_kN * 1.28)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['MBS\ncuerda', f'Con\n{nombre}'],
                       fontsize=8.5)
    ax.set_ylabel('Carga de rotura (kN)', fontsize=9)
    ax.set_title('MBS real\nvs nudo', fontsize=11,
                 fontweight='bold', color=COLORS['primary'], pad=6)
    ax.grid(True, axis='y', alpha=0.15)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)

    # Texto explicativo debajo
    ax.text(0.5, -mbs_kN * 0.12,
            f'Con este nudo la cuerda\nrompe a {mbs_nudo:.1f} kN\nen lugar de {mbs_kN:.1f} kN',
            ha='center', fontsize=8, color=COLORS['text'],
            alpha=0.75, style='italic',
            transform=ax.transData)


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(18, 10))

    # ── Título ────────────────────────────────────────────────────────
    fig.suptitle(
        'FÍSICA DEL RESCATE — Nudos y Resistencia de la Cuerda',
        fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.97)
    fig.text(
        0.5, 0.925,
        'Un nudo siempre crea un punto débil — ¿cuánto se pierde?',
        ha='center', fontsize=12, color=COLORS['warning'],
        style='italic')

    # ── Ejes ──────────────────────────────────────────────────────────
    ax_diagram = fig.add_axes([0.02, 0.22, 0.30, 0.68])
    ax_bar     = fig.add_axes([0.36, 0.22, 0.35, 0.68])
    ax_force   = fig.add_axes([0.75, 0.22, 0.23, 0.68])

    # ── Slider MBS ────────────────────────────────────────────────────
    ax_sl_mbs = fig.add_axes([0.15, 0.13, 0.75, 0.025])
    sl_mbs = Slider(
        ax_sl_mbs, 'MBS cuerda (kN)',
        5, 40, valinit=ROPE_STATIC_MBS,
        color=COLORS['rope'], valstep=0.5)
    sl_mbs.label.set_color(COLORS['rope'])
    sl_mbs.valtext.set_color(COLORS['rope'])

    # ── RadioButtons ──────────────────────────────────────────────────
    ax_radio = fig.add_axes([0.02, 0.03, 0.10, 0.10])
    ax_radio.set_facecolor(COLORS['panel'])
    radio = RadioButtons(
        ax_radio,
        [k[0] for k in KNOTS],
        active=0,
        activecolor=COLORS['primary'])

    # Colores individuales para las etiquetas del radio
    for lbl, (_, _, color, _) in zip(radio.labels, KNOTS):
        lbl.set_color(color)
        lbl.set_fontsize(8.5)

    # Estado mutable compartido entre callbacks
    state = {'knot_idx': 0}

    def update(_=None):
        knot_idx = state['knot_idx']
        mbs_kN   = float(sl_mbs.val)

        dibujar_diagrama(ax_diagram, knot_idx, mbs_kN)
        dibujar_barras(ax_bar, knot_idx, mbs_kN)
        dibujar_fuerza(ax_force, knot_idx, mbs_kN)

        fig.canvas.draw_idle()

    def on_radio(label):
        # Busca el índice por nombre
        for i, (nombre, _, _, _) in enumerate(KNOTS):
            if nombre == label:
                state['knot_idx'] = i
                break
        update()

    sl_mbs.on_changed(update)
    radio.on_clicked(on_radio)

    # ── Texto fijo inferior ───────────────────────────────────────────
    fig.text(
        0.5, 0.01,
        'Eficiencia ≥ 75%: uso en rescate  │  '
        'Nudo en ocho: estándar NFPA/UIAA  │  '
        'Nunca usar nudo simple como anclaje principal  │  '
        'MBS = Resistencia Mínima de Rotura (Minimum Breaking Strength)',
        ha='center', fontsize=8.5, color=COLORS['text'],
        alpha=0.55, style='italic')

    # ── Leyenda de zonas de color ──────────────────────────────────────
    fig.text(
        0.14, 0.055,
        'Zonas de eficiencia:',
        fontsize=9, color=COLORS['text'], fontweight='bold')
    fig.text(
        0.14, 0.040,
        '  ≥75%: aceptable en rescate',
        fontsize=9, color=COLORS['accent'])
    fig.text(
        0.14, 0.027,
        '  60–75%: con precaución',
        fontsize=9, color=COLORS['warning'])
    fig.text(
        0.14, 0.014,
        '  <60%: evitar en rescate',
        fontsize=9, color=COLORS['danger'])

    # Primer renderizado
    update()
    plt.show()


if __name__ == '__main__':
    main()
