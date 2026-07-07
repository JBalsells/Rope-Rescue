"""
05_propagacion_celular.py
Propagación de Incendio — Autómata Celular 2D (Pygame)

Simula el avance de un frente de fuego sobre un terreno heterogéneo:
  • Tipos de combustible: pasto, matorral, bosque
  • Cortafuegos naturales: ríos, carreteras
  • Viento con dirección (8 rumbos) y velocidad variables
  • Humedad del combustible ajustable
  • Retardante aéreo (clic derecho del ratón)

Física:
  El spread desde cada celda ardiendo a sus 8 vecinas sigue:
      P_ignición = P_base(tipo) × factor_viento × (1 − humedad)
  donde factor_viento se calcula con el producto escalar entre
  la dirección del viento y la dirección del vecino.

Controles:
  Clic izquierdo    — ignitar zona (radio 2 celdas)
  Clic derecho      — aplicar retardante
  ← →               — rotar dirección del viento ±45°
  ↑ ↓               — velocidad del viento +/- 0.5
  M / N             — humedad +5 % / −5 %
  R                 — resetear terreno (nueva semilla aleatoria)
  SPACE             — pausar / reanudar
"""

import sys
import os
import math
import time
import random

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import pygame

# ── Layout ─────────────────────────────────────────────────────────────────────
COLS, ROWS  = 128, 64
CS          = 10                    # pixels per cell
GRID_W      = COLS * CS             # 1280
GRID_H      = ROWS * CS             # 640
PANEL_H     = 160
WIN_W       = GRID_W
WIN_H       = GRID_H + PANEL_H      # 1280 × 800
FPS         = 18
SIM_STEPS   = 2                     # simulation steps per frame

# ── Cell states ────────────────────────────────────────────────────────────────
EMPTY   = 0
GRASS   = 1
BRUSH   = 2
FOREST  = 3
ROAD    = 4
WATER   = 5
BURNING = 6
EMBERS  = 7
BURNT   = 8
WET     = 9

FUEL_STATES = frozenset({GRASS, BRUSH, FOREST})

# base_prob, burn_steps, description
FUEL_DATA = [
    (GRASS,  0.60, 3,  'Pasto'),
    (BRUSH,  0.40, 7,  'Matorral'),
    (FOREST, 0.26, 13, 'Bosque'),
]

# ── RGB colors per state ───────────────────────────────────────────────────────
CELL_COLORS = np.array([
    [ 22,  28,  16],   # EMPTY   — suelo desnudo
    [ 74, 118,  48],   # GRASS   — pasto
    [ 52,  85,  32],   # BRUSH   — matorral
    [ 28,  57,  18],   # FOREST  — bosque
    [ 78,  72,  68],   # ROAD    — carretera
    [ 28,  76, 148],   # WATER   — agua
    [255, 128,   8],   # BURNING — ardiendo
    [195,  42,   4],   # EMBERS  — brasas
    [ 44,  38,  34],   # BURNT   — quemado
    [ 46, 116, 198],   # WET     — retardante
], dtype=np.uint8)

# UI colors
C_BG      = (15,  15, 26)
C_PANEL   = (22,  33, 62)
C_TEXT    = (236, 239, 241)
C_DIM     = (130, 140, 160)
C_PRIMARY = (0,  188, 212)
C_DANGER  = (244,  67,  54)
C_WARN    = (255, 193,   7)
C_ACCENT  = ( 76, 175,  80)
C_INFO    = ( 33, 150, 243)


# ── Terrain generation ─────────────────────────────────────────────────────────

def generate_terrain(seed=None):
    """Generate a random terrain with fuel types and natural firebreaks."""
    rng  = np.random.default_rng(seed if seed is not None else random.randint(0, 9999))
    s    = np.full((ROWS, COLS), GRASS, dtype=np.uint8)
    bt   = np.zeros((ROWS, COLS), dtype=np.int16)
    yi, xi = np.ogrid[:ROWS, :COLS]

    # Forest patches (larger, clustered in upper half)
    for _ in range(7):
        cx = int(rng.integers(12, COLS - 12))
        cy = int(rng.integers(5, ROWS // 2))
        r  = int(rng.integers(5, 13))
        s[((xi - cx) ** 2 + (yi - cy) ** 2) < r ** 2] = FOREST

    # Smaller forest patches (lower half)
    for _ in range(3):
        cx = int(rng.integers(10, COLS - 10))
        cy = int(rng.integers(ROWS // 2, ROWS - 6))
        r  = int(rng.integers(4, 9))
        s[((xi - cx) ** 2 + (yi - cy) ** 2) < r ** 2] = FOREST

    # Brush patches
    for _ in range(14):
        cx = int(rng.integers(4, COLS - 4))
        cy = int(rng.integers(3, ROWS - 3))
        r  = int(rng.integers(2, 8))
        s[((xi - cx) ** 2 + (yi - cy) ** 2) < r ** 2] = BRUSH

    # Bare soil patches (natural firebreaks — rocky outcrops)
    for _ in range(6):
        cx = int(rng.integers(8, COLS - 8))
        cy = int(rng.integers(5, ROWS - 5))
        r  = int(rng.integers(2, 5))
        s[((xi - cx) ** 2 + (yi - cy) ** 2) < r ** 2] = EMPTY

    # River (sinusoidal, roughly 3/5 from top)
    ry_base = ROWS * 3 // 5
    for c in range(COLS):
        ry = int(ry_base + 4 * np.sin(c * 0.13 + 0.8))
        for dy in range(-2, 3):
            nr = ry + dy
            if 0 <= nr < ROWS:
                s[nr, c] = WATER

    # Road (diagonal strip, upper right)
    rc0 = COLS * 2 // 3
    for row in range(ROWS):
        col = rc0 - row // 3
        for dc in range(2):
            if 0 <= col + dc < COLS:
                s[row, col + dc] = ROAD

    return s, bt


# ── Spread exposure (pure NumPy, no scipy needed) ──────────────────────────────

def compute_exposure(burning: np.ndarray,
                     wdx: float, wdy: float, wspeed: float) -> np.ndarray:
    """
    For each cell, sum the weighted burning-neighbour count.
    Weight includes wind alignment: downwind cells get higher probability.
    """
    H, W    = burning.shape
    exp     = np.zeros((H, W), dtype=np.float32)
    wn      = math.sqrt(wdx * wdx + wdy * wdy)
    wdx_n   = wdx / wn if wn > 0 else 0.0
    wdy_n   = wdy / wn if wn > 0 else 0.0

    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            dist = math.sqrt(dx * dx + dy * dy)
            if wspeed > 0 and wn > 0:
                dot  = (dx * wdx_n + dy * wdy_n) / dist
                wmul = max(0.06, 1.0 + wspeed * 0.20 * dot)
            else:
                wmul = 1.0
            weight = wmul / dist

            # Source slice → target slice (no edge clamping needed; numpy clips)
            sy = slice(max(0, -dy), H - max(0, dy) if max(0, dy) else H)
            sx = slice(max(0, -dx), W - max(0, dx) if max(0, dx) else W)
            ty = slice(max(0,  dy), H - max(0, -dy) if max(0, -dy) else H)
            tx = slice(max(0,  dx), W - max(0, -dx) if max(0, -dx) else W)
            exp[ty, tx] += burning[sy, sx] * weight

    return exp


# ── Fire update step ───────────────────────────────────────────────────────────

def update_fire(state: np.ndarray, bt: np.ndarray,
                wdx: float, wdy: float, wspeed: float,
                moisture: float) -> tuple[np.ndarray, np.ndarray]:
    s   = state.copy()
    btt = bt.copy()

    burning  = (s == BURNING)
    btt[burning] -= 1
    s[burning & (btt <= 0)] = EMBERS
    s[s == EMBERS] = BURNT

    burn_float = (s == BURNING).astype(np.float32)
    exposure   = compute_exposure(burn_float, wdx, wdy, wspeed)
    m_factor   = max(0.02, 1.0 - moisture * 0.82)
    rnd        = np.random.random(s.shape).astype(np.float32)

    for ftype, base_p, burn_steps, _ in FUEL_DATA:
        mask   = (s == ftype)
        P      = base_p * m_factor * exposure
        ignite = mask & (rnd < P)
        s[ignite]   = BURNING
        btt[ignite] = burn_steps + np.random.randint(-1, 2, size=s.shape)[ignite]

    # Wet / road / water cells are fireproof
    s[(state == WET)   & (s == BURNING)] = WET
    s[(state == ROAD)  & (s == BURNING)] = ROAD
    s[(state == WATER) & (s == BURNING)] = WATER

    return s, btt


# ── Rendering ──────────────────────────────────────────────────────────────────

def render_grid(screen: pygame.Surface, state: np.ndarray, tick: int):
    """Render the fire grid using surfarray for fast pixel operations."""
    flick = 0.82 + 0.18 * math.sin(tick * 0.5)

    # Build (COLS, ROWS, 3) color array — surfarray uses (x, y) = (COLS, ROWS)
    rgb = CELL_COLORS[state.T].copy()

    # Flickering for BURNING cells
    bmask = (state.T == BURNING)
    rgb[bmask, 0] = int(np.clip(255 * flick, 210, 255))
    rgb[bmask, 1] = int(60 + 80 * flick)
    rgb[bmask, 2] = 0

    # Glow tint for EMBERS
    emask = (state.T == EMBERS)
    rgb[emask, 0] = int(200 * flick)
    rgb[emask, 1] = int(35 * flick)
    rgb[emask, 2] = 0

    # Create small surface and scale up
    small = pygame.surfarray.make_surface(rgb)
    scaled = pygame.transform.scale(small, (GRID_W, GRID_H))
    screen.blit(scaled, (0, 0))


# ── Wind compass ───────────────────────────────────────────────────────────────

def draw_compass(screen: pygame.Surface, fonts: tuple,
                 cx: int, cy: int, cr: int,
                 wind_angle: int, wspeed: float):
    sm, md, _ = fonts
    pygame.draw.circle(screen, (38, 50, 80), (cx, cy), cr)
    pygame.draw.circle(screen, C_PRIMARY, (cx, cy), cr, 2)

    for deg, label in ((0, 'N'), (90, 'E'), (180, 'S'), (270, 'W')):
        a = math.radians(deg - 90)
        px = int(cx + (cr + 13) * math.cos(a))
        py = int(cy + (cr + 13) * math.sin(a))
        t  = sm.render(label, True, C_DIM)
        screen.blit(t, (px - t.get_width() // 2, py - t.get_height() // 2))

    # Wind arrow
    if wspeed > 0.05:
        a   = math.radians(wind_angle - 90)
        ax_ = int(cx + cr * 0.72 * math.cos(a))
        ay_ = int(cy + cr * 0.72 * math.sin(a))
        pygame.draw.line(screen, C_DANGER, (cx, cy), (ax_, ay_), 4)
        for side in (1, -1):
            ha = math.radians(wind_angle - 90 + side * 145)
            hx = int(ax_ + 9 * math.cos(ha))
            hy = int(ay_ + 9 * math.sin(ha))
            pygame.draw.line(screen, C_DANGER, (ax_, ay_), (hx, hy), 3)

    dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'O', 'NO']
    dir_label = dirs[round(wind_angle / 45) % 8]
    speed_str = f'Viento: {dir_label}  {wspeed:.1f}/5'
    t = sm.render(speed_str, True, C_TEXT)
    screen.blit(t, (cx - t.get_width() // 2, GRID_H + 8))


# ── Panel ──────────────────────────────────────────────────────────────────────

def draw_panel(screen: pygame.Surface, fonts: tuple,
               state: np.ndarray, init_fuel: int,
               wind_angle: int, wspeed: float, moisture: float,
               paused: bool, sim_steps: int):
    sm, md, lg = fonts

    pygame.draw.rect(screen, C_PANEL, (0, GRID_H, WIN_W, PANEL_H))
    pygame.draw.line(screen, C_PRIMARY, (0, GRID_H), (WIN_W, GRID_H), 1)

    # ── Wind compass (left)
    draw_compass(screen, fonts, 72, GRID_H + 82, 55, wind_angle, wspeed)

    # ── Stats (center-left)
    sx = 178
    burnt   = int(np.sum(state == BURNT))
    burning = int(np.sum(state == BURNING))
    b_pct   = 100 * burnt / max(1, init_fuel)
    elapsed = sim_steps / (FPS * SIM_STEPS)

    stats = [
        (f'Área quemada   {b_pct:5.1f} %',    C_DANGER),
        (f'Celdas ardiendo {burning:4d}',       C_WARN),
        (f'Humedad       {int(moisture*100):3d} %', C_INFO),
        (f'Tiempo sim.    {elapsed:5.0f} s',   C_DIM),
    ]
    for i, (txt, col) in enumerate(stats):
        t = md.render(txt, True, col)
        screen.blit(t, (sx, GRID_H + 14 + i * 33))

    if paused:
        t = lg.render('II  PAUSADO', True, C_WARN)
        screen.blit(t, (sx + 220, GRID_H + 60))

    # ── Legend (center-right)
    lx = 630
    t  = md.render('Leyenda:', True, C_TEXT)
    screen.blit(t, (lx, GRID_H + 10))
    entries = [
        (GRASS,   'Pasto'),
        (BRUSH,   'Matorral'),
        (FOREST,  'Bosque'),
        (ROAD,    'Carretera'),
        (WATER,   'Agua / Río'),
        (BURNING, 'Ardiendo'),
        (BURNT,   'Quemado'),
        (WET,     'Retardante'),
    ]
    cols_lg = 2
    for i, (sv, label) in enumerate(entries):
        col_i = i % cols_lg
        row_i = i // cols_lg
        ox = lx + col_i * 130
        oy = GRID_H + 30 + row_i * 16
        pygame.draw.rect(screen, tuple(int(v) for v in CELL_COLORS[sv]),
                         (ox, oy, 13, 11))
        t = sm.render(label, True, C_TEXT)
        screen.blit(t, (ox + 16, oy))

    # ── Controls (right)
    cx2 = WIN_W - 270
    t   = md.render('Controles:', True, C_TEXT)
    screen.blit(t, (cx2, GRID_H + 10))
    lines = [
        'Clic izq → ignitar',
        'Clic der → retardante',
        '← → viento dir.',
        '↑ ↓ viento vel.',
        'M/N  humedad ±',
        'R  reset   SPACE  pausa',
    ]
    for i, line in enumerate(lines):
        t = sm.render(line, True, C_DIM)
        screen.blit(t, (cx2, GRID_H + 30 + i * 20))


# ── Mouse painting ─────────────────────────────────────────────────────────────

def paint(state: np.ndarray, bt: np.ndarray,
          mx: int, my: int, paint_type: int):
    gc = mx // CS
    gr = my // CS
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            r, c = gr + dr, gc + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                if paint_type == BURNING and state[r, c] in FUEL_STATES:
                    state[r, c]  = BURNING
                    bt[r, c]     = 8
                elif paint_type == WET and state[r, c] not in {WATER, ROAD, BURNT}:
                    state[r, c]  = WET


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption('Propagación de Incendio — Autómata Celular  |  R=reset  SPACE=pausa')
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock  = pygame.time.Clock()

    sm  = pygame.font.SysFont('monospace', 11)
    md  = pygame.font.SysFont('monospace', 13)
    lg  = pygame.font.SysFont('monospace', 20, bold=True)
    fonts = (sm, md, lg)

    # ── Simulation state
    state, bt   = generate_terrain()
    init_fuel   = int(np.sum(np.isin(state, list(FUEL_STATES))))
    wind_angle  = 270   # degrees CW from N; 270 = west (fire moves east)
    wspeed      = 2.0   # 0..5
    moisture    = 0.18  # 0 = bone dry, 1 = soaked
    paused      = False
    sim_steps   = 0     # total simulation steps executed
    tick        = 0     # render tick (for flicker)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    state, bt = generate_terrain()
                    init_fuel = int(np.sum(np.isin(state, list(FUEL_STATES))))
                    sim_steps = 0
                    tick      = 0
                elif event.key == pygame.K_LEFT:
                    wind_angle = (wind_angle - 45) % 360
                elif event.key == pygame.K_RIGHT:
                    wind_angle = (wind_angle + 45) % 360
                elif event.key == pygame.K_UP:
                    wspeed = min(5.0, round(wspeed + 0.5, 1))
                elif event.key == pygame.K_DOWN:
                    wspeed = max(0.0, round(wspeed - 0.5, 1))
                elif event.key == pygame.K_m:
                    moisture = min(0.95, round(moisture + 0.05, 2))
                elif event.key == pygame.K_n:
                    moisture = max(0.0,  round(moisture - 0.05, 2))

        # Mouse painting (held button)
        mb = pygame.mouse.get_pressed()
        mx, my = pygame.mouse.get_pos()
        if my < GRID_H:
            if mb[0]:
                paint(state, bt, mx, my, BURNING)
            elif mb[2]:
                paint(state, bt, mx, my, WET)

        # Simulation update
        if not paused:
            rad  = math.radians(wind_angle - 90)
            wdx  = math.cos(rad)
            wdy  = math.sin(rad)
            for _ in range(SIM_STEPS):
                state, bt = update_fire(state, bt, wdx, wdy, wspeed, moisture)
            sim_steps += SIM_STEPS
            tick      += 1

        # Render
        screen.fill(C_BG)
        render_grid(screen, state, tick)
        draw_panel(screen, fonts, state, init_fuel,
                   wind_angle, wspeed, moisture, paused, sim_steps)

        # Grid border
        pygame.draw.rect(screen, C_PRIMARY, (0, 0, GRID_W, GRID_H), 1)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == '__main__':
    main()
