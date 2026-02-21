"""
╔══════════════════════════════════════════════════════════════════════╗
║  FÍSICA DEL RESCATE · Módulo 11: Camilla en Tirolesa (Pygame)      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación animada del paso de una camilla por una tirolesa,       ║
║  mostrando en tiempo real cómo cambian las fuerzas cuando la        ║
║  carga se desplaza a lo largo de la línea.                          ║
║                                                                      ║
║  Física:                                                             ║
║   • Con carga fuera del centro: T_izq ≠ T_der                      ║
║   • La flecha (sag) varía con la posición de la carga              ║
║   • El ángulo V en el punto de carga → fuerzas en los anclajes     ║
║   • Componente horizontal H = W·x·(L−x) / (d·L)                   ║
║   • T_izq = H / cos(α_izq),  T_der = H / cos(α_der)              ║
║   • Ángulo V = 180° − α_izq − α_der                                ║
║                                                                      ║
║  Controles:                                                          ║
║   [←/→]     Mover camilla a lo largo de la tirolesa                ║
║   [↑/↓]     Aumentar / reducir flecha (sag %)                      ║
║   [W/S]     Aumentar / reducir masa de la carga                     ║
║   [+/−]     Aumentar / reducir vano (longitud)                      ║
║   [ESPACIO]  Travesía automática (ida y vuelta)                     ║
║   [R]        Reiniciar                                               ║
║   [ESC]      Salir                                                   ║
║                                                                      ║
║  Ejecutar:  python 11_camilla_en_tirolesa.py                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import pygame
from config import PG_COLORS as C, G

WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Límites de seguridad ──────────────────────────────────────────────
NFPA_WORK_LOAD = 13.5   # kN
ROPE_MBS = 30.0          # kN cuerda estática 11 mm

# ── Zonas del layout (píxeles) ────────────────────────────────────────
SCENE_L, SCENE_R = 70, 840
SCENE_T, SCENE_B = 120, 410

GRAPH_L, GRAPH_R = 70, 840
GRAPH_T, GRAPH_B = 450, 650

PANEL_L = 870
PANEL_T = 100


# ══════════════════════════════════════════════════════════════════════
#  Física de la tirolesa con carga puntual móvil
# ══════════════════════════════════════════════════════════════════════

def compute_rope_length(span, d_center):
    """Longitud total de la cuerda a partir del vano y la flecha central."""
    half = span / 2.0
    return 2.0 * math.sqrt(half * half + d_center * d_center)


def solve_sag_at(x, span, rope_length):
    """
    Bisección: encontrar la flecha d en la posición x
    para una cuerda inextensible de longitud rope_length.
    sqrt(x² + d²) + sqrt((L-x)² + d²) = S
    """
    if x < 0.02 * span or x > 0.98 * span:
        return 0.001
    lo, hi = 0.0001, rope_length * 0.5
    for _ in range(64):
        mid = (lo + hi) * 0.5
        s = math.sqrt(x * x + mid * mid) + math.sqrt((span - x) ** 2 + mid * mid)
        if s < rope_length:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def compute_forces(x, span, d, mass_kg):
    """
    Fuerzas en el punto de carga de una tirolesa.
    Retorna dict con todas las magnitudes.
    """
    W_kN = mass_kg * G / 1000.0
    x = max(0.01 * span, min(x, 0.99 * span))

    alpha_L = math.atan2(d, x)
    alpha_R = math.atan2(d, span - x)

    # Componente horizontal (igual en ambos lados)
    H = W_kN * x * (span - x) / (d * span) if d > 0.001 else 0.0

    T_L = H / math.cos(alpha_L) if math.cos(alpha_L) > 1e-6 else 999.0
    T_R = H / math.cos(alpha_R) if math.cos(alpha_R) > 1e-6 else 999.0

    v_angle = 180.0 - math.degrees(alpha_L) - math.degrees(alpha_R)

    return {
        'W': W_kN,
        'H': H,
        'T_L': T_L,
        'T_R': T_R,
        'alpha_L_deg': math.degrees(alpha_L),
        'alpha_R_deg': math.degrees(alpha_R),
        'v_angle': v_angle,
        'd': d,
        'x': x,
    }


# ══════════════════════════════════════════════════════════════════════
#  Utilidades de dibujo
# ══════════════════════════════════════════════════════════════════════

def lerp_color(c1, c2, t):
    """Interpolación lineal entre dos colores RGB."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def safety_color(v_angle):
    """Color según peligrosidad del ángulo V."""
    if v_angle > 160:
        return C['danger']
    if v_angle > 140:
        return C['secondary']
    if v_angle > 120:
        return C['warning']
    return C['accent']


def tension_color(t_kn):
    """Color según tensión respecto a los límites."""
    if t_kn > ROPE_MBS:
        return C['danger']
    if t_kn > NFPA_WORK_LOAD:
        return C['secondary']
    if t_kn > NFPA_WORK_LOAD * 0.7:
        return C['warning']
    return C['accent']


# ══════════════════════════════════════════════════════════════════════
#  Simulador principal
# ══════════════════════════════════════════════════════════════════════

class HighlineSimulator:
    """Simulación de travesía de camilla por tirolesa."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Física del Rescate — Camilla en Tirolesa')
        self.clock = pygame.time.Clock()

        self.ft = pygame.font.SysFont('DejaVu Sans', 28, bold=True)
        self.fb = pygame.font.SysFont('DejaVu Sans', 19, bold=True)
        self.fm = pygame.font.SysFont('DejaVu Sans', 14)
        self.fs = pygame.font.SysFont('DejaVu Sans', 12)
        self.fx = pygame.font.SysFont('DejaVu Sans', 11)

        self.reset()

    # ── Estado ────────────────────────────────────────────────────────

    def reset(self):
        self.span_m = 30.0
        self.sag_center_pct = 5.0
        self.mass_kg = 100
        self.load_pos = 0.5        # 0..1 a lo largo del vano
        self.auto_traverse = False
        self.traverse_dir = 1
        self.traverse_speed = 0.15  # ratio/segundo
        self._rebuild_profile()

    def _rebuild_profile(self):
        """Precalcula el perfil de tensiones a lo largo del vano."""
        L = self.span_m
        d_c = L * self.sag_center_pct / 100.0
        S = compute_rope_length(L, d_c)
        self._rope_len = S
        self._d_center = d_c

        N = 120
        self._profile_n = N
        self._profile_T_L = []
        self._profile_T_R = []
        self._profile_V = []
        self._profile_d = []

        for i in range(N):
            ratio = (i + 0.5) / N
            x = ratio * L
            d = solve_sag_at(x, L, S)
            f = compute_forces(x, L, d, self.mass_kg)
            self._profile_T_L.append(f['T_L'])
            self._profile_T_R.append(f['T_R'])
            self._profile_V.append(f['v_angle'])
            self._profile_d.append(d)

    # ── Actualización ─────────────────────────────────────────────────

    def update(self, dt):
        if self.auto_traverse:
            self.load_pos += self.traverse_dir * self.traverse_speed * dt
            if self.load_pos >= 0.95:
                self.load_pos = 0.95
                self.traverse_dir = -1
            elif self.load_pos <= 0.05:
                self.load_pos = 0.05
                self.traverse_dir = 1

    def _current_forces(self):
        """Calcula fuerzas en la posición actual de la carga."""
        L = self.span_m
        x = self.load_pos * L
        d = solve_sag_at(x, L, self._rope_len)
        return compute_forces(x, L, d, self.mass_kg)

    # ── Coordenadas ───────────────────────────────────────────────────

    def _scene_x(self, phys_x):
        """Metros → píxeles (horizontal)."""
        return SCENE_L + (phys_x / self.span_m) * (SCENE_R - SCENE_L)

    def _scene_y(self, sag):
        """Flecha en metros → píxeles (vertical, 0 = anclajes)."""
        # Escala vertical exagerada para visibilidad
        max_d = max(self._d_center * 2.5, 0.5)
        frac = sag / max_d
        anchor_y = SCENE_T + 30
        return anchor_y + frac * (SCENE_B - anchor_y - 30)

    # ── Dibujado: escena de la tirolesa ───────────────────────────────

    def _draw_scene(self, f):
        L = self.span_m
        d = f['d']
        x_m = f['x']

        anchor_y = self._scene_y(0)
        load_px = int(self._scene_x(x_m))
        load_py = int(self._scene_y(d))
        anch_L = (int(self._scene_x(0)), anchor_y)
        anch_R = (int(self._scene_x(L)), anchor_y)

        # ── Fondo y borde de escena ───────────────────────────────────
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (SCENE_L - 5, SCENE_T, SCENE_R - SCENE_L + 10,
                          SCENE_B - SCENE_T), border_radius=6)

        # ── Línea horizontal de referencia (nivel de anclajes) ────────
        pygame.draw.line(self.screen, C['grid'],
                         (SCENE_L, anchor_y), (SCENE_R, anchor_y), 1)

        # ── Perfil de la cuerda sin carga (línea tenue) ──────────────
        prev = anch_L
        for i in range(self._profile_n):
            ratio = (i + 0.5) / self._profile_n
            px = int(self._scene_x(ratio * L))
            py = int(self._scene_y(self._profile_d[i]))
            pygame.draw.line(self.screen, C['grid'], prev, (px, py), 1)
            prev = (px, py)
        pygame.draw.line(self.screen, C['grid'], prev, anch_R, 1)

        # ── Cuerda cargada (dos segmentos) ────────────────────────────
        col_L = tension_color(f['T_L'])
        col_R = tension_color(f['T_R'])
        pygame.draw.line(self.screen, col_L,
                         anch_L, (load_px, load_py), 4)
        pygame.draw.line(self.screen, col_R,
                         (load_px, load_py), anch_R, 4)

        # ── Anclajes ─────────────────────────────────────────────────
        for pos, label in [(anch_L, 'Anclaje A'), (anch_R, 'Anclaje B')]:
            pygame.draw.rect(self.screen, C['anchor'],
                             (pos[0] - 8, pos[1] - 8, 16, 16))
            pygame.draw.rect(self.screen, C['text'],
                             (pos[0] - 8, pos[1] - 8, 16, 16), width=2)
            s = self.fs.render(label, True, C['anchor'])
            self.screen.blit(s, (pos[0] - s.get_width() // 2,
                                 pos[1] - 26))

        # ── Flechas de tensión en anclajes ────────────────────────────
        arr_len_max = 90
        for anchor, T_kN, alpha_deg, sign in [
            (anch_L, f['T_L'], f['alpha_L_deg'], 1),
            (anch_R, f['T_R'], f['alpha_R_deg'], -1),
        ]:
            ratio = min(T_kN / ROPE_MBS, 1.0)
            arr_len = 30 + ratio * (arr_len_max - 30)
            rad = math.radians(alpha_deg)
            dx = sign * arr_len * math.cos(rad)
            dy = arr_len * math.sin(rad)

            end = (int(anchor[0] + dx), int(anchor[1] + dy))
            col_t = tension_color(T_kN)
            pygame.draw.line(self.screen, col_t, anchor, end, 3)
            # Punta de flecha
            perp_dx = -sign * 5 * math.sin(rad)
            perp_dy = 5 * math.cos(rad)
            tip = end
            p1 = (int(tip[0] - sign * 10 * math.cos(rad) + perp_dx),
                  int(tip[1] - 10 * math.sin(rad) + perp_dy))
            p2 = (int(tip[0] - sign * 10 * math.cos(rad) - perp_dx),
                  int(tip[1] - 10 * math.sin(rad) - perp_dy))
            pygame.draw.polygon(self.screen, col_t, [tip, p1, p2])

            # Etiqueta
            lbl = self.fs.render(f'{T_kN:.1f} kN', True, col_t)
            off_x = 12 * sign
            self.screen.blit(lbl, (end[0] + off_x - (0 if sign > 0 else lbl.get_width()),
                                   end[1] - 6))

        # ── Ángulo V con arco ─────────────────────────────────────────
        v_col = safety_color(f['v_angle'])
        arc_r = 35
        # Ángulo del segmento izquierdo (va hacia arriba-izquierda)
        a_L_rad = math.atan2(-(anchor_y - load_py), anch_L[0] - load_px)
        a_R_rad = math.atan2(-(anchor_y - load_py), anch_R[0] - load_px)

        # Dibujar arco entre los dos ángulos
        start_a = min(a_L_rad, a_R_rad)
        end_a = max(a_L_rad, a_R_rad)
        n_arc = 40
        arc_pts = []
        for i in range(n_arc + 1):
            a = start_a + (end_a - start_a) * i / n_arc
            px = load_px + int(arc_r * math.cos(a))
            py = load_py - int(arc_r * math.sin(a))
            arc_pts.append((px, py))
        if len(arc_pts) > 1:
            pygame.draw.lines(self.screen, v_col, False, arc_pts, 2)

        # Etiqueta del ángulo V
        mid_a = (start_a + end_a) / 2.0
        lbl_x = load_px + int((arc_r + 18) * math.cos(mid_a))
        lbl_y = load_py - int((arc_r + 18) * math.sin(mid_a))
        s = self.fm.render(f'{f["v_angle"]:.1f}', True, v_col)
        self.screen.blit(s, (lbl_x - s.get_width() // 2,
                             lbl_y - s.get_height() // 2))

        # ── Flecha vertical de sag ────────────────────────────────────
        pygame.draw.line(self.screen, C['warning'],
                         (load_px + 35, anchor_y),
                         (load_px + 35, load_py), 1)
        # Marcas
        for yy in [anchor_y, load_py]:
            pygame.draw.line(self.screen, C['warning'],
                             (load_px + 30, yy), (load_px + 40, yy), 1)
        mid_sag_y = (anchor_y + load_py) // 2
        s = self.fx.render(f'd={d:.2f}m ({d / L * 100:.1f}%)',
                           True, C['warning'])
        self.screen.blit(s, (load_px + 44, mid_sag_y - 6))

        # ── Camilla ──────────────────────────────────────────────────
        self._draw_litter(load_px, load_py, f)

        # ── Ángulos con la horizontal ─────────────────────────────────
        # Izquierdo
        s = self.fx.render(f'aL={f["alpha_L_deg"]:.1f}',
                           True, C['text'])
        self.screen.blit(s, (anch_L[0] + 20, anchor_y + 4))
        # Derecho
        s = self.fx.render(f'aR={f["alpha_R_deg"]:.1f}',
                           True, C['text'])
        self.screen.blit(s, (anch_R[0] - 80, anchor_y + 4))

        # ── Etiqueta posición ────────────────────────────────────────
        s = self.fx.render(
            f'x = {x_m:.1f} m  ({self.load_pos * 100:.0f}% del vano)',
            True, C['text'])
        self.screen.blit(s, (load_px - s.get_width() // 2,
                             SCENE_B - 18))

    def _draw_litter(self, cx, cy, f):
        """Dibuja la camilla con persona y flecha de peso."""
        # Conexión cuerda → camilla (eslingas)
        pygame.draw.line(self.screen, C['anchor'],
                         (cx, cy), (cx, cy + 12), 2)

        # Polea/roldana
        pygame.draw.circle(self.screen, C['text'], (cx, cy), 6, 2)
        pygame.draw.circle(self.screen, C['anchor'], (cx, cy), 3)

        # Camilla
        w, h = 56, 24
        ly = cy + 14
        v_col = safety_color(f['v_angle'])
        pygame.draw.rect(self.screen, v_col,
                         (cx - w // 2, ly, w, h), border_radius=4)
        pygame.draw.rect(self.screen, C['text'],
                         (cx - w // 2, ly, w, h), width=2, border_radius=4)

        # Persona
        pygame.draw.circle(self.screen, C['primary'],
                           (cx - 10, ly + 8), 5)
        pygame.draw.line(self.screen, C['primary'],
                         (cx - 10, ly + 13), (cx - 10, ly + 22), 2)

        # Masa
        s = self.fx.render(f'{self.mass_kg}kg', True, C['text'])
        self.screen.blit(s, (cx + 4, ly + 5))

        # Flecha de peso
        arrow_top = ly + h + 4
        arrow_bot = arrow_top + 28
        pygame.draw.line(self.screen, C['danger'],
                         (cx, arrow_top), (cx, arrow_bot), 2)
        pygame.draw.polygon(self.screen, C['danger'], [
            (cx, arrow_bot + 5),
            (cx - 4, arrow_bot),
            (cx + 4, arrow_bot),
        ])
        s = self.fx.render(f'W={f["W"]:.2f}kN', True, C['danger'])
        self.screen.blit(s, (cx + 8, arrow_top + 6))

    # ── Dibujado: gráfico de tensiones ────────────────────────────────

    def _draw_graph(self, f):
        gx, gy = GRAPH_L, GRAPH_T
        gw = GRAPH_R - GRAPH_L
        gh = GRAPH_B - GRAPH_T

        # Fondo
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (gx - 5, gy - 5, gw + 10, gh + 30),
                         border_radius=6)

        # Título
        s = self.fm.render('Tension (kN) vs Posicion en el vano', True, C['text'])
        self.screen.blit(s, (gx + gw // 2 - s.get_width() // 2, gy - 3))

        # Área del gráfico
        gx_inner = gx + 50
        gw_inner = gw - 60
        gy_inner = gy + 18
        gh_inner = gh - 28

        pygame.draw.rect(self.screen, (12, 12, 22),
                         (gx_inner, gy_inner, gw_inner, gh_inner))

        # Escala vertical
        all_T = self._profile_T_L + self._profile_T_R
        if not all_T:
            return
        max_T = max(max(all_T), NFPA_WORK_LOAD * 1.1, 5.0)
        max_T = min(max_T, 80.0)  # cap para no explotar visualmente

        def map_x(ratio):
            return gx_inner + int(ratio * gw_inner)

        def map_y(t_kn):
            frac = t_kn / max_T
            return gy_inner + gh_inner - int(frac * gh_inner)

        # Grid horizontal + etiquetas
        for t_val in [5, 10, NFPA_WORK_LOAD, 20, 25, ROPE_MBS]:
            if t_val > max_T:
                continue
            yy = map_y(t_val)
            is_limit = t_val in (NFPA_WORK_LOAD, ROPE_MBS)
            col = C['danger'] if is_limit else C['grid']
            style_w = 1
            pygame.draw.line(self.screen, col,
                             (gx_inner, yy), (gx_inner + gw_inner, yy),
                             style_w)
            lbl = f'{t_val:.0f}' if t_val == int(t_val) else f'{t_val:.1f}'
            if is_limit:
                lbl += ' NFPA' if t_val == NFPA_WORK_LOAD else ' MBS'
            s = self.fx.render(lbl, True, col)
            self.screen.blit(s, (gx_inner - s.get_width() - 4, yy - 6))

        # Grid vertical (25%, 50%, 75%)
        for pct in [0.25, 0.5, 0.75]:
            xx = map_x(pct)
            pygame.draw.line(self.screen, C['grid'],
                             (xx, gy_inner), (xx, gy_inner + gh_inner), 1)
            s = self.fx.render(f'{pct * 100:.0f}%', True, C['grid'])
            self.screen.blit(s, (xx - 8, gy_inner + gh_inner + 2))

        # Ejes
        s = self.fx.render('0%', True, C['grid'])
        self.screen.blit(s, (gx_inner - 2, gy_inner + gh_inner + 2))
        s = self.fx.render('100%', True, C['grid'])
        self.screen.blit(s, (gx_inner + gw_inner - 18,
                             gy_inner + gh_inner + 2))

        # Curvas T_L y T_R
        N = self._profile_n
        for data, color, lbl_text in [
            (self._profile_T_L, (100, 180, 255), 'T izq'),
            (self._profile_T_R, (255, 160, 80), 'T der'),
        ]:
            pts = []
            for i in range(N):
                ratio = (i + 0.5) / N
                px = map_x(ratio)
                py = map_y(min(data[i], max_T))
                py = max(gy_inner, min(py, gy_inner + gh_inner))
                pts.append((px, py))
            if len(pts) > 1:
                pygame.draw.lines(self.screen, color, False, pts, 2)

        # Leyenda
        leg_x = gx_inner + 8
        leg_y = gy_inner + 6
        pygame.draw.line(self.screen, (100, 180, 255),
                         (leg_x, leg_y + 5), (leg_x + 20, leg_y + 5), 2)
        s = self.fx.render('T izq', True, (100, 180, 255))
        self.screen.blit(s, (leg_x + 24, leg_y))
        leg_y += 14
        pygame.draw.line(self.screen, (255, 160, 80),
                         (leg_x, leg_y + 5), (leg_x + 20, leg_y + 5), 2)
        s = self.fx.render('T der', True, (255, 160, 80))
        self.screen.blit(s, (leg_x + 24, leg_y))

        # Línea vertical de posición actual
        cur_x = map_x(self.load_pos)
        pygame.draw.line(self.screen, C['warning'],
                         (cur_x, gy_inner), (cur_x, gy_inner + gh_inner), 2)

        # Puntos actuales
        cur_T_L = f['T_L']
        cur_T_R = f['T_R']
        pygame.draw.circle(self.screen, (100, 180, 255),
                           (cur_x, map_y(min(cur_T_L, max_T))), 5)
        pygame.draw.circle(self.screen, (255, 160, 80),
                           (cur_x, map_y(min(cur_T_R, max_T))), 5)

    # ── Dibujado: panel de datos ──────────────────────────────────────

    def _draw_panel(self, f):
        px, py = PANEL_L, PANEL_T
        pw = WIDTH - PANEL_L - 15
        ph = GRAPH_B - PANEL_T + 20

        pygame.draw.rect(self.screen, C['panel'],
                         (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (px, py, pw, ph), width=1, border_radius=8)

        x = px + 12
        y = py + 10

        def heading(text, color=C['primary']):
            nonlocal y
            s = self.fb.render(text, True, color)
            self.screen.blit(s, (x, y))
            y += 24

        def line(text, color=C['text']):
            nonlocal y
            s = self.fs.render(text, True, color)
            self.screen.blit(s, (x + 5, y))
            y += 17

        def sep():
            nonlocal y
            pygame.draw.line(self.screen, C['grid'],
                             (x, y + 2), (x + pw - 24, y + 2), 1)
            y += 8

        # ── Parámetros ───────────────────────────────────────────────
        heading('PARAMETROS DEL SISTEMA')
        line(f'Vano (L):       {self.span_m:.0f} m')
        line(f'Flecha centro:  {self._d_center:.2f} m  '
             f'({self.sag_center_pct:.1f}%)', C['warning'])
        line(f'Carga:          {self.mass_kg} kg  '
             f'({f["W"]:.2f} kN)', C['danger'])
        line(f'Posicion:       {f["x"]:.1f} m  '
             f'({self.load_pos * 100:.0f}%)')
        sep()

        # ── Ángulos ──────────────────────────────────────────────────
        v_col = safety_color(f['v_angle'])
        heading('ANGULOS')
        line(f'a izquierdo:    {f["alpha_L_deg"]:.1f} deg  '
             f'(cuerda-horizontal)')
        line(f'a derecho:      {f["alpha_R_deg"]:.1f} deg')

        y += 2
        s = self.fb.render(f'Angulo V = {f["v_angle"]:.1f} deg', True, v_col)
        self.screen.blit(s, (x + 5, y))
        y += 22

        # Status del ángulo V
        if f['v_angle'] > 160:
            line('CRITICO: angulo muy abierto', C['danger'])
            line('Fuerzas extremas en anclajes', C['danger'])
        elif f['v_angle'] > 140:
            line('PELIGROSO: fuerzas muy altas', C['secondary'])
        elif f['v_angle'] > 120:
            line('PRECAUCION: monitorear tension', C['warning'])
        else:
            line('Angulo aceptable', C['accent'])
        sep()

        # ── Tensiones ────────────────────────────────────────────────
        heading('TENSIONES')
        tl_col = tension_color(f['T_L'])
        tr_col = tension_color(f['T_R'])
        line(f'H (horizontal): {f["H"]:.2f} kN  (igual ambos lados)',
             C['info'])
        y += 3
        line(f'T izquierdo:    {f["T_L"]:.2f} kN', tl_col)
        line(f'T derecho:      {f["T_R"]:.2f} kN', tr_col)
        line(f'T maximo:       {max(f["T_L"], f["T_R"]):.2f} kN',
             tension_color(max(f['T_L'], f['T_R'])))

        # Barra visual de tensión
        y += 5
        bar_w = pw - 30
        bar_h = 12
        for label, T_kN, col in [
            ('Izq', f['T_L'], (100, 180, 255)),
            ('Der', f['T_R'], (255, 160, 80)),
        ]:
            s = self.fx.render(label, True, col)
            self.screen.blit(s, (x + 3, y))
            bar_x = x + 30
            pygame.draw.rect(self.screen, (30, 30, 45),
                             (bar_x, y, bar_w - 30, bar_h), border_radius=2)
            fill_w = int((bar_w - 30) * min(T_kN / max(ROPE_MBS * 1.1, 1), 1.0))
            fill_col = tension_color(T_kN)
            if fill_w > 0:
                pygame.draw.rect(self.screen, fill_col,
                                 (bar_x, y, fill_w, bar_h), border_radius=2)
            # Marcas NFPA y MBS
            for lim, lim_col in [(NFPA_WORK_LOAD, C['warning']),
                                  (ROPE_MBS, C['danger'])]:
                lx = bar_x + int((bar_w - 30) * lim / (ROPE_MBS * 1.1))
                if bar_x < lx < bar_x + bar_w - 30:
                    pygame.draw.line(self.screen, lim_col,
                                     (lx, y - 1), (lx, y + bar_h + 1), 1)
            y += bar_h + 5

        sep()

        # ── Seguridad ────────────────────────────────────────────────
        heading('SEGURIDAD')
        T_max = max(f['T_L'], f['T_R'])

        checks = []
        # NFPA
        if T_max <= NFPA_WORK_LOAD:
            checks.append(
                (f'NFPA:  {T_max:.1f} <= {NFPA_WORK_LOAD} kN  [OK]',
                 C['accent']))
        else:
            checks.append(
                (f'NFPA:  {T_max:.1f} > {NFPA_WORK_LOAD} kN  [EXCEDE]',
                 C['danger']))

        # MBS
        sf = ROPE_MBS / T_max if T_max > 0 else 999
        if sf >= 10:
            checks.append((f'FS rotura: {sf:.1f}:1  [OK]', C['accent']))
        elif sf >= 3:
            checks.append((f'FS rotura: {sf:.1f}:1  [BAJO]', C['warning']))
        else:
            checks.append(
                (f'FS rotura: {sf:.1f}:1  [CRITICO]', C['danger']))

        # Angulo V
        if f['v_angle'] < 120:
            checks.append(
                (f'Angulo V: {f["v_angle"]:.0f} deg  [OK]', C['accent']))
        elif f['v_angle'] < 160:
            checks.append(
                (f'Angulo V: {f["v_angle"]:.0f} deg  [AMPLIO]', C['warning']))
        else:
            checks.append(
                (f'Angulo V: {f["v_angle"]:.0f} deg  [CRITICO]', C['danger']))

        # Flecha mínima recomendada para estar bajo NFPA
        d_min = f['W'] * self.span_m / (4 * NFPA_WORK_LOAD)
        sag_min_pct = d_min / self.span_m * 100
        checks.append(
            (f'Flecha minima para NFPA: {sag_min_pct:.1f}%  '
             f'({d_min:.2f} m)', C['info']))

        for text, color in checks:
            line(text, color)

        sep()

        # ── Reglas educativas ─────────────────────────────────────────
        heading('CONCEPTOS CLAVE', C['warning'])
        rules = [
            'La carga en el CENTRO genera la maxima',
            'tension en AMBOS anclajes (peor caso).',
            '',
            'Con carga fuera del centro: T_izq != T_der',
            'La componente H es IGUAL en ambos lados.',
            '',
            'Angulo V amplio = mayor multiplicacion',
            'de fuerza (igual que anclaje en V).',
            '',
            'NUNCA tensar la tirolesa "bien bonita".',
            'Mas flecha = menos fuerza = mas seguro.',
        ]
        for r in rules:
            if r:
                s = self.fx.render(r, True, C['dark_text'])
                self.screen.blit(s, (x + 5, y))
            y += 13

    # ── Dibujado: controles ───────────────────────────────────────────

    def _draw_controls(self):
        cy = HEIGHT - 40
        pygame.draw.rect(self.screen, C['panel'],
                         (0, cy - 10, WIDTH, 50))

        auto_lbl = 'ON' if self.auto_traverse else 'OFF'
        controls = [
            '[Izq/Der] Mover camilla',
            f'[Arr/Abj] Flecha: {self.sag_center_pct:.1f}%',
            f'[W/S] Masa: {self.mass_kg}kg',
            f'[+/-] Vano: {self.span_m:.0f}m',
            f'[ESPACIO] Auto: {auto_lbl}',
            '[R] Reiniciar',
            '[ESC] Salir',
        ]
        cx = 12
        for ctrl in controls:
            is_auto = 'Auto' in ctrl and self.auto_traverse
            col = C['warning'] if is_auto else C['dark_text']
            s = self.fx.render(ctrl, True, col)
            self.screen.blit(s, (cx, cy))
            cx += s.get_width() + 15

    # ── Dibujado principal ────────────────────────────────────────────

    def draw(self):
        self.screen.fill(C['bg'])

        # Título
        s = self.ft.render(
            'TIROLESA — Paso de Camilla con Analisis de Fuerzas',
            True, C['primary'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 12))

        # Subtítulo
        s = self.fm.render(
            'H = W*x*(L-x)/(d*L)    T = H/cos(a)    '
            'Angulo V = 180 - aL - aR',
            True, C['warning'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 48))

        # Fórmula de contexto
        s = self.fx.render(
            'La flecha REAL de la cuerda cambia segun la posicion '
            'de la carga (cuerda inextensible de longitud fija)',
            True, C['dark_text'])
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 68))

        f = self._current_forces()
        self._draw_scene(f)
        self._draw_graph(f)
        self._draw_panel(f)
        self._draw_controls()

        pygame.display.flip()

    # ── Bucle principal ───────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.auto_traverse = not self.auto_traverse
                    elif event.key == pygame.K_r:
                        self.reset()

                    # Flecha (sag)
                    elif event.key == pygame.K_UP:
                        self.sag_center_pct = min(
                            self.sag_center_pct + 0.5, 25.0)
                        self._rebuild_profile()
                    elif event.key == pygame.K_DOWN:
                        self.sag_center_pct = max(
                            self.sag_center_pct - 0.5, 0.5)
                        self._rebuild_profile()

                    # Masa
                    elif event.key == pygame.K_w:
                        self.mass_kg = min(self.mass_kg + 10, 500)
                        self._rebuild_profile()
                    elif event.key == pygame.K_s:
                        self.mass_kg = max(self.mass_kg - 10, 10)
                        self._rebuild_profile()

                    # Vano
                    elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS,
                                       pygame.K_EQUALS):
                        self.span_m = min(self.span_m + 5, 150)
                        self._rebuild_profile()
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.span_m = max(self.span_m - 5, 10)
                        self._rebuild_profile()

            # Movimiento manual con teclas sostenidas
            keys = pygame.key.get_pressed()
            if not self.auto_traverse:
                if keys[pygame.K_LEFT]:
                    self.load_pos = max(self.load_pos - 0.4 * dt, 0.03)
                if keys[pygame.K_RIGHT]:
                    self.load_pos = min(self.load_pos + 0.4 * dt, 0.97)

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = HighlineSimulator()
    sim.run()
