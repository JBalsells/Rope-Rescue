"""
╔══════════════════════════════════════════════════════════════════════╗
║      FÍSICA DEL RESCATE · Módulo 19: Factor de Seguridad (FS)        ║
╠══════════════════════════════════════════════════════════════════════╣
║  ¿Por qué usamos FS = 10:1 cuando hay vidas en juego?                ║
║                                                                      ║
║  FS = Resistencia del sistema / Carga real aplicada                  ║
║                                                                      ║
║  FS = 10:1  → rescate con vida humana (NFPA 1983)                   ║
║  FS =  5:1  → equipos técnicos                                       ║
║  FS =  3:1  → cargas no vitales                                      ║
║                                                                      ║
║  Razón clave: las cargas dinámicas pueden multiplicar la             ║
║  fuerza estática por un factor de 5-10×. El FS absorbe esa          ║
║  incertidumbre y garantiza el margen de supervivencia.               ║
║                                                                      ║
║  Ejecutar:  python 19_factor_de_seguridad.py                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
from matplotlib.patches import FancyBboxPatch
from config import COLORS, G, ROPE_STATIC_MBS, NFPA_WORK_LOAD, apply_mpl_style


# ── Constantes del módulo ─────────────────────────────────────────────

# Modos de operación: etiqueta → factor de seguridad requerido
MODOS = {
    'Rescate (vida)': 10,
    'Técnico':         5,
    'Equipo':          3,
}

# Comparativas de FS para distintos sectores (etiqueta, FS, color)
FS_COMPARATIVA = [
    ('Rescate vida (NFPA)',      10, COLORS['accent']),
    ('Alpinismo / escalada',      5, COLORS['info']),
    ('Construcción (andamios)',    4, COLORS['secondary']),
    ('Equipo rescate (no vida)',   3, COLORS['warning']),
    ('Puentes (estructuras)',      2, COLORS['anchor']),
]

# Equipo disponible: (nombre, resistencia_kN, eficiencia_nudo)
EQUIPOS = [
    ('Cuerda estática 11mm',    ROPE_STATIC_MBS,        1.00),
    ('Mosquetón HMS certificado', 23.0,                 1.00),
    ('Anclaje perno expansivo',  20.0,                  1.00),
    ('Nudo en ocho',             ROPE_STATIC_MBS * 0.80, 1.00),
]


# ── Helpers de dibujo ─────────────────────────────────────────────────

def _panel_fondo(ax):
    """Aplica fondo de panel y quita ejes estándar."""
    ax.set_facecolor(COLORS['panel'])
    for sp in ax.spines.values():
        sp.set_edgecolor(COLORS['grid'])
        sp.set_linewidth(1.2)


def _dibujar_termometro(ax, m, fs_modo, modo_label):
    """
    Panel ax_main — 'El termómetro de seguridad'.
    Barra vertical que muestra carga real, margen requerido y MBS.
    """
    ax.clear()
    _panel_fondo(ax)
    ax.axis('off')

    F_real_kN = m * G / 1000.0          # carga real en kN
    F_min_kN  = F_real_kN * fs_modo     # mínimo requerido por el FS
    MBS       = ROPE_STATIC_MBS          # 30 kN

    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, MBS + 5)

    # ── Eje de la barra ───────────────────────────────────────────────
    BAR_X, BAR_W = 4.2, 1.8
    BAR_MAX = MBS + 2.0   # máximo visual

    # Zona roja: 0 → F_real
    h_real = min(F_real_kN, BAR_MAX)
    ax.add_patch(FancyBboxPatch(
        (BAR_X, 0), BAR_W, max(h_real, 0.05),
        boxstyle='square,pad=0', facecolor=COLORS['danger'],
        edgecolor='none', alpha=0.85, zorder=2))

    # Zona naranja: F_real → F_min (margen necesario)
    if F_min_kN > F_real_kN:
        h_margin = min(F_min_kN, BAR_MAX) - h_real
        ax.add_patch(FancyBboxPatch(
            (BAR_X, h_real), BAR_W, max(h_margin, 0),
            boxstyle='square,pad=0', facecolor=COLORS['warning'],
            edgecolor='none', alpha=0.80, zorder=2))

    # Zona verde: F_min → MBS (capacidad disponible)
    verde_inicio = min(max(F_min_kN, F_real_kN), BAR_MAX)
    verde_fin    = BAR_MAX
    if verde_fin > verde_inicio:
        ax.add_patch(FancyBboxPatch(
            (BAR_X, verde_inicio), BAR_W, verde_fin - verde_inicio,
            boxstyle='square,pad=0', facecolor=COLORS['accent'],
            edgecolor='none', alpha=0.70, zorder=2))

    # Contorno de la barra
    ax.add_patch(FancyBboxPatch(
        (BAR_X, 0), BAR_W, BAR_MAX,
        boxstyle='square,pad=0', facecolor='none',
        edgecolor=COLORS['text'], linewidth=1.5, alpha=0.35, zorder=3))

    # ── Marcas horizontales con etiquetas ─────────────────────────────
    def _marca(y, label, color, lw=2.0):
        y_c = min(y, BAR_MAX)
        ax.plot([BAR_X - 0.4, BAR_X + BAR_W + 0.4], [y_c, y_c],
                color=color, lw=lw, zorder=4, linestyle='--', alpha=0.9)
        ax.text(BAR_X + BAR_W + 0.65, y_c, label,
                va='center', fontsize=9, color=color, fontweight='bold')

    _marca(F_real_kN, f'Carga real: {F_real_kN:.2f} kN', COLORS['danger'])
    _marca(F_min_kN,  f'Mínimo requerido\n(FS {fs_modo}:1): {F_min_kN:.2f} kN',
           COLORS['warning'])
    _marca(MBS, f'MBS cuerda: {MBS:.0f} kN', COLORS['accent'])

    # ── Escala numérica en el lateral izquierdo ───────────────────────
    for tick_val in np.arange(0, BAR_MAX + 1, 5):
        ax.plot([BAR_X - 0.2, BAR_X], [tick_val, tick_val],
                color=COLORS['text'], lw=0.8, alpha=0.3)
        ax.text(BAR_X - 0.4, tick_val, f'{tick_val:.0f}',
                ha='right', va='center', fontsize=7.5,
                color=COLORS['text'], alpha=0.5)
    ax.text(BAR_X - 0.9, BAR_MAX / 2, 'kN', rotation=90,
            ha='center', va='center', fontsize=9,
            color=COLORS['text'], alpha=0.45)

    # ── Advertencia si el sistema es insuficiente ─────────────────────
    if F_min_kN > MBS:
        ax.text(5, MBS + 3.8,
                'SISTEMA INSUFICIENTE\n'
                f'Necesitas {F_min_kN:.1f} kN pero el MBS es {MBS:.0f} kN',
                ha='center', va='center', fontsize=10, fontweight='bold',
                color=COLORS['danger'],
                bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['bg'],
                          edgecolor=COLORS['danger'], lw=2.0, alpha=0.95),
                zorder=6)
    else:
        # Texto del margen disponible
        margen = MBS - F_min_kN
        ax.text(5, MBS + 3.5,
                f'Margen disponible: {margen:.1f} kN',
                ha='center', va='center', fontsize=9,
                color=COLORS['accent'], alpha=0.8)

    # ── Leyenda de colores ────────────────────────────────────────────
    leyenda = [
        (COLORS['danger'],  'Carga real (m×g)'),
        (COLORS['warning'], f'Margen de seguridad (FS={fs_modo})'),
        (COLORS['accent'],  'Capacidad sobrante'),
    ]
    for i, (clr, lbl) in enumerate(leyenda):
        y_ley = 1.5 + i * 1.35
        ax.add_patch(FancyBboxPatch(
            (0.3, y_ley - 0.35), 0.7, 0.70,
            boxstyle='round,pad=0.05', facecolor=clr,
            edgecolor='none', alpha=0.80))
        ax.text(1.2, y_ley + 0.0, lbl, va='center',
                fontsize=8.5, color=COLORS['text'])

    # ── Fórmula ───────────────────────────────────────────────────────
    ax.text(5, -0.9,
            f'FS = {MBS:.0f} kN ÷ {F_real_kN:.2f} kN = {MBS/F_real_kN:.1f}   '
            f'(necesario: {fs_modo}:1)',
            ha='center', va='center', fontsize=8.5,
            color=COLORS['text'], alpha=0.70,
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                      edgecolor=COLORS['grid'], alpha=0.8))

    ax.set_title('¿Cuánto debe aguantar el sistema?',
                 fontsize=11, fontweight='bold',
                 color=COLORS['primary'], pad=8)


def _dibujar_comparativa(ax, modo_label):
    """
    Panel ax_compare — Comparación de FS para distintos contextos.
    Barras horizontales con el modo activo destacado.
    """
    ax.clear()
    _panel_fondo(ax)

    nombres = [e[0] for e in FS_COMPARATIVA]
    valores  = [e[1] for e in FS_COMPARATIVA]
    colores  = [e[2] for e in FS_COMPARATIVA]

    # Mapear el modo actual al nombre completo de la comparativa
    _mapa_modo = {
        'Rescate (vida)': 'Rescate vida (NFPA)',
        'Técnico':        'Alpinismo / escalada',
        'Equipo':         'Equipo rescate (no vida)',
    }
    nombre_destacado = _mapa_modo.get(modo_label, '')

    bars = ax.barh(nombres, valores, color=colores, height=0.55,
                   edgecolor='none', alpha=0.75)

    # Resaltar la barra del modo activo
    for bar, nombre in zip(bars, nombres):
        if nombre == nombre_destacado:
            bar.set_edgecolor('white')
            bar.set_linewidth(2.5)
            bar.set_alpha(1.0)

    # Etiquetas de valor
    for bar, val in zip(bars, valores):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                f'{val}:1', va='center', fontsize=10,
                fontweight='bold', color=COLORS['text'])

    # Línea vertical en FS=10 como referencia de rescate
    ax.axvline(10, color=COLORS['danger'], ls='--', lw=1.5, alpha=0.6)
    ax.text(10.1, len(nombres) - 0.1, 'NFPA\n10:1',
            fontsize=7.5, color=COLORS['danger'], alpha=0.75, va='top')

    ax.set_xlim(0, 13)
    ax.set_xlabel('Factor de Seguridad', fontsize=10, color=COLORS['text'])
    ax.set_title('FS por sector de actividad\n'
                 '¿Por qué tan alto en rescate?',
                 fontsize=10, fontweight='bold', color=COLORS['warning'], pad=8)
    ax.tick_params(axis='y', labelsize=8.5)
    ax.grid(axis='x', alpha=0.15)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)

    # Nota explicativa
    ax.text(0.5, -0.12,
            'Las cargas dinámicas multiplican la fuerza real hasta 10×',
            transform=ax.transAxes, ha='center', fontsize=8,
            color=COLORS['text'], alpha=0.55, style='italic')


def _dibujar_equipos(ax, m, fs_modo):
    """
    Panel ax_system — Equipo disponible vs requisito mínimo del FS.
    Barras verticales; rojo si no cumple, verde si cumple.
    """
    ax.clear()
    _panel_fondo(ax)

    F_real_kN = m * G / 1000.0
    F_min_kN  = F_real_kN * fs_modo      # umbral que debe superar cada equipo

    nombres   = [e[0] for e in EQUIPOS]
    resist    = [e[1] for e in EQUIPOS]   # resistencia en kN
    x         = np.arange(len(EQUIPOS))

    # Asignar color según cumplimiento
    colores = []
    for r in resist:
        if r >= F_min_kN:
            colores.append(COLORS['accent'])
        else:
            colores.append(COLORS['danger'])

    bars = ax.bar(x, resist, color=colores, width=0.55,
                  edgecolor='white', linewidth=0.8, alpha=0.88)

    # Etiqueta de valor y cumplimiento sobre cada barra
    for bar, r, c in zip(bars, resist, colores):
        top = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, top + 0.4,
                f'{r:.1f} kN', ha='center', va='bottom',
                fontsize=8.5, fontweight='bold', color=c)
        estado = 'OK' if r >= F_min_kN else 'NO CUMPLE'
        ax.text(bar.get_x() + bar.get_width() / 2, top / 2,
                estado, ha='center', va='center',
                fontsize=9, fontweight='bold',
                color='white', alpha=0.9)

    # Línea roja del requisito mínimo
    ax.axhline(F_min_kN, color=COLORS['danger'], lw=2.0,
               ls='--', zorder=5)
    ax.text(len(EQUIPOS) - 0.5, F_min_kN + 0.5,
            f'Mínimo requerido\n(FS {fs_modo}:1): {F_min_kN:.2f} kN',
            ha='right', va='bottom', fontsize=8,
            color=COLORS['danger'], fontweight='bold')

    # Línea de MBS de referencia
    ax.axhline(ROPE_STATIC_MBS, color=COLORS['accent'], lw=1.2,
               ls=':', alpha=0.6, zorder=4)
    ax.text(0, ROPE_STATIC_MBS + 0.3, f'MBS ref: {ROPE_STATIC_MBS:.0f} kN',
            fontsize=7.5, color=COLORS['accent'], alpha=0.65)

    ax.set_xticks(x)
    ax.set_xticklabels(nombres, fontsize=8, wrap=True)
    ax.set_ylabel('Resistencia (kN)', fontsize=9)
    ax.set_ylim(0, ROPE_STATIC_MBS + 5)
    ax.set_title('¿Qué equipo cumple el FS requerido?',
                 fontsize=10, fontweight='bold',
                 color=COLORS['primary'], pad=8)
    ax.grid(axis='y', alpha=0.15)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)

    # Etiquetas largas del eje X con salto de línea manual
    etiq = [
        'Cuerda\nestática 11mm',
        'Mosquetón\nHMS',
        'Anclaje\nperno',
        'Nudo en\nocho (×0.8)',
    ]
    ax.set_xticklabels(etiq, fontsize=8)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle('FÍSICA DEL RESCATE — Factor de Seguridad (FS)',
                 fontsize=21, fontweight='bold',
                 color=COLORS['primary'], y=0.977)
    fig.text(0.5, 0.935,
             'FS = Resistencia del sistema / Carga real   '
             '→   Rescate con vida: FS = 10:1',
             fontsize=12, ha='center',
             color=COLORS['warning'], fontstyle='italic')

    # ── Ejes principales ──────────────────────────────────────────────
    ax_main    = fig.add_axes([0.02, 0.22, 0.34, 0.68])
    ax_compare = fig.add_axes([0.40, 0.22, 0.26, 0.68])
    ax_system  = fig.add_axes([0.70, 0.22, 0.28, 0.68])

    # ── Slider de masa ────────────────────────────────────────────────
    ax_sl_mass = fig.add_axes([0.15, 0.13, 0.75, 0.025])
    ax_sl_mass.set_facecolor(COLORS['panel'])
    sl_mass = Slider(ax_sl_mass, 'Masa (kg)', 1, 200,
                     valinit=80, valstep=1,
                     color=COLORS['primary'])
    sl_mass.valtext.set_fontsize(11)

    # ── RadioButtons: tipo de operación ──────────────────────────────
    ax_radio = fig.add_axes([0.02, 0.03, 0.12, 0.14])
    ax_radio.set_facecolor(COLORS['panel'])
    for sp in ax_radio.spines.values():
        sp.set_edgecolor(COLORS['grid'])
    radio = RadioButtons(ax_radio, list(MODOS.keys()),
                         activecolor=COLORS['primary'])
    for lbl in radio.labels:
        lbl.set_fontsize(9)
        lbl.set_color(COLORS['text'])

    # ── Update ────────────────────────────────────────────────────────
    def update(_=None):
        m          = float(sl_mass.val)
        modo_label = radio.value_selected
        fs_modo    = MODOS[modo_label]

        _dibujar_termometro(ax_main, m, fs_modo, modo_label)
        _dibujar_comparativa(ax_compare, modo_label)
        _dibujar_equipos(ax_system, m, fs_modo)

        fig.canvas.draw_idle()

    sl_mass.on_changed(update)
    radio.on_clicked(update)

    # ── Textos fijos ──────────────────────────────────────────────────
    fig.text(0.5, 0.012,
             'NFPA 1983: FS = 10:1 para sistemas que soportan vidas humanas  │  '
             'Las cargas dinámicas pueden ser 5–10× la carga estática  │  '
             'MBS cuerda estática 11mm = 30 kN',
             fontsize=9, ha='center',
             color=COLORS['text'], alpha=0.55, fontstyle='italic')

    # Etiqueta junto al radio button
    fig.text(0.08, 0.175, 'Tipo de operación:',
             fontsize=9, ha='center', color=COLORS['text'], alpha=0.7)

    update()
    plt.show()


if __name__ == '__main__':
    main()
