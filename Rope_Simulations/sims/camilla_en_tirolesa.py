"""
╔══════════════════════════════════════════════════════════════════════╗
║  FÍSICA DEL RESCATE · Módulo 11: Camilla en Tirolesa (Pygame)      ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación animada del paso de una camilla por una tirolesa,       ║
║  mostrando en tiempo real cómo cambian las fuerzas cuando la        ║
║  carga se desplaza a lo largo de la línea.                          ║
║                                                                      ║
║  Física (Caso 1: carro sobre POLEA + línea de control):            ║
║   • La polea rueda libre → la cuerda tiene UNA tensión:            ║
║       T = W / (sin α_izq + sin α_der)   (anclajes A y B iguales)   ║
║   • La línea de control aporta la fuerza horizontal:               ║
║       F_control = T·(cos α_izq − cos α_der)  (tracción/retención)  ║
║   • La flecha (sag) varía con la posición de la carga             ║
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
from config import PG_COLORS as C, NFPA_WORK_LOAD, ROPE_STATIC_MBS
from physics import (highline_rope_length as compute_rope_length,
                     solve_sag_at, highline_pulley_forces)
import viz


def compute_forces(x, span, d, mass_kg):
    """Modelo de POLEA (Caso 1): el carro rueda libre en la tirolesa, así que
    la cuerda tiene UNA sola tensión (ambos anclajes ven lo mismo) y una línea
    de control aporta la fuerza horizontal de tracción/retención.
    Se exponen T_L = T_R = T para dibujar los dos tramos con igual tensión."""
    f = highline_pulley_forces(x, span, d, mass_kg)
    f['T_L'] = f['T_R'] = f['T']
    return f

WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Límites de seguridad (fuente única: config) ───────────────────────
ROPE_MBS = ROPE_STATIC_MBS   # kN cuerda estática 11 mm

# ── Zonas del layout (píxeles) ────────────────────────────────────────
SCENE_L, SCENE_R = 70, 840
SCENE_T, SCENE_B = 120, 410

GRAPH_L, GRAPH_R = 70, 840
GRAPH_T, GRAPH_B = 450, 650

PANEL_L = 870
PANEL_T = 100


# Física en physics.py (compute_rope_length/solve_sag_at/compute_forces).
# Colores de seguridad en viz.py; envoltorios finos con la paleta pygame:

def safety_color(v_angle):
    """Color según peligrosidad del ángulo V."""
    return viz.v_angle_color(v_angle, C)


def tension_color(t_kn):
    """Color según tensión respecto a los límites NFPA / MBS."""
    return viz.tension_color(t_kn, C)


# ══════════════════════════════════════════════════════════════════════
#  Simulador principal
# ══════════════════════════════════════════════════════════════════════

class HighlineSimulator:
    """Simulación de travesía de camilla por tirolesa."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Camilla en Tirolesa')
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
        self._profile_T = []      # tensión de la cuerda (polea: única)
        self._profile_Fc = []     # fuerza de la línea de control (magnitud)
        self._profile_V = []
        self._profile_d = []
        self._profile_alpha_L = []
        self._profile_alpha_R = []

        for i in range(N):
            ratio = (i + 0.5) / N
            x = ratio * L
            d = solve_sag_at(x, L, S)
            f = compute_forces(x, L, d, self.mass_kg)
            self._profile_T_L.append(f['T_L'])
            self._profile_T_R.append(f['T_R'])
            self._profile_T.append(f['T'])
            self._profile_Fc.append(abs(f['f_control']))
            self._profile_V.append(f['v_angle'])
            self._profile_d.append(d)
            self._profile_alpha_L.append(f['alpha_L_deg'])
            self._profile_alpha_R.append(f['alpha_R_deg'])

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

        # ── Polea / carro que rueda sobre la tirolesa ────────────────
        pygame.draw.circle(self.screen, C['anchor'], (load_px, load_py), 9)
        pygame.draw.circle(self.screen, C['text'], (load_px, load_py), 9, 2)
        pygame.draw.circle(self.screen, C['bg'], (load_px, load_py), 3)

        # ── Línea de control (tracción / retención) ──────────────────
        fc = f['f_control']
        CTRL = (200, 90, 255)
        if abs(fc) > 0.005:
            to_right = fc > 0                       # >0: sostiene hacia B
            end_x = SCENE_R - 15 if to_right else SCENE_L + 15
            pygame.draw.line(self.screen, CTRL,
                             (load_px, load_py), (end_x, load_py), 3)
            adx = 18 if to_right else -18           # flecha de tracción
            tip = (load_px + adx, load_py)
            pygame.draw.polygon(self.screen, CTRL, [
                tip, (int(tip[0] - adx * 0.55), load_py - 6),
                (int(tip[0] - adx * 0.55), load_py + 6)])
            lbl = self.fs.render(f'control: {abs(fc):.2f} kN', True, CTRL)
            lx = (load_px + end_x) // 2 - lbl.get_width() // 2
            self.screen.blit(lbl, (lx, load_py - 20))

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
        # Dirección calculada en coordenadas de pantalla (hacia la carga),
        # proporcional a la tensión, color azul fijo.
        BLUE = (100, 180, 255)
        arr_len_max = 90
        for anchor, T_kN in [(anch_L, f['T_L']), (anch_R, f['T_R'])]:
            ratio = min(T_kN / ROPE_MBS, 1.0)
            arr_len = 30 + ratio * (arr_len_max - 30)
            lw = max(2, int(2 + ratio * 3))

            # Vector exacto desde el anclaje al punto de carga (pantalla)
            vec_x = load_px - anchor[0]
            vec_y = load_py - anchor[1]
            norm = math.sqrt(vec_x * vec_x + vec_y * vec_y)
            if norm < 1:
                continue
            ux = vec_x / norm
            uy = vec_y / norm

            ex = int(anchor[0] + arr_len * ux)
            ey = int(anchor[1] + arr_len * uy)

            pygame.draw.line(self.screen, BLUE, anchor, (ex, ey), lw)

            # Punta de flecha
            perp_x = -uy
            perp_y = ux
            tip = (ex, ey)
            p1 = (int(tip[0] - 10 * ux + 5 * perp_x),
                  int(tip[1] - 10 * uy + 5 * perp_y))
            p2 = (int(tip[0] - 10 * ux - 5 * perp_x),
                  int(tip[1] - 10 * uy - 5 * perp_y))
            pygame.draw.polygon(self.screen, BLUE, [tip, p1, p2])

            # Etiqueta
            lbl = self.fs.render(f'{T_kN:.1f} kN', True, BLUE)
            off_sign = 1 if anchor[0] < load_px else -1
            lbl_x = ex + 12 * off_sign - (0 if off_sign > 0 else lbl.get_width())
            self.screen.blit(lbl, (lbl_x, ey - 6))

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

    # ── Dibujado: gráficos de tensión y ángulos ───────────────────────

    def _draw_graph(self, f):
        gx, gy = GRAPH_L, GRAPH_T
        gw = GRAPH_R - GRAPH_L
        if not self._profile_T:
            return

        # Fondo
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (gx - 5, gy - 8, gw + 10, 232), border_radius=6)

        # Título
        s = self.fm.render('Fuerza en la cuerda segun donde esta la camilla',
                           True, C['primary'])
        self.screen.blit(s, (gx + 4, gy - 4))

        x0 = gx + 44
        pw = gw - 96
        p_top = gy + 24
        p_h = 150
        p_bot = p_top + p_h
        N = self._profile_n
        CTRL = (200, 90, 255)
        TCOL = C['accent']

        def map_x(ratio):
            return x0 + int(ratio * pw)

        # Escala Y automática (la curva no se aplasta arriba)
        data_max = max(max(self._profile_T), max(self._profile_Fc))
        step = 2 if data_max <= 11 else 5 if data_max <= 28 else 10
        y_max = max(math.ceil(data_max * 1.25 / step) * step, step)

        def map_y(v):
            return p_bot - int(min(v, y_max) / y_max * p_h)

        pygame.draw.rect(self.screen, (12, 12, 22), (x0, p_top, pw, p_h))

        # Grid horizontal + etiqueta kN
        s = self.fx.render('kN', True, C['grid'])
        self.screen.blit(s, (x0 - s.get_width() - 4, p_top - 12))
        v = step
        while v <= y_max + 0.01:
            yy = map_y(v)
            pygame.draw.line(self.screen, C['grid'], (x0, yy), (x0 + pw, yy), 1)
            s = self.fx.render(f'{v:.0f}', True, C['grid'])
            self.screen.blit(s, (x0 - s.get_width() - 4, yy - 6))
            v += step

        # Líneas de límite (solo si entran en la escala)
        for lim, lbl, col in [(NFPA_WORK_LOAD, 'NFPA', C['warning']),
                              (ROPE_MBS, 'rotura', C['danger'])]:
            if lim <= y_max:
                yy = map_y(lim)
                pygame.draw.line(self.screen, col, (x0, yy), (x0 + pw, yy), 1)
                s = self.fx.render(lbl, True, col)
                self.screen.blit(s, (x0 + pw + 3, yy - 6))

        # Curvas
        for data, color in [(self._profile_T, TCOL), (self._profile_Fc, CTRL)]:
            pts = [(map_x((i + 0.5) / N), map_y(data[i])) for i in range(N)]
            if len(pts) > 1:
                pygame.draw.lines(self.screen, color, False, pts, 3)

        # Posición actual: línea + puntos
        cur_x = map_x(self.load_pos)
        pygame.draw.line(self.screen, C['warning'], (cur_x, p_top), (cur_x, p_bot), 2)
        pygame.draw.circle(self.screen, TCOL, (cur_x, map_y(f['T'])), 6)
        pygame.draw.circle(self.screen, CTRL, (cur_x, map_y(abs(f['f_control']))), 6)

        # Leyenda con el valor ACTUAL (esquina superior izquierda, sin encimar)
        ly = p_top + 6
        for color, lbl in [
                (TCOL, f"Tension de la cuerda (A=B): {f['T']:.1f} kN"),
                (CTRL, f"Linea de control: {abs(f['f_control']):.2f} kN")]:
            pygame.draw.line(self.screen, color, (x0 + 8, ly + 7), (x0 + 26, ly + 7), 4)
            s = self.fs.render(lbl, True, color)
            self.screen.blit(s, (x0 + 32, ly))
            ly += 18

        # Eje X: A — centro — B
        for ratio, lbl, big in [(0.0, 'A', True), (0.25, '25%', False),
                                (0.5, 'centro', True), (0.75, '75%', False),
                                (1.0, 'B', True)]:
            xx = map_x(ratio)
            pygame.draw.line(self.screen, C['grid'], (xx, p_top), (xx, p_bot), 1)
            col = C['text'] if big else C['grid']
            s = self.fs.render(lbl, True, col) if big else self.fx.render(lbl, True, col)
            self.screen.blit(s, (xx - s.get_width() // 2, p_bot + 4))

    # ── Dibujado: panel de datos ──────────────────────────────────────

    def _draw_panel(self, f):
        px, py = PANEL_L, PANEL_T
        pw = WIDTH - PANEL_L - 15
        ph = HEIGHT - PANEL_T - 52   # llena toda la altura hasta la barra de controles

        pygame.draw.rect(self.screen, C['panel'],
                         (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (px, py, pw, ph), width=1, border_radius=8)

        # Limitar todo el dibujo al interior del recuadro
        self.screen.set_clip(pygame.Rect(px + 2, py + 2, pw - 4, ph - 4))

        x = px + 12
        y = py + 10
        y_max = py + ph - 6   # límite inferior del contenido

        def heading(text, color=C['primary']):
            nonlocal y
            if y > y_max:
                return
            s = self.fb.render(text, True, color)
            self.screen.blit(s, (x, y))
            y += 24

        def line(text, color=C['text']):
            nonlocal y
            if y > y_max:
                return
            s = self.fs.render(text, True, color)
            self.screen.blit(s, (x + 5, y))
            y += 17

        def sep():
            nonlocal y
            if y > y_max:
                return
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
        line(f'a izquierdo (A): {f["alpha_L_deg"]:.1f} deg  '
             f'(cuerda-horizontal)')
        line(f'a derecho (B):   {f["alpha_R_deg"]:.1f} deg')

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

        # ── Tensiones (modelo de polea) ──────────────────────────────
        heading('TENSIONES')
        t_col = tension_color(f['T'])
        line('Carro sobre polea: la cuerda tiene UNA', C['info'])
        line('sola tension (anclajes A y B iguales).', C['info'])
        y += 3
        line(f'Tension cuerda (A=B): {f["T"]:.2f} kN', t_col)
        line(f'Linea control (trac/ret): {abs(f["f_control"]):.2f} kN',
             (200, 90, 255))

        # Barra visual de tensión
        y += 5
        bar_w = pw - 30
        bar_h = 12
        for label, T_kN, col in [
            ('Cuerda', f['T'], C['accent']),
            ('Control', abs(f['f_control']), (200, 90, 255)),
        ]:
            s = self.fx.render(label, True, col)
            self.screen.blit(s, (x + 3, y))
            bar_x = x + 62
            bw = bar_w - 62
            pygame.draw.rect(self.screen, (30, 30, 45),
                             (bar_x, y, bw, bar_h), border_radius=2)
            fill_w = int(bw * min(T_kN / max(ROPE_MBS * 1.1, 1), 1.0))
            fill_col = tension_color(T_kN)
            if fill_w > 0:
                pygame.draw.rect(self.screen, fill_col,
                                 (bar_x, y, fill_w, bar_h), border_radius=2)
            # Marcas NFPA y MBS
            for lim, lim_col in [(NFPA_WORK_LOAD, C['warning']),
                                  (ROPE_MBS, C['danger'])]:
                lx = bar_x + int(bw * lim / (ROPE_MBS * 1.1))
                if bar_x < lx < bar_x + bw:
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
            'El carro rueda en polea: la cuerda tiene',
            'UNA sola tension (anclajes A y B iguales).',
            '',
            'La linea de control aporta la fuerza',
            'horizontal (traccion para mover, retencion',
            'para sostener). En el centro es 0.',
            '',
            'La carga en el CENTRO da la maxima tension',
            'de cuerda; cerca de un anclaje, mas control.',
            '',
            'NUNCA tensar la tirolesa "bien bonita".',
            'Mas flecha = menos fuerza = mas seguro.',
        ]
        for r in rules:
            if y + 13 > y_max:
                break
            if r:
                s = self.fx.render(r, True, C['dark_text'])
                self.screen.blit(s, (x + 5, y))
            y += 13

        # Restaurar clip completo
        self.screen.set_clip(None)

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
            'Carro en polea: T = W/(sin aL + sin aR) (igual A y B)    '
            'Control = T*(cos aL - cos aR)',
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


from registry import simulation


@simulation(backend='pygame', order=7,
            title='Camilla en tirolesa (animado)',
            description='Fuerzas mientras la camilla cruza la línea.')
def main():
    """Punto de entrada uniforme para el framework / launcher."""
    HighlineSimulator().run()


if __name__ == '__main__':
    main()
