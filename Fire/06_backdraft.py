"""
06_backdraft.py
Backdraft — Animación por Fases (Pygame)

Muestra el desarrollo completo del fenómeno de backdraft en un
compartimento sellado, crítico para la seguridad de bomberos.

Fases de la simulación:
  0. IGNICIÓN        — fuego visible, O₂ al 21 %
  1. DESARROLLO      — fuego crece, O₂ baja, CO sube
  2. AGOTAMIENTO O₂  — llamas se reducen, humo denso
  3. FUEGO LATENTE   — sin llamas, gases explosivos acumulados
  4. SEÑALES AVISO   — humo pulsa en rendija de puerta
  5. BACKDRAFT       — apertura de puerta → EXPLOSIÓN

Controles:
  SPACE / ENTER — avanzar a la siguiente fase (cuando esté lista)
  R             — reiniciar desde fase 0
  ESC / Q       — salir
"""

import sys
import os
import math
import random

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import pygame
import numpy as np

# ── Window ─────────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 1280, 720
FPS          = 30

# ── UI Colors ──────────────────────────────────────────────────────────────────
C_BG       = ( 10,  10,  20)
C_PANEL    = ( 22,  33,  62)
C_TEXT     = (236, 239, 241)
C_DIM      = (130, 140, 160)
C_PRIMARY  = (  0, 188, 212)
C_DANGER   = (244,  67,  54)
C_WARN     = (255, 193,   7)
C_ACCENT   = ( 76, 175,  80)
C_INFO     = ( 33, 150, 243)
C_SAFE     = (  0, 200, 136)
C_WALL     = ( 84,  97, 110)
C_FLOOR    = ( 55,  50,  44)

# ── Room geometry (pixels) ─────────────────────────────────────────────────────
RM_X1, RM_X2 = 80,  810     # inner left/right
RM_Y1, RM_Y2 = 60,  560     # inner top/bottom
RM_W         = RM_X2 - RM_X1
RM_H         = RM_Y2 - RM_Y1
WALL_T       = 18            # wall thickness

# Door in right wall
DOOR_W       = 55
DOOR_H       = int(RM_H * 0.78)
DOOR_X       = RM_X2 + WALL_T // 2      # center x of door opening
DOOR_TOP     = RM_Y2 - DOOR_H
DOOR_BOT     = RM_Y2

# Meter panel
METER_X      = 850
METER_Y1     = 60

# ── Phase definitions ──────────────────────────────────────────────────────────
# Each phase: (duration_s, o2_end, co_end_ppm, t_end_c, smoke_end, name)
PHASES = [
    # dur   O₂%   CO ppm   T°C   smoke%  label
    (  6,  19.5,     80,   120,   0.08,  'IGNICIÓN'),
    ( 18,  14.8,    600,   380,   0.35,  'DESARROLLO DEL INCENDIO'),
    ( 20,   9.2,   2000,   480,   0.62,  'AGOTAMIENTO DE O₂'),
    ( 18,   6.5,   4500,   420,   0.82,  'FUEGO LATENTE — GASES ACUMULÁNDOSE'),
    ( 14,   5.8,   6200,   390,   0.90,  'SEÑALES DE BACKDRAFT'),
    ( 10,   5.8,   6200,   900,   0.95,  '⚠  BACKDRAFT  ⚠'),
]
# Valores de inicio/fin de cada fase: PHASE_START[i] → inicio de la fase i
# PHASE_START tiene len(PHASES)+1 entradas (incluye el estado final)
PHASE_START = [(21.0, 0, 20, 0.0)]   # (O2%, CO ppm, T°C, smoke%)
for _dur, _o2e, _coe, _te, _sme, _ in PHASES:
    PHASE_START.append((_o2e, _coe, _te, _sme))


def lerp(a, b, t):
    return a + (b - a) * min(1.0, max(0.0, t))


def phase_values(phase_idx: int, t_frac: float):
    """Interpolate O2, CO, T, smoke within phase."""
    s  = PHASE_START[phase_idx]
    e  = PHASE_START[phase_idx + 1]
    return (
        lerp(s[0], e[0], t_frac),
        lerp(s[1], e[1], t_frac),
        lerp(s[2], e[2], t_frac),
        lerp(s[3], e[3], t_frac),
    )


# ── Particle system ────────────────────────────────────────────────────────────

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'ptype', 'size')

    def __init__(self, x, y, ptype='fire'):
        self.x   = float(x)
        self.y   = float(y)
        self.ptype = ptype
        if ptype == 'fire':
            self.vx      = random.uniform(-1.2, 1.2)
            self.vy      = random.uniform(-4.0, -1.5)
            self.max_life= random.randint(20, 55)
            self.size    = random.randint(4, 10)
        elif ptype == 'smoke':
            self.vx      = random.uniform(-0.8, 0.8)
            self.vy      = random.uniform(-2.2, -0.8)
            self.max_life= random.randint(50, 110)
            self.size    = random.randint(6, 16)
        else:  # puff (door gap)
            self.vx      = random.uniform(1.5, 4.0)
            self.vy      = random.uniform(-0.5, 0.5)
            self.max_life= random.randint(18, 40)
            self.size    = random.randint(3, 8)
        self.life = 0

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.vy   *= 0.982
        self.vx   *= 0.988
        self.life += 1

    @property
    def alive(self):
        return self.life < self.max_life

    def draw(self, screen: pygame.Surface):
        frac  = self.life / self.max_life
        alpha = int(220 * (1 - frac))
        r     = max(2, self.size - int(self.size * frac * 0.5))

        surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        if self.ptype == 'fire':
            t = min(1.0, frac * 2)
            color = (255, max(0, int(180 - 160 * t)), 0, alpha)
        elif self.ptype == 'smoke':
            v = int(60 + 80 * frac)
            color = (v, v, v + 15, alpha)
        else:  # puff
            color = (160, 155, 140, alpha)

        pygame.draw.circle(surf, color, (r + 1, r + 1), r)
        screen.blit(surf, (int(self.x) - r - 1, int(self.y) - r - 1))


# ── Explosion effect ───────────────────────────────────────────────────────────

class Explosion:
    def __init__(self):
        self.t     = 0.0
        self.dt    = 1.0 / (FPS * 3.5)   # lasts ~3.5 s
        self.done  = False
        self.debris = []
        for _ in range(40):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(4, 18)
            self.debris.append({
                'x': DOOR_X, 'y': (DOOR_TOP + DOOR_BOT) // 2,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle) - 5,
                'color': random.choice([
                    (255, 180, 0), (255, 100, 0), (255, 50, 0), (200, 40, 0),
                ]),
                'life': 0, 'max_life': random.randint(30, 90),
            })

    def update(self):
        self.t += self.dt
        for d in self.debris:
            d['x']   += d['vx']
            d['y']   += d['vy']
            d['vy']  += 0.35   # gravity
            d['vx']  *= 0.97
            d['life'] += 1
        self.debris = [d for d in self.debris if d['life'] < d['max_life']]
        if self.t >= 1.0:
            self.done = True

    def draw(self, screen: pygame.Surface, fonts: tuple):
        sm, md, lg = fonts
        t = self.t

        # White flash (first 0.12 s)
        if t < 0.12:
            flash_a = int(255 * (1 - t / 0.12))
            flash_s = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            flash_s.fill((255, 255, 255, flash_a))
            screen.blit(flash_s, (0, 0))

        # Fireball expanding from door
        if 0.04 < t < 0.7:
            r      = int(400 * (t - 0.04) / 0.66)
            alpha  = int(200 * (1 - (t - 0.04) / 0.66))
            ball_s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            for ring_r, ring_col, ring_a in (
                (r,           (255, 80,  0), alpha),
                (int(r*0.65), (255,180,  0), min(255, alpha + 40)),
                (int(r*0.30), (255,255,120), min(255, alpha + 80)),
            ):
                pygame.draw.circle(ball_s, (*ring_col, ring_a),
                                   (r + 2, r + 2), ring_r)
            cy_exp = (DOOR_TOP + DOOR_BOT) // 2
            screen.blit(ball_s, (DOOR_X - r - 2, cy_exp - r - 2))

        # Debris
        for d in self.debris:
            frac  = d['life'] / d['max_life']
            alpha = int(230 * (1 - frac))
            r     = max(2, 5 - int(5 * frac))
            ds    = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(ds, (*d['color'], alpha), (r + 1, r + 1), r)
            screen.blit(ds, (int(d['x']) - r, int(d['y']) - r))

        # Shockwave ring
        if 0.03 < t < 0.35:
            sw_r = int(WIN_W * 0.8 * (t - 0.03) / 0.32)
            sw_a = int(180 * (1 - (t - 0.03) / 0.32))
            if sw_r > 0:
                sw_s = pygame.Surface((sw_r * 2 + 4, sw_r * 2 + 4), pygame.SRCALPHA)
                cx_e = DOOR_X
                cy_e = (DOOR_TOP + DOOR_BOT) // 2
                pygame.draw.circle(sw_s, (255, 220, 80, sw_a),
                                   (sw_r + 2, sw_r + 2), sw_r, 3)
                screen.blit(sw_s, (cx_e - sw_r - 2, cy_e - sw_r - 2))

        # BACKDRAFT text (flashing)
        if t > 0.15:
            flash_t = int(t * 5) % 2 == 0
            if flash_t:
                txt = lg.render('¡ B A C K D R A F T !', True, C_DANGER)
                screen.blit(txt, (WIN_W // 2 - txt.get_width() // 2,
                                  WIN_H // 2 - 30))
            tip = md.render('La apertura de puertas puede ser fatal', True, C_WARN)
            screen.blit(tip, (WIN_W // 2 - tip.get_width() // 2, WIN_H // 2 + 20))


# ── Room drawing ───────────────────────────────────────────────────────────────

def draw_room(screen: pygame.Surface,
              o2: float, co: float, t_c: float, smoke: float,
              phase_idx: int, tick: int):
    """Draw cross-section of room with thermal layers."""

    # Walls (outer rect)
    outer = pygame.Rect(RM_X1 - WALL_T, RM_Y1 - WALL_T,
                        RM_W + 2 * WALL_T, RM_H + 2 * WALL_T)
    pygame.draw.rect(screen, C_WALL, outer)

    # Door gap (cut in right wall)
    pygame.draw.rect(screen, C_BG,
                     (RM_X2, DOOR_TOP, WALL_T + 2, DOOR_H))

    # Interior background
    pygame.draw.rect(screen, (18, 18, 28), (RM_X1, RM_Y1, RM_W, RM_H))

    # Hot gas layer (fills from ceiling down proportional to smoke)
    layer_h = int(RM_H * smoke * 0.9)
    if layer_h > 4:
        # Temperature-based color
        t_frac = min(1.0, t_c / 650.0)
        r_c    = int(80  + 175 * t_frac)
        g_c    = int(30  - 30  * t_frac)
        b_c    = int(8)
        smoke_a = int(min(210, 90 + 120 * smoke))

        layer_surf = pygame.Surface((RM_W, layer_h), pygame.SRCALPHA)
        # Gradient (hotter at ceiling, cooler at interface)
        for row in range(layer_h):
            row_frac = row / layer_h   # 0=ceiling, 1=interface
            ri = int(r_c * (1 - row_frac * 0.4))
            gi = int(g_c + 30 * row_frac)
            bi = int(b_c + 20 * row_frac)
            ai = int(smoke_a * (1 - row_frac * 0.35))
            pygame.draw.line(layer_surf, (ri, gi, bi, ai),
                             (0, row), (RM_W, row))
        screen.blit(layer_surf, (RM_X1, RM_Y1))

    # Interface dashed line
    intf_y = RM_Y1 + layer_h
    if 0 < layer_h < RM_H:
        for x in range(RM_X1, RM_X2, 18):
            pygame.draw.line(screen, C_WARN, (x, intf_y), (x + 10, intf_y), 1)

    # Floor
    pygame.draw.rect(screen, C_FLOOR, (RM_X1, RM_Y2 - 12, RM_W, 12))

    # ── Fire (phases 0-2)
    if phase_idx <= 2:
        fire_intensity = 1.0 if phase_idx == 0 else max(0.0,
            (1.0 - smoke * 1.1) if phase_idx == 1 else (1.0 - smoke * 1.3))
        fire_intensity = max(0.0, fire_intensity)

        if fire_intensity > 0.05:
            flick = 0.80 + 0.20 * math.sin(tick * 0.6)
            fire_centers = [RM_X1 + RM_W * 0.22, RM_X1 + RM_W * 0.38,
                            RM_X1 + RM_W * 0.54, RM_X1 + RM_W * 0.66]
            for j, xc in enumerate(fire_centers):
                fh  = int((70 + 30 * fire_intensity) * flick
                          * (0.75 + 0.25 * math.sin(j * 1.7 + tick * 0.3)))
                fw  = int(18 * fire_intensity)
                y0  = RM_Y2 - 12
                c1  = (255, max(0, int(200 * fire_intensity)), 0)
                c2  = (255, max(0, int(90  * fire_intensity)), 0)
                if fw > 2:
                    pts_inner = [(int(xc)-fw//2, y0), (int(xc), y0-int(fh*0.7)), (int(xc)+fw//2, y0)]
                    pts_outer = [(int(xc)-fw, y0), (int(xc), y0-fh), (int(xc)+fw, y0)]
                    pygame.draw.polygon(screen, c1, pts_inner)
                    pygame.draw.polygon(screen, c2, pts_outer)

    # ── Glowing embers only (phase 3-4)
    if 2 < phase_idx < 5:
        flick = 0.6 + 0.4 * math.sin(tick * 0.2)
        ember_xs = [RM_X1 + RM_W * f for f in (0.22, 0.38, 0.54, 0.66)]
        for xc in ember_xs:
            col = (int(180 * flick), int(30 * flick), 0)
            pygame.draw.circle(screen, col, (int(xc), RM_Y2 - 18), 5)

    # ── Door outline and neutral plane
    pygame.draw.rect(screen, C_WALL,
                     (RM_X2, DOOR_TOP - 4, WALL_T, 4))   # lintel
    # Neutral plane in door
    if smoke > 0.1:
        h_n = DOOR_TOP + int(DOOR_H * (1 - smoke * 0.75))
        h_n = max(DOOR_TOP + 5, min(DOOR_BOT - 5, h_n))
        pygame.draw.line(screen, (170, 170, 200),
                         (RM_X2, h_n), (RM_X2 + WALL_T, h_n), 2)


# ── Flow arrows (door) ─────────────────────────────────────────────────────────

def draw_flow_arrows(screen: pygame.Surface, smoke: float, phase_idx: int, tick: int):
    if smoke < 0.05:
        return
    h_n = DOOR_TOP + int(DOOR_H * (1 - smoke * 0.75))
    h_n = max(DOOR_TOP + 15, min(DOOR_BOT - 15, h_n))

    # Smoke outflow (above neutral plane) — animated offset
    if h_n > DOOR_TOP + 20:
        cy_out = (DOOR_TOP + h_n) // 2
        offset = int(8 * math.sin(tick * 0.25))
        ax_end = RM_X2 + WALL_T + 45 + offset
        pygame.draw.line(screen, (150, 130, 110),
                         (RM_X2 + WALL_T, cy_out), (ax_end, cy_out), 2)
        pygame.draw.polygon(screen, (150, 130, 110), [
            (ax_end,      cy_out),
            (ax_end - 10, cy_out - 5),
            (ax_end - 10, cy_out + 5),
        ])

    # Air inflow (below neutral plane)
    if DOOR_BOT - h_n > 20 and phase_idx < 4:
        cy_in = (h_n + DOOR_BOT) // 2
        offset = int(6 * math.sin(tick * 0.25 + 1.5))
        ax_start = RM_X2 + WALL_T + 45 + offset
        pygame.draw.line(screen, C_INFO,
                         (ax_start, cy_in), (RM_X2 + WALL_T + 2, cy_in), 2)
        pygame.draw.polygon(screen, C_INFO, [
            (RM_X2 + WALL_T + 2, cy_in),
            (RM_X2 + WALL_T + 12, cy_in - 5),
            (RM_X2 + WALL_T + 12, cy_in + 5),
        ])


# ── Smoke puffing at door gap (phase 4 warning sign) ──────────────────────────

def puff_warning(particles: list, tick: int, phase_idx: int):
    if phase_idx == 4 and tick % 8 == 0:
        # Puff smoke out and sometimes back in
        direction = 1 if (tick // 40) % 2 == 0 else -1
        for _ in range(3):
            p = Particle(RM_X2 + WALL_T, random.randint(DOOR_TOP + 5, DOOR_BOT - 10),
                         ptype='puff')
            p.vx *= direction
            particles.append(p)


# ── Meters panel ───────────────────────────────────────────────────────────────

def draw_meters(screen: pygame.Surface, fonts: tuple,
                o2: float, co: float, t_c: float, smoke: float,
                phase_idx: int, phase_name: str):
    sm, md, lg = fonts
    x0, y0 = METER_X, METER_Y1
    bar_w, bar_h = 260, 22
    padding = 44

    # Background
    pygame.draw.rect(screen, C_PANEL, (x0 - 15, y0 - 15,
                                       WIN_W - x0 + 5, WIN_H - y0 + 5))
    pygame.draw.line(screen, C_PRIMARY, (x0 - 15, y0 - 15),
                     (x0 - 15, WIN_H), 2)

    t_hdr = lg.render('ESTADO DEL COMPARTIMENTO', True, C_TEXT)
    screen.blit(t_hdr, (x0, y0))
    y0 += 35

    # ── Phase
    pcol = C_DANGER if 'BACKDRAFT' in phase_name else (
           C_WARN   if 'SEÑALES'   in phase_name else C_TEXT)
    pt = md.render(f'Fase: {phase_name}', True, pcol)
    screen.blit(pt, (x0, y0))
    y0 += 30

    # ── Meter bars
    def meter_bar(label, value, vmin, vmax, y,
                  low_good=True, danger_thresh=None, warn_thresh=None):
        frac = (value - vmin) / max(1e-6, vmax - vmin)
        frac = max(0.0, min(1.0, frac))
        fill = int(bar_w * frac)

        if low_good:  # O2: high is good
            inv = 1 - frac
            col = (C_ACCENT if inv < 0.3 else C_WARN if inv < 0.6 else C_DANGER)
        else:         # CO, T, smoke: low is good
            col = (C_ACCENT if frac < 0.4 else C_WARN if frac < 0.75 else C_DANGER)

        # Background
        pygame.draw.rect(screen, (40, 45, 65), (x0, y, bar_w, bar_h))
        pygame.draw.rect(screen, col, (x0, y, fill, bar_h))
        pygame.draw.rect(screen, (60, 70, 90), (x0, y, bar_w, bar_h), 1)

        lt = sm.render(label, True, C_DIM)
        screen.blit(lt, (x0 - 2, y - 15))
        vt = md.render(f'{value:.1f}', True, C_TEXT)
        screen.blit(vt, (x0 + bar_w + 8, y + 2))

    meter_bar(f'O₂  (%)  — normal: 21%',
              o2, 0, 21, y0, low_good=True)
    y0 += padding

    meter_bar(f'CO  (ppm) — IDLH: 1200 ppm',
              min(co, 7000), 0, 7000, y0, low_good=False)
    y0 += padding

    meter_bar(f'Temperatura  (°C)',
              t_c, 20, 700, y0, low_good=False)
    y0 += padding

    meter_bar(f'Densidad humo/gases  (%)',
              smoke * 100, 0, 100, y0, low_good=False)
    y0 += padding + 10

    # ── Threshold alerts
    alerts = []
    if o2 < 16:
        alerts.append(('O₂ < 16 %: combustión se extingue', C_WARN))
    if o2 < 10:
        alerts.append(('O₂ < 10 %: riesgo para bomberos', C_DANGER))
    if co > 1200:
        alerts.append(('CO > IDLH: 1 200 ppm — USE SCBA', C_DANGER))
    if co > 4000:
        alerts.append(('CO > 4 000 ppm: MEZCLA EXPLOSIVA', C_DANGER))
    if phase_idx == 4:
        alerts.append(('Humo pulsa en rendija → BACKDRAFT', C_DANGER))

    for txt, col in alerts[-4:]:
        t = sm.render('⚠  ' + txt, True, col)
        screen.blit(t, (x0, y0))
        y0 += 20

    # ── Controls reminder
    y0 = WIN_H - 110
    pygame.draw.line(screen, (50, 60, 90), (x0 - 15, y0), (WIN_W, y0), 1)
    for i, line in enumerate([
        'SPACE/ENTER — siguiente fase',
        'R — reiniciar  |  ESC — salir',
    ]):
        t = sm.render(line, True, C_DIM)
        screen.blit(t, (x0, y0 + 10 + i * 18))


# ── Phase narrative ────────────────────────────────────────────────────────────

NARRATIVES = [
    ['El fuego se inicia con O₂ al 21 %.',
     'Las llamas son visibles.',
     'El CO comienza a producirse.'],
    ['El fuego crece y consume O₂.',
     'La capa de gases calientes desciende.',
     'El CO supera niveles peligrosos.'],
    ['O₂ < 16 %: las llamas se reducen drásticamente.',
     'El fuego pasa a combustión incompleta.',
     'Se producen grandes cantidades de CO y vapores de pirolisis.'],
    ['Sin llamas visibles — pero el fuego NO está apagado.',
     'La habitación está llena de gases EXPLOSIVOS.',
     'La temperatura del material aún es alta (energía almacenada).'],
    ['SEÑALES DE BACKDRAFT:',
     '• Humo que pulsa (entra y sale) en rendijas',
     '• Vidrios con manchas de hollín',
     '• Calor intenso al acercarse a la puerta'],
    ['PUERTA ABIERTA → ENTRADA DE OXÍGENO',
     'Los gases a alta temperatura se inflaman INSTANTÁNEAMENTE.',
     'Velocidad de deflagración: >300 m/s'],
]


def draw_narrative(screen: pygame.Surface, fonts: tuple, phase_idx: int):
    sm, md, _ = fonts
    narr = NARRATIVES[min(phase_idx, len(NARRATIVES) - 1)]
    x0, y0 = RM_X1 - WALL_T, WIN_H - 105
    pygame.draw.rect(screen, (20, 25, 40), (x0, y0, RM_X2 + WALL_T - x0 + 2, 100))
    pygame.draw.line(screen, C_PRIMARY, (x0, y0), (RM_X2 + WALL_T + 2, y0), 1)
    col = C_DANGER if phase_idx >= 4 else C_TEXT
    for i, line in enumerate(narr[:3]):
        t = sm.render(line, True, col)
        screen.blit(t, (x0 + 8, y0 + 8 + i * 28))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption('Backdraft — Simulación de Fases')
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock  = pygame.time.Clock()

    sm  = pygame.font.SysFont('monospace', 11)
    md  = pygame.font.SysFont('monospace', 13)
    lg  = pygame.font.SysFont('monospace', 17, bold=True)
    fonts = (sm, md, lg)

    particles: list[Particle] = []
    explosion: Explosion | None = None

    phase_idx  = 0
    phase_t    = 0.0        # seconds elapsed in current phase
    phase_done = False      # ready to advance
    tick       = 0

    def reset():
        nonlocal phase_idx, phase_t, phase_done, particles, explosion, tick
        phase_idx  = 0
        phase_t    = 0.0
        phase_done = False
        particles  = []
        explosion  = None
        tick       = 0

    def advance_phase():
        nonlocal phase_idx, phase_t, phase_done, explosion
        if phase_idx < len(PHASES) - 1:
            phase_idx += 1
            phase_t    = 0.0
            phase_done = False
            if phase_idx == len(PHASES) - 1:   # backdraft phase
                explosion = Explosion()
        elif phase_done and explosion and explosion.done:
            reset()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if phase_done:
                        advance_phase()
                elif event.key == pygame.K_r:
                    reset()

        # ── Simulation tick
        dur      = PHASES[phase_idx][0]
        phase_t  = min(phase_t + dt, dur)
        t_frac   = phase_t / dur
        if t_frac >= 0.98 and not phase_done:
            phase_done = True

        o2, co, t_c, smoke = phase_values(phase_idx, t_frac)

        # Particle emission
        if phase_idx <= 2 and o2 > 8:     # active fire
            emit_n = max(0, int((o2 - 8) / 2))
            for _ in range(emit_n):
                xc = random.choice([int(RM_X1 + RM_W * f)
                                    for f in (0.22, 0.38, 0.54, 0.66)])
                particles.append(Particle(xc, RM_Y2 - 18, 'fire'))
        if smoke > 0.1:                    # smoke rising
            if tick % 2 == 0:
                xc = random.randint(RM_X1 + 20, RM_X2 - 20)
                yc = RM_Y1 + int(RM_H * (1 - smoke * 0.85))
                particles.append(Particle(xc, yc, 'smoke'))

        puff_warning(particles, tick, phase_idx)

        for p in particles:
            p.update()
        particles = [p for p in particles if p.alive]
        if len(particles) > 400:          # cap particle count
            particles = particles[-400:]

        if explosion:
            explosion.update()

        # ── Render
        screen.fill(C_BG)
        draw_room(screen, o2, co, t_c, smoke, phase_idx, tick)
        draw_flow_arrows(screen, smoke, phase_idx, tick)

        for p in particles:
            p.draw(screen)

        if explosion:
            explosion.draw(screen, fonts)

        draw_meters(screen, fonts, o2, co, t_c, smoke, phase_idx,
                    PHASES[phase_idx][-1])
        draw_narrative(screen, fonts, phase_idx)

        # "Advance" prompt
        if phase_done and not (explosion and not explosion.done):
            pulse = 0.6 + 0.4 * math.sin(tick * 0.15)
            col   = tuple(int(c * pulse) for c in C_WARN)
            prompt_txt = '▶  SPACE / ENTER  para avanzar a siguiente fase'
            t = md.render(prompt_txt, True, col)
            screen.blit(t, (RM_X1 - WALL_T, WIN_H - 130))

        pygame.display.flip()
        tick += 1

    pygame.quit()


if __name__ == '__main__':
    main()
