"""
Configuración autocontenida para simulaciones de comportamiento del fuego.
Incluye las constantes del proyecto raíz + extensiones específicas de fuego.
"""

# ── Constantes físicas generales ──────────────────────────────────────────────
G = 9.81   # m/s²

# ── Paleta de colores (Matplotlib) ────────────────────────────────────────────
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

# ── Estilo Matplotlib oscuro ──────────────────────────────────────────────────
_MPL_STYLE = {
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
    import matplotlib.pyplot as plt
    plt.rcParams.update(_MPL_STYLE)
    plt.rcParams['font.size'] = 11


# ── Constantes Físicas del Fuego ─────────────────────────────────────────────
FLASHOVER_TEMP    = 600.0   # °C — temperatura de flashover (capa superior)
ROLLOVER_TEMP     = 300.0   # °C — inicio de rollover
IGNITION_TEMP     = 300.0   # °C — temperatura típica de ignición
MIN_COMBUSTION_O2 = 16.0    # % O₂ — mínimo para combustión sostenida
BACKDRAFT_O2      = 8.0     # % O₂ — umbral de riesgo backdraft
ROOM_HEIGHT       = 2.5     # m   — altura estándar de habitación
DOOR_HEIGHT       = 2.0     # m   — altura estándar de puerta
K_RHO_C           = 0.72e5  # W²·s/(m⁴·K²) — producto k·ρ·c para yeso/concreto

# ── Modelo de crecimiento t² (NFPA 72 / ISO 16733) ───────────────────────────
# Factor α (kW/s²): Q(t) = α · t²
FIRE_GROWTH = {
    0: ('Lento',        0.00293),   # 1 MW en ~18 min
    1: ('Medio',        0.01172),   # 1 MW en ~9 min
    2: ('Rápido',       0.04689),   # 1 MW en ~4.5 min
    3: ('Ultrarápido',  0.18776),   # 1 MW en ~2.3 min
}

# ── Paleta extendida para visualizaciones de fuego ────────────────────────────
FC = dict(COLORS)
FC.update({
    'flame':      '#FF6600',
    'ember':      '#FF3300',
    'smoke':      '#7B7B8B',
    'hot_gas':    '#CC2200',
    'char':       '#2A2A2A',
    'safe':       '#00CC88',
    'layer_hot':  '#DD2200',
    'layer_warm': '#FF8800',
    'layer_cold': '#1565C0',
    'terrain':    '#5D7A4A',
    'wall':       '#546E7A',
    'neutral':    '#AAAACC',
})
