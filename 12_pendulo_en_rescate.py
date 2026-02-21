"""
╔══════════════════════════════════════════════════════════════════════╗
║  FISICA DEL RESCATE · Modulo 12: Pendulo en Rescate (Pygame)       ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulacion animada del efecto pendulo en rescate.                  ║
║  Cuando una carga oscila en una cuerda, la fuerza en el anclaje    ║
║  NO es solo el peso: F = W + mv²/r (fuerza centripeta).            ║
║                                                                      ║
║  Fisica:                                                             ║
║   • Conservacion de energia: v = sqrt(2·g·r·(1-cos(theta)))        ║
║   • Fuerza en el fondo: F = mg·(3 - 2·cos(theta_0))               ║
║   • A 90° de liberacion: F = 3mg (3x el peso!)                    ║
║   • A 180° de liberacion: F = 5mg (5x el peso!)                   ║
║   • Fuerza en tiempo real durante toda la oscilacion               ║
║                                                                      ║
║  Controles:                                                          ║
║   [1] 30°  [2] 45°  [3] 60°  [4] 90°  [5] 120°                   ║
║   [ESPACIO] Liberar / Reiniciar pendulo                             ║
║   [ARRIBA/ABAJO] Ajustar masa (40-200 kg)                          ║
║   [+/-]  Ajustar longitud de cuerda (2-20 m)                       ║
║   [R] Reiniciar                                                      ║
║   [ESC] Salir                                                        ║
║                                                                      ║
║  Ejecutar:  python 12_pendulo_en_rescate.py                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import math
import pygame
from config import PG_COLORS as C, G

# ── Configuracion de pantalla ────────────────────────────────────────
WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Limites de seguridad ────────────────────────────────────────────
NFPA_WORK_LOAD = 13.5   # kN
ROPE_MBS = 30.0          # kN cuerda estatica 11 mm
UIAA_MAX_IMPACT = 12.0   # kN

# ── Layout (pixeles) ────────────────────────────────────────────────
SCENE_L, SCENE_R = 30, 870
SCENE_T, SCENE_B = 70, 560

GRAPH_L, GRAPH_R = 30, 870
GRAPH_T, GRAPH_B = 580, 830

PANEL_L = 890
PANEL_T = 70

# ── Constantes de simulacion ────────────────────────────────────────
PHYSICS_SUBSTEPS = 8     # subdivisions por frame para precision
DAMPING = 0.998          # amortiguacion por substep (muy ligera)
TRAIL_MAX = 300          # puntos del trail del pendulo


# ══════════════════════════════════════════════════════════════════════
#  Utilidades de dibujo
# ══════════════════════════════════════════════════════════════════════

def lerp_color(c1, c2, t):
    """Interpolacion lineal entre dos colores RGB."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def force_color(f_kn):
    """Color segun nivel de fuerza respecto a limites."""
    if f_kn > ROPE_MBS:
        return C['danger']
    if f_kn > NFPA_WORK_LOAD:
        return C['secondary']
    if f_kn > NFPA_WORK_LOAD * 0.7:
        return C['warning']
    return C['accent']


def draw_arrow(surface, color, start, end, width=2, head_size=8):
    """Dibuja una flecha desde start hasta end."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # perpendicular

    pygame.draw.line(surface, color, start, end, width)
    # Punta de flecha
    tip = end
    p1 = (int(tip[0] - head_size * ux + head_size * 0.5 * px),
          int(tip[1] - head_size * uy + head_size * 0.5 * py))
    p2 = (int(tip[0] - head_size * ux - head_size * 0.5 * px),
          int(tip[1] - head_size * uy - head_size * 0.5 * py))
    pygame.draw.polygon(surface, color, [tip, p1, p2])


# ══════════════════════════════════════════════════════════════════════
#  Fisica del pendulo
# ══════════════════════════════════════════════════════════════════════

def pendulum_force_at_angle(mass_kg, rope_len, theta, omega):
    """
    Fuerza en el anclaje para un pendulo simple.
    F = m·g·cos(theta) + m·omega²·r
      = m·(g·cos(theta) + omega²·r)

    theta: angulo medido desde la vertical (0 = abajo)
    omega: velocidad angular (rad/s)
    """
    f_newtons = mass_kg * (G * math.cos(theta) + omega * omega * rope_len)
    return f_newtons


def max_force_formula(mass_kg, release_angle_rad):
    """
    Fuerza maxima en el fondo del pendulo.
    F_max = m·g·(3 - 2·cos(theta_0))
    """
    return mass_kg * G * (3.0 - 2.0 * math.cos(release_angle_rad))


def force_multiplier(release_angle_rad):
    """Multiplicador de fuerza: F_max / (m·g) = 3 - 2·cos(theta_0)"""
    return 3.0 - 2.0 * math.cos(release_angle_rad)


# ══════════════════════════════════════════════════════════════════════
#  Simulador principal
# ══════════════════════════════════════════════════════════════════════

class PendulumSimulator:
    """Simulacion del efecto pendulo en rescate vertical."""

    ANGLE_PRESETS = {
        pygame.K_1: 30,
        pygame.K_2: 45,
        pygame.K_3: 60,
        pygame.K_4: 90,
        pygame.K_5: 120,
    }

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Fisica del Rescate - Pendulo en Rescate')
        self.clock = pygame.time.Clock()

        # Fuentes
        self.ft = pygame.font.SysFont('DejaVu Sans', 26, bold=True)
        self.fb = pygame.font.SysFont('DejaVu Sans', 17, bold=True)
        self.fm = pygame.font.SysFont('DejaVu Sans', 14)
        self.fs = pygame.font.SysFont('DejaVu Sans', 12)
        self.fx = pygame.font.SysFont('DejaVu Sans', 11)
        self.fi = pygame.font.SysFont('DejaVu Sans', 10)

        # Estado
        self.release_angle_deg = 60
        self.mass_kg = 80
        self.rope_len_m = 8.0

        self.reset()

    # ── Estado ────────────────────────────────────────────────────────

    def reset(self):
        """Reinicia la simulacion al estado inicial."""
        self.theta = math.radians(self.release_angle_deg)  # angulo actual
        self.omega = 0.0    # velocidad angular
        self.swinging = False
        self.released = False

        self.peak_force_N = 0.0
        self.current_force_N = self.mass_kg * G  # peso estatico
        self.time_elapsed = 0.0

        # Trail del pendulo (para dibujar trayectoria)
        self.trail = []

        # Historial de fuerza vs angulo para grafico
        self.force_history = []   # lista de (theta_deg, force_kN)
        self.force_time_history = []  # lista de (time, force_kN)

        # Calcular fuerza maxima teorica
        self._update_theoretical()

    def _update_theoretical(self):
        """Recalcula valores teoricos."""
        theta0 = math.radians(self.release_angle_deg)
        self.theoretical_max_N = max_force_formula(self.mass_kg, theta0)
        self.theoretical_max_kN = self.theoretical_max_N / 1000.0
        self.weight_N = self.mass_kg * G
        self.weight_kN = self.weight_N / 1000.0
        self.multiplier = force_multiplier(theta0)

    def release(self):
        """Libera el pendulo desde el angulo configurado."""
        self.reset()
        self.theta = math.radians(self.release_angle_deg)
        self.omega = 0.0
        self.swinging = True
        self.released = True

    # ── Actualizacion de fisica ──────────────────────────────────────

    def update(self, dt):
        """Actualiza la fisica del pendulo con substeps."""
        if not self.swinging:
            # Calcular fuerza estatica en posicion actual
            self.current_force_N = pendulum_force_at_angle(
                self.mass_kg, self.rope_len_m, self.theta, 0.0)
            return

        sub_dt = dt / PHYSICS_SUBSTEPS
        for _ in range(PHYSICS_SUBSTEPS):
            # Ecuacion de movimiento: d²theta/dt² = -(g/r)*sin(theta)
            alpha = -(G / self.rope_len_m) * math.sin(self.theta)
            self.omega += alpha * sub_dt
            self.omega *= DAMPING  # amortiguacion
            self.theta += self.omega * sub_dt

        self.time_elapsed += dt

        # Fuerza actual en el anclaje
        self.current_force_N = pendulum_force_at_angle(
            self.mass_kg, self.rope_len_m, self.theta, self.omega)

        # Asegurar que la fuerza no sea negativa (fisicamente, la cuerda
        # no tira - pero en un pendulo simple con angulos < 180, siempre
        # hay tension si theta < 90 desde vertical)
        self.current_force_N = max(0.0, self.current_force_N)

        # Actualizar pico
        if self.current_force_N > self.peak_force_N:
            self.peak_force_N = self.current_force_N

        # Historial para grafico
        theta_deg = math.degrees(self.theta)
        force_kN = self.current_force_N / 1000.0
        self.force_history.append((theta_deg, force_kN))
        if len(self.force_history) > 2000:
            self.force_history = self.force_history[-1500:]

        self.force_time_history.append((self.time_elapsed, force_kN))
        if len(self.force_time_history) > 2000:
            self.force_time_history = self.force_time_history[-1500:]

        # Trail
        self.trail.append(self.theta)
        if len(self.trail) > TRAIL_MAX:
            self.trail = self.trail[-TRAIL_MAX:]

    # ── Coordenadas de la escena ─────────────────────────────────────

    def _anchor_screen(self):
        """Posicion del anclaje en pixeles."""
        # Anclaje en la esquina superior izquierda del area de escena
        # (en la pared/edificio)
        ax = SCENE_L + 200
        ay = SCENE_T + 40
        return ax, ay

    def _pendulum_scale(self):
        """Pixeles por metro para la escena del pendulo."""
        available_h = SCENE_B - SCENE_T - 80
        available_w = SCENE_R - SCENE_L - 250
        max_dim = min(available_h, available_w)
        scale = max_dim / (self.rope_len_m * 1.15)
        return min(scale, 35.0)

    def _bob_screen(self, theta=None):
        """Posicion del bob en pixeles dado un angulo."""
        if theta is None:
            theta = self.theta
        ax, ay = self._anchor_screen()
        scale = self._pendulum_scale()
        bx = ax + self.rope_len_m * math.sin(theta) * scale
        by = ay + self.rope_len_m * math.cos(theta) * scale
        return int(bx), int(by)

    # ── Dibujo: Escena del pendulo ───────────────────────────────────

    def _draw_scene(self):
        """Dibuja la escena principal del pendulo."""
        ax, ay = self._anchor_screen()
        scale = self._pendulum_scale()

        # ── Fondo de la escena ───────────────────────────────────────
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (SCENE_L, SCENE_T, SCENE_R - SCENE_L,
                          SCENE_B - SCENE_T), border_radius=6)

        # ── Edificio / pared (lado izquierdo) ────────────────────────
        wall_x = SCENE_L
        wall_w = 180
        wall_t = SCENE_T
        wall_b = SCENE_B

        # Pared principal
        pygame.draw.rect(self.screen, (40, 45, 55),
                         (wall_x, wall_t, wall_w, wall_b - wall_t))
        # Borde de la pared
        pygame.draw.line(self.screen, (65, 70, 80),
                         (wall_x + wall_w, wall_t),
                         (wall_x + wall_w, wall_b), 3)

        # Textura de ladrillos
        brick_h = 20
        brick_w = 40
        for row in range(int((wall_b - wall_t) / brick_h) + 1):
            yy = wall_t + row * brick_h
            offset = (brick_w // 2) if row % 2 == 1 else 0
            pygame.draw.line(self.screen, (50, 55, 65),
                             (wall_x, yy), (wall_x + wall_w, yy), 1)
            for col in range(int(wall_w / brick_w) + 2):
                xx = wall_x + col * brick_w + offset
                if wall_x <= xx <= wall_x + wall_w:
                    pygame.draw.line(self.screen, (50, 55, 65),
                                     (xx, yy), (xx, yy + brick_h), 1)

        # ── Linea vertical (plomada) desde el anclaje ────────────────
        plumb_bottom = ay + int(self.rope_len_m * scale) + 10
        pygame.draw.line(self.screen, (C['grid'][0], C['grid'][1], C['grid'][2]),
                         (ax, ay), (ax, min(plumb_bottom, SCENE_B - 10)), 1)

        # ── Arco del angulo de liberacion (referencia) ───────────────
        if self.released or not self.swinging:
            release_rad = math.radians(self.release_angle_deg)
            arc_r = 50
            n_arc = 30
            arc_pts = []
            for i in range(n_arc + 1):
                a = release_rad * i / n_arc
                px = ax + arc_r * math.sin(a)
                py = ay + arc_r * math.cos(a)
                arc_pts.append((int(px), int(py)))
            if len(arc_pts) > 1:
                pygame.draw.lines(self.screen, C['info'], False, arc_pts, 1)
            # Etiqueta del angulo
            mid_a = release_rad / 2.0
            lx = ax + int((arc_r + 16) * math.sin(mid_a))
            ly = ay + int((arc_r + 16) * math.cos(mid_a))
            s = self.fx.render(f'{self.release_angle_deg}', True, C['info'])
            self.screen.blit(s, (lx - s.get_width() // 2,
                                 ly - s.get_height() // 2))

        # ── Linea fantasma a posicion de liberacion ──────────────────
        if self.released:
            release_rad = math.radians(self.release_angle_deg)
            gx = ax + int(self.rope_len_m * math.sin(release_rad) * scale)
            gy = ay + int(self.rope_len_m * math.cos(release_rad) * scale)
            pygame.draw.line(self.screen, (*C['info'][:3],),
                             (ax, ay), (gx, gy), 1)
            # Circulo fantasma
            pygame.draw.circle(self.screen, C['info'], (gx, gy), 8, 1)

        # ── Trail (trayectoria) ──────────────────────────────────────
        if len(self.trail) > 2:
            trail_pts = []
            for i, th in enumerate(self.trail):
                bx, by = self._bob_screen(th)
                trail_pts.append((bx, by))
            # Dibujar con opacidad degradante
            for i in range(1, len(trail_pts)):
                alpha = i / len(trail_pts)
                col = lerp_color((20, 20, 40), C['primary'], alpha * 0.5)
                pygame.draw.line(self.screen, col,
                                 trail_pts[i - 1], trail_pts[i], 1)

        # ── Cuerda ──────────────────────────────────────────────────
        bx, by = self._bob_screen()

        # Color de cuerda segun tension
        f_kn = self.current_force_N / 1000.0
        rope_col = force_color(f_kn)
        # Efecto de cuerda con pequeno sway
        rope_thickness = 3
        pygame.draw.line(self.screen, rope_col, (ax, ay), (bx, by),
                         rope_thickness)

        # ── Anclaje ─────────────────────────────────────────────────
        # Placa de anclaje en la pared
        pygame.draw.rect(self.screen, C['anchor'],
                         (ax - 12, ay - 12, 24, 24), border_radius=3)
        pygame.draw.rect(self.screen, C['text'],
                         (ax - 12, ay - 12, 24, 24), width=2, border_radius=3)
        # Perno central
        pygame.draw.circle(self.screen, (60, 60, 70), (ax, ay), 4)
        pygame.draw.circle(self.screen, C['text'], (ax, ay), 4, 1)

        s = self.fx.render('ANCLAJE', True, C['anchor'])
        self.screen.blit(s, (ax - s.get_width() // 2, ay - 26))

        # ── Persona / carga ─────────────────────────────────────────
        self._draw_person(bx, by)

        # ── Flecha de fuerza en el anclaje ───────────────────────────
        # Flecha apuntando desde el anclaje hacia la cuerda (tension)
        f_ratio = min(f_kn / (self.weight_kN * 5), 1.0)
        arrow_len = 30 + f_ratio * 80
        # Direccion: desde anclaje hacia el bob
        dx = bx - ax
        dy = by - ay
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            ux, uy = dx / dist, dy / dist
            end_x = ax + ux * arrow_len
            end_y = ay + uy * arrow_len
            draw_arrow(self.screen, force_color(f_kn),
                       (ax, ay), (int(end_x), int(end_y)), 3, 10)
            # Etiqueta de fuerza
            lbl = self.fs.render(f'{f_kn:.2f} kN', True, force_color(f_kn))
            lbl_x = int(end_x + ux * 12)
            lbl_y = int(end_y + uy * 12)
            self.screen.blit(lbl, (lbl_x - lbl.get_width() // 2,
                                   lbl_y - lbl.get_height() // 2))

        # ── Flecha de peso (siempre hacia abajo) ────────────────────
        w_arrow_len = 30 + min(self.weight_kN / 5.0, 1.0) * 40
        draw_arrow(self.screen, C['danger'],
                   (bx, by + 22),
                   (bx, by + 22 + int(w_arrow_len)), 2, 8)
        s = self.fx.render(f'W={self.weight_kN:.2f}kN', True, C['danger'])
        self.screen.blit(s, (bx + 10, by + 28))

        # ── Flecha centripeta (hacia el anclaje, cuando oscila) ─────
        if self.swinging and abs(self.omega) > 0.05:
            fc_N = self.mass_kg * self.omega * self.omega * self.rope_len_m
            fc_kN = fc_N / 1000.0
            if fc_kN > 0.05:
                fc_ratio = min(fc_kN / (self.weight_kN * 3), 1.0)
                fc_len = 20 + fc_ratio * 60
                # Hacia el anclaje
                if dist > 0:
                    end_cx = bx - ux * fc_len
                    end_cy = by - uy * fc_len
                    draw_arrow(self.screen, C['primary'],
                               (bx, by),
                               (int(end_cx), int(end_cy)), 2, 7)
                    s = self.fi.render(f'Fc={fc_kN:.2f}kN', True, C['primary'])
                    self.screen.blit(s, (int(end_cx) - s.get_width() - 4,
                                         int(end_cy) - 4))

        # ── Angulo actual ───────────────────────────────────────────
        theta_deg = math.degrees(self.theta)
        s = self.fs.render(f'theta = {theta_deg:.1f} deg', True, C['text'])
        self.screen.blit(s, (ax + 30, ay + 10))

        # ── Velocidad ───────────────────────────────────────────────
        v = abs(self.omega) * self.rope_len_m
        s = self.fx.render(f'v = {v:.2f} m/s', True, C['dark_text'])
        self.screen.blit(s, (ax + 30, ay + 26))

        # ── Indicador de estado ─────────────────────────────────────
        if not self.released:
            s = self.fm.render('Presione ESPACIO para liberar', True,
                               C['warning'])
            self.screen.blit(s, (SCENE_L + (SCENE_R - SCENE_L) // 2
                                 - s.get_width() // 2, SCENE_B - 28))
        elif self.swinging and abs(self.omega) < 0.01 and self.time_elapsed > 2:
            s = self.fm.render('Pendulo en reposo - ESPACIO para relanzar',
                               True, C['dark_text'])
            self.screen.blit(s, (SCENE_L + (SCENE_R - SCENE_L) // 2
                                 - s.get_width() // 2, SCENE_B - 28))

    def _draw_person(self, cx, cy):
        """Dibuja una persona simplificada (rescatista/paciente)."""
        # Conexion cuerda-arnes
        pygame.draw.line(self.screen, C['anchor'],
                         (cx, cy), (cx, cy + 6), 2)

        # Cabeza
        pygame.draw.circle(self.screen, C['primary'], (cx, cy + 12), 6)
        pygame.draw.circle(self.screen, C['text'], (cx, cy + 12), 6, 1)

        # Cuerpo
        pygame.draw.line(self.screen, C['text'], (cx, cy + 18), (cx, cy + 34), 2)

        # Brazos
        pygame.draw.line(self.screen, C['text'],
                         (cx - 8, cy + 22), (cx + 8, cy + 22), 2)

        # Piernas
        pygame.draw.line(self.screen, C['text'],
                         (cx, cy + 34), (cx - 6, cy + 44), 2)
        pygame.draw.line(self.screen, C['text'],
                         (cx, cy + 34), (cx + 6, cy + 44), 2)

        # Arnes (circulo en cintura)
        pygame.draw.circle(self.screen, C['rope'], (cx, cy + 28), 3, 1)

        # Etiqueta masa
        s = self.fi.render(f'{self.mass_kg}kg', True, C['text'])
        self.screen.blit(s, (cx + 10, cy + 16))

    # ── Dibujo: Grafico de fuerza vs tiempo ──────────────────────────

    def _draw_graph(self):
        """Dibuja el grafico de fuerza vs tiempo."""
        gx, gy = GRAPH_L, GRAPH_T
        gw = GRAPH_R - GRAPH_L
        gh = GRAPH_B - GRAPH_T

        # Fondo
        pygame.draw.rect(self.screen, (18, 18, 30),
                         (gx, gy, gw, gh), border_radius=6)

        # Titulo
        s = self.fm.render('Fuerza en Anclaje (kN) vs Tiempo',
                           True, C['text'])
        self.screen.blit(s, (gx + gw // 2 - s.get_width() // 2, gy + 3))

        # Area interna
        ix = gx + 55
        iw = gw - 70
        iy = gy + 22
        ih = gh - 42

        pygame.draw.rect(self.screen, (12, 12, 22), (ix, iy, iw, ih))

        # Escala vertical
        max_f = max(self.theoretical_max_kN * 1.2, self.weight_kN * 3.5,
                    NFPA_WORK_LOAD * 1.1)
        if self.peak_force_N > 0:
            max_f = max(max_f, self.peak_force_N / 1000.0 * 1.15)
        max_f = min(max_f, 60.0)

        def map_y(f_kn):
            frac = f_kn / max_f
            return iy + ih - int(frac * ih)

        # Lineas de referencia horizontal
        for val, label, col in [
            (self.weight_kN, f'Peso={self.weight_kN:.2f}', C['info']),
            (NFPA_WORK_LOAD, f'NFPA={NFPA_WORK_LOAD}', C['danger']),
            (self.theoretical_max_kN, f'F_max={self.theoretical_max_kN:.2f}',
             C['warning']),
        ]:
            if val > max_f:
                continue
            yy = map_y(val)
            pygame.draw.line(self.screen, col, (ix, yy), (ix + iw, yy), 1)
            s = self.fi.render(label, True, col)
            self.screen.blit(s, (ix - s.get_width() - 3, yy - 5))

        # Grid kN
        step = 2.0 if max_f < 15 else 5.0 if max_f < 30 else 10.0
        val = step
        while val < max_f:
            yy = map_y(val)
            pygame.draw.line(self.screen, C['grid'], (ix, yy),
                             (ix + iw, yy), 1)
            s = self.fi.render(f'{val:.0f}', True, C['grid'])
            self.screen.blit(s, (ix - s.get_width() - 3, yy - 5))
            val += step

        # Datos de fuerza vs tiempo
        if len(self.force_time_history) > 1:
            # Ventana de tiempo: ultimos 10 segundos
            t_window = 10.0
            t_max = self.time_elapsed
            t_min = max(0, t_max - t_window)

            pts = []
            for t, f_kn in self.force_time_history:
                if t < t_min:
                    continue
                frac_x = (t - t_min) / t_window if t_window > 0 else 0.5
                px = ix + int(frac_x * iw)
                py = map_y(min(f_kn, max_f))
                py = max(iy, min(py, iy + ih))
                pts.append((px, py))

            if len(pts) > 1:
                # Dibujar area rellena (gradiente simplificado)
                base_y = map_y(0)
                for i in range(1, len(pts)):
                    x1, y1 = pts[i - 1]
                    x2, y2 = pts[i]
                    f_avg = (self.force_time_history[
                        max(0, len(self.force_time_history) - len(pts) + i)][1]
                        if i < len(pts) else self.weight_kN)
                    col = force_color(f_avg)
                    fill_col = (col[0] // 5, col[1] // 5, col[2] // 5)
                    if x2 > x1:
                        pygame.draw.rect(self.screen, fill_col,
                                         (x1, min(y1, y2), x2 - x1,
                                          base_y - min(y1, y2)))

                # Linea principal
                pygame.draw.lines(self.screen, C['primary'], False, pts, 2)

                # Punto actual
                if pts:
                    pygame.draw.circle(self.screen, C['white'],
                                       pts[-1], 4)

        # Etiquetas de tiempo
        s = self.fi.render('Tiempo (s)', True, C['grid'])
        self.screen.blit(s, (ix + iw // 2 - s.get_width() // 2,
                             iy + ih + 4))

        # Eje Y label
        s = self.fi.render('kN', True, C['grid'])
        self.screen.blit(s, (ix - 20, iy - 12))

    # ── Dibujo: Barra de fuerza (gauge vertical) ────────────────────

    def _draw_force_gauge(self, px, py, pw, ph):
        """Dibuja un gauge vertical de fuerza."""
        # Fondo del gauge
        pygame.draw.rect(self.screen, (25, 25, 40),
                         (px, py, pw, ph), border_radius=4)
        pygame.draw.rect(self.screen, C['grid'],
                         (px, py, pw, ph), width=1, border_radius=4)

        # Titulo
        s = self.fi.render('FUERZA', True, C['text'])
        self.screen.blit(s, (px + pw // 2 - s.get_width() // 2, py + 3))
        s = self.fi.render('ANCLAJE', True, C['text'])
        self.screen.blit(s, (px + pw // 2 - s.get_width() // 2, py + 14))

        # Area de la barra
        bar_x = px + 12
        bar_w = pw - 24
        bar_y = py + 30
        bar_h = ph - 50

        # Fondo de la barra
        pygame.draw.rect(self.screen, (15, 15, 25),
                         (bar_x, bar_y, bar_w, bar_h))

        # Escala: 0 a max_force_display
        max_display = max(self.theoretical_max_kN * 1.3, NFPA_WORK_LOAD * 1.2,
                          self.weight_kN * 5)
        if self.peak_force_N > 0:
            max_display = max(max_display, self.peak_force_N / 1000.0 * 1.15)

        f_kn = self.current_force_N / 1000.0
        fill_frac = min(f_kn / max_display, 1.0)
        fill_h = int(fill_frac * bar_h)

        # Relleno con color segun nivel
        col = force_color(f_kn)
        if fill_h > 0:
            # Gradiente vertical simplificado
            for row in range(fill_h):
                frac = row / max(fill_h, 1)
                rc = lerp_color((col[0] // 3, col[1] // 3, col[2] // 3),
                                col, frac)
                yy = bar_y + bar_h - fill_h + row
                pygame.draw.line(self.screen, rc,
                                 (bar_x + 1, yy),
                                 (bar_x + bar_w - 1, yy), 1)

        # Marcas de referencia
        for val, label, mcol in [
            (self.weight_kN, 'W', C['info']),
            (NFPA_WORK_LOAD, 'NFPA', C['danger']),
            (ROPE_MBS, 'MBS', (200, 40, 40)),
        ]:
            if val > max_display:
                continue
            frac = val / max_display
            yy = bar_y + bar_h - int(frac * bar_h)
            pygame.draw.line(self.screen, mcol,
                             (bar_x - 2, yy), (bar_x + bar_w + 2, yy), 1)
            s = self.fi.render(label, True, mcol)
            self.screen.blit(s, (bar_x + bar_w + 4, yy - 5))

        # Pico de fuerza
        if self.peak_force_N > 0:
            peak_kn = self.peak_force_N / 1000.0
            if peak_kn <= max_display:
                peak_frac = peak_kn / max_display
                peak_y = bar_y + bar_h - int(peak_frac * bar_h)
                pygame.draw.line(self.screen, C['warning'],
                                 (bar_x - 3, peak_y),
                                 (bar_x + bar_w + 3, peak_y), 2)
                # Triangulo indicador
                pygame.draw.polygon(self.screen, C['warning'], [
                    (bar_x - 5, peak_y),
                    (bar_x - 10, peak_y - 4),
                    (bar_x - 10, peak_y + 4),
                ])

        # Valor actual
        s = self.fb.render(f'{f_kn:.2f}', True, col)
        self.screen.blit(s, (px + pw // 2 - s.get_width() // 2,
                             py + ph - 18))

    # ── Dibujo: Panel de datos ──────────────────────────────────────

    def _draw_panel(self):
        """Dibuja el panel lateral con datos y controles."""
        px, py = PANEL_L, PANEL_T
        pw = WIDTH - PANEL_L - 12
        ph = HEIGHT - PANEL_T - 12

        pygame.draw.rect(self.screen, C['panel'],
                         (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (px, py, pw, ph), width=1, border_radius=8)

        x = px + 12
        y = py + 8

        def heading(text, color=C['primary']):
            nonlocal y
            s = self.fb.render(text, True, color)
            self.screen.blit(s, (x, y))
            y += 21

        def line(text, color=C['text']):
            nonlocal y
            s = self.fs.render(text, True, color)
            self.screen.blit(s, (x + 4, y))
            y += 15

        def line_sm(text, color=C['dark_text']):
            nonlocal y
            s = self.fx.render(text, True, color)
            self.screen.blit(s, (x + 4, y))
            y += 13

        def sep():
            nonlocal y
            pygame.draw.line(self.screen, C['grid'],
                             (x, y + 2), (x + pw - 24, y + 2), 1)
            y += 7

        # ── Gauge de fuerza (a la derecha del panel) ─────────────────
        gauge_w = 70
        gauge_h = 250
        gauge_x = px + pw - gauge_w - 10
        gauge_y = py + 10
        self._draw_force_gauge(gauge_x, gauge_y, gauge_w, gauge_h)

        # ── Parametros ──────────────────────────────────────────────
        heading('PARAMETROS')
        line(f'Masa:            {self.mass_kg} kg')
        line(f'Peso (W):        {self.weight_kN:.2f} kN')
        line(f'Longitud cuerda: {self.rope_len_m:.1f} m')
        line(f'Angulo liberac.: {self.release_angle_deg} deg')
        sep()

        # ── Estado actual ───────────────────────────────────────────
        heading('ESTADO ACTUAL')
        theta_deg = math.degrees(self.theta)
        f_kn = self.current_force_N / 1000.0
        v = abs(self.omega) * self.rope_len_m

        f_col = force_color(f_kn)
        line(f'Angulo actual:   {theta_deg:+.1f} deg')
        line(f'Velocidad:       {v:.2f} m/s')
        line(f'Vel. angular:    {abs(self.omega):.3f} rad/s')
        line(f'Fuerza anclaje:  {f_kn:.2f} kN', f_col)
        line(f'Multiplo peso:   {f_kn / self.weight_kN:.2f}x W'
             if self.weight_kN > 0 else 'N/A', f_col)
        sep()

        # ── Fuerza maxima ───────────────────────────────────────────
        peak_kn = self.peak_force_N / 1000.0
        peak_col = force_color(peak_kn) if peak_kn > 0 else C['text']
        heading('FUERZA MAXIMA')
        line(f'Pico medido:     {peak_kn:.2f} kN', peak_col)
        if self.weight_kN > 0 and peak_kn > 0:
            line(f'Multiplo:        {peak_kn / self.weight_kN:.2f}x W',
                 peak_col)
        line(f'Teorico max:     {self.theoretical_max_kN:.2f} kN', C['warning'])
        line(f'Multiplicador:   {self.multiplier:.2f}x', C['warning'])
        sep()

        # ── Formula ─────────────────────────────────────────────────
        heading('FORMULA')
        line_sm('F_max = m*g*(3 - 2*cos(theta_0))', C['primary'])
        line_sm(f'     = {self.mass_kg}*{G}*(3 - 2*cos({self.release_angle_deg}))')
        line_sm(f'     = {self.theoretical_max_kN:.2f} kN', C['warning'])
        y += 2
        line_sm('En el fondo: F = mg*cos(th) + m*w^2*r', C['primary'])
        line_sm('  (peso radial + centripeta)')
        sep()

        # ── Tabla de multiplicadores ─────────────────────────────────
        heading('TABLA DE MULTIPLICADORES')
        line_sm('Angulo    Multiplicador    Fuerza', C['text'])

        angles_table = [30, 45, 60, 90, 120, 150, 180]
        for a in angles_table:
            mult = force_multiplier(math.radians(a))
            f_val = self.mass_kg * G * mult / 1000.0
            marker = ' <--' if a == self.release_angle_deg else ''
            col = C['warning'] if a == self.release_angle_deg else C['dark_text']
            if a == self.release_angle_deg:
                col = C['warning']
            elif mult > 4:
                col = C['danger']
            elif mult > 2.5:
                col = C['secondary']

            line_sm(f'  {a:>3} deg    {mult:.2f}x           '
                    f'{f_val:.2f} kN{marker}', col)
        sep()

        # ── Seguridad ──────────────────────────────────────────────
        heading('SEGURIDAD', C['danger'])
        if peak_kn > ROPE_MBS:
            line('ROTURA DE CUERDA POSIBLE', C['danger'])
            line(f'Fuerza ({peak_kn:.1f}kN) > MBS ({ROPE_MBS}kN)', C['danger'])
        elif peak_kn > NFPA_WORK_LOAD:
            line('EXCEDE LIMITE NFPA', C['secondary'])
            line(f'Fuerza ({peak_kn:.1f}kN) > NFPA ({NFPA_WORK_LOAD}kN)',
                 C['secondary'])
        elif peak_kn > UIAA_MAX_IMPACT:
            line('EXCEDE LIMITE UIAA', C['warning'])
            line(f'Fuerza ({peak_kn:.1f}kN) > UIAA ({UIAA_MAX_IMPACT}kN)',
                 C['warning'])
        elif self.released:
            line('Dentro de limites seguros', C['accent'])
            line(f'Fuerza ({peak_kn:.1f}kN) < UIAA ({UIAA_MAX_IMPACT}kN)',
                 C['accent'])
        else:
            line('Esperando liberacion...', C['dark_text'])
        sep()

        # ── Educacion ──────────────────────────────────────────────
        heading('CONCEPTO CLAVE', C['info'])
        line_sm('Cuando un rescatista oscila como', C['dark_text'])
        line_sm('pendulo, la fuerza en el anclaje', C['dark_text'])
        line_sm('se multiplica. Una caida lateral', C['dark_text'])
        line_sm('que se convierte en pendulo genera', C['dark_text'])
        line_sm('fuerzas inesperadamente altas.', C['dark_text'])
        y += 3
        line_sm('A 90 deg: 3x el peso (peligroso)', C['secondary'])
        line_sm('A 180 deg: 5x el peso (catastrofico)', C['danger'])
        sep()

        # ── Controles ──────────────────────────────────────────────
        heading('CONTROLES', C['dark_text'])
        controls = [
            ('[1-5] Angulo: 30/45/60/90/120 deg', C['dark_text']),
            ('[ESPACIO] Liberar / Reiniciar', C['dark_text']),
            ('[Arriba/Abajo] Masa +/- 5 kg', C['dark_text']),
            ('[+/-] Cuerda +/- 0.5 m', C['dark_text']),
            ('[R] Reiniciar   [ESC] Salir', C['dark_text']),
        ]
        for text, col in controls:
            line_sm(text, col)

    # ── Dibujo: Titulo ──────────────────────────────────────────────

    def _draw_title(self):
        """Dibuja el titulo superior."""
        s = self.ft.render(
            'FISICA DEL RESCATE  |  Modulo 12: Efecto Pendulo en Rescate',
            True, C['primary'])
        self.screen.blit(s, (15, 15))

        # Subtitulo
        sub = (f'Masa: {self.mass_kg}kg  |  '
               f'Cuerda: {self.rope_len_m:.1f}m  |  '
               f'Angulo: {self.release_angle_deg} deg  |  '
               f'F_max teorica: {self.theoretical_max_kN:.2f} kN  '
               f'({self.multiplier:.1f}x W)')
        s = self.fm.render(sub, True, C['dark_text'])
        self.screen.blit(s, (15, 48))

    # ── Bucle principal ─────────────────────────────────────────────

    def run(self):
        """Bucle principal de la simulacion."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap para evitar saltos

            # ── Eventos ─────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_SPACE:
                        self.release()

                    elif event.key == pygame.K_r:
                        self.reset()

                    elif event.key in self.ANGLE_PRESETS:
                        self.release_angle_deg = self.ANGLE_PRESETS[event.key]
                        self._update_theoretical()
                        if not self.swinging:
                            self.theta = math.radians(self.release_angle_deg)
                            self.current_force_N = pendulum_force_at_angle(
                                self.mass_kg, self.rope_len_m,
                                self.theta, 0.0)

                    elif event.key == pygame.K_UP:
                        self.mass_kg = min(200, self.mass_kg + 5)
                        self._update_theoretical()

                    elif event.key == pygame.K_DOWN:
                        self.mass_kg = max(40, self.mass_kg - 5)
                        self._update_theoretical()

                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                       pygame.K_KP_PLUS):
                        self.rope_len_m = min(20.0, self.rope_len_m + 0.5)
                        self._update_theoretical()

                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.rope_len_m = max(2.0, self.rope_len_m - 0.5)
                        self._update_theoretical()

            # ── Actualizar fisica ───────────────────────────────────
            self.update(dt)

            # ── Dibujar ─────────────────────────────────────────────
            self.screen.fill(C['bg'])
            self._draw_title()
            self._draw_scene()
            self._draw_graph()
            self._draw_panel()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ══════════════════════════════════════════════════════════════════════
#  Punto de entrada
# ══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    sim = PendulumSimulator()
    sim.run()
