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
║  Ejecutar:  python 17b_nudos_y_resistencia.py                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from config import COLORS, ROPE_STATIC_MBS, NFPA_WORK_LOAD, apply_mpl_style


# ── Datos de nudos (nombre, eficiencia %, color hex, descripción) ──────
# Ordenados por eficiencia descendente
KNOTS = [
    ('Sin nudo',             100, '#4CAF50',
     'Referencia: resistencia total de la cuerda'),
    ('Nudo en ocho',          80, '#00BCD4',
     'El más usado en rescate. Fácil de verificar. Estándar NFPA/UIAA.'),
    ('Ocho en seno',          78, '#26C6DA',
     'Bucle en el seno de la cuerda. No corta la cuerda.'),
    ('Ocho doble (orejas)',   77, '#00ACC1',
     'Crea dos gazas simultáneas. Ideal para anclajes en Y.'),
    ('As de guía (Bowline)',   75, '#2196F3',
     'Anclaje rápido en extremo. No usar bajo carga dinámica sola.'),
    ('As de guía doble',      72, '#42A5F5',
     'Bowline con doble vuelta. Más seguro ante cargas variables.'),
    ('Nudo dinámico (HMS)',    70, '#E91E63',
     'Freno y rappel reversible. Requiere mosquetón de pera (HMS).'),
    ('Pescador doble',         70, '#9C27B0',
     'Unión de dos cuerdas. Muy seguro, compacto y fiable.'),
    ('Zeppelin (bend)',        68, '#7E57C2',
     'Unión segura. Notable: fácil de deshacer incluso bajo carga.'),
    ('Mariposa alpina',        68, '#FF9800',
     'Nudo de línea media. Cargable en tres direcciones.'),
    ('Pescador simple',        65, '#CE93D8',
     'Versión simple del pescador. Menos segura que el doble.'),
    ('Ballestrinque',          65, '#66BB6A',
     'Anclaje rápido en postes y mosquetones. Puede deslizar.'),
    ('Prusik',                 65, '#FF7043',
     'Nudo de fricción para ascenso y bloqueo. Libera bajo carga.'),
    ('Klemheist',              63, '#FFA726',
     'Fricción con cinta o cordino. Unidireccional.'),
    ('Bachmann',               62, '#78909C',
     'Fricción con mosquetón añadido. Permite ajuste manual.'),
    ('Garda (Ratchet)',        60, '#A1887F',
     'Trinquete de progreso. Solo carga en un sentido.'),
    ('Nudo simple',            60, '#F44336',
     'El más débil. Solo como tope de emergencia, nunca anclaje.'),
    ('Nudo de agua',           55, '#AB47BC',
     'Para unir cintas y slings. Revisar siempre antes de usar.'),
    ('Nudo plano',             45, '#B71C1C',
     'PELIGROSO: se desliza y vira bajo carga. NO usar en rescate.'),
]

# Umbral mínimo recomendado de eficiencia en rescate (NFPA / UIAA)
EFFICIENCY_MIN = 75


# ── Visualización ──────────────────────────────────────────────────────

def dibujar_barras(ax, mbs_kN):
    """
    Barras horizontales de eficiencia para todos los nudos.
    El eje X es eficiencia (%) / kN resultante.
    """
    ax.clear()
    n = len(KNOTS)

    # ── Zonas de color de fondo ──────────────────────────────────────
    ax.axvspan(0,              60,             facecolor=COLORS['danger'],  alpha=0.07)
    ax.axvspan(60,             EFFICIENCY_MIN, facecolor=COLORS['warning'], alpha=0.07)
    ax.axvspan(EFFICIENCY_MIN, 100,            facecolor=COLORS['accent'],  alpha=0.07)

    # ── Líneas de referencia verticales ──────────────────────────────
    ax.axvline(EFFICIENCY_MIN, color=COLORS['warning'], lw=1.8, ls='--', alpha=0.85, zorder=3)
    ax.axvline(60,             color=COLORS['danger'],  lw=1.2, ls=':',  alpha=0.70, zorder=3)

    # Línea NFPA como % del MBS actual (mínimo de carga de trabajo)
    nfpa_efic = (NFPA_WORK_LOAD / mbs_kN) * 100.0
    if 0 < nfpa_efic < 100:
        ax.axvline(nfpa_efic, color='#FF6F00', lw=1.6, ls='-.', alpha=0.65, zorder=3)
        ax.text(nfpa_efic + 0.5, 0.97,
                f'NFPA {NFPA_WORK_LOAD:.1f} kN',
                fontsize=8, color='#FF6F00', va='top', ha='left',
                transform=ax.get_xaxis_transform())

    # ── Etiquetas de zona (en la parte superior del gráfico) ─────────
    ax.text(30,               0.995, 'Evitar en rescate',
            fontsize=8, color=COLORS['danger'],  va='top', ha='center',
            transform=ax.get_xaxis_transform(), style='italic')
    ax.text(67.5,             0.995, 'Con precaución',
            fontsize=8, color=COLORS['warning'], va='top', ha='center',
            transform=ax.get_xaxis_transform(), style='italic')
    ax.text(87.5,             0.995, 'Aceptable en rescate',
            fontsize=8, color=COLORS['accent'],  va='top', ha='center',
            transform=ax.get_xaxis_transform(), style='italic')

    # ── Barras y etiquetas ───────────────────────────────────────────
    y_positions = np.arange(n)

    for i, (nombre, efic, _hex, desc) in enumerate(KNOTS):
        mbs_con_nudo = mbs_kN * efic / 100.0

        # Color por eficiencia: semáforo verde/ámbar/rojo del tema terminal
        if efic >= EFFICIENCY_MIN:
            color, alpha_b, lw_brd, ec = COLORS['accent'], 0.90, 0.8, COLORS['accent']
        elif efic >= 60:
            color, alpha_b, lw_brd, ec = COLORS['warning'], 0.85, 0.8, COLORS['warning']
        else:
            color, alpha_b, lw_brd, ec = COLORS['danger'], 0.80, 2.2, COLORS['danger']

        ax.barh(y_positions[i], efic,
                color=color, alpha=alpha_b, height=0.65,
                edgecolor=ec, linewidth=lw_brd, zorder=2)

        # Valor kN al final de la barra
        ax.text(efic + 0.7, y_positions[i],
                f'{efic}%  →  {mbs_con_nudo:.1f} kN',
                va='center', ha='left', fontsize=9.0,
                color=color, fontweight='bold')

        # Descripción breve dentro de la barra (si hay espacio)
        if efic >= 30:
            ax.text(efic * 0.5, y_positions[i], desc,
                    va='center', ha='center', fontsize=6.5,
                    color='white', alpha=0.75, zorder=5,
                    clip_on=True)

        # Marcador "NO RESCATE" para nudos muy peligrosos
        if efic < 50:
            ax.text(efic * 0.25, y_positions[i], '⚠ NO RESCATE',
                    va='center', ha='center', fontsize=7.5,
                    color='white', fontweight='bold', alpha=0.95, zorder=6)

    # ── Etiquetas del eje Y (nombres de nudos) ───────────────────────
    ax.set_yticks(y_positions)
    ax.set_yticklabels([k[0] for k in KNOTS], fontsize=9.5)
    for tick, (_, efic, color, _) in zip(ax.get_yticklabels(), KNOTS):
        tick.set_color(COLORS['danger'] if efic < 60 else COLORS['text'])
        tick.set_fontweight('bold' if efic < 60 else 'normal')
    ax.tick_params(axis='y', length=0, pad=6)

    # ── Configuración de ejes ────────────────────────────────────────
    ax.set_xlim(-1, 115)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_xlabel('Resistencia que le queda a la cuerda con el nudo (%)',
                  fontsize=11, color=COLORS['text'])
    ax.set_xticks([0, 25, 50, 60, EFFICIENCY_MIN, 100])
    ax.set_xticklabels(['0%', '25%', '50%', '60%', f'{EFFICIENCY_MIN}%', '100%'],
                       fontsize=9.5)
    ax.grid(True, axis='x', alpha=0.15)
    ax.invert_yaxis()
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)


# ── Interfaz principal ─────────────────────────────────────────────────

from registry import simulation


@simulation(backend='mpl', order=4,
            title='Nudos y resistencia de la cuerda',
            description='Eficiencia de cada nudo sobre el MBS.')
def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(17, 11))

    fig.suptitle(
        'Nudos: cuánta resistencia le quitan a la cuerda',
        fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.975)
    fig.text(
        0.5, 0.935,
        'Todo nudo debilita la cuerda. Verde = aguanta bien; rojo = aguanta poco.',
        ha='center', fontsize=12, color=COLORS['warning'], style='italic')

    # ── Eje principal (gráfico de barras) ─────────────────────────────
    ax_bar = fig.add_axes([0.19, 0.20, 0.78, 0.70])

    # ── Slider MBS ────────────────────────────────────────────────────
    ax_sl = fig.add_axes([0.22, 0.05, 0.155, 0.026])
    sl_mbs = Slider(
        ax_sl, 'Resistencia (kN)',
        5, 40, valinit=ROPE_STATIC_MBS,
        color=COLORS['rope'], valstep=0.5)
    sl_mbs.label.set_color(COLORS['rope'])
    sl_mbs.label.set_size(9.5)

    def update(_=None):
        dibujar_barras(ax_bar, float(sl_mbs.val))
        fig.canvas.draw_idle()

    from controls import attach_editable_numbers
    attach_editable_numbers(fig, [
        (sl_mbs, 5, 40, lambda v: f'{v:.1f}'),
    ], redraw=update, frame=(0.06, 0.02, 0.40, 0.115))

    # ── Leyenda de zonas ──────────────────────────────────────────────
    fig.text(0.74, 0.060, 'Colores:',
             fontsize=9, color=COLORS['text'], fontweight='bold')
    fig.text(0.74, 0.046, '  verde  ≥75 %: aceptable en rescate',
             fontsize=9, color=COLORS['accent'])
    fig.text(0.74, 0.033, '  ámbar  60–75 %: usar con precaución',
             fontsize=9, color=COLORS['warning'])
    fig.text(0.74, 0.020, '  rojo   <60 %: evitar en rescate',
             fontsize=9, color=COLORS['danger'])

    fig.text(
        0.5, 0.005,
        'Nudo en ocho: el más usado en rescate  │  '
        'Prusik / Klemheist / Bachmann: nudos de fricción  │  '
        'Nudo plano: PELIGROSO, nunca como anclaje',
        ha='center', fontsize=8, color=COLORS['text'],
        alpha=0.55, style='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
