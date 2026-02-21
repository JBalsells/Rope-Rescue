"""
╔══════════════════════════════════════════════════════════════════════╗
║     FÍSICA DEL RESCATE · Módulo 16: Personas como Anclaje           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Cuando no hay punto de anclaje fijo disponible, se puede usar       ║
║  el peso y la fricción de varias personas como sistema de anclaje.  ║
║                                                                      ║
║  Física:                                                             ║
║   • Cada persona aporta: F_persona = m_persona × g × μ_suelo        ║
║   • Personas en paralelo: F_total = N × F_persona                   ║
║   • Mínimo necesario: N_min = ceil(W × FS / F_persona)              ║
║   • FS (Factor de Seguridad) NFPA = 10:1 para vida humana           ║
║                                                                      ║
║  Posiciones de anclaje (de mayor a menor efectividad):              ║
║   • Tumbado boca arriba:  μ_efectivo ≈ 0.80  (máx. superficie)     ║
║   • Sentado con pies:     μ_efectivo ≈ 0.65  (piernas + fricción)  ║
║   • De pie inclinado:     μ_efectivo ≈ 0.45  (solo fricción)       ║
║                                                                      ║
║  Controles: Deslizadores de masa de carga, masa por persona,        ║
║             número de personas y posición de anclaje.               ║
║  Ejecutar:  python 16_personas_como_anclaje.py                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, RadioButtons
from matplotlib.patches import FancyArrowPatch, Circle, FancyBboxPatch
from config import COLORS, G, NFPA_WORK_LOAD, apply_mpl_style


# ── Posiciones de anclaje humano ─────────────────────────────────────
POSITIONS = {
    'Tumbado\n(más efectivo)': {
        'mu':   0.80,
        'color': COLORS['accent'],
        'desc': 'Tumbado boca arriba, toda la superficie del cuerpo\n'
                'contra el suelo. Máxima fricción y área de contacto.',
    },
    'Sentado\ncon pies': {
        'mu':   0.65,
        'color': COLORS['warning'],
        'desc': 'Sentado con piernas extendidas, pies apoyados.\n'
                'Combina fricción corporal con fuerza de piernas.',
    },
    'De pie\ninclinado': {
        'mu':   0.45,
        'color': COLORS['secondary'],
        'desc': 'De pie inclinado hacia atrás contra la cuerda.\n'
                'Solo fricción de botas contra el suelo.',
    },
}

SAFETY_FACTORS = {
    'Vida humana\n(NFPA 10:1)': 10.0,
    'Equipo pesado\n(5:1)':     5.0,
    'Ejercicio /\nentrenamiento (3:1)': 3.0,
}


def draw_stick_person(ax, cx, cy, scale=0.55, color='#ECEFF1', active=True,
                      position='sitting'):
    """Dibuja una figura humana simplificada en la posición de anclaje."""
    alpha = 1.0 if active else 0.25
    lw = 2.0

    if position == 'lying':
        # Tumbado boca arriba (horizontal)
        head = Circle((cx - scale * 0.55, cy), scale * 0.12,
                       fill=False, edgecolor=color, linewidth=lw, alpha=alpha)
        ax.add_patch(head)
        # Cuerpo horizontal
        ax.plot([cx - 0.42 * scale, cx + 0.55 * scale],
                [cy, cy], color=color, linewidth=lw, alpha=alpha)
        # Brazos hacia abajo (en el suelo)
        ax.plot([cx - 0.1 * scale, cx - 0.3 * scale],
                [cy, cy - 0.25 * scale], color=color, linewidth=lw, alpha=alpha)
        ax.plot([cx + 0.1 * scale, cx + 0.3 * scale],
                [cy, cy - 0.25 * scale], color=color, linewidth=lw, alpha=alpha)
        # Piernas
        ax.plot([cx + 0.55 * scale, cx + 0.75 * scale],
                [cy, cy - 0.2 * scale], color=color, linewidth=lw, alpha=alpha)
        ax.plot([cx + 0.55 * scale, cx + 0.75 * scale],
                [cy, cy + 0.2 * scale], color=color, linewidth=lw, alpha=alpha)

    elif position == 'sitting':
        # Sentado con pies extendidos
        head = Circle((cx, cy + 0.5 * scale), scale * 0.12,
                       fill=False, edgecolor=color, linewidth=lw, alpha=alpha)
        ax.add_patch(head)
        # Torso
        ax.plot([cx, cx], [cy + 0.38 * scale, cy + 0.1 * scale],
                color=color, linewidth=lw, alpha=alpha)
        # Muslos (horizontal)
        ax.plot([cx, cx + 0.45 * scale],
                [cy + 0.1 * scale, cy + 0.1 * scale],
                color=color, linewidth=lw, alpha=alpha)
        # Piernas (vertical hacia abajo)
        ax.plot([cx + 0.45 * scale, cx + 0.45 * scale],
                [cy + 0.1 * scale, cy - 0.2 * scale],
                color=color, linewidth=lw, alpha=alpha)
        # Brazos extendidos hacia la cuerda
        ax.plot([cx, cx - 0.35 * scale],
                [cy + 0.3 * scale, cy + 0.1 * scale],
                color=color, linewidth=lw, alpha=alpha)
        ax.plot([cx, cx + 0.15 * scale],
                [cy + 0.3 * scale, cy + 0.1 * scale],
                color=color, linewidth=lw, alpha=alpha)

    else:  # standing
        # De pie inclinado
        head = Circle((cx, cy + 0.7 * scale), scale * 0.12,
                       fill=False, edgecolor=color, linewidth=lw, alpha=alpha)
        ax.add_patch(head)
        # Cuerpo inclinado hacia atrás
        ax.plot([cx, cx + 0.15 * scale],
                [cy + 0.58 * scale, cy + 0.08 * scale],
                color=color, linewidth=lw, alpha=alpha)
        # Brazos al frente (sosteniendo cuerda)
        ax.plot([cx, cx - 0.35 * scale],
                [cy + 0.45 * scale, cy + 0.55 * scale],
                color=color, linewidth=lw, alpha=alpha)
        ax.plot([cx, cx - 0.15 * scale],
                [cy + 0.45 * scale, cy + 0.55 * scale],
                color=color, linewidth=lw, alpha=alpha)
        # Piernas
        ax.plot([cx + 0.15 * scale, cx - 0.05 * scale],
                [cy + 0.08 * scale, cy - 0.25 * scale],
                color=color, linewidth=lw, alpha=alpha)
        ax.plot([cx + 0.15 * scale, cx + 0.35 * scale],
                [cy + 0.08 * scale, cy - 0.25 * scale],
                color=color, linewidth=lw, alpha=alpha)


def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(17, 9.5))
    fig.suptitle('FÍSICA DEL RESCATE — Personas como Anclaje',
                 fontsize=22, fontweight='bold', color=COLORS['primary'],
                 y=0.97)
    fig.text(0.5, 0.925,
             'Cuando no hay anclaje fijo: ¿cuántas personas se necesitan '
             'para sostener la carga con seguridad?',
             fontsize=12, ha='center', color=COLORS['warning'],
             fontstyle='italic')

    # ── Ejes ─────────────────────────────────────────────────────────
    ax_scene  = fig.add_axes([0.03, 0.26, 0.44, 0.62])   # Escena principal
    ax_bar    = fig.add_axes([0.54, 0.55, 0.43, 0.35])   # Barras de fuerza
    ax_curve  = fig.add_axes([0.54, 0.26, 0.43, 0.25])   # Curva N vs masa

    # ── Widgets ──────────────────────────────────────────────────────
    ax_sl_load   = fig.add_axes([0.12, 0.17, 0.35, 0.022])
    ax_sl_mass   = fig.add_axes([0.12, 0.13, 0.35, 0.022])
    ax_sl_n      = fig.add_axes([0.12, 0.09, 0.35, 0.022])

    ax_radio_pos = fig.add_axes([0.56, 0.08, 0.18, 0.14])
    ax_radio_sf  = fig.add_axes([0.78, 0.08, 0.19, 0.14])

    sl_load = Slider(ax_sl_load, 'Masa carga (kg)',  10, 400,
                     valinit=100, color=COLORS['danger'], valstep=1)
    sl_mass = Slider(ax_sl_mass, 'Masa/persona (kg)', 40, 130,
                     valinit=75, color=COLORS['info'], valstep=1)
    sl_n    = Slider(ax_sl_n,   'Personas disponibles', 1, 20,
                     valinit=4, color=COLORS['accent'], valstep=1)

    radio_pos = RadioButtons(
        ax_radio_pos,
        list(POSITIONS.keys()),
        active=1,
        activecolor=COLORS['warning'],
    )
    radio_sf = RadioButtons(
        ax_radio_sf,
        list(SAFETY_FACTORS.keys()),
        active=0,
        activecolor=COLORS['warning'],
    )

    for rb in (radio_pos, radio_sf):
        rb.ax.set_facecolor(COLORS['panel'])
        for label in rb.labels:
            label.set_color(COLORS['text'])
            label.set_fontsize(8.5)

    ax_radio_pos.set_title('Posición', fontsize=9, color=COLORS['text'],
                           pad=3, fontweight='bold')
    ax_radio_sf.set_title('Factor seguridad', fontsize=9,
                          color=COLORS['text'], pad=3, fontweight='bold')

    def get_position_key():
        return list(POSITIONS.keys())[radio_pos.value_selected == np.array(
            list(POSITIONS.keys()))].tolist() or list(POSITIONS.keys())[1]

    def update(_=None):
        m_load  = sl_load.val
        m_person = sl_mass.val
        n_avail  = int(sl_n.val)

        pos_label = radio_pos.value_selected
        sf_label  = radio_sf.value_selected

        # Fallback si radio aún no tiene valor seleccionado
        if pos_label not in POSITIONS:
            pos_label = list(POSITIONS.keys())[1]
        if sf_label not in SAFETY_FACTORS:
            sf_label = list(SAFETY_FACTORS.keys())[0]

        mu        = POSITIONS[pos_label]['mu']
        pos_color = POSITIONS[pos_label]['color']
        sf        = SAFETY_FACTORS[sf_label]

        # Posición para la figura (nombre corto)
        pos_short = pos_label.split('\n')[0].lower()
        if 'tumb' in pos_short:
            pos_key = 'lying'
        elif 'sent' in pos_short:
            pos_key = 'sitting'
        else:
            pos_key = 'standing'

        # ── Física ───────────────────────────────────────────────────
        W_N   = m_load * G            # Peso de la carga (N)
        W_kN  = W_N / 1000.0          # Peso (kN)

        # Fuerza que puede aplicar cada persona como anclaje
        F_person_N  = m_person * G * mu   # Sin factor de seguridad
        F_person_kN = F_person_N / 1000.0

        # Personas mínimas SIN factor de seguridad
        n_min_raw = math.ceil(W_N / F_person_N)

        # Personas mínimas CON factor de seguridad
        n_min_sf = math.ceil((W_N * sf) / F_person_N)

        # Fuerza total disponible con n_avail personas
        F_total_avail_kN = n_avail * F_person_kN

        # ¿Es suficiente con las personas disponibles?
        # Para vida humana, la capacidad debe cubrir W×SF
        capacidad_requerida_kN = W_kN * sf
        es_suficiente = F_total_avail_kN >= capacidad_requerida_kN
        es_suficiente_sin_sf = F_total_avail_kN >= W_kN

        # ── ESCENA PRINCIPAL ─────────────────────────────────────────
        ax_scene.clear()
        ax_scene.set_xlim(-0.5, 10.5)
        ax_scene.set_ylim(-1.5, 5.5)
        ax_scene.set_aspect('equal')
        ax_scene.axis('off')
        ax_scene.set_title('Diagrama del Sistema de Anclaje Humano',
                            fontsize=13, fontweight='bold', pad=8)

        # Suelo
        ax_scene.fill_between([-0.5, 10.5], [-1.5, -1.5], [0, 0],
                               color=COLORS['anchor'], alpha=0.18)
        ax_scene.plot([-0.5, 10.5], [0, 0],
                      color=COLORS['anchor'], lw=2.5, alpha=0.6)

        # Borde de precipicio / punto de carga
        cliff_x = 0.6
        ax_scene.fill_between([cliff_x - 0.4, cliff_x + 0.2],
                               [-1.5, -1.5], [0, 0],
                               color='#37474F', alpha=0.9)
        ax_scene.plot([cliff_x + 0.2, cliff_x + 0.2], [-1.5, 0],
                      color='#546E7A', lw=3)

        # Punto de desviación / borde (mosquetón)
        edge_x, edge_y = cliff_x + 0.2, 0
        ax_scene.plot(edge_x, edge_y, 'o',
                      color=COLORS['warning'], ms=10, zorder=10)

        # ── Peso en el aire ──────────────────────────────────────────
        load_x, load_y = cliff_x + 0.2, -0.9
        # Rectángulo de carga
        load_w, load_h = 0.55, 0.4
        rect = FancyBboxPatch(
            (load_x - load_w / 2, load_y - load_h / 2),
            load_w, load_h,
            boxstyle='round,pad=0.05',
            facecolor=COLORS['danger'], edgecolor=COLORS['text'],
            linewidth=1.5, alpha=0.9, zorder=8)
        ax_scene.add_patch(rect)
        ax_scene.text(load_x, load_y,
                      f'{m_load:.0f} kg\n{W_kN:.2f} kN',
                      ha='center', va='center', fontsize=9,
                      fontweight='bold', color='white', zorder=9)

        # Cuerda vertical (carga al borde)
        ax_scene.plot([load_x, edge_x], [load_y + load_h / 2, edge_y],
                      color=COLORS['rope'], lw=3, zorder=7)

        # ── Cuerda horizontal (borde a personas) ─────────────────────
        n_show = min(n_avail, 10)  # Máx 10 figuras en pantalla
        person_spacing = 0.82
        rope_start_x = edge_x
        rope_end_x   = rope_start_x + 0.3 + n_show * person_spacing + 0.3

        ax_scene.plot([rope_start_x, rope_end_x], [0.25, 0.25],
                      color=COLORS['rope'], lw=3, zorder=5)

        # ── Figuras humanas ──────────────────────────────────────────
        for i in range(n_show):
            px = rope_start_x + 0.55 + i * person_spacing
            py = 0

            is_active = (i < n_avail)
            # Color según si son suficientes o no
            if i < n_min_sf:
                p_color = pos_color
            else:
                p_color = COLORS['grid']

            draw_stick_person(ax_scene, px, py, scale=0.48,
                              color=p_color, active=is_active,
                              position=pos_key)

            # Número de persona
            ax_scene.text(px, py - 0.55, f'P{i+1}',
                          ha='center', fontsize=7,
                          color=p_color if is_active else COLORS['grid'],
                          alpha=1.0 if is_active else 0.3)

        if n_avail > n_show:
            ax_scene.text(rope_end_x - 0.1, 0.5,
                          f'+{n_avail - n_show}\nmás',
                          fontsize=8, color=COLORS['text'],
                          ha='center', alpha=0.7)

        # ── Panel de resultado ────────────────────────────────────────
        result_color = COLORS['accent'] if es_suficiente else COLORS['danger']
        if es_suficiente_sin_sf and not es_suficiente:
            result_color = COLORS['warning']

        if es_suficiente:
            status_txt = f'✓ SUFICIENTE  ({n_avail} pers. ≥ {n_min_sf} req.)'
        elif es_suficiente_sin_sf:
            status_txt = f'⚠ SIN MARGEN DE SEGURIDAD ({n_avail} pers.)'
        else:
            status_txt = f'✗ INSUFICIENTE ({n_avail} pers. < {n_min_sf} req.)'

        ax_scene.text(5.2, 4.8, status_txt,
                      ha='center', fontsize=12, fontweight='bold',
                      color=result_color,
                      bbox=dict(boxstyle='round,pad=0.45',
                                facecolor=COLORS['bg'],
                                edgecolor=result_color, alpha=0.93),
                      zorder=15)

        # Datos numéricos
        info = (
            f'Peso carga:       {W_kN:.3f} kN\n'
            f'μ ({pos_label.split(chr(10))[0]}):  {mu:.2f}\n'
            f'Fuerza/persona:  {F_person_kN:.3f} kN\n'
            f'Req. sin FS:     {n_min_raw} personas\n'
            f'Req. con FS {sf:.0f}:1   {n_min_sf} personas\n'
            f'F total disponible: {F_total_avail_kN:.2f} kN'
        )
        ax_scene.text(5.2, 3.0, info,
                      ha='center', fontsize=9.5,
                      color=COLORS['text'],
                      fontfamily='monospace',
                      bbox=dict(boxstyle='round,pad=0.5',
                                facecolor=COLORS['panel'],
                                edgecolor=COLORS['grid'], alpha=0.92),
                      zorder=15)

        # ── GRÁFICO DE BARRAS DE FUERZA ───────────────────────────────
        ax_bar.clear()

        bar_labels = [
            f'Carga\n({m_load:.0f} kg)',
            f'Fuerza total\n({n_avail} personas)',
            f'Req. sin FS\n({n_min_raw} pers.)',
            f'Req. con FS {sf:.0f}:1\n({n_min_sf} pers.)',
        ]
        bar_vals = [
            W_kN,
            F_total_avail_kN,
            n_min_raw * F_person_kN,
            n_min_sf * F_person_kN,
        ]
        bar_cols = [
            COLORS['danger'],
            result_color,
            COLORS['warning'],
            COLORS['info'],
        ]

        bars = ax_bar.barh(bar_labels, bar_vals, color=bar_cols,
                           height=0.5, alpha=0.85,
                           edgecolor=COLORS['bg'], linewidth=0.5)
        for bar, v in zip(bars, bar_vals):
            ax_bar.text(bar.get_width() + max(bar_vals) * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        f'{v:.2f} kN',
                        va='center', fontsize=9.5, fontweight='bold',
                        color=COLORS['text'])

        # Línea de la carga
        ax_bar.axvline(W_kN, color=COLORS['danger'], ls='--',
                       lw=1.5, alpha=0.6, label=f'Peso carga ({W_kN:.2f} kN)')

        ax_bar.set_xlabel('Fuerza (kN)', fontsize=10)
        ax_bar.set_title(f'Comparativa de Fuerzas  (F/persona = {F_person_kN:.3f} kN)',
                          fontsize=11, fontweight='bold', pad=6)
        ax_bar.set_xlim(0, max(bar_vals) * 1.28)
        ax_bar.legend(fontsize=8, loc='lower right',
                      facecolor=COLORS['bg'], edgecolor=COLORS['grid'])
        ax_bar.grid(axis='x', alpha=0.13)
        for spine in ('top', 'right'):
            ax_bar.spines[spine].set_visible(False)

        # ── CURVA N_min vs MASA CARGA ─────────────────────────────────
        ax_curve.clear()
        masses = np.linspace(10, 400, 400)
        n_min_curve_noSF = np.ceil((masses * G) / F_person_N)
        n_min_curve_sf   = np.ceil((masses * G * sf) / F_person_N)

        ax_curve.plot(masses, n_min_curve_noSF,
                      color=COLORS['warning'], lw=2, ls='--',
                      label=f'Sin FS (μ={mu:.2f})')
        ax_curve.plot(masses, n_min_curve_sf,
                      color=COLORS['info'], lw=2,
                      label=f'Con FS {sf:.0f}:1')
        ax_curve.axhline(n_avail, color=COLORS['accent'], ls=':',
                         lw=1.5, alpha=0.7,
                         label=f'Disponibles: {n_avail}')

        ax_curve.axvline(m_load, color=COLORS['danger'], ls='--',
                         lw=1.2, alpha=0.6)
        ax_curve.plot(m_load, n_min_sf, 'o', color=COLORS['info'],
                      ms=8, zorder=10)

        ax_curve.set_xlabel('Masa de la carga (kg)', fontsize=10)
        ax_curve.set_ylabel('N° personas mínimas', fontsize=10)
        ax_curve.set_title('Personas necesarias según masa de la carga',
                            fontsize=10, fontweight='bold', pad=5)
        ax_curve.set_xlim(10, 400)
        ax_curve.set_ylim(0, max(n_min_curve_sf.max(), n_avail + 1) + 1)
        ax_curve.legend(fontsize=8, loc='upper left',
                        facecolor=COLORS['bg'], edgecolor=COLORS['grid'])
        ax_curve.grid(True, alpha=0.12)
        for spine in ('top', 'right'):
            ax_curve.spines[spine].set_visible(False)

        fig.canvas.draw_idle()

    # Conectar widgets
    sl_load.on_changed(update)
    sl_mass.on_changed(update)
    sl_n.on_changed(update)
    radio_pos.on_clicked(update)
    radio_sf.on_clicked(update)

    # ── Textos informativos fijos ─────────────────────────────────────
    fig.text(0.02, 0.015,
             '💡 F_persona = m_persona × g × μ_suelo  │  '
             'F_total = N × F_persona  │  '
             'N_min = ⌈(W × FS) / F_persona⌉  │  '
             'FS NFPA vida humana = 10:1',
             fontsize=9, color=COLORS['text'], alpha=0.6, fontstyle='italic')
    fig.text(0.02, 0.04,
             '⚠ Regla práctica: 2–3 personas por cada 100 kg de carga '
             '(posición sentada, suelo seco). '
             'Siempre aplicar factor de seguridad 10:1 en rescate con vida humana.',
             fontsize=9, color=COLORS['warning'], alpha=0.75, fontstyle='italic')

    update()
    plt.show()


if __name__ == '__main__':
    main()
