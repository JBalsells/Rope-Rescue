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

# ── Paleta de colores (Matplotlib) ────────────────────────────────────
COLORS = {
    'bg':        '#0f0f1a',
    'panel':     '#16213e',
    'primary':   '#00BCD4',
    'secondary': '#FF5722',
    'accent':    '#4CAF50',
    'warning':   '#FFC107',
    'danger':    '#F44336',
    'info':      '#2196F3',
    'text':      '#ECEFF1',
    'grid':      '#2a2a3e',
    'rope':      '#FFA726',
    'anchor':    '#78909C',
}

# ── Paleta de colores (Pygame, tuplas RGB) ────────────────────────────
PG_COLORS = {
    'bg':        (15, 15, 26),
    'panel':     (22, 33, 62),
    'primary':   (0, 188, 212),
    'secondary': (255, 87, 34),
    'accent':    (76, 175, 80),
    'warning':   (255, 193, 7),
    'danger':    (244, 67, 54),
    'info':      (33, 150, 243),
    'text':      (236, 239, 241),
    'grid':      (42, 42, 62),
    'rope':      (255, 167, 38),
    'anchor':    (120, 144, 156),
    'white':     (255, 255, 255),
    'black':     (0, 0, 0),
    'dark_text': (180, 180, 200),
}

# ── Estilo Matplotlib ─────────────────────────────────────────────────
MPL_STYLE = {
    'figure.facecolor': COLORS['bg'],
    'axes.facecolor':   COLORS['bg'],
    'axes.edgecolor':   COLORS['grid'],
    'axes.labelcolor':  COLORS['text'],
    'text.color':       COLORS['text'],
    'xtick.color':      COLORS['text'],
    'ytick.color':      COLORS['text'],
    'grid.color':       COLORS['grid'],
    'grid.alpha':       0.3,
}


def apply_mpl_style():
    """Aplica el estilo oscuro profesional a matplotlib."""
    import matplotlib.pyplot as plt
    plt.rcParams.update(MPL_STYLE)
    plt.rcParams['font.size'] = 11
