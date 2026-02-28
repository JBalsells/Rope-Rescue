"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 20: Carga Estática vs Dinámica         ║
╠══════════════════════════════════════════════════════════════════════╣
║  La MISMA masa genera fuerzas MUY DISTINTAS según cómo se aplica    ║
║  la carga. Tres escenarios comparados en tiempo real.                ║
║                                                                      ║
║  Escenario 1 — Estática:       F = m×g           (×1.0)             ║
║  Escenario 2 — Cuasi-estática: F ≈ m×(g + v/t)  (×1.5 aprox.)      ║
║  Escenario 3 — Dinámica:       F = m×(g + v²/2d) (×5–50)           ║
║                                                                      ║
║  Cuerda estática: elongación ≈ 1.5% → distancia de parada muy corta ║
║  → fuerza de impacto muy alta. Las cuerdas dinámicas absorben        ║
║  energía estirando más (elongación ≈ 30–40%).                        ║
║                                                                      ║
║  Ejecutar:  python 20_carga_estatica_vs_dinamica.py                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from config import (COLORS, G, ROPE_STATIC_MBS,
                    ROPE_DYNAMIC_MBS, NFPA_WORK_LOAD, apply_mpl_style)


# ── Constantes del módulo ─────────────────────────────────────────────

L_CUERDA   = 10.0   # longitud de cuerda de referencia (m)
ELONG_EST  = 0.015  # elongación cuerda estática al MBS (1.5 %)
T_STOP_S2  = 0.30   # tiempo de parada en escenario 2 (s)
H_S2_CAIDA = 0.10   # altura de caída escenario 2 (m)


# ── Funciones de cálculo ──────────────────────────────────────────────

def calcular_escenario1(m):
    """
    Escenario 1 — Carga estática.
    F = m × g. Multiplicador = 1.0 siempre.
    """
    F_N   = m * G
    F_kN  = F_N / 1000.0
    mult  = 1.0
    return F_N, F_kN, mult


def calcular_escenario2(m):
    """
    Escenario 2 — Carga cuasi-estática.
    Caída de H_S2_CAIDA metros, detenida en T_STOP_S2 segundos.
    v = sqrt(2·g·H), a = v/t, F = m·(g + a).
    """
    v       = np.sqrt(2.0 * G * H_S2_CAIDA)
    a_brake = v / T_STOP_S2
    F_N     = m * (G + a_brake)
    F_kN    = F_N / 1000.0
    F_stat  = m * G
    mult    = F_N / F_stat if F_stat > 0 else 1.0
    return F_N, F_kN, mult, v, a_brake


def calcular_escenario3(m, h):
    """
    Escenario 3 — Carga dinámica.
    Caída de h metros, cuerda estática detiene en d_stop = ELONG_EST × L_CUERDA.
    v = sqrt(2·g·h), a = v²/(2·d_stop), F = m·(g + a).
    Maneja h=0 sin división por cero.
    """
    F_stat_N = m * G
    if h <= 0.0:
        return F_stat_N, F_stat_N / 1000.0, 1.0, 0.0, 0.0

    v      = np.sqrt(2.0 * G * h)
    d_stop = ELONG_EST * L_CUERDA          # distancia de parada ≈ 0.15 m
    a_brake = v ** 2 / (2.0 * d_stop)
    F_N    = m * (G + a_brake)
    F_kN   = F_N / 1000.0
    mult   = F_N / F_stat_N if F_stat_N > 0 else 1.0
    return F_N, F_kN, mult, v, a_brake


# ── Color de recuadro según multiplicador ─────────────────────────────

def _color_mult(mult):
    if mult < 1.5:
        return COLORS['accent']
    elif mult < 3.0:
        return COLORS['warning']
    elif mult < 7.0:
        return COLORS['secondary']
    else:
        return COLORS['danger']


# ── Dibujo de un panel de escenario ──────────────────────────────────

def _dibujar_escenario(ax, titulo, subtitulo, m,
                        F_N, F_kN, mult,
                        h_caida=0.0, mostrar_caida=False):
    """
    Dibuja el panel completo de un escenario:
      - Anclaje (triángulo arriba)
      - Cuerda vertical
      - Masa (caja)
      - Flecha de fuerza proporcional
      - Recuadro con F y multiplicador
      - Barra de % de MBS al fondo
      - Advertencia NFPA si aplica
    """
    ax.clear()
    ax.set_facecolor(COLORS['panel'])
    for sp in ax.spines.values():
        sp.set_edgecolor(COLORS['grid'])
        sp.set_linewidth(1.2)
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    # ── Título ────────────────────────────────────────────────────────
    color_mult = _color_mult(mult)
    ax.text(5, 9.65, titulo, ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['primary'])
    ax.text(5, 9.25, subtitulo, ha='center', va='center',
            fontsize=13, fontweight='bold', color=color_mult)

    # ── Anclaje (triángulo) en la parte superior ───────────────────────
    anc_x, anc_y = 5.0, 8.5
    tri_size = 0.4
    ax.plot([anc_x - tri_size, anc_x + tri_size, anc_x, anc_x - tri_size],
            [anc_y - tri_size * 1.2, anc_y - tri_size * 1.2,
             anc_y + tri_size * 0.8, anc_y - tri_size * 1.2],
            color=COLORS['anchor'], lw=2.5, solid_capstyle='round', zorder=4)
    ax.plot(anc_x, anc_y, 'o', color=COLORS['anchor'], ms=6, zorder=5)

    # ── Posición de la masa ────────────────────────────────────────────
    masa_top = 5.8
    masa_bot = masa_top - 1.0
    masa_cx  = 5.0

    # En escenario dinámico, dibujar posición de inicio de caída (punteada)
    if mostrar_caida and h_caida > 0:
        # Escalar la altura de caída al espacio visual disponible
        escala_h = min(h_caida / 10.0, 1.0) * 1.8   # máximo 1.8 unidades visuales
        pos_caida_top = masa_top + escala_h
        pos_caida_bot = masa_bot + escala_h

        # Masa fantasma en posición de inicio de caída
        ax.add_patch(FancyBboxPatch(
            (masa_cx - 0.65, pos_caida_bot), 1.3, 1.0,
            boxstyle='round,pad=0.05', facecolor=COLORS['warning'],
            edgecolor=COLORS['warning'], linewidth=1.0,
            alpha=0.25, zorder=2))
        ax.text(masa_cx, pos_caida_bot + 0.5,
                f'{m:.0f} kg', ha='center', va='center',
                fontsize=8, color=COLORS['warning'], alpha=0.5)

        # Línea punteada de trayectoria de caída
        y_tray = np.linspace(pos_caida_bot, masa_top, 20)
        ax.plot([masa_cx + 0.05] * len(y_tray), y_tray,
                color=COLORS['warning'], lw=1.2, ls='--', alpha=0.45, zorder=1)

        # Cota de altura de caída
        ax.annotate('', xy=(masa_cx - 1.2, masa_top),
                    xytext=(masa_cx - 1.2, pos_caida_top),
                    arrowprops=dict(arrowstyle='<->', color=COLORS['warning'],
                                    lw=1.5, alpha=0.75))
        ax.text(masa_cx - 1.8, (masa_top + pos_caida_top) / 2,
                f'h={h_caida:.1f}m',
                va='center', ha='center', fontsize=7.5,
                color=COLORS['warning'], alpha=0.85, rotation=90)

        # Cuerda desde anclaje hasta posición de caída (punteada)
        ax.plot([masa_cx, masa_cx], [anc_y - tri_size * 1.2, pos_caida_top],
                color=COLORS['rope'], lw=2.0, ls=':', alpha=0.3, zorder=2)

    # Cuerda desde anclaje hasta masa (sólida)
    ax.plot([masa_cx, masa_cx], [anc_y - tri_size * 1.2, masa_top],
            color=COLORS['rope'], lw=2.5, alpha=0.85, zorder=3)

    # Masa (caja coloreada)
    ax.add_patch(FancyBboxPatch(
        (masa_cx - 0.65, masa_bot), 1.3, 1.0,
        boxstyle='round,pad=0.05', facecolor=COLORS['info'],
        edgecolor='white', linewidth=2.0, alpha=0.90, zorder=4))
    ax.text(masa_cx, masa_bot + 0.5, f'{m:.0f} kg',
            ha='center', va='center', fontsize=10,
            fontweight='bold', color='white', zorder=5)

    # ── Flecha de fuerza proporcional ─────────────────────────────────
    # La flecha del escenario 1 es la referencia (longitud = 1.2 unidades).
    # Las demás escalan según el multiplicador, con cap para no salirse.
    F_ref_N  = 80.0 * G                  # 80 kg como referencia visual
    long_ref = 1.4                        # unidades visuales para F_ref
    escala   = F_N / F_ref_N
    long_flecha = min(long_ref * escala, 3.0)  # cap en 3 unidades

    flecha_inicio = masa_bot
    flecha_fin    = masa_bot - long_flecha

    ax.annotate('', xy=(masa_cx, max(flecha_fin, 0.3)),
                xytext=(masa_cx, flecha_inicio),
                arrowprops=dict(arrowstyle='->', color=color_mult,
                                lw=3.5, mutation_scale=22),
                zorder=6)

    # ── Recuadro de datos ─────────────────────────────────────────────
    recuadro_y = max(flecha_fin - 0.15, 0.1)
    texto_F = (f'F = {F_N:,.0f} N\n'
               f'  = {F_kN:.2f} kN\n'
               f'  × {mult:.1f} vs estática')
    ax.text(masa_cx, recuadro_y, texto_F,
            ha='center', va='top', fontsize=8.5, fontweight='bold',
            color=color_mult,
            bbox=dict(boxstyle='round,pad=0.35', facecolor=COLORS['bg'],
                      edgecolor=color_mult, lw=1.8, alpha=0.92),
            zorder=7)

    # Advertencia NFPA si supera la carga de trabajo
    if F_kN > NFPA_WORK_LOAD:
        ax.text(5, 0.5,
                f'¡Supera carga NFPA! ({NFPA_WORK_LOAD} kN)',
                ha='center', va='center', fontsize=8, fontweight='bold',
                color=COLORS['danger'],
                bbox=dict(boxstyle='round,pad=0.25', facecolor=COLORS['bg'],
                          edgecolor=COLORS['danger'], lw=1.5, alpha=0.90),
                zorder=8)

    # ── Barra de porcentaje del MBS ────────────────────────────────────
    # Pequeña barra horizontal al fondo del panel (y ≈ 0.18–0.30)
    pct = min(F_kN / ROPE_STATIC_MBS, 1.0)
    BAR_Y, BAR_H = 0.18, 0.22
    BAR_X0, BAR_LEN = 1.0, 8.0

    # Fondo gris de la barra
    ax.add_patch(FancyBboxPatch(
        (BAR_X0, BAR_Y), BAR_LEN, BAR_H,
        boxstyle='round,pad=0.02', facecolor=COLORS['grid'],
        edgecolor='none', alpha=0.6))

    # Relleno proporcional al porcentaje
    color_pct = (COLORS['accent']    if pct < 0.40 else
                 COLORS['warning']   if pct < 0.70 else
                 COLORS['secondary'] if pct < 1.00 else
                 COLORS['danger'])
    ax.add_patch(FancyBboxPatch(
        (BAR_X0, BAR_Y), max(pct * BAR_LEN, 0.05), BAR_H,
        boxstyle='round,pad=0.02', facecolor=color_pct,
        edgecolor='none', alpha=0.80))

    ax.text(BAR_X0 - 0.1, BAR_Y + BAR_H / 2,
            '0', ha='right', va='center',
            fontsize=7, color=COLORS['text'], alpha=0.5)
    ax.text(BAR_X0 + BAR_LEN + 0.1, BAR_Y + BAR_H / 2,
            f'MBS\n{ROPE_STATIC_MBS:.0f} kN',
            ha='left', va='center',
            fontsize=7, color=COLORS['text'], alpha=0.5)
    ax.text(5, BAR_Y + BAR_H / 2,
            f'{pct * 100:.1f}% del MBS',
            ha='center', va='center', fontsize=7.5,
            fontweight='bold', color='white', alpha=0.9)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(19, 11))
    fig.suptitle('FÍSICA DEL RESCATE — Carga Estática vs Dinámica',
                 fontsize=21, fontweight='bold',
                 color=COLORS['primary'], y=0.977)
    fig.text(0.5, 0.935,
             'La MISMA masa genera fuerzas MUY DISTINTAS según cómo se aplica la carga',
             fontsize=12, ha='center',
             color=COLORS['warning'], fontstyle='italic')

    # ── Ejes de los tres escenarios ───────────────────────────────────
    ax_s1 = fig.add_axes([0.02, 0.22, 0.28, 0.68])
    ax_s2 = fig.add_axes([0.36, 0.22, 0.28, 0.68])
    ax_s3 = fig.add_axes([0.70, 0.22, 0.28, 0.68])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_mass = fig.add_axes([0.15, 0.13, 0.75, 0.025])
    ax_sl_h    = fig.add_axes([0.15, 0.07, 0.75, 0.025])

    ax_sl_mass.set_facecolor(COLORS['panel'])
    ax_sl_h.set_facecolor(COLORS['panel'])

    sl_mass = Slider(ax_sl_mass, 'Masa (kg)',             1,   200, valinit=80,
                     valstep=1,   color=COLORS['primary'])
    sl_h    = Slider(ax_sl_h,    'Altura caída Esc. 3 (m)', 0.0, 10.0, valinit=3.0,
                     valstep=0.1, color=COLORS['danger'])

    sl_mass.valtext.set_fontsize(11)
    sl_h.valtext.set_fontsize(11)

    # ── Update ────────────────────────────────────────────────────────
    def update(_=None):
        m = float(sl_mass.val)
        h = float(sl_h.val)

        # ── Escenario 1: estático ──────────────────────────────────
        F1_N, F1_kN, mult1 = calcular_escenario1(m)
        _dibujar_escenario(
            ax_s1,
            'Escenario 1 — Estática',
            f'× {mult1:.1f}',
            m, F1_N, F1_kN, mult1,
            mostrar_caida=False)

        # ── Escenario 2: cuasi-estático ────────────────────────────
        F2_N, F2_kN, mult2, v2, a2 = calcular_escenario2(m)
        subtit2 = f'× {mult2:.2f}'
        _dibujar_escenario(
            ax_s2,
            f'Escenario 2 — Cuasi-estática\n'
            f'(caída {H_S2_CAIDA*100:.0f} cm, para en {T_STOP_S2:.2f} s)',
            subtit2,
            m, F2_N, F2_kN, mult2,
            mostrar_caida=False)

        # Añadir nota de velocidad y desaceleración en ax_s2
        ax_s2.text(5, 8.85,
                   f'v = {v2:.2f} m/s  |  a = {a2:.1f} m/s²',
                   ha='center', va='center', fontsize=7.5,
                   color=COLORS['text'], alpha=0.60)

        # ── Escenario 3: dinámico ──────────────────────────────────
        F3_N, F3_kN, mult3, v3, a3 = calcular_escenario3(m, h)
        subtit3 = f'× {mult3:.1f}'
        _dibujar_escenario(
            ax_s3,
            f'Escenario 3 — Dinámica\n'
            f'(caída {h:.1f} m, cuerda estática)',
            subtit3,
            m, F3_N, F3_kN, mult3,
            h_caida=h, mostrar_caida=True)

        if h > 0:
            d_stop = ELONG_EST * L_CUERDA
            ax_s3.text(5, 8.85,
                       f'v = {v3:.2f} m/s  |  d_stop = {d_stop:.2f} m  |  a = {a3:.0f} m/s²',
                       ha='center', va='center', fontsize=7.5,
                       color=COLORS['text'], alpha=0.60)

        fig.canvas.draw_idle()

    sl_mass.on_changed(update)
    sl_h.on_changed(update)

    # ── Textos fijos ──────────────────────────────────────────────────
    fig.text(0.5, 0.012,
             'En rescate: las cuerdas estáticas transmiten ~10× más fuerza que las dinámicas '
             'ante la misma caída. Por eso las cuerdas dinámicas ABSORBEN energía.',
             fontsize=9.5, ha='center',
             color=COLORS['text'], alpha=0.60, fontstyle='italic')

    # Etiquetas de los sliders a la izquierda
    fig.text(0.08, 0.143, 'Masa:', fontsize=9,
             ha='center', color=COLORS['text'], alpha=0.7)
    fig.text(0.08, 0.083, 'Altura\nEsc. 3:', fontsize=9,
             ha='center', color=COLORS['text'], alpha=0.7)

    # Nota sobre cuerda estática vs dinámica
    fig.text(0.02, 0.93,
             f'Cuerda estática: d_stop = {ELONG_EST*100:.1f}% × {L_CUERDA:.0f}m = '
             f'{ELONG_EST*L_CUERDA:.2f}m  |  '
             f'MBS cuerda estática: {ROPE_STATIC_MBS:.0f} kN  |  '
             f'NFPA carga trabajo: {NFPA_WORK_LOAD} kN',
             fontsize=8, ha='left',
             color=COLORS['text'], alpha=0.45)

    update()
    plt.show()


if __name__ == '__main__':
    main()
