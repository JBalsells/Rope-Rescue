"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 17: Mosquetones                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  Tipos de mosquetones y colocación correcta en sistemas de rescate.  ║
║                                                                      ║
║  Resistencia efectiva según eje y ángulo de carga (modelo elíptico): ║
║   F_ef(θ) = (F_mayor · F_menor) / √[(F_menor·cosθ)²+(F_mayor·sinθ)²]║
║                                                                      ║
║  Eje mayor (cerrado):   21–30 kN  según tipo                         ║
║  Eje menor (cerrado):    8–10 kN  según tipo                         ║
║  Puerta abierta:         7–9 kN   según tipo                         ║
║                                                                      ║
║  θ = 0°  → carga en eje mayor  (máxima resistencia)                 ║
║  θ = 90° → carga en eje menor  (mínima resistencia, carga lateral)   ║
║                                                                      ║
║  Ejecutar:  python 17_mosquetones.py                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.patches import Arc, Patch
from config import COLORS, NFPA_WORK_LOAD, apply_mpl_style


# ── Datos de mosquetones ──────────────────────────────────────────────
MOSQUETONES = [
    {
        'nombre':            'Óvalo',
        'descripcion':       'Simétrico · poleas y macarrones',
        'eje_mayor_kN':      21,
        'eje_menor_kN':       8,
        'puerta_abierta_kN':  7,
        'color':             COLORS['info'],
        'usos':              'Poleas, macarrones de fijación, sistemas de rapel',
    },
    {
        'nombre':            'D Asimétrica',
        'descripcion':       'Uso general · rescate y escalada',
        'eje_mayor_kN':      25,
        'eje_menor_kN':       8,
        'puerta_abierta_kN':  7,
        'color':             COLORS['accent'],
        'usos':              'Anclajes, reuniones, descensores, polipastos',
    },
    {
        'nombre':            'HMS / Pera',
        'descripcion':       'Asegurar y rapelar · freno munter',
        'eje_mayor_kN':      25,
        'eje_menor_kN':       9,
        'puerta_abierta_kN':  8,
        'color':             COLORS['warning'],
        'usos':              'Rapel, aseguramiento dinámico, freno munter',
    },
    {
        'nombre':            'D Rescate',
        'descripcion':       'Alta resistencia · sistemas multipunto',
        'eje_mayor_kN':      30,
        'eje_menor_kN':      10,
        'puerta_abierta_kN':  9,
        'color':             COLORS['secondary'],
        'usos':              'Sistemas de rescate, polipastos, anclajes multipunto',
    },
]


def resistencia_efectiva(F_mayor, F_menor, theta_deg):
    """
    Resistencia efectiva según ángulo de carga respecto al eje mayor.
    Modelo elíptico: F_mayor en θ=0°, F_menor en θ=90°.
    """
    t = np.radians(np.asarray(theta_deg, dtype=float))
    denom = np.sqrt((F_menor * np.cos(t)) ** 2 + (F_mayor * np.sin(t)) ** 2)
    return (F_mayor * F_menor) / np.where(denom < 1e-6, 1e-6, denom)


def _dibujar_forma(ax, tipo_idx, gate_open, c):
    """Dibuja el contorno esquemático del mosquetón. Devuelve (bolt_y, load_y)."""
    lw = 5.5
    t50 = np.linspace(0, np.pi, 60)

    if tipo_idx == 0:                               # ── Óvalo ──
        # Arco superior e inferior + dos laterales rectos
        ax.plot(-0.65 + 0.65 * np.cos(t50),
                 1.10 + 0.42 * np.sin(t50),
                 color=c, lw=lw, solid_capstyle='round', zorder=4)
        ax.plot(-0.65 + 0.65 * np.cos(t50 + np.pi),
                -1.10 - 0.42 * np.sin(t50),
                 color=c, lw=lw, solid_capstyle='round', zorder=4)
        ax.plot([-0.65, -0.65], [-1.10, 1.10],
                color=c, lw=lw, solid_capstyle='round', zorder=4)       # espina
        if gate_open:
            ax.plot([0.65, 1.30], [-1.10, -0.35],
                    color=c, lw=lw - 1.5, ls='--', alpha=0.7, zorder=4)
            ax.plot([0.65, 1.25], [ 1.10,  0.55],
                    color=c, lw=lw - 1.5, ls='--', alpha=0.6, zorder=4)
        else:
            ax.plot([0.65, 0.65], [-1.10, 1.10],
                    color=c, lw=lw, solid_capstyle='round', zorder=4)   # puerta
        return 1.52, -1.52

    elif tipo_idx == 1:                             # ── D Asimétrica ──
        ax.plot([-0.70, -0.70], [-1.30, 1.30],
                color=c, lw=lw + 2, solid_capstyle='round', zorder=4)   # espina
        t_d = np.linspace(-np.pi / 2, np.pi / 2, 80)
        xd = 0.20 + 1.10 * np.cos(t_d)
        yd = 1.30 * np.sin(t_d)
        ax.plot(xd, yd, color=c, lw=lw, solid_capstyle='round', zorder=4)
        ax.plot([-0.70, xd[ 0]], [yd[ 0], yd[ 0]], color=c, lw=lw, zorder=4)
        ax.plot([-0.70, xd[-1]], [yd[-1], yd[-1]], color=c, lw=lw, zorder=4)
        gx = -0.10
        if gate_open:
            ax.plot([gx, gx - 0.55], [-1.30, -0.55],
                    color=c, lw=lw - 2, ls='--', alpha=0.7, zorder=4)
        else:
            ax.plot([gx, gx], [-1.30, 1.30],
                    color=c, lw=lw - 2, solid_capstyle='round', zorder=4)
        return 1.30, -1.30

    elif tipo_idx == 2:                             # ── HMS / Pera ──
        t_pear = np.linspace(-np.pi / 2, np.pi / 2, 80)
        r_top, r_bot = 1.20, 0.70
        r_interp = r_bot + (r_top - r_bot) * (np.sin(t_pear) + 1) / 2
        xp = 0.10 + r_interp * np.cos(t_pear)
        yp = 1.30 * np.sin(t_pear)
        ax.plot(xp, yp, color=c, lw=lw, solid_capstyle='round', zorder=4)
        ax.plot([-0.65, xp[ 0]], [yp[ 0], yp[ 0]], color=c, lw=lw, zorder=4)
        ax.plot([-0.65, xp[-1]], [yp[-1], yp[-1]], color=c, lw=lw, zorder=4)
        ax.plot([-0.65, -0.65], [-1.30, 1.30],
                color=c, lw=lw, solid_capstyle='round', zorder=4)
        gx = -0.15
        if gate_open:
            ax.plot([gx, gx - 0.50], [-1.30, -0.60],
                    color=c, lw=lw - 2, ls='--', alpha=0.7, zorder=4)
        else:
            ax.plot([gx, gx], [-1.30, 1.30],
                    color=c, lw=lw - 2, solid_capstyle='round', zorder=4)
        return 1.30, -1.30

    else:                                           # ── D Rescate (grande) ──
        ax.plot([-0.85, -0.85], [-1.55, 1.55],
                color=c, lw=lw + 3, solid_capstyle='round', zorder=4)
        t_d = np.linspace(-np.pi / 2, np.pi / 2, 80)
        xd = 0.25 + 1.35 * np.cos(t_d)
        yd = 1.55 * np.sin(t_d)
        ax.plot(xd, yd, color=c, lw=lw, solid_capstyle='round', zorder=4)
        ax.plot([-0.85, xd[ 0]], [yd[ 0], yd[ 0]], color=c, lw=lw, zorder=4)
        ax.plot([-0.85, xd[-1]], [yd[-1], yd[-1]], color=c, lw=lw, zorder=4)
        gx = -0.15
        if gate_open:
            ax.plot([gx, gx - 0.65], [-1.55, -0.75],
                    color=c, lw=lw - 2, ls='--', alpha=0.7, zorder=4)
        else:
            ax.plot([gx, gx], [-1.55, 1.55],
                    color=c, lw=lw - 2, solid_capstyle='round', zorder=4)
        # Indicador de seguro (trilock)
        for y_seg in [-1.05, -1.55]:
            ax.plot([gx - 0.22, gx + 0.22], [y_seg, y_seg],
                    color=COLORS['text'], lw=2, alpha=0.55, zorder=5)
        ax.text(gx - 0.55, -1.30, 'seguro', fontsize=7,
                color=COLORS['text'], alpha=0.55, va='center')
        return 1.55, -1.55


def dibujar_mosqueton(ax, tipo_idx, gate_open, load_angle_deg, load_kN, eff_kN):
    """Dibuja el diagrama completo del mosquetón con indicadores de carga."""
    ax.clear()
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.9, 3.5)
    ax.set_aspect('equal')
    ax.axis('off')

    m = MOSQUETONES[tipo_idx]
    c = m['color']

    bolt_y, load_y = _dibujar_forma(ax, tipo_idx, gate_open, c)

    # Puntos de anclaje (arriba: ancla / abajo: carga)
    ax.plot([0], [bolt_y], 'D', color=COLORS['anchor'], ms=9, zorder=6)
    ax.plot([0], [load_y], 'D', color=COLORS['anchor'], ms=9, zorder=6)

    # Indicador de eje mayor
    ax.annotate('', xy=(0, bolt_y + 0.25), xytext=(0, load_y - 0.25),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'],
                                lw=1.2, alpha=0.22))
    ax.text(0.18, 0, 'eje\nmayor', fontsize=7, color=COLORS['text'],
            alpha=0.35, va='center', rotation=90)

    # Flecha de carga (dirección ajustable)
    angle_rad = np.radians(load_angle_deg)
    arr_len = 1.50
    dx = arr_len * np.sin(angle_rad)
    dy = -arr_len * np.cos(angle_rad)

    arr_color = (COLORS['accent']  if load_angle_deg < 20 else
                 COLORS['warning'] if load_angle_deg < 50 else
                 COLORS['danger'])

    ax.annotate('', xy=(dx, load_y + dy), xytext=(0, load_y),
                arrowprops=dict(arrowstyle='->', color=arr_color,
                                lw=3.5, mutation_scale=22))

    ax.text(dx * 1.15, load_y + dy - 0.22,
            f'{load_kN:.2f} kN aplicados\n→ {eff_kN:.2f} kN efectivos',
            ha='center', fontsize=9, fontweight='bold', color=arr_color,
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                      edgecolor=arr_color, alpha=0.90), zorder=7)

    # Arco del ángulo de carga
    if load_angle_deg > 3:
        arc = Arc((0, load_y), 1.0, 1.0, angle=0,
                  theta1=-90, theta2=-90 + load_angle_deg,
                  color=arr_color, lw=1.5, zorder=5)
        ax.add_patch(arc)
        mid_ang = np.radians(-90 + load_angle_deg / 2)
        ax.text(0.68 * np.cos(mid_ang), load_y + 0.68 * np.sin(mid_ang),
                f'{load_angle_deg:.0f}°',
                fontsize=8, color=arr_color, ha='center', fontweight='bold')

    # Estado de la puerta
    gate_lbl = '⚠ PUERTA ABIERTA' if gate_open else '✓ Puerta cerrada'
    gate_col = COLORS['danger'] if gate_open else COLORS['accent']
    ax.text(0, load_y - 1.05, gate_lbl,
            ha='center', fontsize=10, fontweight='bold', color=gate_col,
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['bg'],
                      edgecolor=gate_col, alpha=0.92), zorder=7)

    # Título del diagrama
    ax.set_title(f'{m["nombre"]}  ·  {m["descripcion"]}',
                 fontsize=13, fontweight='bold', color=c, pad=8)

    # Usos típicos
    ax.text(-3.3, -3.7,
            f'Usos: {m["usos"]}',
            fontsize=8, color=COLORS['text'], alpha=0.62, va='bottom',
            style='italic')


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(16, 9))
    fig.suptitle(
        'FÍSICA DEL RESCATE — Mosquetones: Tipos y Colocación Correcta',
        fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.97)

    # ── Ejes ──────────────────────────────────────────────────────────
    ax_diag = fig.add_axes([0.02, 0.22, 0.38, 0.67])   # diagrama mosquetón
    ax_crv  = fig.add_axes([0.46, 0.42, 0.51, 0.44])   # curva F vs ángulo
    ax_bar  = fig.add_axes([0.46, 0.22, 0.51, 0.17])   # barras comparación

    # ── Sliders ───────────────────────────────────────────────────────
    ax_sl_tipo = fig.add_axes([0.15, 0.15, 0.28, 0.025])
    ax_sl_ang  = fig.add_axes([0.15, 0.09, 0.75, 0.025])
    ax_sl_gate = fig.add_axes([0.57, 0.15, 0.33, 0.025])

    sl_tipo = Slider(ax_sl_tipo, 'Tipo (0–3)', 0, 3,
                     valinit=1, valstep=1, color=COLORS['primary'])
    sl_ang  = Slider(ax_sl_ang,  'Ángulo de carga (°)', 0, 90,
                     valinit=0, valstep=1, color=COLORS['secondary'])
    sl_gate = Slider(ax_sl_gate, 'Puerta  0=cerrada / 1=abierta', 0, 1,
                     valinit=0, valstep=1, color=COLORS['danger'])

    # Textos actualizables (pre-creados para evitar acumulación)
    tipo_text   = fig.text(0.44, 0.155, '', fontsize=10, fontweight='bold',
                           ha='right', va='center', color=COLORS['primary'])
    status_text = fig.text(0.21, 0.185, '', fontsize=11, fontweight='bold',
                           ha='center', va='center', color=COLORS['accent'],
                           bbox=dict(boxstyle='round,pad=0.4',
                                     facecolor=COLORS['bg'],
                                     edgecolor=COLORS['accent'], alpha=0.0))

    def update(_=None):
        tipo_idx  = int(sl_tipo.val)
        ang_deg   = float(sl_ang.val)
        gate_open = bool(int(sl_gate.val))

        m = MOSQUETONES[tipo_idx]
        c = m['color']

        # Resistencia aplicable
        F_mayor = m['puerta_abierta_kN'] if gate_open else m['eje_mayor_kN']
        F_menor = m['eje_menor_kN']
        eff_kN  = float(resistencia_efectiva(F_mayor, F_menor, ang_deg))

        # ── Diagrama ────────────────────────────────────────────────
        dibujar_mosqueton(ax_diag, tipo_idx, gate_open,
                          ang_deg, NFPA_WORK_LOAD, eff_kN)

        # ── Curva F vs ángulo ───────────────────────────────────────
        ax_crv.clear()
        angles_arr = np.linspace(0, 90, 400)

        for idx, msq in enumerate(MOSQUETONES):
            Fm = msq['puerta_abierta_kN'] if gate_open else msq['eje_mayor_kN']
            Fn = msq['eje_menor_kN']
            F_curve = resistencia_efectiva(Fm, Fn, angles_arr)
            selected = (idx == tipo_idx)
            ax_crv.plot(angles_arr, F_curve,
                        color=msq['color'],
                        lw=3.0 if selected else 1.5,
                        alpha=1.0 if selected else 0.30,
                        label=msq['nombre'])

        # Línea NFPA
        ax_crv.axhline(NFPA_WORK_LOAD, color=COLORS['danger'],
                       ls='--', lw=1.5, alpha=0.75)
        ax_crv.text(2, NFPA_WORK_LOAD + 0.35,
                    f'Límite NFPA: {NFPA_WORK_LOAD} kN',
                    fontsize=8, color=COLORS['danger'], alpha=0.85)

        # Punto actual
        ax_crv.plot(ang_deg, eff_kN, 'o', color=c, ms=12, zorder=10)
        ax_crv.axvline(ang_deg, color=COLORS['warning'], ls='--', lw=1.5, alpha=0.7)
        ax_crv.axhline(eff_kN,  color=COLORS['warning'], ls='--', lw=1.2, alpha=0.5)
        ax_crv.text(ang_deg + 2.5, eff_kN + 0.5,
                    f'θ={ang_deg:.0f}° → {eff_kN:.1f} kN',
                    fontsize=10, fontweight='bold', color=COLORS['warning'],
                    bbox=dict(boxstyle='round', facecolor=COLORS['bg'],
                              edgecolor=COLORS['warning'], alpha=0.92))

        # Zonas coloreadas
        ax_crv.axvspan( 0, 20, facecolor=COLORS['accent'],  alpha=0.06)
        ax_crv.axvspan(20, 50, facecolor=COLORS['warning'], alpha=0.05)
        ax_crv.axvspan(50, 90, facecolor=COLORS['danger'],  alpha=0.06)

        ax_crv.set_xlabel('Ángulo de carga desde el eje mayor (°)', fontsize=11)
        ax_crv.set_ylabel('Resistencia efectiva (kN)', fontsize=11)
        gate_txt = 'PUERTA ABIERTA' if gate_open else 'puerta cerrada'
        ax_crv.set_title(
            f'F_ef(θ) = (F_M·F_m) / √[(F_m·cosθ)²+(F_M·sinθ)²]'
            f'   [{gate_txt}]',
            fontsize=10, fontweight='bold', color=COLORS['warning'], pad=8)
        ax_crv.set_xlim(0, 90)
        ax_crv.set_ylim(0, 35)
        ax_crv.grid(True, alpha=0.15)
        ax_crv.legend(fontsize=9, loc='upper right',
                      facecolor=COLORS['panel'], edgecolor=COLORS['grid'],
                      framealpha=0.85, labelcolor=COLORS['text'])
        for sp in ('top', 'right'):
            ax_crv.spines[sp].set_visible(False)

        # Etiquetas de zonas
        ax_crv.text(10, 1.5, 'SEGURO\n(< 20°)',
                    fontsize=7, color=COLORS['accent'],  ha='center',
                    alpha=0.75, style='italic')
        ax_crv.text(35, 1.5, 'PRECAUCIÓN\n(20°–50°)',
                    fontsize=7, color=COLORS['warning'], ha='center',
                    alpha=0.75, style='italic')
        ax_crv.text(70, 1.5, 'PELIGROSO\n(> 50°)',
                    fontsize=7, color=COLORS['danger'],  ha='center',
                    alpha=0.75, style='italic')

        # ── Gráfico de barras comparativo ───────────────────────────
        ax_bar.clear()
        x  = np.arange(4)
        bw = 0.25

        for i, msq in enumerate(MOSQUETONES):
            Fm_i = msq['puerta_abierta_kN'] if gate_open else msq['eje_mayor_kN']
            ax_bar.bar(i - bw, Fm_i,              bw,
                       color=msq['color'], alpha=0.90, edgecolor=msq['color'], lw=1.5)
            ax_bar.bar(i,      msq['eje_menor_kN'], bw,
                       color=msq['color'], alpha=0.45, edgecolor=msq['color'], lw=1.5)
            ax_bar.bar(i + bw, msq['puerta_abierta_kN'] if not gate_open else msq['eje_menor_kN'],
                       bw,
                       color=msq['color'], alpha=0.20, edgecolor=msq['color'],
                       lw=1.5, ls='--')

        # Marcador de resistencia efectiva actual
        Fm_cur = m['puerta_abierta_kN'] if gate_open else m['eje_mayor_kN']
        ax_bar.plot(tipo_idx - bw, eff_kN, 'v', color=COLORS['warning'],
                    ms=9, zorder=5)
        ax_bar.text(tipo_idx - bw + 0.04, eff_kN + 0.5,
                    f'{eff_kN:.1f} kN',
                    fontsize=7, color=COLORS['warning'],
                    ha='center', fontweight='bold')

        ax_bar.axhline(NFPA_WORK_LOAD, color=COLORS['danger'],
                       ls='--', lw=1.2, alpha=0.75)
        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels([msq['nombre'] for msq in MOSQUETONES], fontsize=9)
        ax_bar.set_ylabel('kN', fontsize=9)
        ax_bar.set_title('Comparativa de resistencias por tipo',
                         fontsize=10, color=COLORS['text'], pad=4)
        ax_bar.set_ylim(0, 35)
        ax_bar.grid(True, axis='y', alpha=0.15)

        legend_patches = [
            Patch(facecolor=COLORS['text'], alpha=0.90,
                  label='Eje mayor' + (' (puerta abierta)' if gate_open else ' (cerrada)')),
            Patch(facecolor=COLORS['text'], alpha=0.45,
                  label='Eje menor (cerrada)'),
            Patch(facecolor=COLORS['text'], alpha=0.20,
                  label='Puerta abierta' if not gate_open else 'Eje menor ref.'),
        ]
        ax_bar.legend(handles=legend_patches, fontsize=7, loc='upper right',
                      facecolor=COLORS['panel'], edgecolor=COLORS['grid'],
                      framealpha=0.85, labelcolor=COLORS['text'])
        for sp in ('top', 'right'):
            ax_bar.spines[sp].set_visible(False)

        # ── Textos actualizables ────────────────────────────────────
        tipo_text.set_text(f'→ {m["nombre"]}')
        tipo_text.set_color(c)

        if eff_kN >= NFPA_WORK_LOAD * 1.5:
            status, st_col = '✓ SEGURO', COLORS['accent']
        elif eff_kN >= NFPA_WORK_LOAD:
            status, st_col = '⚠ PRECAUCIÓN', COLORS['warning']
        else:
            status, st_col = '✗ PELIGROSO — no apto para rescate', COLORS['danger']

        status_text.set_text(
            f'{m["nombre"]}  │  θ={ang_deg:.0f}°  │  '
            f'{"Puerta abierta" if gate_open else "Puerta cerrada"}  │  '
            f'F_ef = {eff_kN:.2f} kN  │  {status}')
        status_text.set_color(st_col)
        status_text.get_bbox_patch().set_edgecolor(st_col)
        status_text.get_bbox_patch().set_alpha(0.92)

        fig.canvas.draw_idle()

    sl_tipo.on_changed(update)
    sl_ang.on_changed(update)
    sl_gate.on_changed(update)

    # ── Textos fijos ──────────────────────────────────────────────────
    fig.text(0.5, 0.925,
             'REGLAS DE ORO:  Carga siempre en el eje mayor  ·  '
             'Puerta hacia afuera de la carga  ·  '
             'Nunca cargado lateralmente  ·  '
             'Verificar seguro cerrado antes de cargar',
             fontsize=11, ha='center', color=COLORS['danger'],
             fontweight='bold', style='italic')

    fig.text(0.02, 0.015,
             'Óvalo: simétrico, poleas  │  D Asimétrica: uso general  │  '
             'HMS/Pera: rapel y aseguramiento  │  D Rescate: sistemas de alta carga  │  '
             'Eje mayor 21–30 kN  │  Eje menor 8–10 kN  │  Puerta abierta 7–9 kN',
             fontsize=9, color=COLORS['text'], alpha=0.55, style='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
