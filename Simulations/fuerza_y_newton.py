"""
╔══════════════════════════════════════════════════════════════════════╗
║          FÍSICA DEL RESCATE · Módulo 01: ¿Qué es un Newton?          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Visualización interactiva de F = m · a y su relación con el         ║
║  peso de cargas en sistemas de rescate con cuerdas.                  ║
║                                                                      ║
║  Modo "Caída libre"  – v₀=0, gravedad constante, v gana con h        ║
║  Modo "Frenado"      – F impacto al parar en t segundos              ║
║    F = m·(g + v/t)   donde v = √(2·g·h)                             ║
║                                                                      ║
║  Controles: Masa · Altura de caída · Tiempo de frenado               ║
║  Ejecutar:  python 01_fuerza_y_newton.py                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
from matplotlib.patches import FancyBboxPatch, Circle
from config import COLORS, G, NFPA_WORK_LOAD, ROPE_STATIC_MBS, apply_mpl_style


# ── Constantes de presentación ────────────────────────────────────────
REF_OBJECTS = [          # (masa_kg, etiqueta, color)
    (0.102, 'Manzana pequeña  ≈ 1 N',  '#4CAF50'),
    (1.0,   'Libro 1 kg  ≈ 10 N',      '#2196F3'),
    (10.0,  'Mochila 10 kg  ≈ 98 N',   '#9C27B0'),
    (70.0,  'Persona 70 kg  ≈ 686 N',  '#FF9800'),
    (102.0, '≈ 102 kg  = 1 kN exacto', '#F44336'),
]

MODE_FREE  = 'Caída libre'
MODE_BRAKE = 'Frenado (impacto)'

BW, BH = 0.85, 0.85   # ancho/alto de la caja de masa


# ── Helpers de dibujo ─────────────────────────────────────────────────

def _ground(ax, y=0.0, x0=-2.2, x1=2.2):
    ax.plot([x0, x1], [y, y], color=COLORS['anchor'], lw=3, zorder=2)
    for xi in np.linspace(x0, x1, 12):
        ax.plot([xi, xi - 0.14], [y, y - 0.28],
                color=COLORS['anchor'], lw=1, alpha=0.4)


def _box(ax, cx, y_bot, label='', color=None, alpha=0.92):
    color = color or COLORS['primary']
    p = FancyBboxPatch((cx - BW/2, y_bot), BW, BH,
                       boxstyle='round,pad=0.05',
                       facecolor=color, edgecolor='white',
                       linewidth=2.2, alpha=alpha, zorder=5)
    ax.add_patch(p)
    ax.text(cx, y_bot + BH/2, label, ha='center', va='center',
            fontsize=12, fontweight='bold', color='white', zorder=6)


def _zigzag(ax, x, y0, y1, n=9, amp=0.22, **kw):
    """Cuerda/resorte bajo tensión entre (x,y0) y (x,y1)."""
    ys = np.linspace(y0, y1, n + 2)
    xs = np.empty_like(ys)
    xs[0] = x;  xs[-1] = x
    for i in range(1, n + 1):
        xs[i] = x + amp * (1 if i % 2 == 1 else -1)
    ax.plot(xs, ys, **kw)


def _arrow(ax, x, y_base, y_tip, color, lw=3.5, ms=22):
    ax.annotate('', xy=(x, y_tip), xytext=(x, y_base),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, mutation_scale=ms),
                zorder=4)


# ── Dibujo del panel 1 – Caída libre ─────────────────────────────────

def _draw_free_fall(ax, m, h, F_N, F_kN, v, Ep):
    MAX_H = 20.0
    ax.set_xlim(-2.8, 2.8)
    ax.set_ylim(-2.5, MAX_H + 3.5)
    ax.axis('off')
    ax.set_title('La gravedad actúa sobre la masa\n(F = m × g  siempre constante)',
                 fontsize=11, color=COLORS['text'], pad=4)

    _ground(ax)
    ax.text(0, -0.55, 'Suelo  (h = 0)', ha='center',
            fontsize=9, color=COLORS['anchor'])

    # Masa
    _box(ax, 0, h, label=f'{m:.0f} kg')

    # v₀ = 0
    ax.text(0, h + BH + 0.45, 'v₀ = 0 m/s',
            ha='center', fontsize=11, color=COLORS['accent'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.25', facecolor=COLORS['bg'],
                      edgecolor=COLORS['accent'], lw=1.8, alpha=0.9))
    ax.text(0, h + BH + 1.1, 'g = 9.81 m/s²',
            ha='center', fontsize=9, color=COLORS['text'], alpha=0.6)

    # Flecha peso (hacia abajo)
    ALEN = 2.6
    tip = max(h - ALEN, 0.1) if h >= ALEN else max(h - max(h * 0.85, 0.35), 0.05)
    _arrow(ax, 0, h, tip, COLORS['danger'], lw=4, ms=24)
    ax.text(0.55, (h + tip) / 2, f'F = {F_N:,.0f} N\n  = {F_kN:.3f} kN',
            fontsize=10, fontweight='bold', color=COLORS['danger'], va='center')

    if h >= 0.5:
        # Anotación altura
        ax.annotate('', xy=(-2.0, 0), xytext=(-2.0, h),
                    arrowprops=dict(arrowstyle='<->', color=COLORS['warning'], lw=1.8))
        ax.text(-2.45, h / 2, f'h = {h:.1f} m',
                fontsize=9, color=COLORS['warning'],
                va='center', ha='center', rotation=90)
        # Trayectoria punteada
        ty = np.linspace(h, 0.05, 30)
        ax.plot([0.06] * len(ty), ty, color=COLORS['warning'],
                lw=1.2, ls='--', alpha=0.22, zorder=1)
        # Velocidad al suelo
        ax.text(0, -1.35,
                f'Al llegar al suelo:\nv = √(2·g·h) = {v:.1f} m/s',
                ha='center', fontsize=11, color=COLORS['accent'], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.35', facecolor=COLORS['panel'],
                          edgecolor=COLORS['accent'], lw=2.0, alpha=0.95))
        # Barras de energía
        if Ep > 0:
            E_ref = m * G * MAX_H
            bx0, blen_max = 1.15, 1.45
            by0 = MAX_H * 0.72
            ep_bar = Ep / E_ref * blen_max
            for by, bl, lbl, clr in [
                (by0 + 0.55, ep_bar, 'Ep (inicio)', COLORS['warning']),
                (by0,        ep_bar, 'Ec (suelo)',  COLORS['accent']),
            ]:
                ax.add_patch(FancyBboxPatch(
                    (bx0, by - 0.14), max(bl, 0.05), 0.28,
                    boxstyle='round,pad=0.02',
                    facecolor=clr, edgecolor='none', alpha=0.7))
                ax.text(bx0 - 0.06, by, f'{lbl}: {Ep:,.0f} J',
                        fontsize=8, color=clr, va='center', ha='right')
    else:
        ax.text(0, -1.35,
                'Mueve el slider de altura\npara ver la velocidad ganada',
                ha='center', fontsize=9, color=COLORS['text'],
                alpha=0.5, style='italic')


# ── Dibujo del panel 1 – Frenado ─────────────────────────────────────

def _draw_braking(ax, m, h, F_N, F_kN, v, t_b, a_brake, F_imp_N, F_imp_kN, d_brake):
    MAX_H = 20.0
    BRAKE_Y = -2.0    # centro de la masa frenada (display fijo)
    mass_top = BRAKE_Y + BH / 2
    mass_bot = BRAKE_Y - BH / 2

    ax.set_xlim(-2.8, 2.8)
    ax.set_ylim(-5.2, MAX_H + 3.5)
    ax.axis('off')
    ax.set_title('Caída + frenado: la cuerda aplica\nfuerza de impacto  F = m·(g + v/t)',
                 fontsize=11, color=COLORS['text'], pad=4)

    _ground(ax)
    ax.text(1.6, 0.22, '← cuerda se tensa', ha='center',
            fontsize=8, color=COLORS['anchor'], alpha=0.75)

    # ── Fase 1: masa antes de caer ────────────────────────────────────
    _box(ax, 0, h, label=f'{m:.0f} kg')
    ax.text(0, h + BH + 0.45, 'v₀ = 0 m/s',
            ha='center', fontsize=10, color=COLORS['accent'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.22', facecolor=COLORS['bg'],
                      edgecolor=COLORS['accent'], lw=1.5, alpha=0.9))

    if h >= 0.5:
        # Flecha peso (indicativa, más suave)
        tip_g = max(h - 2.2, h / 2)
        _arrow(ax, 0, h, tip_g, COLORS['danger'], lw=2.5, ms=16)
        ax.text(0.5, (h + tip_g) / 2, f'g·m = {F_N:,.0f} N',
                fontsize=8, color=COLORS['danger'], va='center', alpha=0.7)

        # Altura
        ax.annotate('', xy=(-2.0, 0), xytext=(-2.0, h),
                    arrowprops=dict(arrowstyle='<->', color=COLORS['warning'], lw=1.5))
        ax.text(-2.45, h / 2, f'h = {h:.1f} m',
                fontsize=9, color=COLORS['warning'],
                va='center', ha='center', rotation=90)

        # Trayectoria punteada
        ty = np.linspace(h, 0.05, 25)
        ax.plot([0.05] * len(ty), ty, color=COLORS['warning'],
                lw=1, ls='--', alpha=0.18, zorder=1)

        # Velocidad en el suelo
        ax.text(0, 0.28, f'v impacto = {v:.1f} m/s',
                ha='center', fontsize=9, color=COLORS['warning'],
                fontweight='bold', alpha=0.9)

        # ── Fase 2: cuerda frenando (zona bajo tierra) ────────────────
        # Etiqueta de zona
        ax.text(-1.8, (mass_top - 0.1) / 2,
                f'Cuerda\nfrenando\nd = {d_brake:.2f} m',
                ha='center', fontsize=8, color=COLORS['rope'],
                va='center', alpha=0.85)

        # Zigzag: desde el suelo hasta la parte superior de la masa
        _zigzag(ax, 0, -0.12, mass_top, n=9, amp=0.23,
                color=COLORS['rope'], lw=2.8, alpha=0.88, zorder=3)

        # Masa detenida (gris para distinguirla de la masa inicial)
        _box(ax, 0, mass_bot, label=f'{m:.0f} kg',
             color='#546E7A', alpha=0.88)

        # Escala de flechas: mg fijo = 1.2 unidades, F_imp proporcional
        MG_LEN = 1.2
        IMP_LEN = min((F_imp_N / F_N) * MG_LEN, 3.8) if F_N > 0 else MG_LEN

        # Flecha F_impacto (hacia ARRIBA, roja, grande)
        _arrow(ax, 0, mass_top, mass_top + IMP_LEN, COLORS['danger'], lw=4.5, ms=26)
        ax.text(0.55, mass_top + IMP_LEN / 2,
                f'F impacto\n= {F_imp_N:,.0f} N\n= {F_imp_kN:.3f} kN',
                fontsize=9, fontweight='bold', color=COLORS['danger'], va='center')

        # Flecha mg (hacia ABAJO, naranja, pequeña)
        _arrow(ax, 0, mass_bot, mass_bot - MG_LEN, COLORS['secondary'], lw=2.5, ms=18)
        ax.text(-0.6, mass_bot - MG_LEN / 2,
                f'mg\n{F_N:,.0f} N',
                fontsize=8, color=COLORS['secondary'], va='center', ha='right')

        # v final = 0
        ax.text(0, mass_bot - 0.6, 'v final = 0 m/s',
                ha='center', fontsize=10, color=COLORS['accent'], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.22', facecolor=COLORS['bg'],
                          edgecolor=COLORS['accent'], lw=1.5, alpha=0.9))

        # Desaceleración
        ax.text(0, mass_bot - 1.35,
                f'a frenado = v/t = {a_brake:.1f} m/s²',
                ha='center', fontsize=9, color=COLORS['text'], alpha=0.7)

    else:
        ax.text(0, -1.5,
                'Aumenta la altura de caída\npara ver la fuerza de frenado',
                ha='center', fontsize=9, color=COLORS['text'],
                alpha=0.5, style='italic')


# ── Dibujo del panel 2 – N vs kN (modo caída libre) ──────────────────

def _draw_units_free(ax, m, F_N, F_kN):
    ax.set_xlim(0, 10);  ax.set_ylim(0, 10);  ax.axis('off')
    ax.set_title('La misma fuerza,\ndos unidades distintas',
                 fontsize=12, color=COLORS['text'], pad=4)

    ax.text(5, 9.1, f'{F_N:,.1f} N',
            ha='center', va='center', fontsize=30, fontweight='bold',
            color=COLORS['warning'],
            bbox=dict(boxstyle='round,pad=0.45', facecolor=COLORS['panel'],
                      edgecolor=COLORS['warning'], lw=2.5))
    ax.text(5, 8.25, '(Newtons)',
            ha='center', fontsize=10, color=COLORS['text'], alpha=0.75)

    ax.annotate('', xy=(5, 7.35), xytext=(5, 7.85),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'],
                                lw=1.8, mutation_scale=16))
    ax.text(5, 7.12, '÷ 1 000', ha='center', fontsize=10,
            color=COLORS['text'], alpha=0.65,
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['bg'],
                      edgecolor=COLORS['grid'], lw=1))
    ax.annotate('', xy=(5, 6.50), xytext=(5, 6.90),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'],
                                lw=1.8, mutation_scale=16))

    ax.text(5, 5.75, f'{F_kN:.3f} kN',
            ha='center', va='center', fontsize=30, fontweight='bold',
            color=COLORS['primary'],
            bbox=dict(boxstyle='round,pad=0.45', facecolor=COLORS['panel'],
                      edgecolor=COLORS['primary'], lw=2.5))
    ax.text(5, 4.95, '(kilonewtons  =  1 000 N)',
            ha='center', fontsize=10, color=COLORS['text'], alpha=0.75)

    ax.plot([0.5, 9.5], [4.5, 4.5], color=COLORS['grid'], lw=1, alpha=0.5)
    ax.text(5, 4.25, 'Escala de referencia  (log)',
            ha='center', fontsize=9, color=COLORS['text'], alpha=0.6)

    BAR_X0, BAR_MAX, REF_MAX_N = 1.0, 7.5, 1000.0
    y_row = 3.75
    for mass_ref, label, color in REF_OBJECTS:
        bar_len = np.log10(mass_ref * G + 1) / np.log10(REF_MAX_N + 1) * BAR_MAX
        ax.add_patch(FancyBboxPatch(
            (BAR_X0, y_row - 0.14), max(bar_len, 0.1), 0.28,
            boxstyle='round,pad=0.02', facecolor=color, edgecolor='none', alpha=0.7))
        ax.text(BAR_X0 - 0.1, y_row, label,
                ha='right', va='center', fontsize=8, color=color)
        y_row -= 0.65

    f_cur_bar = np.log10(F_N + 1) / np.log10(REF_MAX_N + 1) * BAR_MAX
    f_cur_bar = max(min(f_cur_bar, BAR_MAX), 0.15)
    ax.add_patch(FancyBboxPatch(
        (BAR_X0, y_row - 0.16), f_cur_bar, 0.32,
        boxstyle='round,pad=0.02', facecolor=COLORS['warning'],
        edgecolor='white', lw=1.2, alpha=0.9))
    ax.text(BAR_X0 - 0.1, y_row, f'← Tu masa\n   {m:.0f} kg',
            ha='right', va='center', fontsize=8,
            color=COLORS['warning'], fontweight='bold')


# ── Dibujo del panel 2 – Frenado (estática vs impacto) ───────────────

def _draw_units_brake(ax, m, F_N, F_kN, F_imp_N, F_imp_kN, a_brake, t_b, d_brake, v):
    ax.set_xlim(0, 10);  ax.set_ylim(0, 10);  ax.axis('off')
    ax.set_title('Fuerza estática  vs  fuerza de impacto',
                 fontsize=12, color=COLORS['text'], pad=4)

    # Columna izquierda: F estática
    ax.text(2.5, 9.3, 'F estática', ha='center', fontsize=10,
            color=COLORS['primary'], fontweight='bold')
    ax.text(2.5, 8.85, '(masa colgando en reposo)', ha='center',
            fontsize=7.5, color=COLORS['text'], alpha=0.6)
    ax.text(2.5, 7.95, f'{F_N:,.0f} N',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=COLORS['primary'],
            bbox=dict(boxstyle='round,pad=0.35', facecolor=COLORS['panel'],
                      edgecolor=COLORS['primary'], lw=2.0))
    ax.text(2.5, 7.1, f'= {F_kN:.3f} kN',
            ha='center', fontsize=13, color=COLORS['primary'], fontweight='bold')
    ax.text(2.5, 6.6, '= m × g',
            ha='center', fontsize=9, color=COLORS['text'], alpha=0.55)

    # Separador vertical
    ax.plot([5, 5], [1.0, 9.6], color=COLORS['grid'], lw=1, alpha=0.5)

    # Columna derecha: F impacto
    ax.text(7.5, 9.3, 'F impacto', ha='center', fontsize=10,
            color=COLORS['danger'], fontweight='bold')
    ax.text(7.5, 8.85, f'(frenando en {t_b:.2f} s)', ha='center',
            fontsize=7.5, color=COLORS['text'], alpha=0.6)
    ax.text(7.5, 7.95, f'{F_imp_N:,.0f} N',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=COLORS['danger'],
            bbox=dict(boxstyle='round,pad=0.35', facecolor=COLORS['panel'],
                      edgecolor=COLORS['danger'], lw=2.0))
    ax.text(7.5, 7.1, f'= {F_imp_kN:.3f} kN',
            ha='center', fontsize=13, color=COLORS['danger'], fontweight='bold')
    ax.text(7.5, 6.6, '= m·(g + v/t)',
            ha='center', fontsize=9, color=COLORS['text'], alpha=0.55)

    # Multiplicador central
    mult = F_imp_N / F_N if F_N > 0 else 1.0
    m_color = (COLORS['danger']    if mult > 5
               else COLORS['secondary'] if mult > 2
               else COLORS['warning']   if mult > 1.2
               else COLORS['accent'])
    ax.text(5, 5.7, f'× {mult:.1f}',
            ha='center', va='center', fontsize=28, fontweight='bold',
            color=m_color,
            bbox=dict(boxstyle='round,pad=0.35', facecolor=COLORS['panel'],
                      edgecolor=m_color, lw=2.2))
    ax.text(5, 5.05, 'veces el peso estático',
            ha='center', fontsize=8.5, color=COLORS['text'], alpha=0.7)

    # Separador horizontal
    ax.plot([0.3, 9.7], [4.65, 4.65], color=COLORS['grid'], lw=1, alpha=0.4)

    # Tabla de datos
    rows = [
        ('Velocidad de impacto:',  f'{v:.2f} m/s',       COLORS['warning']),
        ('Desaceleración:',        f'{a_brake:.1f} m/s²', COLORS['danger']),
        ('Tiempo de frenado:',     f'{t_b:.2f} s',        COLORS['secondary']),
        ('Distancia de frenado:',  f'{d_brake:.3f} m',    COLORS['info']),
    ]
    y_r = 4.3
    for lbl, val, clr in rows:
        ax.text(0.5, y_r, lbl, ha='left', fontsize=8.5,
                color=COLORS['text'], alpha=0.75)
        ax.text(9.5, y_r, val, ha='right', fontsize=8.5,
                fontweight='bold', color=clr)
        y_r -= 0.62

    # Fórmula
    ax.text(5, 1.55,
            f'F = m·(g + v/t)  =  {m:.0f}·({G:.2f} + {a_brake:.2f})',
            ha='center', fontsize=8, color=COLORS['text'], alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.2', facecolor=COLORS['panel'],
                      edgecolor=COLORS['grid'], lw=1))
    ax.text(5, 0.9, f'= {m:.0f} × {G + a_brake:.2f} = {F_imp_N:,.0f} N',
            ha='center', fontsize=9, color=COLORS['danger'], fontweight='bold')


# ── Dibujo del panel 3 – Barras comparativas ─────────────────────────

def _draw_bar(ax, m, F_N, F_kN, F_imp_N=None, F_imp_kN=None, t_b=None, h=None):
    brake_mode = F_imp_N is not None
    f_shock_kN = m * G * 1.77 / 1000.0

    if brake_mode:
        scenarios = [
            (f'F impacto\n({m:.0f} kg, t={t_b:.2f}s)', F_imp_kN,        COLORS['danger']),
            (f'Peso estático\n({m:.0f} kg)',             F_kN,            COLORS['warning']),
            ('Rescatista + paciente\n(160 kg × g)',       160*G/1000,     COLORS['primary']),
            ('Choque caída factor 1',                     f_shock_kN,     COLORS['secondary']),
            ('Carga trabajo NFPA 1983',                   NFPA_WORK_LOAD, COLORS['danger']),
            ('Rotura cuerda estática 11mm',               ROPE_STATIC_MBS,COLORS['accent']),
        ]
        title = (f'F impacto: {F_imp_kN:.2f} kN  vs  Peso: {F_kN:.2f} kN\n'
                 f'(masa {m:.0f} kg · caída {h:.1f} m · frenado en {t_b:.2f} s)')
    else:
        scenarios = [
            (f'Peso de {m:.0f} kg\n({F_N:,.0f} N)',     F_kN,            COLORS['warning']),
            ('Rescatista + paciente\n(160 kg × g)',        160*G/1000,    COLORS['primary']),
            ('Fuerza de choque\n(caída factor 1)',          f_shock_kN,   COLORS['secondary']),
            ('Carga trabajo\nNFPA 1983',                   NFPA_WORK_LOAD,COLORS['danger']),
            ('Rotura cuerda\nestática 11 mm',              ROPE_STATIC_MBS,COLORS['accent']),
        ]
        title = (f'Misma masa ({m:.0f} kg) en contexto de rescate\n'
                 '1 kN = 1 000 N  (kilonewton = mil newtons)')

    names = [s[0] for s in scenarios]
    vals  = [s[1] for s in scenarios]
    cols  = [s[2] for s in scenarios]

    bars = ax.barh(names, vals, color=cols, height=0.55,
                   edgecolor='white', linewidth=0.3, alpha=0.88)

    if brake_mode:
        bars[0].set_edgecolor(COLORS['danger'])
        bars[0].set_linewidth(2.5)
        bars[0].set_alpha(1.0)

    for bar, v_val in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f'{v_val:.2f} kN\n= {v_val*1000:,.0f} N',
                va='center', fontsize=9, fontweight='bold',
                color=COLORS['text'])

    # Advertencia si F_impacto supera la carga de trabajo NFPA
    if brake_mode and F_imp_kN > NFPA_WORK_LOAD:
        warn_color = COLORS['danger'] if F_imp_kN > ROPE_STATIC_MBS else COLORS['secondary']
        warn_text  = ('¡SUPERA ROTURA CUERDA!'
                      if F_imp_kN > ROPE_STATIC_MBS
                      else '⚠ Supera carga NFPA 1983')
        ax.text(max(vals) * 0.5, -0.6, warn_text,
                ha='center', fontsize=10, fontweight='bold', color=warn_color,
                bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['panel'],
                          edgecolor=warn_color, lw=2))

    ax.set_xlabel('Fuerza (kN)', fontsize=11)
    ax.set_xlim(0, max(vals) * 1.52)
    ax.set_title(title, fontsize=10, fontweight='bold',
                 color=COLORS['text'], pad=8)
    ax.grid(axis='x', alpha=0.15)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(19, 11))
    fig.suptitle('FÍSICA DEL RESCATE — ¿Qué es un Newton?',
                 fontsize=22, fontweight='bold', color=COLORS['primary'], y=0.977)
    fig.text(0.5, 0.935,
             'F = m · a   →   1 N = 1 kg · 1 m/s²   →   Peso = m · g',
             fontsize=13, ha='center', color=COLORS['warning'], fontstyle='italic')

    # ── Ejes principales ──────────────────────────────────────────────
    ax_fall  = fig.add_axes([0.02, 0.23, 0.31, 0.68])
    ax_units = fig.add_axes([0.37, 0.23, 0.26, 0.68])
    ax_bar   = fig.add_axes([0.67, 0.23, 0.31, 0.68])

    # ── Radio buttons ─────────────────────────────────────────────────
    ax_radio = fig.add_axes([0.02, 0.03, 0.11, 0.15])
    ax_radio.set_facecolor(COLORS['panel'])
    for sp in ax_radio.spines.values():
        sp.set_edgecolor(COLORS['grid'])

    radio = RadioButtons(ax_radio, [MODE_FREE, MODE_BRAKE],
                         activecolor=COLORS['primary'])
    for lbl in radio.labels:
        lbl.set_fontsize(9)
        lbl.set_color(COLORS['text'])

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_m = fig.add_axes([0.18, 0.165, 0.78, 0.022])
    ax_sl_h = fig.add_axes([0.18, 0.108, 0.78, 0.022])
    ax_sl_t = fig.add_axes([0.18, 0.050, 0.78, 0.022])

    sl_mass = Slider(ax_sl_m, 'Masa (kg)',             1,    200,  valinit=70,
                     color=COLORS['primary'],   valstep=1)
    sl_h    = Slider(ax_sl_h, 'Altura de caída (m)',   0.0,  20.0, valinit=0.0,
                     color=COLORS['secondary'], valstep=0.5)
    sl_t    = Slider(ax_sl_t, 'Tiempo de frenado (s)', 0.01, 1.0,  valinit=0.5,
                     color=COLORS['danger'],    valstep=0.01)

    for sl in (sl_mass, sl_h, sl_t):
        sl.valtext.set_fontsize(11)

    # ── Nota estática del slider de tiempo ────────────────────────────
    fig.text(0.155, 0.062, 'solo aplica en\nmodo Frenado',
             fontsize=7, color=COLORS['danger'], alpha=0.55,
             ha='center', va='center', fontstyle='italic')

    # ── Update ────────────────────────────────────────────────────────
    def update(_=None):
        m    = float(sl_mass.val)
        h    = float(sl_h.val)
        t_b  = float(sl_t.val)
        mode = radio.value_selected

        F_N   = m * G
        F_kN  = F_N / 1000.0
        v     = np.sqrt(2.0 * G * h) if h > 0 else 0.0
        Ep    = m * G * h

        a_brake  = v / t_b if v > 0 else 0.0
        F_imp_N  = m * (G + a_brake)
        F_imp_kN = F_imp_N / 1000.0
        d_brake  = v * t_b / 2.0

        ax_fall.clear()
        ax_units.clear()
        ax_bar.clear()

        if mode == MODE_FREE:
            _draw_free_fall(ax_fall, m, h, F_N, F_kN, v, Ep)
            _draw_units_free(ax_units, m, F_N, F_kN)
            _draw_bar(ax_bar, m, F_N, F_kN)
        else:
            _draw_braking(ax_fall, m, h, F_N, F_kN,
                          v, t_b, a_brake, F_imp_N, F_imp_kN, d_brake)
            _draw_units_brake(ax_units, m, F_N, F_kN,
                              F_imp_N, F_imp_kN, a_brake, t_b, d_brake, v)
            _draw_bar(ax_bar, m, F_N, F_kN,
                      F_imp_N=F_imp_N, F_imp_kN=F_imp_kN, t_b=t_b, h=h)

        fig.canvas.draw_idle()

    sl_mass.on_changed(update)
    sl_h.on_changed(update)
    sl_t.on_changed(update)
    radio.on_clicked(update)

    # ── Nota al pie ───────────────────────────────────────────────────
    fig.text(0.02, 0.012,
             '1 N ≈ peso de una manzana pequeña  │  1 kN = 1 000 N ≈ 102 kg  │  '
             'En rescate técnico trabajamos en kilo-Newtons (kN)',
             fontsize=9, color=COLORS['text'], alpha=0.55, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
