"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 21: Sistema English Reeve             ║
╠══════════════════════════════════════════════════════════════════════╣
║  El Sistema English Reeve es una tirolesa de rescate controlada:   ║
║  la víctima, suspendida de un carrito (carriage), es desplazada    ║
║  horizontalmente a lo largo de la cuerda principal (highline)      ║
║  mediante una cuerda de control con ventaja mecánica (VM).         ║
║  Un sistema vertical independiente permite subir/bajar a la        ║
║  víctima mediante otra VM. Belay independiente siempre activo.     ║
║                                                                      ║
║  Componentes:                                                        ║
║   • Highline: cuerda tensada entre anclaje A y anclaje B           ║
║   • Carriage: polea doble de travesía sobre la highline            ║
║   • VM horizontal: 3:1 / 4:1 / 6:1 para mover el carrito         ║
║   • VM vertical: 2:1 / 3:1 / 4:1 para subir/bajar la víctima     ║
║   • Belay line: cuerda de seguridad independiente                  ║
║   • PCD: capturador de progreso — impide retroceso                 ║
║                                                                      ║
║  Controles:                                                          ║
║   [←/→]     Mover carrito           [↑/↓]  Ajustar carga         ║
║   [A/Z]     Alt. anclaje A (0–30m)  [S/X]  Flecha (0.5–20%)      ║
║   [L/K]     Vano (20–100m)          [1/2/3] VM horizontal         ║
║   [PgUp/PgDn] Subir/bajar víctima   [4/5/6] VM vertical           ║
║   [F]       Fricción ON/OFF          [R]    Reiniciar posición     ║
║   [ESC]     Salir                                                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import pygame
from config import PG_COLORS as C, G

# ── Pantalla ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 800
FPS = 60

# ── Constantes físicas ────────────────────────────────────────────────
ROPE_MBS   = 30.0   # kN  — MBS cuerda estática 11 mm
PULLEY_EFF = 0.92   # eficiencia por polea
FRICTION_K = 0.08   # coeficiente de fricción del carriage (μ)
V_WARN     = 120    # ángulo V de advertencia (°)
V_DANGER   = 150    # ángulo V peligroso (°)

# ── VM horizontal (cuerda de control para travesía) ───────────────────
MA_HORIZ = [
    {'label': '3:1  Z-rig',     'ma': 3, 'pulleys': 2},
    {'label': '4:1  Compuesto', 'ma': 4, 'pulleys': 3},
    {'label': '6:1  Compuesto', 'ma': 6, 'pulleys': 4},
]

# ── VM vertical (sistema de izado/descenso) ───────────────────────────
MA_VERT = [
    {'label': '2:1  Simple',    'ma': 2, 'pulleys': 1},
    {'label': '3:1  Z-rig',     'ma': 3, 'pulleys': 2},
    {'label': '4:1  Compuesto', 'ma': 4, 'pulleys': 3},
]

# ── Geometría de escena ────────────────────────────────────────────────
SCENE_W     = 800           # ancho del área de escena (px)
ANC_A_X     = 70            # X del anclaje A
ANC_B_X     = 730           # X del anclaje B
SPAN_SCR    = ANC_B_X - ANC_A_X   # 660 px ≡ span_m metros
BASE_Y      = 285           # Y del nivel de referencia (nivel anclaje B)
GROUND_Y    = 695           # Y de la línea de suelo / fondo del cañón
PANEL_X     = SCENE_W + 10
PANEL_W     = WIDTH - PANEL_X - 8
CARRIAGE_R  = 12            # radio visual del carriage (px)
HOOK_LEN    = 26            # longitud del gancho del carriage hacia abajo


# ── Funciones de física ───────────────────────────────────────────────

def _rope_length(span_m, h_A, h_B, sag_pct):
    """
    Longitud total de la cuerda calculada a partir de la flecha
    en el punto medio del vano (medida desde la recta A-B).
    """
    x_mid    = span_m / 2.0
    y_ab_mid = h_A + (h_B - h_A) * x_mid / span_m
    d        = sag_pct / 100.0 * span_m
    y_P_mid  = y_ab_mid - d
    return (math.sqrt(x_mid**2 + (y_P_mid - h_A)**2) +
            math.sqrt(x_mid**2 + (y_P_mid - h_B)**2))


def _solve_load_y(x_m, L, h_A, h_B, S):
    """
    Bisección (64 iter.): halla y_P tal que |AP| + |PB| = S.
    """
    y_ab = h_A + (h_B - h_A) * x_m / L
    y_hi, y_lo = y_ab, y_ab - S
    for _ in range(64):
        mid = (y_hi + y_lo) * 0.5
        f   = (math.sqrt(x_m**2       + (h_A - mid)**2) +
               math.sqrt((L - x_m)**2 + (h_B - mid)**2) - S)
        if f < 0:
            y_hi = mid
        else:
            y_lo = mid
    return (y_hi + y_lo) * 0.5


def _compute_forces(x_m, L, h_A, h_B, y_P, W_kN):
    """Equilibrio estático en el carriage P."""
    x_m = max(x_m, 1e-3)
    x_m = min(x_m, L - 1e-3)

    len_PA = math.sqrt(x_m**2       + (y_P - h_A)**2)
    len_PB = math.sqrt((L - x_m)**2 + (y_P - h_B)**2)
    sag_A  = h_A - y_P
    sag_B  = h_B - y_P

    denom = (L - x_m) * sag_A / x_m + sag_B
    if abs(denom) < 1e-9:
        T_A = T_B = W_kN * 50.0
    else:
        T_B = W_kN * len_PB / denom
        T_A = T_B * (L - x_m) * len_PA / (x_m * len_PB)

    uA_x = -x_m       / len_PA
    uA_y =  sag_A     / len_PA
    uB_x =  (L - x_m) / len_PB
    uB_y =  sag_B     / len_PB

    dot     = max(-1.0, min(1.0, uA_x * uB_x + uA_y * uB_y))
    v_angle = math.degrees(math.acos(dot))
    alpha_A = math.degrees(math.atan2(sag_A, x_m))
    alpha_B = math.degrees(math.atan2(sag_B, L - x_m))

    return {
        'T_A': T_A, 'T_B': T_B,
        'v_angle': v_angle,
        'alpha_A': alpha_A, 'alpha_B': alpha_B,
        'len_PA': len_PA,   'len_PB': len_PB,
        'uA': (uA_x, uA_y), 'uB': (uB_x, uB_y),
    }


# ── Simulador ─────────────────────────────────────────────────────────

class EnglishReeveSimulator:
    """Simulador interactivo del Sistema English Reeve con VM vertical."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Física del Rescate — Sistema English Reeve')
        self.clock  = pygame.time.Clock()

        self.font_title = pygame.font.SysFont('DejaVu Sans', 22, bold=True)
        self.font_big   = pygame.font.SysFont('DejaVu Sans', 16, bold=True)
        self.font_med   = pygame.font.SysFont('DejaVu Sans', 13)
        self.font_sm    = pygame.font.SysFont('DejaVu Sans', 12)
        self.font_xs    = pygame.font.SysFont('DejaVu Sans', 11)

        # ── Estado del sistema ────────────────────────────────────────
        self.span_m      = 40.0   # vano A-B (m)
        self.h_A         = 8.0    # altura anclaje A sobre nivel B (m)
        self.h_B         = 0.0    # anclaje B en nivel de referencia
        self.sag_pct     = 5.0    # flecha central (% del vano)
        self.pos_pct     = 50.0   # posición carriage A→B (%)
        self.load_kg     = 120    # carga total víctima + camilla (kg)
        self.ma_idx      = 1      # VM horizontal [0=3:1, 1=4:1, 2=6:1]
        self.ma_vert_idx = 1      # VM vertical   [0=2:1, 1=3:1, 2=4:1]
        self.friction    = False  # fricción en poleas
        self.move_dir    = 0      # -1=hacia A, 0=parado, +1=hacia B
        self.load_drop_m = 8.0   # profundidad de cuelgue vertical (m)
        self.drop_dir    = 0      # -1=subiendo, 0=parado, +1=bajando

    # ── Física ───────────────────────────────────────────────────────

    def _physics(self):
        L    = self.span_m
        h_A  = self.h_A
        h_B  = self.h_B
        x_m  = self.pos_pct / 100.0 * L
        W_kN = self.load_kg * G / 1000.0

        cfg_h  = MA_HORIZ[self.ma_idx]
        cfg_v  = MA_VERT[self.ma_vert_idx]
        ma_h   = cfg_h['ma'];  n_h = cfg_h['pulleys']
        ma_v   = cfg_v['ma'];  n_v = cfg_v['pulleys']

        S   = _rope_length(L, h_A, h_B, self.sag_pct)
        y_P = _solve_load_y(x_m, L, h_A, h_B, S)
        f   = _compute_forces(x_m, L, h_A, h_B, y_P, W_kN)

        eff_h = PULLEY_EFF ** n_h if self.friction else 1.0
        eff_v = PULLEY_EFF ** n_v if self.friction else 1.0

        sin_A  = math.sin(math.radians(f['alpha_A']))
        sin_B  = math.sin(math.radians(f['alpha_B']))
        cos_A  = math.cos(math.radians(f['alpha_A']))
        cos_B  = math.cos(math.radians(f['alpha_B']))
        fric_A = FRICTION_K * W_kN * cos_A if self.friction else 0.0
        fric_B = FRICTION_K * W_kN * cos_B if self.friction else 0.0

        F_ctrl_B = (W_kN * sin_B + fric_B) / (ma_h * eff_h)
        F_ctrl_A = (W_kN * sin_A + fric_A) / (ma_h * eff_h)
        F_vert   = W_kN / (ma_v * eff_v)

        F_anc_A = f['T_A']
        F_anc_B = f['T_B'] + F_ctrl_B * eff_h * ma_h / 2.0
        F_belay = W_kN

        SF_A  = ROPE_MBS / f['T_A']  if f['T_A']  > 0.01 else 999.0
        SF_B  = ROPE_MBS / f['T_B']  if f['T_B']  > 0.01 else 999.0
        SF_bl = ROPE_MBS / F_belay

        return {
            'W_kN': W_kN, 'x_m': x_m, 'y_P': y_P, 'S': S,
            'T_A': f['T_A'],   'T_B': f['T_B'],
            'v_angle': f['v_angle'],
            'alpha_A': f['alpha_A'], 'alpha_B': f['alpha_B'],
            'uA': f['uA'],     'uB': f['uB'],
            'len_PA': f['len_PA'], 'len_PB': f['len_PB'],
            'F_ctrl_A': F_ctrl_A,  'F_ctrl_B': F_ctrl_B,
            'F_vert': F_vert,
            'F_anc_A': F_anc_A, 'F_anc_B': F_anc_B,
            'F_belay': F_belay,
            'SF_A': SF_A, 'SF_B': SF_B, 'SF_bl': SF_bl,
            'eff_h': eff_h, 'eff_v': eff_v,
            'ma_h': ma_h,   'ma_v': ma_v,
            'n_h': n_h,     'n_v': n_v,
        }

    # ── Conversión metros ↔ píxeles ───────────────────────────────────

    def _ppm(self):
        return SPAN_SCR / self.span_m

    def _to_scr(self, x_m, y_m):
        """Convierte (x_m, y_m) en el sistema físico a píxeles de pantalla."""
        ppm = self._ppm()
        return int(ANC_A_X + x_m * ppm), int(BASE_Y - y_m * ppm)

    # ── Helpers de dibujo ─────────────────────────────────────────────

    def _anchor(self, sx, sy, label, color):
        """Dibuja anclaje con diamante y etiqueta."""
        sz = 11
        pts = [(sx, sy - sz), (sx + sz, sy), (sx, sy + sz), (sx - sz, sy)]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, C['white'], pts, 2)
        # Perno de anclaje vertical
        pygame.draw.line(self.screen, color, (sx, sy - sz), (sx, sy - sz - 10), 3)
        # Placa de anclaje
        pygame.draw.rect(self.screen, color, (sx - 14, sy - sz - 18, 28, 8),
                         border_radius=3)
        surf = self.font_xs.render(label, True, color)
        self.screen.blit(surf, (sx - surf.get_width() // 2, sy - sz - 33))

    def _carriage(self, sx, sy):
        """Dibuja el carriage (polea doble de travesía)."""
        # Dos poleas sobre la highline
        pygame.draw.circle(self.screen, C['primary'], (sx - 9, sy), CARRIAGE_R, 3)
        pygame.draw.circle(self.screen, C['primary'], (sx + 9, sy), CARRIAGE_R, 3)
        pygame.draw.circle(self.screen, C['primary'], (sx - 9, sy), 3)
        pygame.draw.circle(self.screen, C['primary'], (sx + 9, sy), 3)
        # Barra inferior conectora
        pygame.draw.rect(self.screen, C['primary'],
                         (sx - 9, sy + CARRIAGE_R - 1, 18, 7), border_radius=2)
        # Gancho de carga
        pygame.draw.line(self.screen, C['primary'],
                         (sx, sy + CARRIAGE_R + 6), (sx, sy + HOOK_LEN), 3)
        # Argolla del gancho
        pygame.draw.circle(self.screen, C['primary'],
                            (sx, sy + HOOK_LEN), 5, 2)

    def _load_box(self, sx, sy, kg):
        """Dibuja camilla con víctima."""
        w, h = 72, 50
        rect = pygame.Rect(sx - w // 2, sy, w, h)
        pygame.draw.rect(self.screen, (100, 25, 25), rect, border_radius=5)
        pygame.draw.rect(self.screen, C['danger'], rect, 2, border_radius=5)
        # Cruz médica
        cx, cy = sx, sy + h // 2
        pygame.draw.rect(self.screen, C['text'],
                         (cx - 11, cy - 3, 22, 6), border_radius=2)
        pygame.draw.rect(self.screen, C['text'],
                         (cx - 3, cy - 11, 6, 22), border_radius=2)
        # Etiqueta de peso debajo
        sur = self.font_xs.render(f'{kg} kg', True, C['warning'])
        self.screen.blit(sur, (sx - sur.get_width() // 2, sy + h + 4))

    def _pulley(self, sx, sy, r=7, color=None):
        """Dibuja polea (círculo de redirección)."""
        c = color or C['primary']
        pygame.draw.circle(self.screen, c, (sx, sy), r, 2)
        pygame.draw.circle(self.screen, c, (sx, sy), 3)

    def _arrow(self, x1, y1, dx, dy, color, lw=2, label='', lo=(5, -12)):
        """Flecha vectorial desde (x1,y1) con desplazamiento (dx,dy)."""
        x2, y2 = int(x1 + dx), int(y1 + dy)
        pygame.draw.line(self.screen, color, (int(x1), int(y1)), (x2, y2), lw)
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            ux, uy = dx / length, dy / length
            px, py = -uy, ux
            hs = 8
            p1 = (int(x2 - ux*hs + px*hs*0.5), int(y2 - uy*hs + py*hs*0.5))
            p2 = (int(x2 - ux*hs - px*hs*0.5), int(y2 - uy*hs - py*hs*0.5))
            pygame.draw.polygon(self.screen, color, [(x2, y2), p1, p2])
        if label:
            surf = self.font_xs.render(label, True, color)
            self.screen.blit(surf,
                             (int(x1 + dx*0.55) + lo[0],
                              int(y1 + dy*0.55) + lo[1]))

    def _txt(self, s, x, y, color=None, font=None):
        surf = (font or self.font_med).render(s, True, color or C['text'])
        self.screen.blit(surf, (x, y))
        return surf.get_height()

    # ── Escena ────────────────────────────────────────────────────────

    def _draw_scene(self, ph):
        """Dibuja toda la escena: terreno, cuerdas, carriage y fuerzas."""
        ppm = self._ppm()

        # Posiciones en pantalla
        ax, ay = self._to_scr(0,           self.h_A)
        bx, by = self._to_scr(self.span_m, self.h_B)
        px, py = self._to_scr(ph['x_m'],   ph['y_P'])

        # Posición de la víctima (profundidad de cuelgue)
        drop_px  = int(self.load_drop_m * ppm)
        hook_y   = py + HOOK_LEN             # donde termina el gancho
        ly_raw   = hook_y + drop_px          # parte superior de la caja (sin clamp)
        at_ground = ly_raw > GROUND_Y - 62
        ly       = min(ly_raw, GROUND_Y - 62)

        # ── Terreno y cañón ───────────────────────────────────────────
        # Pared izquierda (anclaje A)
        cliff_a = [(0, ay + 14), (ax + 36, ay + 14),
                   (ax + 42, GROUND_Y), (0, GROUND_Y)]
        pygame.draw.polygon(self.screen, (38, 48, 62), cliff_a)
        pygame.draw.lines(self.screen, (80, 95, 115), False,
                          [(0, ay + 14), (ax + 36, ay + 14)], 2)

        # Pared derecha (anclaje B)
        cliff_b = [(bx - 36, by + 14), (SCENE_W, by + 14),
                   (SCENE_W, GROUND_Y), (bx - 42, GROUND_Y)]
        pygame.draw.polygon(self.screen, (38, 48, 62), cliff_b)
        pygame.draw.lines(self.screen, (80, 95, 115), False,
                          [(bx - 36, by + 14), (SCENE_W, by + 14)], 2)

        # Línea y relleno del fondo del cañón
        pygame.draw.line(self.screen, (75, 88, 108),
                         (0, GROUND_Y), (SCENE_W, GROUND_Y), 2)
        for hx in range(6, SCENE_W, 22):
            pygame.draw.line(self.screen, (55, 65, 82),
                             (hx, GROUND_Y + 1), (hx + 14, GROUND_Y + 13), 1)
        surf_ab = self.font_xs.render('CAÑÓN / ABISMO', True, (65, 78, 98))
        self.screen.blit(surf_ab,
                         (SCENE_W // 2 - surf_ab.get_width() // 2, GROUND_Y + 5))

        # Escalera de referencia vertical en A
        ref_y_px = int(self.h_A * ppm)
        if ref_y_px > 8:
            pygame.draw.line(self.screen, C['grid'],
                             (ax - 28, ay), (ax - 28, by), 1)
            pygame.draw.line(self.screen, C['grid'],
                             (ax - 32, ay), (ax - 24, ay), 1)
            pygame.draw.line(self.screen, C['grid'],
                             (ax - 32, by), (ax - 24, by), 1)
            surf_h = self.font_xs.render(f'{self.h_A:.1f} m', True, C['grid'])
            self.screen.blit(surf_h,
                             (ax - 52, (ay + by) // 2 - 5))

        # ── Belay line (verde) ────────────────────────────────────────
        bel_off = -20  # desplazamiento lateral para distinguirla
        pygame.draw.line(self.screen, C['accent'],
                         (ax + 5, ay), (px + bel_off, py), 2)
        pygame.draw.line(self.screen, C['accent'],
                         (px + bel_off, py), (px + bel_off, ly), 2)
        pygame.draw.circle(self.screen, C['accent'], (px + bel_off, py), 4)
        mid_bx = (ax + 5 + px + bel_off) // 2
        mid_by = (ay + py) // 2
        surf_bl = self.font_xs.render('Belay', True, C['accent'])
        self.screen.blit(surf_bl,
                         (mid_bx - surf_bl.get_width() // 2, mid_by - 14))

        # ── Highline — tramos A-P y P-B ───────────────────────────────
        pygame.draw.line(self.screen, C['rope'], (ax, ay), (px, py), 5)
        pygame.draw.line(self.screen, C['rope'], (px, py), (bx, by), 5)

        # Longitudes de tramos
        m_ap_x = (ax + px) // 2
        m_ap_y = (ay + py) // 2
        m_pb_x = (px + bx) // 2
        m_pb_y = (py + by) // 2
        self._txt(f'{ph["len_PA"]:.1f} m', m_ap_x - 16, m_ap_y - 18,
                  C['rope'], self.font_xs)
        self._txt(f'{ph["len_PB"]:.1f} m', m_pb_x - 16, m_pb_y - 18,
                  C['rope'], self.font_xs)

        # ── Cuerda de control horizontal (azul, hacia B) ──────────────
        ctrl_col   = C['info']
        ctrl_end_x = bx + 8
        ctrl_end_y = by - 30
        pygame.draw.line(self.screen, ctrl_col,
                         (px, py), (ctrl_end_x, ctrl_end_y), 2)
        self._pulley(ctrl_end_x, ctrl_end_y, r=6, color=ctrl_col)
        surf_mah = self.font_xs.render(
            f'VM {MA_HORIZ[self.ma_idx]["label"].split()[0]}', True, ctrl_col)
        self.screen.blit(surf_mah,
                         (ctrl_end_x - surf_mah.get_width() // 2,
                          ctrl_end_y - 22))

        # ── Cuerda vertical de izado/descenso (dorado) ────────────────
        vert_col = (240, 195, 55)

        # Segmento de carga: gancho → víctima
        pygame.draw.line(self.screen, vert_col,
                         (px, hook_y), (px, ly), 4)

        # Polea de redirección en el gancho del carriage
        self._pulley(px, hook_y, r=7, color=vert_col)

        # Segmento haul: desde redirect hacia anclaje B (VM vert.)
        haul_end_x = bx + 8
        haul_end_y = by + 22
        pygame.draw.line(self.screen, vert_col,
                         (px, hook_y), (haul_end_x, haul_end_y), 2)
        self._pulley(haul_end_x, haul_end_y, r=6, color=vert_col)
        surf_mav = self.font_xs.render(
            f'VM {MA_VERT[self.ma_vert_idx]["label"].split()[0]}', True, vert_col)
        self.screen.blit(surf_mav,
                         (haul_end_x - surf_mav.get_width() // 2,
                          haul_end_y + 8))

        # Indicador de profundidad de cuelgue
        if drop_px > 30:
            mid_y = (hook_y + ly) // 2
            surf_d = self.font_xs.render(f'{self.load_drop_m:.1f} m', True, vert_col)
            self.screen.blit(surf_d, (px + 10, mid_y - 6))

        # Aviso si la víctima toca el suelo
        if at_ground:
            surf_gnd = self.font_sm.render('SUELO', True, C['danger'])
            self.screen.blit(surf_gnd, (px - surf_gnd.get_width() // 2, ly - 18))

        # ── Anclajes ──────────────────────────────────────────────────
        self._anchor(ax, ay, 'ANCLAJE A', C['warning'])
        self._anchor(bx, by, 'ANCLAJE B', C['info'])

        # ── Carriage ─────────────────────────────────────────────────
        self._carriage(px, py)

        # ── Víctima / camilla ─────────────────────────────────────────
        self._load_box(px, ly, self.load_kg)

        # ── Vectores de fuerza ────────────────────────────────────────
        scale = 24.0 / max(ph['W_kN'], 0.1)

        # Peso W (desde centro de la caja hacia abajo)
        cx_box = px
        cy_box = ly + 25
        self._arrow(cx_box, cy_box, 0, ph['W_kN'] * scale * 1.4,
                    C['danger'], lw=3, label=f'{ph["W_kN"]:.2f} kN')

        # Tensión T_A
        uA = ph['uA']
        arr_A = min(ph['T_A'] * scale, 105)
        self._arrow(px, py, uA[0] * arr_A, -uA[1] * arr_A,
                    C['warning'], lw=3, label=f'T_A={ph["T_A"]:.1f}')

        # Tensión T_B
        uB = ph['uB']
        arr_B = min(ph['T_B'] * scale, 105)
        self._arrow(px, py, uB[0] * arr_B, -uB[1] * arr_B,
                    C['warning'], lw=3, label=f'T_B={ph["T_B"]:.1f}')

        # ── Ángulo V (indicador circular sobre el carriage) ───────────
        v = ph['v_angle']
        v_col = (C['accent'] if v < V_WARN else
                 C['warning'] if v < V_DANGER else C['danger'])
        pygame.draw.circle(self.screen, v_col, (px, py), 24, 2)
        surf_v = self.font_sm.render(f'V={v:.0f}°', True, v_col)
        self.screen.blit(surf_v,
                         (px - surf_v.get_width() // 2, py - 40))

        # ── Indicador de dirección de movimiento ──────────────────────
        if self.move_dir > 0:
            surf_dir = self.font_sm.render('→ hacia B', True, C['info'])
            self.screen.blit(surf_dir, (px + 32, py - 20))
        elif self.move_dir < 0:
            surf_dir = self.font_sm.render('hacia A ←', True, C['info'])
            self.screen.blit(surf_dir, (px - surf_dir.get_width() - 32, py - 20))

        # Indicador de subida / bajada
        if self.drop_dir > 0:
            surf_dr = self.font_sm.render('▼ bajando', True, vert_col)
            self.screen.blit(surf_dr, (px + 12, ly + 58))
        elif self.drop_dir < 0:
            surf_dr = self.font_sm.render('▲ subiendo', True, vert_col)
            self.screen.blit(surf_dr, (px + 12, ly - 20))

        # ── Escala gráfica ────────────────────────────────────────────
        scale_px = int(10.0 * ppm)
        sx0 = ANC_A_X
        sy0 = GROUND_Y + 20
        pygame.draw.line(self.screen, C['anchor'],
                         (sx0, sy0), (sx0 + scale_px, sy0), 2)
        pygame.draw.line(self.screen, C['anchor'],
                         (sx0, sy0 - 4), (sx0, sy0 + 4), 2)
        pygame.draw.line(self.screen, C['anchor'],
                         (sx0 + scale_px, sy0 - 4),
                         (sx0 + scale_px, sy0 + 4), 2)
        self._txt('10 m', sx0 + scale_px // 2 - 14, sy0 + 6,
                  C['anchor'], self.font_xs)

    # ── Panel de información ──────────────────────────────────────────

    def _draw_panel(self, ph):
        """Panel derecho con cálculos y estado completo del sistema."""
        px0  = PANEL_X
        py0  = 36
        pw   = PANEL_W
        ph_h = HEIGHT - py0 - 8
        pygame.draw.rect(self.screen, C['panel'],
                         (px0, py0, pw, ph_h), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (px0, py0, pw, ph_h), 1, border_radius=8)

        x0 = px0 + 12
        y  = py0 + 10

        def sep():
            nonlocal y
            pygame.draw.line(self.screen, C['grid'],
                             (x0, y), (px0 + pw - 12, y), 1)
            y += 6

        def heading(s, col=None):
            nonlocal y
            surf = self.font_big.render(s, True, col or C['primary'])
            self.screen.blit(surf, (x0, y))
            y += surf.get_height() + 4

        def line_t(s, col=None, fnt=None):
            nonlocal y
            surf = (fnt or self.font_med).render(s, True, col or C['text'])
            self.screen.blit(surf, (x0 + 4, y))
            y += surf.get_height() + 3

        def kv(label, value, lc=None, vc=None):
            nonlocal y
            sl = self.font_med.render(label, True, lc or C['anchor'])
            sv = self.font_med.render(value, True, vc or C['warning'])
            self.screen.blit(sl, (x0 + 4, y))
            self.screen.blit(sv, (x0 + 4 + sl.get_width() + 4, y))
            y += sl.get_height() + 3

        # ── Identificación ────────────────────────────────────────────
        heading('English Reeve')
        kv('VM horizontal:', MA_HORIZ[self.ma_idx]['label'])
        kv('VM vertical:',   MA_VERT[self.ma_vert_idx]['label'],
           vc=(240, 195, 55))
        kv('Carga total:',
           f'{self.load_kg} kg  = {ph["W_kN"]:.2f} kN',
           vc=C['danger'])
        kv('Vano A–B:',      f'{self.span_m:.0f} m')
        kv('Alt. anclaje A:',f'{self.h_A:.1f} m')
        kv('Flecha central:',
           f'{self.sag_pct:.1f}% ({self.sag_pct/100*self.span_m:.1f} m)')
        kv('Posición carriage:', f'{self.pos_pct:.1f}% de A',
           vc=C['info'])
        kv('Profundidad cuelgue:', f'{self.load_drop_m:.1f} m',
           vc=(240, 195, 55))
        sep()

        # ── Highline ─────────────────────────────────────────────────
        heading('Tensiones highline')
        kv('T_A (tramo A–P):', f'{ph["T_A"]:.2f} kN', vc=C['warning'])
        kv('T_B (tramo P–B):', f'{ph["T_B"]:.2f} kN', vc=C['warning'])
        kv('Long. total cuerda:', f'{ph["S"]:.2f} m')
        v = ph['v_angle']
        v_col = (C['accent'] if v < V_WARN else
                 C['warning'] if v < V_DANGER else C['danger'])
        kv('Ángulo V:', f'{v:.1f}°', vc=v_col)
        if v >= V_DANGER:
            line_t('⚠ PELIGROSO — aumentar flecha', C['danger'], self.font_sm)
        elif v >= V_WARN:
            line_t('! ángulo elevado — controlar', C['warning'], self.font_sm)
        sep()

        # ── Sistema horizontal ────────────────────────────────────────
        heading('Control horizontal (haul line)')
        eff_h_s = f'{ph["eff_h"]:.1%}' if self.friction else 'ideal'
        kv('VM:', f'{ph["ma_h"]}:1  ef.: {eff_h_s}')
        kv('F → B:',
           f'{ph["F_ctrl_B"]:.2f} kN ({ph["F_ctrl_B"]*1000/G:.0f} kg)',
           vc=C['info'])
        kv('F → A:',
           f'{ph["F_ctrl_A"]:.2f} kN ({ph["F_ctrl_A"]*1000/G:.0f} kg)',
           vc=C['info'])
        sep()

        # ── Sistema vertical ─────────────────────────────────────────
        heading('Sistema vertical (izado / descenso)', col=(240, 195, 55))
        eff_v_s = f'{ph["eff_v"]:.1%}' if self.friction else 'ideal'
        kv('VM vert.:', f'{ph["ma_v"]}:1  ef.: {eff_v_s}', vc=(240, 195, 55))
        kv('F izar/descender:',
           f'{ph["F_vert"]:.2f} kN ({ph["F_vert"]*1000/G:.0f} kg)',
           vc=(240, 195, 55))
        kv('Profundidad actual:', f'{self.load_drop_m:.1f} m',
           vc=(240, 195, 55))
        line_t('[PgUp] Subir   [PgDn] Bajar', C['anchor'], self.font_xs)
        line_t('[4] 2:1   [5] 3:1   [6] 4:1', C['anchor'], self.font_xs)
        sep()

        # ── Cargas en anclajes ────────────────────────────────────────
        heading('Cargas en anclajes')
        kv('Anclaje A:', f'{ph["F_anc_A"]:.2f} kN', vc=C['warning'])
        kv('Anclaje B:', f'{ph["F_anc_B"]:.2f} kN', vc=C['warning'])
        kv('Belay (peor caso):', f'{ph["F_belay"]:.2f} kN', vc=C['accent'])
        sep()

        # ── Factores de seguridad ─────────────────────────────────────
        heading('Factores de seguridad')

        def sf_col(sf):
            return (C['accent'] if sf >= 15.0 else
                    C['warning'] if sf >= 10.0 else C['danger'])

        kv('FS highline T_A:', f'{ph["SF_A"]:.1f}:1',  vc=sf_col(ph['SF_A']))
        kv('FS highline T_B:', f'{ph["SF_B"]:.1f}:1',  vc=sf_col(ph['SF_B']))
        kv('FS belay:',        f'{ph["SF_bl"]:.1f}:1', vc=sf_col(ph['SF_bl']))
        kv('MBS cuerda:',      f'{ROPE_MBS:.0f} kN')
        sep()

        # ── Reglas de seguridad ───────────────────────────────────────
        heading('Reglas de seguridad')
        rules = [
            '✓ Belay y highline siempre independientes',
            '✓ FS ≥ 15:1  •  Ángulo V < 120°',
            '✓ PCD activo — impide retroceso',
            '✓ VM vertical independiente del horizontal',
        ]
        for r in rules:
            line_t(r, C['accent'], self.font_xs)
        sep()

        fr_lbl = 'ON' if self.friction else 'OFF'
        fr_col = C['secondary'] if self.friction else C['anchor']
        line_t(f'[F] Fricción poleas: {fr_lbl}', fr_col, self.font_sm)

    # ── Dibujo principal ──────────────────────────────────────────────

    def draw(self):
        self.screen.fill(C['bg'])
        ph = self._physics()

        # Título centrado en la escena
        surf = self.font_title.render(
            'FÍSICA DEL RESCATE — Sistema English Reeve', True, C['primary'])
        self.screen.blit(surf,
                         (SCENE_W // 2 - surf.get_width() // 2, 8))

        self._draw_scene(ph)
        self._draw_panel(ph)

        # ── Barra de controles inferior ───────────────────────────────
        ctrl_y = HEIGHT - 42
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 6, SCENE_W, 48))
        pygame.draw.line(self.screen, C['grid'],
                         (0, ctrl_y - 6), (SCENE_W, ctrl_y - 6), 1)

        controls = [
            ('[←/→] Mover',           None),
            ('[↑/↓] Carga',            None),
            ('[A/Z] Alt.A',            None),
            ('[S/X] Flecha',           None),
            ('[L/K] Vano',             None),
            ('[1/2/3] VM horiz.',      None),
            ('[4/5/6] VM vert.',       (240, 195, 55)),
            ('[PgU/PgD] ▲▼ Víctima',  (240, 195, 55)),
            ('[F] Fricción: ' + ('ON' if self.friction else 'OFF'),
             C['secondary'] if self.friction else None),
            ('[R] Reset',              None),
        ]
        cx = 8
        for txt, col in controls:
            c    = col or C['dark_text']
            surf = self.font_xs.render(txt, True, c)
            if cx + surf.get_width() + 8 > SCENE_W:
                break
            self.screen.blit(surf, (cx, ctrl_y + 8))
            cx += surf.get_width() + 12

        pygame.display.flip()

    # ── Bucle principal ───────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            self.move_dir = 0
            self.drop_dir = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if   event.key == pygame.K_ESCAPE: running = False
                    elif event.key == pygame.K_1: self.ma_idx = 0
                    elif event.key == pygame.K_2: self.ma_idx = 1
                    elif event.key == pygame.K_3: self.ma_idx = 2
                    elif event.key == pygame.K_4: self.ma_vert_idx = 0
                    elif event.key == pygame.K_5: self.ma_vert_idx = 1
                    elif event.key == pygame.K_6: self.ma_vert_idx = 2
                    elif event.key == pygame.K_f: self.friction = not self.friction
                    elif event.key == pygame.K_r: self.pos_pct = 50.0

            keys = pygame.key.get_pressed()

            # Movimiento horizontal del carriage
            if keys[pygame.K_RIGHT]:
                self.pos_pct = min(self.pos_pct + 0.4, 99.0)
                self.move_dir = 1
            if keys[pygame.K_LEFT]:
                self.pos_pct = max(self.pos_pct - 0.4, 1.0)
                self.move_dir = -1

            # Ajuste de carga
            if keys[pygame.K_UP]:
                self.load_kg = min(self.load_kg + 1, 400)
            if keys[pygame.K_DOWN]:
                self.load_kg = max(self.load_kg - 1, 40)

            # Altura anclaje A
            if keys[pygame.K_a]:
                self.h_A = min(self.h_A + 0.1, 30.0)
            if keys[pygame.K_z]:
                self.h_A = max(self.h_A - 0.1, 0.0)

            # Flecha de la highline
            if keys[pygame.K_s]:
                self.sag_pct = min(self.sag_pct + 0.05, 20.0)
            if keys[pygame.K_x]:
                self.sag_pct = max(self.sag_pct - 0.05, 0.5)

            # Vano A-B
            if keys[pygame.K_l]:
                self.span_m = min(self.span_m + 0.2, 100.0)
            if keys[pygame.K_k]:
                self.span_m = max(self.span_m - 0.2, 20.0)

            # Subir / bajar la víctima
            if keys[pygame.K_PAGEUP]:
                self.load_drop_m = max(self.load_drop_m - 0.12, 1.0)
                self.drop_dir = -1
            if keys[pygame.K_PAGEDOWN]:
                self.load_drop_m = min(self.load_drop_m + 0.12, 50.0)
                self.drop_dir = 1

            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = EnglishReeveSimulator()
    sim.run()
