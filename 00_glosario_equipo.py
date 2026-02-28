"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 00: Glosario de Equipo Básico     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Glosario visual interactivo del equipo fundamental de rescate       ║
║  con cuerdas, diseñado para personas sin conocimiento previo.        ║
║                                                                      ║
║  Haz click en cualquier pieza de equipo para ver sus               ║
║  características técnicas y notas de seguridad.                      ║
║                                                                      ║
║  Ejecutar:  python 00_glosario_equipo.py                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
from config import COLORS, G, ROPE_STATIC_MBS, ROPE_DYNAMIC_MBS, NFPA_WORK_LOAD, apply_mpl_style


# ── Datos de los 8 ítems de equipo ────────────────────────────────────

EQUIPO = [
    {
        'nombre':      'Cuerda Estática',
        'categoria':   'Cuerdas y Accesorios',
        'descripcion': (
            'Cuerda de núcleo trenzado (kernmantle) diseñada para sistemas\n'
            'de rescate donde NO se esperan caídas. Su rigidez transmite\n'
            'la fuerza de forma eficiente hacia los anclajes.'
        ),
        'specs': [
            ('Diametro',       '10–11 mm'),
            ('MBS (rotura)',   f'{ROPE_STATIC_MBS:.0f} kN'),
            ('Elongacion',     '< 2%'),
            ('Norma',          'EN 1891 Tipo A'),
            ('Uso principal',  'Rappel, rescate, izar'),
        ],
        'seguridad': (
            'Nunca usar en escalada con caidas posibles.\n'
            'La baja elongacion genera fuerzas de choque muy altas.'
        ),
        'color': COLORS['rope'],
    },
    {
        'nombre':      'Cuerda Dinamica',
        'categoria':   'Cuerdas y Accesorios',
        'descripcion': (
            'Cuerda con alta capacidad de elongacion que absorbe la energia\n'
            'de una caida, reduciendo la fuerza de choque sobre el escalador\n'
            'y los anclajes. Imprescindible en escalada deportiva y de pared.'
        ),
        'specs': [
            ('Diametro',       '9–11 mm'),
            ('MBS (rotura)',   f'{ROPE_DYNAMIC_MBS:.0f} kN'),
            ('Elongacion',     '20–40%'),
            ('Norma',          'EN 892 / UIAA'),
            ('Uso principal',  'Escalada, factor de caida'),
        ],
        'seguridad': (
            'La cuerda dinamica NO es optima para rescate: su elasticidad\n'
            'dificulta el control preciso al izar o descender cargas.'
        ),
        'color': COLORS['accent'],
    },
    {
        'nombre':      'Mosqueton HMS',
        'categoria':   'Conectores',
        'descripcion': (
            'Mosqueton de forma de pera (HMS = Halbmastwurf Sicherung).\n'
            'Su forma asimetrica permite usar el nudo munter directamente\n'
            'para asegurar y rapelar con friccion controlada.'
        ),
        'specs': [
            ('Eje mayor',      '23 kN'),
            ('Eje menor',      '8 kN'),
            ('Con seguro',     '23 kN'),
            ('Norma',          'EN 12275 / NFPA'),
            ('Uso principal',  'Aseguramiento, rapel'),
        ],
        'seguridad': (
            'Cargar SIEMPRE en el eje mayor. La resistencia lateral\n'
            'es hasta 3x menor. Verificar seguro cerrado antes de cargar.'
        ),
        'color': COLORS['warning'],
    },
    {
        'nombre':      'Arnes de Rescate',
        'categoria':   'Equipos de Proteccion Personal',
        'descripcion': (
            'Arnes de cuerpo completo o de asiento certificado para rescate.\n'
            'Distribuye la carga entre piernas y cintura, manteniendo al\n'
            'rescatista en posicion vertical incluso inconsciente.'
        ),
        'specs': [
            ('Certificacion',  'NFPA 1983 / EN 361'),
            ('Anclajes',       'Pecho + dorsal'),
            ('Carga maxima',   '140 kg'),
            ('Test de caida',  '6 kN pico'),
            ('Uso principal',  'Rescate, izar victimas'),
        ],
        'seguridad': (
            'Inspeccionar antes de cada uso. Reemplazar despues de\n'
            'cualquier caida o si tiene mas de 10 anos de uso.'
        ),
        'color': COLORS['info'],
    },
    {
        'nombre':      'Polea de Rescate',
        'categoria':   'Sistemas de Ventaja Mecanica',
        'descripcion': (
            'Polea de alta eficiencia con rodamiento de bolas, disenada para\n'
            'sistemas de polipasto y rescate. Minimiza la perdida de fuerza\n'
            'por friccion al redirigir la cuerda.'
        ),
        'specs': [
            ('Eficiencia',     '95%'),
            ('Carga maxima',   '36 kN'),
            ('Diametro sheave', '50–55 mm'),
            ('Norma',          'EN 12278 / NFPA'),
            ('Uso principal',  'Sistemas de ventaja mecanica'),
        ],
        'seguridad': (
            'Una polea sucia o danada puede bajar la eficiencia al 60–70%.\n'
            'Lubricar el rodamiento y revisar el pin antes de cada uso.'
        ),
        'color': COLORS['primary'],
    },
    {
        'nombre':      'Dispositivo de Descenso',
        'categoria':   'Control de Descenso',
        'descripcion': (
            'Dispositivo en forma de ocho (figura-8) o tubo que genera\n'
            'friccion para controlar la velocidad de descenso. Simple,\n'
            'robusto y sin partes moviles que puedan fallar.'
        ),
        'specs': [
            ('Tipo',           'Figura-8 / tubo'),
            ('Friccion',       'Ajustable por posicion'),
            ('Carga maxima',   '200 kg'),
            ('Material',       'Aluminio aeronautico'),
            ('Uso principal',  'Rapel, descenso de cargas'),
        ],
        'seguridad': (
            'Siempre usar con mano de freno activa. Nunca soltar la cuerda\n'
            'del lado de salida. Compatible con cuerda de 10–11 mm.'
        ),
        'color': COLORS['secondary'],
    },
    {
        'nombre':      'Prusik / Nudo de Friccion',
        'categoria':   'Nudos de Bloqueo',
        'descripcion': (
            'Nudo de friccion que se desliza libremente sin carga pero\n'
            'se bloquea instantaneamente bajo tension. Actua como seguro\n'
            'de vida en sistemas de ascenso y descenso.'
        ),
        'specs': [
            ('Cuerda prusik',  '6 mm diametro'),
            ('Cuerda principal', '10–11 mm'),
            ('Activacion',     'Bajo carga automatica'),
            ('Vueltas',        '3–4 vueltas'),
            ('Uso principal',  'Seguro de vida, ascenso'),
        ],
        'seguridad': (
            'El prusik puede fallar por calor (friccion). En descensos\n'
            'largos, usar dispositivos mecanicos certificados (Tibloc, Ropeman).'
        ),
        'color': '#CE93D8',
    },
    {
        'nombre':      'Casco de Rescate',
        'categoria':   'Equipos de Proteccion Personal',
        'descripcion': (
            'Casco de alta resistencia disenado para proteger contra impactos\n'
            'de objetos en caida y golpes laterales. Equipado con sistema de\n'
            'suspension interior para absorber energia de impacto.'
        ),
        'specs': [
            ('Norma',          'EN 397 / NFPA 1951'),
            ('Resistencia',    '5 J impacto lateral'),
            ('Penetracion',    'Clase P'),
            ('Vida util',      '5 anos desde fabricacion'),
            ('Uso principal',  'Toda operacion de rescate'),
        ],
        'seguridad': (
            'Reemplazar inmediatamente tras cualquier impacto severo,\n'
            'aunque no haya danio visible. El EPS interior puede estar roto.'
        ),
        'color': COLORS['anchor'],
    },
]

# Disposicion en grilla 4x2 (columna, fila)
GRID_COLS = 4
GRID_ROWS = 2


# ── Funciones de dibujo de cada pieza de equipo ───────────────────────

def _draw_cuerda_estatica(ax, cx, cy, color):
    """Cilindro horizontal grueso (cuerda estatica)."""
    # Cuerpo de la cuerda
    rect = mpatches.FancyBboxPatch(
        (cx - 0.38, cy - 0.07), 0.76, 0.14,
        boxstyle='round,pad=0.02',
        facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.9
    )
    ax.add_patch(rect)
    # Extremos redondeados (tapas del cilindro)
    for ex in [cx - 0.38, cx + 0.38]:
        c = Circle((ex, cy), 0.07, facecolor=color,
                   edgecolor='white', linewidth=1.5, alpha=0.9)
        ax.add_patch(c)
    # Lineas de trenzado
    for i in range(6):
        xd = cx - 0.30 + i * 0.12
        ax.plot([xd, xd + 0.06], [cy + 0.07, cy - 0.07],
                color='white', lw=0.8, alpha=0.4)
    # Etiqueta de diametro
    ax.text(cx, cy + 0.18, '11 mm',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_cuerda_dinamica(ax, cx, cy, color):
    """Cilindro horizontal mas delgado con patron de elongacion."""
    # Cuerpo mas delgado
    rect = mpatches.FancyBboxPatch(
        (cx - 0.36, cy - 0.055), 0.72, 0.11,
        boxstyle='round,pad=0.015',
        facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.9
    )
    ax.add_patch(rect)
    for ex in [cx - 0.36, cx + 0.36]:
        c = Circle((ex, cy), 0.055, facecolor=color,
                   edgecolor='white', linewidth=1.5, alpha=0.9)
        ax.add_patch(c)
    # Patron de espiral (indica dinamismo)
    t = np.linspace(0, 4 * np.pi, 60)
    xs = cx - 0.28 + (0.56 / (4 * np.pi)) * t
    ys = cy + 0.035 * np.sin(t)
    ax.plot(xs, ys, color='white', lw=0.7, alpha=0.5)
    ax.text(cx, cy + 0.18, '10 mm  ~30% elong.',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_mosqueton_hms(ax, cx, cy, color):
    """Forma de pera (HMS) dibujada con arcos."""
    # Espina izquierda
    ax.plot([cx - 0.18, cx - 0.18], [cy - 0.30, cy + 0.30],
            color=color, lw=5, solid_capstyle='round', zorder=4)
    # Arco derecho tipo pera (radio variable)
    t = np.linspace(-np.pi / 2, np.pi / 2, 80)
    r_top, r_bot = 0.26, 0.15
    r_interp = r_bot + (r_top - r_bot) * (np.sin(t) + 1) / 2
    xp = cx + 0.00 + r_interp * np.cos(t)
    yp = cy + 0.30 * np.sin(t)
    ax.plot(xp, yp, color=color, lw=4.5, solid_capstyle='round', zorder=4)
    # Conexiones superior e inferior
    ax.plot([cx - 0.18, xp[0]],  [yp[0],  yp[0]],  color=color, lw=4.5, zorder=4)
    ax.plot([cx - 0.18, xp[-1]], [yp[-1], yp[-1]], color=color, lw=4.5, zorder=4)
    # Puerta (cerrojo)
    ax.plot([cx - 0.06, cx - 0.06], [cy - 0.30, cy + 0.30],
            color=color, lw=2.5, solid_capstyle='round', alpha=0.75, zorder=4)
    # Punto de carga
    ax.plot([cx], [cy - 0.30], 'D', color='white', ms=4, zorder=5)


def _draw_arnes(ax, cx, cy, color):
    """Silueta simplificada de arnes con cintas."""
    # Cuerpo central (trapecio)
    body = mpatches.FancyBboxPatch(
        (cx - 0.14, cy - 0.18), 0.28, 0.38,
        boxstyle='round,pad=0.02',
        facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.5
    )
    ax.add_patch(body)
    # Cintas de pierna izquierda y derecha
    for sx in [-0.10, 0.10]:
        leg = mpatches.FancyBboxPatch(
            (cx + sx - 0.055, cy - 0.38), 0.11, 0.22,
            boxstyle='round,pad=0.01',
            facecolor=color, edgecolor='white', linewidth=1.2, alpha=0.7
        )
        ax.add_patch(leg)
    # Hombros (cintas superiores)
    for sx in [-0.12, 0.12]:
        ax.plot([cx + sx, cx + sx * 1.8], [cy + 0.20, cy + 0.30],
                color=color, lw=3.5, solid_capstyle='round')
    # Punto de anclaje dorsal (circulo)
    c = Circle((cx, cy + 0.05), 0.055,
               facecolor=COLORS['warning'], edgecolor='white', linewidth=1.5)
    ax.add_patch(c)
    ax.text(cx, cy + 0.05, 'D', ha='center', va='center',
            fontsize=6, fontweight='bold', color='black')
    ax.text(cx, cy - 0.48, 'Anclaje dorsal',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_polea(ax, cx, cy, color):
    """Circulo con eje central y ranura de cuerda."""
    # Carcasa exterior
    outer = Circle((cx, cy), 0.28,
                   facecolor=COLORS['panel'], edgecolor=color, linewidth=3)
    ax.add_patch(outer)
    # Rodamiento interior
    inner = Circle((cx, cy), 0.16,
                   facecolor=COLORS['bg'], edgecolor=color, linewidth=1.8)
    ax.add_patch(inner)
    # Eje central
    inner2 = Circle((cx, cy), 0.05,
                    facecolor=color, edgecolor='white', linewidth=1)
    ax.add_patch(inner2)
    # Agujero de anclaje (arriba)
    anc = Circle((cx, cy + 0.28), 0.04,
                 facecolor=COLORS['bg'], edgecolor=COLORS['anchor'], linewidth=1.5)
    ax.add_patch(anc)
    # Cuerda pasando por la polea
    ax.plot([cx - 0.10, cx - 0.28], [cy + 0.28, cy + 0.48],
            color=COLORS['rope'], lw=2.5, solid_capstyle='round')
    ax.plot([cx + 0.10, cx + 0.28], [cy + 0.28, cy + 0.48],
            color=COLORS['rope'], lw=2.5, solid_capstyle='round')
    ax.text(cx, cy - 0.40, '95% efic.',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_figura8(ax, cx, cy, color):
    """Dispositivo de descenso forma de figura-8."""
    # Anillo superior (pequeno)
    top = Circle((cx, cy + 0.18), 0.12,
                 facecolor='none', edgecolor=color, linewidth=5)
    ax.add_patch(top)
    # Anillo inferior (grande)
    bot = Circle((cx, cy - 0.12), 0.19,
                 facecolor='none', edgecolor=color, linewidth=5)
    ax.add_patch(bot)
    # Conexion entre los dos anillos (cuello)
    ax.plot([cx - 0.05, cx - 0.05], [cy + 0.06, cy + 0.06],
            color=color, lw=5)
    ax.plot([cx + 0.05, cx + 0.05], [cy + 0.06, cy + 0.06],
            color=color, lw=5)
    # Agujero de mosqueton (arriba del anillo superior)
    hole = Circle((cx, cy + 0.18), 0.055,
                  facecolor=COLORS['bg'], edgecolor='white', linewidth=1.2)
    ax.add_patch(hole)
    ax.text(cx, cy - 0.38, 'Figura-8',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_prusik(ax, cx, cy, color):
    """Nudo prusik: cuerda delgada enrollada sobre cuerda principal."""
    # Cuerda principal (gruesa, vertical)
    ax.plot([cx, cx], [cy - 0.35, cy + 0.35],
            color=COLORS['rope'], lw=6, solid_capstyle='round', alpha=0.85, zorder=3)
    # Cuerda de prusik (delgada) enrollada en 3 vueltas
    n_vueltas = 3
    for i in range(n_vueltas):
        y_offset = cy - 0.12 + i * 0.12
        # Arco izquierdo
        t_left = np.linspace(np.pi / 2, 3 * np.pi / 2, 40)
        xl = cx + 0.09 * np.cos(t_left)
        yl = y_offset + 0.055 * np.sin(t_left)
        ax.plot(xl, yl, color=color, lw=3.5, solid_capstyle='round', zorder=4)
        # Lado derecho (linea recta que cruza)
        ax.plot([cx + 0.00, cx + 0.09], [y_offset + 0.055, y_offset + 0.055],
                color=color, lw=3.5, zorder=4)
        ax.plot([cx + 0.00, cx + 0.09], [y_offset - 0.055, y_offset - 0.055],
                color=color, lw=3.5, zorder=4)
    # Presilla de mosqueton (parte inferior del bucle)
    loop = Circle((cx, cy - 0.38), 0.065,
                  facecolor='none', edgecolor=color, linewidth=2.5, zorder=5)
    ax.add_patch(loop)
    ax.text(cx, cy + 0.45, '6 mm',
            ha='center', va='bottom', fontsize=7,
            color=color, fontweight='bold')


def _draw_casco(ax, cx, cy, color):
    """Casco de rescate: forma semicircular con ala y suspension."""
    # Casquete exterior (semicirculo)
    t = np.linspace(0, np.pi, 80)
    xs = cx + 0.32 * np.cos(t)
    ys = cy + 0.28 * np.sin(t)
    ax.fill_between(xs, cy, ys, facecolor=color, alpha=0.85, zorder=3)
    ax.plot(xs, ys, color='white', lw=2, zorder=4)
    # Ala lateral (borde)
    ax.plot([cx - 0.38, cx + 0.38], [cy, cy],
            color=color, lw=5, solid_capstyle='round', zorder=4)
    # Linea de vision frontal
    ax.plot([cx - 0.28, cx + 0.28], [cy + 0.02, cy + 0.02],
            color='white', lw=1, alpha=0.5, zorder=5)
    # Sistema de suspension (interior)
    for sx in [-0.15, 0.0, 0.15]:
        ax.plot([cx + sx, cx + sx], [cy, cy + 0.20],
                color='white', lw=0.8, alpha=0.35, zorder=5)
    ax.plot([cx - 0.15, cx + 0.15], [cy + 0.10, cy + 0.10],
            color='white', lw=0.8, alpha=0.35, zorder=5)
    # Texto de norma
    ax.text(cx, cy + 0.12, 'EN', ha='center', va='center',
            fontsize=6, color='white', fontweight='bold', alpha=0.6, zorder=6)
    ax.text(cx, cy - 0.14, '5 J  |  5 anos',
            ha='center', va='top', fontsize=7,
            color=color, fontweight='bold')


# Mapa de funciones de dibujo, en el mismo orden que EQUIPO
_DRAW_FNS = [
    _draw_cuerda_estatica,
    _draw_cuerda_dinamica,
    _draw_mosqueton_hms,
    _draw_arnes,
    _draw_polea,
    _draw_figura8,
    _draw_prusik,
    _draw_casco,
]


# ── Dibujado de la grilla y el panel de informacion ───────────────────

def _cell_bounds(idx):
    """Devuelve (x0, y0, w, h) en coordenadas de figura del item idx."""
    col = idx % GRID_COLS
    row = idx // GRID_COLS
    # Panel izquierdo: 0.02–0.62, dividido en 4 columnas x 2 filas
    panel_x0, panel_x1 = 0.03, 0.62
    panel_y0, panel_y1 = 0.12, 0.88
    cell_w = (panel_x1 - panel_x0) / GRID_COLS
    cell_h = (panel_y1 - panel_y0) / GRID_ROWS
    x0 = panel_x0 + col * cell_w
    # Fila 0 = arriba, fila 1 = abajo
    y0 = panel_y1 - (row + 1) * cell_h
    return x0, y0, cell_w, cell_h


def _dibujar_celda(fig, ax_grid, idx, selected):
    """Dibuja la celda de un item en el eje de la grilla."""
    item = EQUIPO[idx]
    col = idx % GRID_COLS
    row = idx // GRID_COLS

    # Coordenadas de celda (en espacio de datos del ax_grid, 0–4 x 0–2)
    cx_data = col + 0.5
    cy_data = (GRID_ROWS - 1 - row) + 0.5   # fila 0 arriba

    # Fondo de celda
    border_color = COLORS['warning'] if selected else COLORS['grid']
    border_lw    = 2.5 if selected else 1.2
    cell_bg = FancyBboxPatch(
        (col + 0.04, (GRID_ROWS - 1 - row) + 0.04),
        0.92, 0.92,
        boxstyle='round,pad=0.02',
        facecolor=COLORS['panel'],
        edgecolor=border_color,
        linewidth=border_lw,
        transform=ax_grid.transData,
        zorder=2
    )
    ax_grid.add_patch(cell_bg)

    # Dibujar el equipo (en axes temporales superpuestos)
    # Usamos ax_grid con coordenadas de datos normalizadas al area de la celda
    draw_fn = _DRAW_FNS[idx]
    draw_fn(ax_grid, cx_data, cy_data + 0.10, item['color'])

    # Nombre del item (abajo de la celda)
    ax_grid.text(cx_data, (GRID_ROWS - 1 - row) + 0.10,
                 item['nombre'],
                 ha='center', va='bottom',
                 fontsize=9.5, fontweight='bold',
                 color=COLORS['warning'] if selected else COLORS['text'],
                 zorder=6)


def _dibujar_panel_info(ax_info, idx):
    """Dibuja el panel de informacion derecho para el item seleccionado."""
    ax_info.clear()
    ax_info.set_xlim(0, 1)
    ax_info.set_ylim(0, 1)
    ax_info.axis('off')

    if idx is None:
        ax_info.text(0.5, 0.55,
                     '<- Selecciona\nun elemento',
                     ha='center', va='center',
                     fontsize=16, color=COLORS['text'],
                     alpha=0.4, fontstyle='italic')
        ax_info.text(0.5, 0.40,
                     'Haz click en cualquier\npieza del panel izquierdo',
                     ha='center', va='center',
                     fontsize=11, color=COLORS['text'], alpha=0.3)
        return

    item = EQUIPO[idx]
    c = item['color']

    y = 0.95

    # Nombre principal
    ax_info.text(0.5, y, item['nombre'],
                 ha='center', va='top',
                 fontsize=18, fontweight='bold', color=c)
    y -= 0.08

    # Categoria
    ax_info.text(0.5, y, item['categoria'],
                 ha='center', va='top',
                 fontsize=10, color=COLORS['text'], alpha=0.65, fontstyle='italic')
    y -= 0.04

    # Separador
    ax_info.plot([0.05, 0.95], [y, y], color=c, lw=1.5, alpha=0.5)
    y -= 0.06

    # Descripcion
    ax_info.text(0.05, y, 'Descripcion:',
                 ha='left', va='top',
                 fontsize=10, fontweight='bold', color=COLORS['primary'])
    y -= 0.05

    ax_info.text(0.05, y, item['descripcion'],
                 ha='left', va='top',
                 fontsize=9, color=COLORS['text'],
                 alpha=0.85, wrap=True,
                 linespacing=1.5)
    y -= 0.18

    # Separador
    ax_info.plot([0.05, 0.95], [y, y], color=COLORS['grid'], lw=0.8, alpha=0.5)
    y -= 0.05

    # Especificaciones tecnicas
    ax_info.text(0.05, y, 'Especificaciones tecnicas:',
                 ha='left', va='top',
                 fontsize=10, fontweight='bold', color=COLORS['primary'])
    y -= 0.055

    for param, valor in item['specs']:
        # Fondo de fila alternado
        row_bg = FancyBboxPatch(
            (0.04, y - 0.03), 0.92, 0.040,
            boxstyle='round,pad=0.005',
            facecolor=COLORS['panel'],
            edgecolor='none', alpha=0.6,
            transform=ax_info.transData
        )
        ax_info.add_patch(row_bg)
        ax_info.text(0.08, y - 0.010, param + ':',
                     ha='left', va='center',
                     fontsize=9, color=COLORS['text'], alpha=0.70)
        ax_info.text(0.92, y - 0.010, valor,
                     ha='right', va='center',
                     fontsize=9, fontweight='bold', color=c)
        y -= 0.050

    y -= 0.02

    # Separador
    ax_info.plot([0.05, 0.95], [y, y], color=COLORS['grid'], lw=0.8, alpha=0.5)
    y -= 0.05

    # Nota de seguridad
    seguridad_bg = FancyBboxPatch(
        (0.03, y - 0.13), 0.94, 0.14,
        boxstyle='round,pad=0.01',
        facecolor=COLORS['danger'],
        edgecolor=COLORS['danger'],
        linewidth=1.5,
        alpha=0.15,
        transform=ax_info.transData
    )
    ax_info.add_patch(seguridad_bg)

    ax_info.text(0.06, y - 0.015,
                 'NOTA DE SEGURIDAD:',
                 ha='left', va='top',
                 fontsize=9, fontweight='bold', color=COLORS['danger'])
    ax_info.text(0.06, y - 0.050,
                 item['seguridad'],
                 ha='left', va='top',
                 fontsize=8.5, color=COLORS['text'],
                 alpha=0.88, linespacing=1.45)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()

    fig = plt.figure(figsize=(19, 10))
    fig.suptitle('FISICA DEL RESCATE — Glosario de Equipo Basico',
                 fontsize=20, fontweight='bold', color=COLORS['primary'], y=0.975)
    fig.text(0.5, 0.934,
             'Haz click en cualquier pieza de equipo para ver sus caracteristicas',
             fontsize=11, ha='center', color=COLORS['warning'], fontstyle='italic')

    # ── Eje de la grilla (panel izquierdo) ────────────────────────────
    ax_grid = fig.add_axes([0.02, 0.10, 0.62, 0.80])
    ax_grid.set_xlim(0, GRID_COLS)
    ax_grid.set_ylim(0, GRID_ROWS)
    ax_grid.axis('off')
    ax_grid.set_facecolor(COLORS['bg'])

    # ── Eje del panel de informacion (panel derecho) ──────────────────
    ax_info = fig.add_axes([0.65, 0.10, 0.33, 0.80])
    ax_info.set_facecolor(COLORS['panel'])
    for sp in ax_info.spines.values():
        sp.set_edgecolor(COLORS['grid'])
        sp.set_linewidth(1.5)

    # Estado de seleccion
    state = {'selected': None}

    def _redibujar():
        ax_grid.clear()
        ax_grid.set_xlim(0, GRID_COLS)
        ax_grid.set_ylim(0, GRID_ROWS)
        ax_grid.axis('off')
        for i in range(len(EQUIPO)):
            _dibujar_celda(fig, ax_grid, i, state['selected'] == i)
        _dibujar_panel_info(ax_info, state['selected'])
        fig.canvas.draw_idle()

    def on_click(event):
        # Solo clicks en el eje de la grilla
        if event.inaxes != ax_grid:
            return
        if event.xdata is None or event.ydata is None:
            return

        xd = event.xdata
        yd = event.ydata

        # Determinar celda clickeada
        col_click = int(xd)
        row_click = int(GRID_ROWS - 1 - int(yd))  # fila 0 = arriba

        if 0 <= col_click < GRID_COLS and 0 <= row_click < GRID_ROWS:
            idx = row_click * GRID_COLS + col_click
            if 0 <= idx < len(EQUIPO):
                if state['selected'] == idx:
                    state['selected'] = None  # deseleccionar al volver a clickear
                else:
                    state['selected'] = idx
                _redibujar()

    fig.canvas.mpl_connect('button_press_event', on_click)

    # ── Nota al pie ───────────────────────────────────────────────────
    fig.text(0.02, 0.018,
             'MBS = Minimum Breaking Strength (Resistencia Minima de Rotura)  |  '
             'NFPA = National Fire Protection Association  |  '
             'EN = European Norm',
             fontsize=8.5, color=COLORS['text'], alpha=0.50, fontstyle='italic')

    # Dibujo inicial
    _redibujar()
    plt.show()


if __name__ == '__main__':
    main()
