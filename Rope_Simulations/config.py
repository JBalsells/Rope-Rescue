"""
Configuración compartida para todos los scripts de Física del Rescate.
Paleta de colores, constantes físicas y utilidades comunes.
"""

# ── Constantes Físicas ────────────────────────────────────────────────
G = 9.81          # Aceleración gravitacional (m/s²)
ROPE_STATIC_MBS = 30.0   # Resistencia mínima de rotura cuerda estática 11mm (kN)
ROPE_DYNAMIC_MBS = 24.0  # Resistencia mínima de rotura cuerda dinámica 10mm (kN)
NFPA_WORK_LOAD = 13.5    # Límite carga de trabajo NFPA (kN) para cuerdas de rescate
UIAA_MAX_IMPACT = 12.0   # Fuerza de choque máxima UIAA (kN)

# ── Paleta de colores — terminal verde fósforo (Matplotlib) ───────────
# Base monocroma verde sobre negro terminal. Se conservan ámbar y rojo
# SOLO para el semáforo de seguridad (precaución / peligro), porque
# transmiten significado; en un CRT verde+ámbar además es de época.
COLORS = {
    'bg':        '#0a0f0a',   # negro terminal
    'panel':     '#0e1a0e',   # panel verde muy oscuro
    'primary':   '#00ff33',   # verde fósforo brillante (líneas/acento)
    'secondary': '#ffb000',   # ámbar (acento secundario CRT)
    'accent':    '#00cc22',   # verde = SEGURO
    'warning':   '#ffcc00',   # ámbar-amarillo = PRECAUCIÓN
    'danger':    '#ff3333',   # rojo = PELIGROSO
    'info':      '#00d9a0',   # verde-teal (segunda serie de datos)
    'text':      '#88cc88',   # verde apagado para texto
    'grid':      '#1a2e1a',   # grilla verde sutil
    'rope':      '#aaff44',   # lima (cuerda, distinta del primary)
    'anchor':    '#5c8a5c',   # verde-gris para estructura/anclajes
}

# ── Paleta de colores (Pygame, tuplas RGB equivalentes) ───────────────
PG_COLORS = {
    'bg':        (10, 15, 10),
    'panel':     (14, 26, 14),
    'primary':   (0, 255, 51),
    'secondary': (255, 176, 0),
    'accent':    (0, 204, 34),
    'warning':   (255, 204, 0),
    'danger':    (255, 51, 51),
    'info':      (0, 217, 160),
    'text':      (136, 204, 136),
    'grid':      (26, 46, 26),
    'rope':      (170, 255, 68),
    'anchor':    (92, 138, 92),
    'white':     (200, 255, 200),   # highlight verde pálido (no blanco puro)
    'black':     (0, 0, 0),
    'dark_text': (90, 140, 90),
}

# ── Estilo Matplotlib — tipografía monospace, grilla sutil, sin bordes ─
MPL_STYLE = {
    'figure.facecolor':  COLORS['bg'],
    'axes.facecolor':    COLORS['bg'],
    'axes.edgecolor':    '#224422',
    'axes.labelcolor':   COLORS['text'],
    'text.color':        COLORS['text'],
    'xtick.color':       COLORS['text'],
    'ytick.color':       COLORS['text'],
    'grid.color':        COLORS['grid'],
    'grid.alpha':        0.4,
    'font.family':       'monospace',
    'axes.spines.top':   False,
    'axes.spines.right': False,
}


def apply_mpl_style():
    """Aplica el estilo terminal verde a matplotlib (tipografía monospace)."""
    import matplotlib.pyplot as plt
    plt.rcParams.update(MPL_STYLE)
    plt.rcParams['font.size'] = 11
