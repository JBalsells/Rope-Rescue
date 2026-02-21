"""
╔══════════════════════════════════════════════════════════════════════╗
║  FISICA DEL RESCATE · Modulo 13: Tripode y Marco en A (Pygame)     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulacion interactiva de las fuerzas de compresion en tripodes    ║
║  y marcos en A usados en rescate vertical.                          ║
║                                                                      ║
║  Fisica:                                                             ║
║   Tripode (3 patas):                                                 ║
║    • F_pata = W / (3 * cos(phi))                                    ║
║    • H_pata = W * tan(phi) / 3                                      ║
║    • V_pata = W / 3                                                  ║
║                                                                      ║
║   Marco en A (2 patas):                                              ║
║    • F_pata = W / (2 * cos(phi))                                    ║
║    • H_pata = W * tan(phi) / 2                                      ║
║    • V_pata = W / 2                                                  ║
║                                                                      ║
║   phi = angulo de cada pata respecto a la vertical                  ║
║   A mayor apertura → mayor compresion → riesgo de pandeo            ║
║   Pandeo critico (Euler): F_cr = pi^2 * E * I / L^2                ║
║                                                                      ║
║  Controles:                                                          ║
║   [Izq/Der]  Ajustar angulo de apertura (phi)                      ║
║   [Arr/Abj]  Aumentar / reducir masa                                ║
║   [T]         Alternar Tripode / Marco en A                         ║
║   [L]         Ajustar longitud de patas                              ║
║   [R]         Reiniciar                                              ║
║   [ESC]       Salir                                                  ║
║                                                                      ║
║  Ejecutar:  python 13_tripode_marco_en_a.py                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import pygame
from config import PG_COLORS as C, G

WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Limites y constantes ────────────────────────────────────────────
ALUMINUM_TUBE_CAPACITY = 15.0   # kN  capacidad tipica tubo aluminio rescate
EULER_EI = 4500.0               # N*m^2  rigidez flexional tipica tubo aluminio
                                # (E~70GPa, I~64e-9 m^4 para tubo 48mm x 3mm)

# ── Zonas del layout (pixeles) ──────────────────────────────────────
SCENE_L, SCENE_R = 40, 780
SCENE_T, SCENE_B = 100, 520

GRAPH_L, GRAPH_R = 40, 780
GRAPH_T, GRAPH_B = 555, 810

PANEL_L = 810
PANEL_T = 100


# ══════════════════════════════════════════════════════════════════════
#  Fisica del tripode / marco en A
# ══════════════════════════════════════════════════════════════════════

def compute_forces(phi_deg, mass_kg, n_legs, leg_length_m):
    """
    Calcula todas las fuerzas en la estructura.
    phi_deg:      angulo de cada pata respecto a la vertical
    mass_kg:      masa colgada del apice
    n_legs:       3 (tripode) o 2 (marco en A)
    leg_length_m: longitud de cada pata en metros
    """
    W_kN = mass_kg * G / 1000.0
    phi_rad = math.radians(phi_deg)

    cos_phi = math.cos(phi_rad)
    sin_phi = math.sin(phi_rad)
    tan_phi = math.tan(phi_rad) if cos_phi > 1e-6 else 999.0

    # Fuerza de compresion por pata
    if cos_phi > 1e-4:
        F_leg = W_kN / (n_legs * cos_phi)
    else:
        F_leg = 999.0

    # Componente vertical por pata
    V_leg = W_kN / n_legs

    # Fuerza horizontal (hacia afuera) por pata
    H_leg = W_kN * tan_phi / n_legs

    # Altura efectiva del apice
    height = leg_length_m * cos_phi

    # Radio de la base (distancia de cada pie al centro en el suelo)
    base_radius = leg_length_m * sin_phi

    # Pandeo de Euler: F_cr = pi^2 * EI / L^2
    F_euler_kN = (math.pi ** 2 * EULER_EI / (leg_length_m ** 2)) / 1000.0

    # Factor de seguridad contra pandeo
    sf_buckling = F_euler_kN / F_leg if F_leg > 0.001 else 999.0

    # Factor de seguridad contra capacidad del tubo
    sf_tube = ALUMINUM_TUBE_CAPACITY / F_leg if F_leg > 0.001 else 999.0

    return {
        'W_kN':         W_kN,
        'phi_deg':      phi_deg,
        'phi_rad':      phi_rad,
        'n_legs':       n_legs,
        'F_leg':        F_leg,
        'V_leg':        V_leg,
        'H_leg':        H_leg,
        'height':       height,
        'base_radius':  base_radius,
        'F_euler_kN':   F_euler_kN,
        'sf_buckling':  sf_buckling,
        'sf_tube':      sf_tube,
        'leg_length':   leg_length_m,
    }


# ══════════════════════════════════════════════════════════════════════
#  Utilidades de dibujo
# ══════════════════════════════════════════════════════════════════════

def lerp_color(c1, c2, t):
    """Interpolacion lineal entre dos colores RGB."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def force_color(F_leg, capacity=ALUMINUM_TUBE_CAPACITY):
    """Color segun peligrosidad de la compresion."""
    ratio = F_leg / capacity
    if ratio < 0.5:
        return C['accent']
    elif ratio < 0.75:
        return lerp_color(C['accent'], C['warning'], (ratio - 0.5) / 0.25)
    elif ratio < 1.0:
        return lerp_color(C['warning'], C['secondary'], (ratio - 0.75) / 0.25)
    else:
        return C['danger']


def draw_arrow(surface, color, start, end, width=2, head_size=10):
    """Dibuja una flecha desde start hasta end."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return

    # Direccion unitaria
    ux, uy = dx / length, dy / length
    # Perpendicular
    px, py = -uy, ux

    # Linea principal
    pygame.draw.line(surface, color, start, end, width)

    # Cabeza de flecha
    p1 = (int(end[0] - head_size * ux + head_size * 0.4 * px),
          int(end[1] - head_size * uy + head_size * 0.4 * py))
    p2 = (int(end[0] - head_size * ux - head_size * 0.4 * px),
          int(end[1] - head_size * uy - head_size * 0.4 * py))
    pygame.draw.polygon(surface, color, [end, p1, p2])


def draw_dashed_line(surface, color, start, end, width=1, dash_len=8, gap_len=5):
    """Dibuja una linea discontinua."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    d = 0.0
    while d < length:
        seg_end = min(d + dash_len, length)
        p1 = (int(start[0] + ux * d), int(start[1] + uy * d))
        p2 = (int(start[0] + ux * seg_end), int(start[1] + uy * seg_end))
        pygame.draw.line(surface, color, p1, p2, width)
        d += dash_len + gap_len


# ══════════════════════════════════════════════════════════════════════
#  Simulador principal
# ══════════════════════════════════════════════════════════════════════

class TripodSimulator:
    """Simulacion de fuerzas en tripode y marco en A para rescate."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Fisica del Rescate -- Tripode y Marco en A')
        self.clock = pygame.time.Clock()

        self.ft = pygame.font.SysFont('DejaVu Sans', 26, bold=True)
        self.fb = pygame.font.SysFont('DejaVu Sans', 18, bold=True)
        self.fm = pygame.font.SysFont('DejaVu Sans', 14)
        self.fs = pygame.font.SysFont('DejaVu Sans', 12)
        self.fx = pygame.font.SysFont('DejaVu Sans', 11)
        self.fi = pygame.font.SysFont('DejaVu Sans', 11, italic=True)

        self.reset()

    # ── Estado ─────────────────────────────────────────────────────

    def reset(self):
        self.phi_deg = 20.0         # angulo de apertura desde vertical
        self.mass_kg = 100          # masa colgada
        self.leg_length_m = 2.5     # longitud de cada pata (m)
        self.is_tripod = True       # True = tripode (3), False = marco en A (2)
        self.anim_time = 0.0        # para animaciones sutiles

    # ── Dibujado: escena del tripode/marco ──────────────────────────

    def _draw_scene(self, f):
        scn_cx = (SCENE_L + SCENE_R) // 2
        scn_w = SCENE_R - SCENE_L
        scn_h = SCENE_B - SCENE_T

        # Fondo de escena
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (SCENE_L - 5, SCENE_T - 5, scn_w + 10, scn_h + 10),
                         border_radius=6)

        # ── Escala de coordenadas ────────────────────────────────────
        # El tripode se dibuja de lado: apice arriba, pies abajo
        # Escala para que quepa bien
        max_dim = max(f['height'], f['base_radius'] * 2.2, 0.5)
        scale = min(scn_h * 0.6, scn_w * 0.35) / max_dim

        # Posicion del apice en pixeles
        apex_px = scn_cx
        apex_py = SCENE_T + 60

        # Posicion del suelo
        ground_py = apex_py + int(f['height'] * scale)
        ground_py = min(ground_py, SCENE_B - 50)

        # ── Suelo / borde ────────────────────────────────────────────
        # Representar el borde del hueco/pozo
        hole_half_w = 60
        hole_depth = 30

        # Suelo a los lados
        pygame.draw.line(self.screen, C['anchor'],
                         (SCENE_L + 10, ground_py),
                         (scn_cx - hole_half_w, ground_py), 3)
        pygame.draw.line(self.screen, C['anchor'],
                         (scn_cx + hole_half_w, ground_py),
                         (SCENE_R - 10, ground_py), 3)

        # Paredes del hueco
        pygame.draw.line(self.screen, C['anchor'],
                         (scn_cx - hole_half_w, ground_py),
                         (scn_cx - hole_half_w, ground_py + hole_depth), 2)
        pygame.draw.line(self.screen, C['anchor'],
                         (scn_cx + hole_half_w, ground_py),
                         (scn_cx + hole_half_w, ground_py + hole_depth), 2)
        pygame.draw.line(self.screen, (40, 40, 55),
                         (scn_cx - hole_half_w, ground_py + hole_depth),
                         (scn_cx + hole_half_w, ground_py + hole_depth), 1)

        # Sombreado bajo el suelo
        for i in range(6):
            alpha_col = lerp_color(C['anchor'], C['bg'], i / 6.0)
            y_hatch = ground_py + 3 + i * 4
            for side in [-1, 1]:
                start_x = scn_cx + side * hole_half_w
                end_x = scn_cx + side * (hole_half_w + 100 + i * 15)
                if side < 0:
                    start_x, end_x = end_x, start_x
                    start_x = max(start_x, SCENE_L + 10)
                else:
                    end_x = min(end_x, SCENE_R - 10)
                pygame.draw.line(self.screen, alpha_col,
                                 (start_x, y_hatch), (end_x, y_hatch), 1)

        # ── Linea vertical de referencia (eje vertical) ──────────────
        draw_dashed_line(self.screen, (50, 50, 70),
                         (apex_px, apex_py - 10),
                         (apex_px, ground_py + hole_depth), 1, 6, 4)

        # ── Patas del tripode/marco ──────────────────────────────────
        phi_rad = f['phi_rad']
        base_r_px = int(f['base_radius'] * scale)
        n_legs = f['n_legs']
        leg_col = force_color(f['F_leg'])

        if n_legs == 3:
            # Vista lateral: la pata trasera esta en el centro (vista de perfil)
            # Patas delanteras (2): se abren a izquierda y derecha
            # Pata trasera (1): va hacia "atras" (se muestra mas corta en perspectiva)
            leg_positions = []

            # Pata izquierda (delantera)
            foot_L = (apex_px - base_r_px, ground_py)
            leg_positions.append(('Pata 1 (izq)', foot_L, True))

            # Pata derecha (delantera)
            foot_R = (apex_px + base_r_px, ground_py)
            leg_positions.append(('Pata 2 (der)', foot_R, True))

            # Pata trasera (perspectiva: mas corta, mas centrada)
            persp_factor = 0.45  # acortamiento por perspectiva
            back_x = apex_px
            back_foot_y = apex_py + int(f['height'] * scale * 0.9)
            foot_B = (back_x, min(back_foot_y, ground_py))
            leg_positions.append(('Pata 3 (post)', foot_B, False))

        else:
            # Marco en A: solo 2 patas
            leg_positions = []
            foot_L = (apex_px - base_r_px, ground_py)
            foot_R = (apex_px + base_r_px, ground_py)
            leg_positions.append(('Pata 1 (izq)', foot_L, True))
            leg_positions.append(('Pata 2 (der)', foot_R, True))

        # Dibujar las patas
        leg_width = max(4, min(8, int(self.leg_length_m * 1.5)))
        for label, foot, is_front in leg_positions:
            col = leg_col if is_front else lerp_color(leg_col, C['bg'], 0.35)
            lw = leg_width if is_front else max(2, leg_width - 2)

            # Pata (tubo)
            pygame.draw.line(self.screen, col,
                             (apex_px, apex_py), foot, lw)

            # Borde mas claro para dar volumen
            highlight = lerp_color(col, C['white'], 0.25)
            if is_front:
                offset = -2 if foot[0] < apex_px else 2
                pygame.draw.line(self.screen, highlight,
                                 (apex_px + offset, apex_py),
                                 (foot[0] + offset, foot[1]),
                                 max(1, lw // 3))

            # Pie (base de la pata)
            pygame.draw.circle(self.screen, C['anchor'], foot, 5)
            pygame.draw.circle(self.screen, col, foot, 5, 2)

            # Etiqueta de la pata
            lbl_x = foot[0]
            lbl_y = foot[1] + 10
            if not is_front:
                lbl_y = foot[1] - 18
            s = self.fx.render(label, True, C['dark_text'])
            self.screen.blit(s, (lbl_x - s.get_width() // 2, lbl_y))

        # ── Apice (cabezal) ──────────────────────────────────────────
        pygame.draw.circle(self.screen, C['text'], (apex_px, apex_py), 10)
        pygame.draw.circle(self.screen, C['primary'], (apex_px, apex_py), 10, 2)
        pygame.draw.circle(self.screen, C['primary'], (apex_px, apex_py), 6)

        # ── Cuerda desde el apice hacia abajo (carga) ────────────────
        rope_bottom = ground_py + hole_depth - 5
        pygame.draw.line(self.screen, C['rope'],
                         (apex_px, apex_py + 10),
                         (apex_px, rope_bottom), 2)

        # Polea en el apice
        pygame.draw.circle(self.screen, C['rope'],
                           (apex_px, apex_py + 12), 4, 2)

        # ── Carga (persona/peso) ─────────────────────────────────────
        load_y = rope_bottom - 35
        load_w, load_h = 30, 26

        # Cuerpo de la carga
        pygame.draw.rect(self.screen, C['secondary'],
                         (apex_px - load_w // 2, load_y,
                          load_w, load_h), border_radius=4)
        pygame.draw.rect(self.screen, C['text'],
                         (apex_px - load_w // 2, load_y,
                          load_w, load_h), width=1, border_radius=4)

        # Texto de masa
        s = self.fx.render(f'{self.mass_kg}kg', True, C['white'])
        self.screen.blit(s, (apex_px - s.get_width() // 2,
                             load_y + load_h // 2 - s.get_height() // 2))

        # Flecha de peso hacia abajo
        w_arrow_top = load_y + load_h + 3
        w_arrow_bot = w_arrow_top + 25
        draw_arrow(self.screen, C['danger'],
                   (apex_px, w_arrow_top), (apex_px, w_arrow_bot), 2, 8)
        s = self.fx.render(f'W = {f["W_kN"]:.2f} kN', True, C['danger'])
        self.screen.blit(s, (apex_px + 10, w_arrow_top + 4))

        # ── Flechas de COMPRESION a lo largo de las patas ────────────
        arrow_scale = min(f['F_leg'] / ALUMINUM_TUBE_CAPACITY, 2.5)
        arrow_len = 25 + int(arrow_scale * 50)

        for label, foot, is_front in leg_positions:
            if not is_front and n_legs == 3:
                continue  # no dibujar flecha en la pata de perspectiva

            # Direccion de la pata (del apice al pie)
            dx = foot[0] - apex_px
            dy = foot[1] - apex_py
            leg_len_px = math.sqrt(dx * dx + dy * dy)
            if leg_len_px < 1:
                continue
            ux, uy = dx / leg_len_px, dy / leg_len_px

            # Flechas de compresion: dos flechas opuestas hacia el centro
            mid_x = (apex_px + foot[0]) / 2
            mid_y = (apex_py + foot[1]) / 2

            # Flecha desde el apice hacia el centro
            arr_start_1 = (int(apex_px + ux * 20), int(apex_py + uy * 20))
            arr_end_1 = (int(apex_px + ux * (20 + arrow_len)),
                         int(apex_py + uy * (20 + arrow_len)))
            draw_arrow(self.screen, leg_col, arr_start_1, arr_end_1, 2, 8)

            # Flecha desde el pie hacia el centro
            arr_start_2 = (int(foot[0] - ux * 20), int(foot[1] - uy * 20))
            arr_end_2 = (int(foot[0] - ux * (20 + arrow_len)),
                         int(foot[1] - uy * (20 + arrow_len)))
            draw_arrow(self.screen, leg_col, arr_start_2, arr_end_2, 2, 8)

            # Etiqueta de fuerza de compresion
            f_lbl_x = int(mid_x + (-uy) * 22)
            f_lbl_y = int(mid_y + ux * 22)
            s = self.fs.render(f'{f["F_leg"]:.2f} kN', True, leg_col)
            bg_rect = s.get_rect()
            bg_rect.center = (f_lbl_x, f_lbl_y)
            bg_rect.inflate_ip(8, 4)
            pygame.draw.rect(self.screen, C['bg'], bg_rect, border_radius=3)
            pygame.draw.rect(self.screen, leg_col, bg_rect, width=1,
                             border_radius=3)
            self.screen.blit(s, (f_lbl_x - s.get_width() // 2,
                                  f_lbl_y - s.get_height() // 2))

        # ── Flechas HORIZONTALES (empuje hacia afuera) en los pies ───
        h_arrow_scale = min(f['H_leg'] / (ALUMINUM_TUBE_CAPACITY * 0.5), 2.5)
        h_arrow_len = 15 + int(h_arrow_scale * 40)
        h_col = force_color(f['H_leg'], ALUMINUM_TUBE_CAPACITY * 0.5)

        for label, foot, is_front in leg_positions:
            if not is_front:
                continue
            direction = -1 if foot[0] < apex_px else 1
            arr_start = (foot[0], foot[1] - 3)
            arr_end = (foot[0] + direction * h_arrow_len, foot[1] - 3)
            draw_arrow(self.screen, h_col, arr_start, arr_end, 2, 7)

            s = self.fx.render(f'H={f["H_leg"]:.2f}kN', True, h_col)
            lbl_x = arr_end[0] + (5 * direction)
            if direction < 0:
                lbl_x = arr_end[0] - s.get_width() - 3
            self.screen.blit(s, (lbl_x, arr_end[1] - 14))

        # ── Arco del angulo phi ──────────────────────────────────────
        arc_r = 45
        # Angulo desde vertical para la pata derecha
        for foot_x_side in [1, -1]:
            if n_legs == 2 or foot_x_side == 1:
                # Arco desde la vertical hasta la pata
                n_arc = 30
                arc_pts = []
                start_angle = math.pi / 2  # vertical hacia abajo
                end_angle = math.pi / 2 - phi_rad * foot_x_side

                if foot_x_side > 0:
                    a_start = -math.pi / 2
                    a_end = -math.pi / 2 + phi_rad
                else:
                    a_start = -math.pi / 2 - phi_rad
                    a_end = -math.pi / 2

                for i in range(n_arc + 1):
                    a = a_start + (a_end - a_start) * i / n_arc
                    px = apex_px + int(arc_r * math.cos(a))
                    py = apex_py - int(arc_r * math.sin(a))
                    arc_pts.append((px, py))

                if len(arc_pts) > 1:
                    pygame.draw.lines(self.screen, C['warning'],
                                      False, arc_pts, 2)

        # Etiqueta del angulo
        angle_lbl_y = apex_py + arc_r + 8
        s = self.fm.render(f'phi = {f["phi_deg"]:.1f} deg', True, C['warning'])
        self.screen.blit(s, (apex_px - s.get_width() // 2, angle_lbl_y))

        # ── Cotas de altura y base ───────────────────────────────────
        # Altura
        cota_x = SCENE_R - 60
        draw_dashed_line(self.screen, C['info'],
                         (cota_x, apex_py), (cota_x, ground_py), 1, 5, 3)
        pygame.draw.line(self.screen, C['info'],
                         (cota_x - 4, apex_py), (cota_x + 4, apex_py), 1)
        pygame.draw.line(self.screen, C['info'],
                         (cota_x - 4, ground_py), (cota_x + 4, ground_py), 1)
        mid_h_y = (apex_py + ground_py) // 2
        s = self.fx.render(f'h={f["height"]:.2f}m', True, C['info'])
        self.screen.blit(s, (cota_x + 8, mid_h_y - 6))

        # Base
        if base_r_px > 5:
            cota_y = ground_py + 25
            draw_dashed_line(self.screen, C['info'],
                             (apex_px - base_r_px, cota_y),
                             (apex_px + base_r_px, cota_y), 1, 5, 3)
            pygame.draw.line(self.screen, C['info'],
                             (apex_px - base_r_px, cota_y - 4),
                             (apex_px - base_r_px, cota_y + 4), 1)
            pygame.draw.line(self.screen, C['info'],
                             (apex_px + base_r_px, cota_y - 4),
                             (apex_px + base_r_px, cota_y + 4), 1)
            s = self.fx.render(f'r={f["base_radius"]:.2f}m', True, C['info'])
            self.screen.blit(s,
                             (apex_px - s.get_width() // 2, cota_y + 6))

        # ── Titulo de la escena ──────────────────────────────────────
        mode_name = 'TRIPODE (3 patas)' if self.is_tripod else 'MARCO EN A (2 patas)'
        mode_col = C['primary'] if self.is_tripod else C['secondary']
        s = self.fb.render(f'Vista lateral: {mode_name}', True, mode_col)
        self.screen.blit(s, (SCENE_L + 10, SCENE_T + 5))

        # Indicador de estado de seguridad
        ratio = f['F_leg'] / ALUMINUM_TUBE_CAPACITY
        if ratio < 0.5:
            status = 'SEGURO'
            st_col = C['accent']
        elif ratio < 0.75:
            status = 'PRECAUCION'
            st_col = C['warning']
        elif ratio < 1.0:
            status = 'PELIGROSO'
            st_col = C['secondary']
        else:
            status = 'CRITICO - EXCEDE CAPACIDAD'
            st_col = C['danger']

        # Parpadeo si critico
        show_status = True
        if ratio >= 1.0:
            show_status = int(self.anim_time * 3) % 2 == 0

        if show_status:
            s = self.fb.render(f'[{status}]', True, st_col)
            bg_r = s.get_rect()
            bg_r.topleft = (SCENE_L + 10, SCENE_B - 35)
            bg_r.inflate_ip(12, 6)
            pygame.draw.rect(self.screen, C['bg'], bg_r, border_radius=4)
            pygame.draw.rect(self.screen, st_col, bg_r, width=2,
                             border_radius=4)
            self.screen.blit(s, (SCENE_L + 16, SCENE_B - 32))

        # Leyenda de compresion
        s = self.fx.render('>>> Compresion (a lo largo de la pata)', True,
                           leg_col)
        self.screen.blit(s, (SCENE_L + 10, SCENE_B - 15))
        s = self.fx.render('>>> Empuje horizontal (en el pie)', True, h_col)
        self.screen.blit(s, (SCENE_L + 300, SCENE_B - 15))

    # ── Dibujado: grafico fuerza vs angulo ──────────────────────────

    def _draw_graph(self, f):
        gx, gy = GRAPH_L, GRAPH_T
        gw = GRAPH_R - GRAPH_L
        gh = GRAPH_B - GRAPH_T

        # Fondo
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (gx - 5, gy - 5, gw + 10, gh + 10),
                         border_radius=6)

        # Titulo
        s = self.fm.render(
            'Fuerza de compresion por pata vs Angulo de apertura (phi)',
            True, C['text'])
        self.screen.blit(s, (gx + gw // 2 - s.get_width() // 2, gy + 2))

        # Area interna del grafico
        gx_i = gx + 70
        gw_i = gw - 90
        gy_i = gy + 22
        gh_i = gh - 52

        pygame.draw.rect(self.screen, (12, 12, 22),
                         (gx_i, gy_i, gw_i, gh_i))

        # ── Escalas ──────────────────────────────────────────────────
        max_angle = 75.0
        W_kN = f['W_kN']
        n_legs = f['n_legs']

        # Calcular max_force para la escala Y
        phi_max_rad = math.radians(max_angle)
        if math.cos(phi_max_rad) > 0.01:
            max_force_curve = W_kN / (n_legs * math.cos(phi_max_rad))
        else:
            max_force_curve = W_kN * 10
        max_force = max(max_force_curve * 1.1, ALUMINUM_TUBE_CAPACITY * 1.2, 5.0)
        max_force = min(max_force, 100.0)

        def map_x(angle_deg):
            return gx_i + int((angle_deg / max_angle) * gw_i)

        def map_y(force_kn):
            frac = force_kn / max_force
            return gy_i + gh_i - int(frac * gh_i)

        # ── Zonas coloreadas ─────────────────────────────────────────
        # Zona segura (fuerza < 50% capacidad)
        safe_limit_angle = None
        warn_limit_angle = None
        danger_limit_angle = None

        for test_deg in range(0, 76):
            test_rad = math.radians(test_deg)
            if math.cos(test_rad) > 0.01:
                test_f = W_kN / (n_legs * math.cos(test_rad))
            else:
                test_f = 999
            if safe_limit_angle is None and test_f > ALUMINUM_TUBE_CAPACITY * 0.5:
                safe_limit_angle = test_deg
            if warn_limit_angle is None and test_f > ALUMINUM_TUBE_CAPACITY * 0.75:
                warn_limit_angle = test_deg
            if danger_limit_angle is None and test_f > ALUMINUM_TUBE_CAPACITY:
                danger_limit_angle = test_deg

        # Dibujar zonas
        zone_data = []
        prev_x_px = gx_i
        if safe_limit_angle and safe_limit_angle < max_angle:
            sx = map_x(safe_limit_angle)
            zone_data.append((prev_x_px, sx, C['accent'], 0.08))
            prev_x_px = sx
        else:
            zone_data.append((prev_x_px, gx_i + gw_i, C['accent'], 0.08))

        if warn_limit_angle and warn_limit_angle < max_angle:
            sx = map_x(warn_limit_angle)
            zone_data.append((prev_x_px, sx, C['warning'], 0.08))
            prev_x_px = sx

        if danger_limit_angle and danger_limit_angle < max_angle:
            sx = map_x(danger_limit_angle)
            zone_data.append((prev_x_px, sx, C['secondary'], 0.08))
            prev_x_px = sx

        if prev_x_px < gx_i + gw_i:
            zone_data.append((prev_x_px, gx_i + gw_i, C['danger'], 0.10))

        for zx1, zx2, zcol, zalpha in zone_data:
            zone_surf = pygame.Surface((max(1, zx2 - zx1), gh_i), pygame.SRCALPHA)
            zone_surf.fill((*zcol, int(255 * zalpha)))
            self.screen.blit(zone_surf, (zx1, gy_i))

        # ── Grid horizontal ──────────────────────────────────────────
        force_ticks = []
        step = 2.0 if max_force < 20 else 5.0 if max_force < 50 else 10.0
        fv = step
        while fv < max_force:
            force_ticks.append(fv)
            fv += step

        for fv in force_ticks:
            yy = map_y(fv)
            if gy_i < yy < gy_i + gh_i:
                pygame.draw.line(self.screen, C['grid'],
                                 (gx_i, yy), (gx_i + gw_i, yy), 1)
                s = self.fx.render(f'{fv:.0f}', True, C['grid'])
                self.screen.blit(s, (gx_i - s.get_width() - 4, yy - 6))

        # Linea de capacidad del tubo
        cap_y = map_y(ALUMINUM_TUBE_CAPACITY)
        if gy_i < cap_y < gy_i + gh_i:
            draw_dashed_line(self.screen, C['danger'],
                             (gx_i, cap_y), (gx_i + gw_i, cap_y), 2, 8, 5)
            s = self.fx.render(f'Capacidad tubo: {ALUMINUM_TUBE_CAPACITY:.0f} kN',
                               True, C['danger'])
            self.screen.blit(s, (gx_i + gw_i - s.get_width() - 5, cap_y - 14))

        # ── Grid vertical ────────────────────────────────────────────
        for angle_tick in range(0, int(max_angle) + 1, 10):
            xx = map_x(angle_tick)
            pygame.draw.line(self.screen, C['grid'],
                             (xx, gy_i), (xx, gy_i + gh_i), 1)
            s = self.fx.render(f'{angle_tick} deg', True, C['grid'])
            self.screen.blit(s, (xx - s.get_width() // 2, gy_i + gh_i + 3))

        # Etiqueta eje Y
        s_y = self.fx.render('kN', True, C['text'])
        self.screen.blit(s_y, (gx_i - 20, gy_i - 14))

        # ── Curva: Tripode ───────────────────────────────────────────
        # Siempre dibujar ambas curvas para comparacion
        for n_legs_curve, curve_col, curve_label, is_active in [
            (3, C['primary'], 'Tripode (n=3)', self.is_tripod),
            (2, C['secondary'], 'Marco A (n=2)', not self.is_tripod),
        ]:
            pts = []
            N = 200
            for i in range(N):
                angle_deg = (i / (N - 1)) * max_angle
                angle_rad = math.radians(angle_deg)
                cos_a = math.cos(angle_rad)
                if cos_a > 0.01:
                    fv = W_kN / (n_legs_curve * cos_a)
                else:
                    fv = max_force
                px = map_x(angle_deg)
                py = map_y(min(fv, max_force))
                py = max(gy_i, min(py, gy_i + gh_i))
                pts.append((px, py))

            if len(pts) > 1:
                lw = 3 if is_active else 1
                alpha_col = curve_col if is_active else lerp_color(
                    curve_col, C['bg'], 0.5)
                pygame.draw.lines(self.screen, alpha_col, False, pts, lw)

        # ── Punto actual ─────────────────────────────────────────────
        cur_x = map_x(f['phi_deg'])
        cur_y = map_y(min(f['F_leg'], max_force))
        cur_y = max(gy_i, min(cur_y, gy_i + gh_i))

        # Lineas de referencia
        pygame.draw.line(self.screen, C['warning'],
                         (cur_x, gy_i), (cur_x, gy_i + gh_i), 2)
        draw_dashed_line(self.screen, C['warning'],
                         (gx_i, cur_y), (cur_x, cur_y), 1, 4, 3)

        # Punto
        pygame.draw.circle(self.screen, C['warning'], (cur_x, cur_y), 7)
        pygame.draw.circle(self.screen, C['white'], (cur_x, cur_y), 7, 2)

        # Etiqueta del punto actual
        lbl_text = f'phi={f["phi_deg"]:.0f} deg  F={f["F_leg"]:.2f} kN'
        s = self.fs.render(lbl_text, True, C['warning'])
        bg_r = s.get_rect()
        lbl_px = cur_x + 12
        lbl_py = cur_y - 18
        # Evitar que salga del area
        if lbl_px + s.get_width() > gx_i + gw_i - 5:
            lbl_px = cur_x - s.get_width() - 12
        if lbl_py < gy_i + 2:
            lbl_py = cur_y + 8
        bg_r.topleft = (lbl_px - 3, lbl_py - 2)
        bg_r.inflate_ip(8, 4)
        pygame.draw.rect(self.screen, C['bg'], bg_r, border_radius=3)
        pygame.draw.rect(self.screen, C['warning'], bg_r, width=1,
                         border_radius=3)
        self.screen.blit(s, (lbl_px, lbl_py))

        # ── Angulo de colapso (marca) ────────────────────────────────
        if danger_limit_angle and danger_limit_angle < max_angle:
            dx = map_x(danger_limit_angle)
            draw_dashed_line(self.screen, C['danger'],
                             (dx, gy_i), (dx, gy_i + gh_i), 1, 4, 4)
            s = self.fx.render(f'Limite: {danger_limit_angle} deg', True,
                               C['danger'])
            self.screen.blit(s, (dx + 4, gy_i + 4))

        # ── Leyenda ──────────────────────────────────────────────────
        leg_x = gx_i + 8
        leg_y = gy_i + 6
        for label, col in [('Tripode (n=3)', C['primary']),
                           ('Marco A (n=2)', C['secondary'])]:
            pygame.draw.line(self.screen, col,
                             (leg_x, leg_y + 5), (leg_x + 18, leg_y + 5), 2)
            s = self.fx.render(label, True, col)
            self.screen.blit(s, (leg_x + 22, leg_y))
            leg_y += 15

    # ── Dibujado: panel de datos ────────────────────────────────────

    def _draw_panel(self, f):
        px, py = PANEL_L, PANEL_T
        pw = WIDTH - PANEL_L - 15
        ph = GRAPH_B - PANEL_T + 10

        pygame.draw.rect(self.screen, C['panel'],
                         (px, py, pw, ph), border_radius=8)
        mode_col = C['primary'] if self.is_tripod else C['secondary']
        pygame.draw.rect(self.screen, mode_col,
                         (px, py, pw, ph), width=1, border_radius=8)

        x = px + 12
        y = py + 10

        def heading(text, color=C['primary']):
            nonlocal y
            s = self.fb.render(text, True, color)
            self.screen.blit(s, (x, y))
            y += 22

        def line(text, color=C['text']):
            nonlocal y
            s = self.fs.render(text, True, color)
            self.screen.blit(s, (x + 5, y))
            y += 16

        def line_small(text, color=C['dark_text']):
            nonlocal y
            s = self.fx.render(text, True, color)
            self.screen.blit(s, (x + 5, y))
            y += 13

        def sep():
            nonlocal y
            pygame.draw.line(self.screen, C['grid'],
                             (x, y + 2), (x + pw - 24, y + 2), 1)
            y += 7

        # ── Tipo de estructura ──────────────────────────────────────
        mode_name = 'TRIPODE (3 patas)' if self.is_tripod else 'MARCO EN A (2 patas)'
        heading(mode_name, mode_col)
        sep()

        # ── Parametros ──────────────────────────────────────────────
        heading('PARAMETROS')
        line(f'Angulo (phi):    {f["phi_deg"]:.1f} deg')
        line(f'Longitud pata:   {f["leg_length"]:.1f} m')
        line(f'Masa:            {self.mass_kg} kg')
        line(f'Peso (W):        {f["W_kN"]:.2f} kN', C['danger'])
        line(f'Numero de patas: {f["n_legs"]}')
        sep()

        # ── Geometria ───────────────────────────────────────────────
        heading('GEOMETRIA')
        line(f'Altura del apice:  {f["height"]:.2f} m', C['info'])
        line(f'Radio de base:     {f["base_radius"]:.2f} m', C['info'])
        sep()

        # ── Fuerzas ─────────────────────────────────────────────────
        f_col = force_color(f['F_leg'])
        heading('FUERZAS POR PATA')

        # Componente vertical
        line(f'V (vertical):     {f["V_leg"]:.2f} kN', C['accent'])

        # Compresion
        line(f'F (compresion):   {f["F_leg"]:.2f} kN', f_col)

        # Horizontal
        h_col = force_color(f['H_leg'], ALUMINUM_TUBE_CAPACITY * 0.5)
        line(f'H (horizontal):   {f["H_leg"]:.2f} kN', h_col)

        # Ratio fuerza/peso
        ratio_fw = f['F_leg'] / f['W_kN'] if f['W_kN'] > 0.001 else 0
        line(f'F/W ratio:        {ratio_fw:.2f}  ({ratio_fw*100:.0f}% del peso)',
             C['warning'])

        y += 2

        # Barra visual de compresion
        bar_w = pw - 30
        bar_h = 14
        s = self.fx.render('Compresion:', True, C['text'])
        self.screen.blit(s, (x + 3, y))
        y += 14
        bar_x = x + 5
        pygame.draw.rect(self.screen, (30, 30, 45),
                         (bar_x, y, bar_w - 10, bar_h), border_radius=2)
        fill_frac = min(f['F_leg'] / max(ALUMINUM_TUBE_CAPACITY * 1.3, 1), 1.0)
        fill_w = int((bar_w - 10) * fill_frac)
        if fill_w > 0:
            pygame.draw.rect(self.screen, f_col,
                             (bar_x, y, fill_w, bar_h), border_radius=2)

        # Marca de capacidad
        cap_x = bar_x + int((bar_w - 10) * (ALUMINUM_TUBE_CAPACITY /
                             max(ALUMINUM_TUBE_CAPACITY * 1.3, 1)))
        pygame.draw.line(self.screen, C['danger'],
                         (cap_x, y - 2), (cap_x, y + bar_h + 2), 2)
        s = self.fx.render(f'{ALUMINUM_TUBE_CAPACITY:.0f}kN', True, C['danger'])
        self.screen.blit(s, (cap_x + 3, y - 2))
        y += bar_h + 8
        sep()

        # ── Formulas ────────────────────────────────────────────────
        heading('FORMULAS', C['warning'])
        n = f['n_legs']
        line_small(f'F_pata = W / ({n} * cos(phi))', C['warning'])
        line_small(f'H_pata = W * tan(phi) / {n}', C['warning'])
        line_small(f'V_pata = W / {n}', C['warning'])
        line_small(f'F_pandeo = pi^2 * EI / L^2', C['info'])
        sep()

        # ── Seguridad ──────────────────────────────────────────────
        heading('SEGURIDAD')

        # Factor vs capacidad tubo
        if f['sf_tube'] >= 3.0:
            sf_col = C['accent']
            sf_status = 'OK'
        elif f['sf_tube'] >= 1.5:
            sf_col = C['warning']
            sf_status = 'BAJO'
        elif f['sf_tube'] >= 1.0:
            sf_col = C['secondary']
            sf_status = 'MINIMO'
        else:
            sf_col = C['danger']
            sf_status = 'EXCEDIDO'

        line(f'FS tubo:    {f["sf_tube"]:.1f}:1  [{sf_status}]', sf_col)
        line(f'  (Cap. tubo: {ALUMINUM_TUBE_CAPACITY:.0f} kN)', C['dark_text'])

        # Factor vs pandeo de Euler
        if f['sf_buckling'] >= 5.0:
            eb_col = C['accent']
            eb_status = 'OK'
        elif f['sf_buckling'] >= 2.0:
            eb_col = C['warning']
            eb_status = 'BAJO'
        elif f['sf_buckling'] >= 1.0:
            eb_col = C['secondary']
            eb_status = 'RIESGOSO'
        else:
            eb_col = C['danger']
            eb_status = 'PANDEO'

        line(f'FS pandeo:  {f["sf_buckling"]:.1f}:1  [{eb_status}]', eb_col)
        line(f'  (F_euler: {f["F_euler_kN"]:.1f} kN  L={f["leg_length"]:.1f}m)',
             C['dark_text'])

        sep()

        # ── Tabla comparativa ───────────────────────────────────────
        heading('COMPARACION', C['info'])
        line_small('Angulo     Tripode     Marco A', C['text'])
        line_small('(phi)    F/W por pata  F/W por pata', C['dark_text'])

        ref_angles = [10, 20, 30, 40, 50, 60, 70]
        for ra in ref_angles:
            ra_rad = math.radians(ra)
            cos_ra = math.cos(ra_rad)
            if cos_ra > 0.01:
                f_tri = 1.0 / (3.0 * cos_ra)
                f_aframe = 1.0 / (2.0 * cos_ra)
            else:
                f_tri = 99.9
                f_aframe = 99.9

            marker = ' <--' if abs(ra - f['phi_deg']) < 3 else ''
            tri_col = C['accent'] if f_tri * f['W_kN'] < ALUMINUM_TUBE_CAPACITY else C['danger']
            af_col = C['accent'] if f_aframe * f['W_kN'] < ALUMINUM_TUBE_CAPACITY else C['danger']

            is_current = abs(ra - f['phi_deg']) < 3
            row_col = C['warning'] if is_current else C['dark_text']
            line_small(
                f' {ra:3d} deg    {f_tri:.3f}W       {f_aframe:.3f}W{marker}',
                row_col)

        sep()

        # ── Consejos educativos ─────────────────────────────────────
        heading('CONCEPTOS CLAVE', C['warning'])
        tips = [
            'A mayor apertura (phi), mayor compresion.',
            'El tripode reparte en 3; el marco A en 2.',
            'Las patas trabajan a COMPRESION, no tension.',
            'La fuerza horizontal empuja los pies.',
            '  -> Anclar/asegurar pies al suelo.',
            'Pandeo: fallo subito sin aviso previo.',
            'Patas mas largas = mas riesgo de pandeo.',
            'NUNCA abrir mas de 45 deg sin ingenieria.',
        ]
        for tip in tips:
            if tip.startswith(' '):
                line_small(tip, C['info'])
            else:
                line_small(tip, C['dark_text'])

    # ── Dibujado: barra de controles ────────────────────────────────

    def _draw_controls(self):
        cy = HEIGHT - 38
        pygame.draw.rect(self.screen, C['panel'],
                         (0, cy - 8, WIDTH, 46))

        mode_lbl = 'Tripode' if self.is_tripod else 'Marco A'
        controls = [
            f'[Izq/Der] Angulo: {self.phi_deg:.0f} deg',
            f'[Arr/Abj] Masa: {self.mass_kg} kg',
            f'[T] Modo: {mode_lbl}',
            f'[L/K] Pata: {self.leg_length_m:.1f} m',
            '[R] Reiniciar',
            '[ESC] Salir',
        ]
        cx = 12
        for ctrl in controls:
            col = C['dark_text']
            if 'Modo' in ctrl:
                col = C['primary'] if self.is_tripod else C['secondary']
            s = self.fx.render(ctrl, True, col)
            self.screen.blit(s, (cx, cy))
            cx += s.get_width() + 18

    # ── Dibujado principal ──────────────────────────────────────────

    def draw(self):
        self.screen.fill(C['bg'])

        # Titulo
        s = self.ft.render(
            'TRIPODE Y MARCO EN A -- Fuerzas de Compresion en Rescate',
            True, C['primary'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 10))

        # Subtitulo con formula principal
        n = 3 if self.is_tripod else 2
        formula_text = (
            f'F_pata = W / ({n} * cos(phi))    '
            f'H = W * tan(phi) / {n}    '
            f'F_pandeo = pi^2 * EI / L^2')
        s = self.fm.render(formula_text, True, C['warning'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 46))

        # Regla de oro
        s = self.fi.render(
            'REGLA: Abrir las patas aumenta la compresion. '
            'Nunca exceder 45 deg sin calculo de ingenieria. '
            'Asegurar los pies contra deslizamiento.',
            True, C['dark_text'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 68))

        # Calcular fuerzas
        n_legs = 3 if self.is_tripod else 2
        f = compute_forces(self.phi_deg, self.mass_kg, n_legs,
                           self.leg_length_m)

        self._draw_scene(f)
        self._draw_graph(f)
        self._draw_panel(f)
        self._draw_controls()

        pygame.display.flip()

    # ── Bucle principal ─────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.reset()

                    # Toggle tripode / marco en A
                    elif event.key == pygame.K_t:
                        self.is_tripod = not self.is_tripod

                    # Longitud de patas
                    elif event.key == pygame.K_l:
                        self.leg_length_m = min(self.leg_length_m + 0.5, 6.0)
                    elif event.key == pygame.K_k:
                        self.leg_length_m = max(self.leg_length_m - 0.5, 1.0)

            # Teclas sostenidas para ajustes continuos
            keys = pygame.key.get_pressed()

            # Angulo
            if keys[pygame.K_RIGHT]:
                self.phi_deg = min(self.phi_deg + 30 * dt, 75.0)
            if keys[pygame.K_LEFT]:
                self.phi_deg = max(self.phi_deg - 30 * dt, 0.0)

            # Masa
            if keys[pygame.K_UP]:
                self.mass_kg = min(self.mass_kg + 50 * dt, 500)
            if keys[pygame.K_DOWN]:
                self.mass_kg = max(self.mass_kg - 50 * dt, 10)

            # Redondear masa a enteros para display
            self.mass_kg = round(self.mass_kg)

            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = TripodSimulator()
    sim.run()
