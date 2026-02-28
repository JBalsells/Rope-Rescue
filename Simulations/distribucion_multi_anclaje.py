"""
╔══════════════════════════════════════════════════════════════════════╗
║  FISICA DEL RESCATE · Modulo 14: Distribucion Multi-Anclaje        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulacion interactiva (Pygame) de la distribucion de fuerzas     ║
║  en sistemas de anclaje con 3 y 4 puntos auto-ecualizados.        ║
║                                                                      ║
║  Fisica clave:                                                       ║
║   F_i = W * cos(alpha_i) / SUM(cos(alpha_j))                       ║
║   donde alpha_i = angulo del tirante i respecto a la vertical       ║
║                                                                      ║
║  Conceptos demostrados:                                              ║
║   - La carga NO se distribuye en partes iguales salvo simetria     ║
║   - Los tirantes mas verticales cargan mas fuerza                   ║
║   - Si un anclaje falla, los demas reciben carga de choque         ║
║   - El angulo maximo de cada tirante afecta la seguridad           ║
║                                                                      ║
║  Controles:                                                          ║
║   [TAB]      Ciclar anclaje seleccionado                            ║
║   [Flechas]  Mover el anclaje seleccionado                          ║
║   [3/4]      Cambiar entre sistema de 3 o 4 puntos                  ║
║   [F]        Simular fallo del anclaje seleccionado                 ║
║   [W/S]      Aumentar / reducir masa de la carga                    ║
║   [R]        Reiniciar                                               ║
║   [ESC]      Salir                                                   ║
║                                                                      ║
║  Ejecutar:  python 14_distribucion_multi_anclaje.py                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import pygame
from config import PG_COLORS as C, G

WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Limites de seguridad ────────────────────────────────────────────
ROPE_MBS = 30.0          # kN cuerda estatica 11 mm
ANCHOR_MBS = 25.0        # kN resistencia tipica anclaje
NFPA_WORK_LOAD = 13.5    # kN limite carga de trabajo NFPA
SAFETY_FACTOR_MIN = 10   # Factor de seguridad minimo rescate

# ── Layout ──────────────────────────────────────────────────────────
SCENE_LEFT = 40
SCENE_RIGHT = 880
SCENE_TOP = 90
SCENE_BOTTOM = 780

PANEL_LEFT = 900
PANEL_TOP = 60
PANEL_WIDTH = WIDTH - PANEL_LEFT - 15
PANEL_HEIGHT = HEIGHT - PANEL_TOP - 55

# ── Punto maestro (centro del sistema, donde convergen los tirantes)
MASTER_POINT_X = 460
MASTER_POINT_Y = 560

# ── Velocidad de movimiento de anclajes ─────────────────────────────
ANCHOR_SPEED = 3
ANCHOR_SPEED_FAST = 8

# ── Colores por anclaje ─────────────────────────────────────────────
ANCHOR_COLORS = [
    (0, 200, 255),     # Anclaje 1 - Cyan
    (255, 180, 0),     # Anclaje 2 - Naranja
    (180, 0, 255),     # Anclaje 3 - Violeta
    (0, 255, 120),     # Anclaje 4 - Verde
]

ANCHOR_LABELS = ['A1', 'A2', 'A3', 'A4']


# ══════════════════════════════════════════════════════════════════════
#  Fisica: Distribucion de fuerzas en multi-anclaje auto-ecualizado
# ══════════════════════════════════════════════════════════════════════

def compute_anchor_forces(anchor_positions, master_point, weight_kn):
    """
    Calcula la fuerza en cada tirante de un sistema auto-ecualizado.

    Para cada tirante i:
      alpha_i = angulo del tirante respecto a la vertical (desde master point)
      F_i = W * cos(alpha_i) / SUM(cos(alpha_j))

    Retorna lista de dicts con toda la informacion por anclaje.
    """
    mx, my = master_point
    n = len(anchor_positions)

    if n == 0:
        return []

    results = []
    cos_sum = 0.0

    # Primera pasada: calcular angulos y cosenos
    for i, (ax, ay) in enumerate(anchor_positions):
        dx = ax - mx
        dy = my - ay  # positivo hacia arriba (anclaje esta arriba del master)
        sling_length = math.sqrt(dx * dx + dy * dy)

        if sling_length < 1.0:
            sling_length = 1.0

        # Angulo respecto a la vertical (linea de carga)
        # vertical = (0, 1) apuntando hacia arriba desde el master point
        cos_alpha = dy / sling_length
        cos_alpha = max(cos_alpha, 0.01)  # evitar cero o negativo
        alpha_deg = math.degrees(math.acos(min(cos_alpha, 1.0)))

        results.append({
            'index': i,
            'pos': (ax, ay),
            'dx': dx,
            'dy': dy,
            'sling_length': sling_length,
            'alpha_deg': alpha_deg,
            'cos_alpha': cos_alpha,
            'force_kn': 0.0,
            'percentage': 0.0,
            'failed': False,
        })
        cos_sum += cos_alpha

    # Segunda pasada: calcular fuerzas
    if cos_sum > 0.001:
        for r in results:
            r['force_kn'] = weight_kn * r['cos_alpha'] / cos_sum
            r['percentage'] = r['force_kn'] / weight_kn * 100.0
    else:
        # Caso degenerado: distribuir uniformemente
        for r in results:
            r['force_kn'] = weight_kn / n
            r['percentage'] = 100.0 / n

    return results


def compute_failure_scenario(anchor_positions, master_point, weight_kn,
                             failed_index):
    """
    Calcula las fuerzas si el anclaje 'failed_index' falla.
    Retorna la lista de resultados con el anclaje fallido marcado.
    """
    remaining_positions = []
    remaining_indices = []
    for i, pos in enumerate(anchor_positions):
        if i != failed_index:
            remaining_positions.append(pos)
            remaining_indices.append(i)

    if not remaining_positions:
        return []

    sub_results = compute_anchor_forces(remaining_positions, master_point,
                                        weight_kn)

    # Reconstruir la lista completa con el fallido incluido
    full_results = []
    sub_idx = 0
    for i in range(len(anchor_positions)):
        if i == failed_index:
            full_results.append({
                'index': i,
                'pos': anchor_positions[i],
                'dx': 0, 'dy': 0,
                'sling_length': 0,
                'alpha_deg': 0,
                'cos_alpha': 0,
                'force_kn': 0.0,
                'percentage': 0.0,
                'failed': True,
            })
        else:
            r = sub_results[sub_idx]
            r['index'] = i
            r['pos'] = anchor_positions[i]
            r['failed'] = False
            full_results.append(r)
            sub_idx += 1

    return full_results


def sling_tension(force_kn, alpha_deg):
    """
    Tension real en el tirante (a lo largo de su eje).
    F_tirante = F_i / cos(alpha_i)
    Donde F_i ya es la componente vertical asignada.

    En realidad, en un sistema ecualizado con placa/anillo,
    la tension en cada tirante es:
    T_i = W * 1 / (N * cos(alpha_i)) para distribucion uniforme,
    pero para la distribucion real:
    T_i = F_i / cos(alpha_i) donde F_i = W * cos(alpha_i) / sum(cos(alpha_j))
    Simplificando: T_i = W / sum(cos(alpha_j))

    En la practica, la tension en el tirante ES la fuerza que transmite
    a lo largo de su eje, que depende del angulo.
    """
    alpha_rad = math.radians(alpha_deg)
    cos_a = math.cos(alpha_rad)
    if cos_a < 0.01:
        return 99.99
    return force_kn / cos_a


# ══════════════════════════════════════════════════════════════════════
#  Clase principal del simulador
# ══════════════════════════════════════════════════════════════════════

class MultiAnchorSim:
    """Simulador de distribucion de fuerzas en multi-anclaje."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Fisica del Rescate -- Distribucion Multi-Anclaje')
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont('DejaVu Sans', 26, bold=True)
        self.font_big = pygame.font.SysFont('DejaVu Sans', 18, bold=True)
        self.font_med = pygame.font.SysFont('DejaVu Sans', 14, bold=True)
        self.font_sm = pygame.font.SysFont('DejaVu Sans', 12)
        self.font_xs = pygame.font.SysFont('DejaVu Sans', 11)
        self.font_formula = pygame.font.SysFont('DejaVu Sans', 13, italic=True)

        self.reset()

    def reset(self):
        """Estado inicial del simulador."""
        self.mass_kg = 100
        self.num_anchors = 3
        self.selected_anchor = 0
        self.show_failure = False
        self.failed_anchor_index = -1
        self.failure_flash_timer = 0.0

        # Posiciones iniciales de los anclajes (3 puntos, espaciados simetricamente)
        self._setup_anchor_positions()

        # Dragging con mouse
        self.dragging_anchor = -1

        # Resultado del calculo de fuerzas
        self.anchor_results = []
        self.failure_results = []

    def _setup_anchor_positions(self):
        """Configura posiciones iniciales simetricas para los anclajes."""
        cx = MASTER_POINT_X
        base_y = 180  # Linea base superior (roca)
        spread = 180  # Separacion horizontal

        if self.num_anchors == 3:
            self.anchor_positions = [
                [cx - spread, base_y],
                [cx, base_y - 40],
                [cx + spread, base_y],
            ]
        else:  # 4 puntos
            self.anchor_positions = [
                [cx - spread, base_y],
                [cx - spread // 3, base_y - 30],
                [cx + spread // 3, base_y - 30],
                [cx + spread, base_y],
            ]

        self.show_failure = False
        self.failed_anchor_index = -1
        if self.selected_anchor >= self.num_anchors:
            self.selected_anchor = 0

    def _recalculate(self):
        """Recalcula todas las fuerzas."""
        W_kN = self.mass_kg * G / 1000.0
        master = (MASTER_POINT_X, MASTER_POINT_Y)

        self.anchor_results = compute_anchor_forces(
            self.anchor_positions, master, W_kN)

        # Calcular escenario de fallo para el anclaje seleccionado
        self.failure_results = compute_failure_scenario(
            self.anchor_positions, master, W_kN, self.selected_anchor)

    # ── Entrada ─────────────────────────────────────────────────────────

    def handle_events(self):
        """Procesa eventos de teclado y mouse."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                elif event.key == pygame.K_TAB:
                    self.selected_anchor = (
                        (self.selected_anchor + 1) % self.num_anchors)
                    self.show_failure = False

                elif event.key == pygame.K_3:
                    if self.num_anchors != 3:
                        self.num_anchors = 3
                        self._setup_anchor_positions()

                elif event.key == pygame.K_4:
                    if self.num_anchors != 4:
                        self.num_anchors = 4
                        self._setup_anchor_positions()

                elif event.key == pygame.K_f:
                    self.show_failure = not self.show_failure
                    if self.show_failure:
                        self.failed_anchor_index = self.selected_anchor
                        self.failure_flash_timer = 2.0
                    else:
                        self.failed_anchor_index = -1

                elif event.key == pygame.K_w:
                    self.mass_kg = min(self.mass_kg + 10, 500)
                elif event.key == pygame.K_s:
                    self.mass_kg = max(self.mass_kg - 10, 20)

                elif event.key == pygame.K_r:
                    saved_n = self.num_anchors
                    self.reset()
                    self.num_anchors = saved_n
                    self._setup_anchor_positions()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = event.pos
                    # Verificar si se hizo clic en un anclaje
                    for i, (ax, ay) in enumerate(self.anchor_positions):
                        dist = math.sqrt((mx - ax) ** 2 + (my - ay) ** 2)
                        if dist < 20:
                            self.dragging_anchor = i
                            self.selected_anchor = i
                            self.show_failure = False
                            break

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_anchor = -1

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_anchor >= 0:
                    mx, my = event.pos
                    # Limitar a la zona de escena y por encima del master point
                    mx = max(SCENE_LEFT + 30, min(mx, SCENE_RIGHT - 30))
                    my = max(SCENE_TOP + 20, min(my, MASTER_POINT_Y - 40))
                    self.anchor_positions[self.dragging_anchor] = [mx, my]

        # Movimiento continuo con flechas (held keys)
        keys = pygame.key.get_pressed()
        speed = ANCHOR_SPEED_FAST if keys[pygame.K_LSHIFT] else ANCHOR_SPEED
        idx = self.selected_anchor

        if idx < len(self.anchor_positions):
            ax, ay = self.anchor_positions[idx]
            moved = False
            if keys[pygame.K_LEFT]:
                ax -= speed
                moved = True
            if keys[pygame.K_RIGHT]:
                ax += speed
                moved = True
            if keys[pygame.K_UP]:
                ay -= speed
                moved = True
            if keys[pygame.K_DOWN]:
                ay += speed
                moved = True

            if moved:
                ax = max(SCENE_LEFT + 30, min(ax, SCENE_RIGHT - 30))
                ay = max(SCENE_TOP + 20, min(ay, MASTER_POINT_Y - 40))
                self.anchor_positions[idx] = [ax, ay]
                if self.show_failure:
                    self.show_failure = False
                    self.failed_anchor_index = -1

        return True

    # ── Dibujo ──────────────────────────────────────────────────────────

    def _force_color(self, percentage, num_points):
        """Color del tirante basado en porcentaje de carga."""
        ideal = 100.0 / num_points
        ratio = percentage / ideal if ideal > 0 else 1.0

        if ratio <= 1.1:
            # Verde (carga equilibrada o menor)
            return C['accent']
        elif ratio <= 1.5:
            # Amarillo (moderadamente sobrecargado)
            t = (ratio - 1.1) / 0.4
            r = int(76 + t * (255 - 76))
            g = int(175 + t * (193 - 175))
            b = int(80 + t * (7 - 80))
            return (r, g, b)
        elif ratio <= 2.0:
            # Naranja a rojo
            t = (ratio - 1.5) / 0.5
            r = int(255)
            g = int(193 - t * 193)
            b = int(7 - t * 7)
            return (r, g, b)
        else:
            return C['danger']

    def draw_rock_face(self):
        """Dibuja la pared de roca de fondo."""
        # Fondo de roca (zona de anclaje)
        rock_rect = pygame.Rect(SCENE_LEFT, SCENE_TOP,
                                SCENE_RIGHT - SCENE_LEFT,
                                SCENE_BOTTOM - SCENE_TOP)
        pygame.draw.rect(self.screen, (35, 35, 50), rock_rect,
                         border_radius=10)

        # Textura de roca (lineas horizontales sutiles)
        for y in range(SCENE_TOP + 15, SCENE_BOTTOM, 28):
            x_start = SCENE_LEFT + 10 + (y * 7) % 30
            x_end = SCENE_RIGHT - 10 - (y * 11) % 40
            pygame.draw.line(self.screen, (42, 42, 58),
                             (x_start, y), (x_end, y), 1)

        # Textura vertical (grietas)
        for x in range(SCENE_LEFT + 60, SCENE_RIGHT - 60, 95):
            y_start = SCENE_TOP + 20 + (x * 3) % 50
            y_end = min(y_start + 120 + (x * 7) % 80, SCENE_BOTTOM - 30)
            pygame.draw.line(self.screen, (45, 45, 62),
                             (x, y_start), (x + 5, y_end), 1)

        # Borde de la roca
        pygame.draw.rect(self.screen, C['anchor'], rock_rect,
                         width=2, border_radius=10)

        # Etiqueta
        lbl = self.font_xs.render('PARED DE ROCA', True, C['anchor'])
        self.screen.blit(lbl, (SCENE_LEFT + 10, SCENE_TOP + 5))

    def draw_anchor_bolts(self):
        """Dibuja los pernos de anclaje en la roca."""
        for i, (ax, ay) in enumerate(self.anchor_positions):
            is_selected = (i == self.selected_anchor)
            is_failed = (self.show_failure and i == self.failed_anchor_index)
            color = ANCHOR_COLORS[i % len(ANCHOR_COLORS)]

            if is_failed:
                # Anclaje fallido: rojo con X
                flash = math.sin(self.failure_flash_timer * 8) > 0
                color = C['danger'] if flash else (100, 30, 30)

            # Perno (base en la roca)
            bolt_size = 14 if is_selected else 10
            pygame.draw.circle(self.screen, (80, 80, 100), (ax, ay),
                               bolt_size + 4)
            pygame.draw.circle(self.screen, color, (ax, ay), bolt_size)

            # Circulo interior (ojo del perno)
            inner_color = C['bg'] if not is_failed else C['danger']
            pygame.draw.circle(self.screen, inner_color, (ax, ay),
                               bolt_size - 4)

            # Highlight de seleccion
            if is_selected and not is_failed:
                pygame.draw.circle(self.screen, C['white'], (ax, ay),
                                   bolt_size + 7, 2)
                # Flecha indicadora
                pygame.draw.polygon(self.screen, C['white'], [
                    (ax, ay - bolt_size - 12),
                    (ax - 6, ay - bolt_size - 20),
                    (ax + 6, ay - bolt_size - 20),
                ])

            # X sobre anclaje fallido
            if is_failed:
                s = bolt_size + 6
                pygame.draw.line(self.screen, C['danger'],
                                 (ax - s, ay - s), (ax + s, ay + s), 4)
                pygame.draw.line(self.screen, C['danger'],
                                 (ax + s, ay - s), (ax - s, ay + s), 4)

            # Etiqueta del anclaje
            label = ANCHOR_LABELS[i]
            if is_failed:
                label += ' FALLO'
            lbl = self.font_med.render(label, True, color)
            lbl_x = ax - lbl.get_width() // 2
            lbl_y = ay - bolt_size - 28 if not is_selected else ay - bolt_size - 38
            self.screen.blit(lbl, (lbl_x, lbl_y))

    def draw_slings_and_forces(self):
        """Dibuja los tirantes y las flechas de fuerza."""
        mx, my = MASTER_POINT_X, MASTER_POINT_Y
        results = self.anchor_results

        for r in results:
            i = r['index']
            ax, ay = r['pos']
            is_failed = (self.show_failure and i == self.failed_anchor_index)
            color = ANCHOR_COLORS[i % len(ANCHOR_COLORS)]

            if is_failed:
                # Tirante roto: linea discontinua roja
                self._draw_dashed_line(self.screen, C['danger'],
                                       (ax, ay), (mx, my), 2, 8)
                continue

            # Color basado en carga
            force_color = self._force_color(r['percentage'], self.num_anchors)

            # Si estamos en modo fallo, usar los resultados de fallo para color
            if self.show_failure and self.failure_results:
                for fr in self.failure_results:
                    if fr['index'] == i and not fr['failed']:
                        force_color = self._force_color(
                            fr['percentage'],
                            self.num_anchors - 1)
                        break

            # Tirante (sling)
            line_width = max(2, min(int(r['percentage'] / 10), 6))
            pygame.draw.line(self.screen, force_color,
                             (ax, ay), (mx, my), line_width)

            # Flecha de fuerza a lo largo del tirante
            self._draw_force_arrow(ax, ay, mx, my, r['force_kn'],
                                   force_color)

            # Etiqueta de angulo en el tirante
            mid_x = (ax + mx) // 2
            mid_y = (ay + my) // 2

            # Desplazar etiqueta perpendicular al tirante
            dx = mx - ax
            dy = my - ay
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                nx = -dy / length * 20
                ny = dx / length * 20
            else:
                nx, ny = 20, 0

            angle_str = f'{r["alpha_deg"]:.1f} deg'
            force_str = f'{r["force_kn"]:.2f} kN'

            # Fondo semitransparente para las etiquetas
            lbl1 = self.font_xs.render(angle_str, True, C['text'])
            lbl2 = self.font_xs.render(force_str, True, force_color)

            pad = 3
            bg_w = max(lbl1.get_width(), lbl2.get_width()) + pad * 2
            bg_h = lbl1.get_height() + lbl2.get_height() + pad * 2
            bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg_surf.fill((15, 15, 26, 200))

            lx = int(mid_x + nx - bg_w // 2)
            ly = int(mid_y + ny - bg_h // 2)
            self.screen.blit(bg_surf, (lx, ly))
            self.screen.blit(lbl1, (lx + pad, ly + pad))
            self.screen.blit(lbl2, (lx + pad,
                                    ly + pad + lbl1.get_height()))

        # Arcos de angulo en el master point
        self._draw_angle_arcs()

    def _draw_force_arrow(self, ax, ay, mx, my, force_kn, color):
        """Dibuja una flecha de fuerza a lo largo del tirante."""
        dx = ax - mx
        dy = ay - my
        length = math.sqrt(dx * dx + dy * dy)
        if length < 10:
            return

        # Normalizar
        ux = dx / length
        uy = dy / length

        # Flecha desde el anclaje hacia el master (direccion de la fuerza)
        arrow_len = min(30 + force_kn * 15, length * 0.35)
        start_x = ax - ux * 25
        start_y = ay - uy * 25
        end_x = start_x - ux * arrow_len
        end_y = start_y - uy * arrow_len

        # Linea de la flecha
        pygame.draw.line(self.screen, color,
                         (int(start_x), int(start_y)),
                         (int(end_x), int(end_y)), 3)

        # Punta de la flecha
        head_size = 8
        perp_x = -uy * head_size
        perp_y = ux * head_size
        tip_x = end_x - ux * head_size
        tip_y = end_y - uy * head_size
        pygame.draw.polygon(self.screen, color, [
            (int(end_x), int(end_y)),
            (int(tip_x + perp_x), int(tip_y + perp_y)),
            (int(tip_x - perp_x), int(tip_y - perp_y)),
        ])

    def _draw_angle_arcs(self):
        """Dibuja arcos que muestran el angulo de cada tirante desde la vertical."""
        mx, my = MASTER_POINT_X, MASTER_POINT_Y
        arc_radius = 40

        for r in self.anchor_results:
            if self.show_failure and r['index'] == self.failed_anchor_index:
                continue

            ax, ay = r['pos']
            alpha = r['alpha_deg']

            if alpha < 2.0:
                continue

            # Angulo del tirante respecto a horizontal
            dx = ax - mx
            dy = my - ay
            sling_angle = math.atan2(dx, dy)  # angulo desde vertical

            # Dibujar arco desde la vertical (arriba) hasta el tirante
            n_pts = max(int(alpha / 2), 8)
            points = []

            for k in range(n_pts + 1):
                t = k / n_pts
                angle = -math.pi / 2 + t * sling_angle
                # Rotar para que 0 sea vertical hacia arriba
                a = -math.pi / 2 + t * sling_angle
                # Angulo medido desde vertical arriba
                a_from_up = t * sling_angle
                px = mx + arc_radius * math.sin(a_from_up)
                py = my - arc_radius * math.cos(a_from_up)
                points.append((int(px), int(py)))

            color = ANCHOR_COLORS[r['index'] % len(ANCHOR_COLORS)]
            if len(points) > 1:
                pygame.draw.lines(self.screen, color, False, points, 1)

    def draw_master_point(self):
        """Dibuja el punto maestro (placa/anillo de ecualizacion)."""
        mx, my = MASTER_POINT_X, MASTER_POINT_Y

        # Anillo de ecualizacion
        pygame.draw.circle(self.screen, C['warning'], (mx, my), 16)
        pygame.draw.circle(self.screen, C['bg'], (mx, my), 11)
        pygame.draw.circle(self.screen, C['warning'], (mx, my), 16, 3)

        # Etiqueta
        lbl = self.font_sm.render('PUNTO MAESTRO', True, C['warning'])
        self.screen.blit(lbl, (mx - lbl.get_width() // 2, my + 20))

    def draw_load(self):
        """Dibuja la carga colgando del punto maestro."""
        mx, my = MASTER_POINT_X, MASTER_POINT_Y
        W_kN = self.mass_kg * G / 1000.0

        # Linea vertical desde el master point
        load_top = my + 16
        load_y = my + 70

        pygame.draw.line(self.screen, C['rope'],
                         (mx, load_top), (mx, load_y - 15), 3)

        # Mosquet'on
        pygame.draw.circle(self.screen, C['anchor'], (mx, load_y - 12), 5)

        # Carga (rectangulo con persona)
        load_w, load_h = 60, 35
        load_rect = pygame.Rect(mx - load_w // 2, load_y,
                                load_w, load_h)
        pygame.draw.rect(self.screen, C['secondary'], load_rect,
                         border_radius=5)
        pygame.draw.rect(self.screen, C['text'], load_rect,
                         width=2, border_radius=5)

        # Icono persona simplificado
        pygame.draw.circle(self.screen, C['primary'],
                           (mx - 10, load_y + 10), 5)
        pygame.draw.line(self.screen, C['primary'],
                         (mx - 10, load_y + 15),
                         (mx - 10, load_y + 28), 2)

        # Texto de masa
        mass_lbl = self.font_med.render(f'{self.mass_kg} kg', True, C['text'])
        self.screen.blit(mass_lbl,
                         (mx + 5, load_y + load_h // 2 - 7))

        # Flecha de peso
        arrow_top = load_y + load_h + 5
        arrow_bottom = arrow_top + 35
        pygame.draw.line(self.screen, C['danger'],
                         (mx, arrow_top), (mx, arrow_bottom), 3)
        pygame.draw.polygon(self.screen, C['danger'], [
            (mx, arrow_bottom + 7),
            (mx - 5, arrow_bottom),
            (mx + 5, arrow_bottom),
        ])

        # Etiqueta de peso
        w_lbl = self.font_med.render(f'W = {W_kN:.2f} kN', True, C['danger'])
        self.screen.blit(w_lbl,
                         (mx - w_lbl.get_width() // 2,
                          arrow_bottom + 12))

    def draw_vertical_reference(self):
        """Dibuja la linea vertical de referencia (direccion de la carga)."""
        mx, my = MASTER_POINT_X, MASTER_POINT_Y

        # Linea vertical punteada
        self._draw_dashed_line(self.screen, (60, 60, 80),
                               (mx, SCENE_TOP + 20), (mx, my), 1, 10)

        lbl = self.font_xs.render('Vertical', True, (60, 60, 80))
        self.screen.blit(lbl, (mx + 5, SCENE_TOP + 25))

    def _draw_dashed_line(self, surface, color, start, end, width, dash_len):
        """Dibuja una linea discontinua."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return
        ux = dx / length
        uy = dy / length

        pos = 0
        drawing = True
        while pos < length:
            seg_end = min(pos + dash_len, length)
            if drawing:
                sx = int(start[0] + ux * pos)
                sy = int(start[1] + uy * pos)
                ex = int(start[0] + ux * seg_end)
                ey = int(start[1] + uy * seg_end)
                pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)
            pos = seg_end + dash_len // 2
            drawing = not drawing

    # ── Panel de datos ──────────────────────────────────────────────────

    def draw_data_panel(self):
        """Panel derecho con toda la informacion numerica."""
        px = PANEL_LEFT
        py = PANEL_TOP
        pw = PANEL_WIDTH
        ph = PANEL_HEIGHT

        # Fondo del panel
        pygame.draw.rect(self.screen, C['panel'],
                         (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (px, py, pw, ph), width=1, border_radius=8)

        x = px + 12
        y = py + 10
        max_w = pw - 24

        # Titulo
        surf = self.font_big.render('ANALISIS DE FUERZAS', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 26

        W_kN = self.mass_kg * G / 1000.0

        # Carga
        surf = self.font_sm.render(
            f'Masa: {self.mass_kg} kg    Peso: {W_kN:.2f} kN',
            True, C['text'])
        self.screen.blit(surf, (x, y))
        y += 18

        surf = self.font_sm.render(
            f'Sistema: {self.num_anchors} puntos',
            True, C['text'])
        self.screen.blit(surf, (x, y))
        y += 18

        ideal_pct = 100.0 / self.num_anchors
        surf = self.font_sm.render(
            f'Distribucion ideal: {ideal_pct:.1f}% cada uno',
            True, C['dark_text'])
        self.screen.blit(surf, (x, y))
        y += 22

        # Separador
        pygame.draw.line(self.screen, C['grid'], (x, y), (x + max_w, y), 1)
        y += 8

        # Datos por anclaje
        surf = self.font_med.render('FUERZA POR ANCLAJE', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 20

        for r in self.anchor_results:
            i = r['index']
            is_selected = (i == self.selected_anchor)
            is_failed = (self.show_failure and i == self.failed_anchor_index)
            color = ANCHOR_COLORS[i % len(ANCHOR_COLORS)]

            if is_failed:
                color = C['danger']

            # Indicador de seleccion
            if is_selected and not is_failed:
                pygame.draw.rect(self.screen, color,
                                 (x - 2, y - 1, max_w + 4, 34),
                                 width=1, border_radius=3)

            label = ANCHOR_LABELS[i]

            if is_failed:
                surf = self.font_sm.render(
                    f'{label}: --- FALLO ---', True, C['danger'])
                self.screen.blit(surf, (x + 4, y))
                y += 18

                # Mostrar nueva fuerza en restantes
                if self.failure_results:
                    for fr in self.failure_results:
                        if fr['index'] == i and fr['failed']:
                            continue

                y += 18
                continue

            force_color = self._force_color(r['percentage'],
                                            self.num_anchors)

            # Linea 1: nombre, angulo, fuerza
            line1 = (f'{label}:  ang={r["alpha_deg"]:.1f} deg  '
                     f'F={r["force_kn"]:.2f} kN  '
                     f'({r["percentage"]:.1f}%)')
            surf = self.font_sm.render(line1, True, force_color)
            self.screen.blit(surf, (x + 4, y))
            y += 16

            # Linea 2: tension en el tirante y factor de seguridad
            t_sling = sling_tension(r['force_kn'], r['alpha_deg'])
            sf = ANCHOR_MBS / t_sling if t_sling > 0.001 else 999
            sf_color = C['accent'] if sf >= SAFETY_FACTOR_MIN else (
                C['warning'] if sf >= 5 else C['danger'])
            sf_sym = 'OK' if sf >= SAFETY_FACTOR_MIN else (
                'ATENCION' if sf >= 5 else 'PELIGRO')

            line2 = (f'       T_tirante={t_sling:.2f} kN  '
                     f'FS={sf:.1f}:1 [{sf_sym}]')
            surf = self.font_xs.render(line2, True, sf_color)
            self.screen.blit(surf, (x + 4, y))
            y += 20

        y += 4
        pygame.draw.line(self.screen, C['grid'], (x, y), (x + max_w, y), 1)
        y += 8

        # Grafico de barras de distribucion
        y = self._draw_bar_chart(x, y, max_w)

        y += 8
        pygame.draw.line(self.screen, C['grid'], (x, y), (x + max_w, y), 1)
        y += 8

        # Analisis de fallo
        y = self._draw_failure_analysis(x, y, max_w)

        y += 8
        pygame.draw.line(self.screen, C['grid'], (x, y), (x + max_w, y), 1)
        y += 8

        # Formulas y notas educativas
        y = self._draw_educational_notes(x, y, max_w)

    def _draw_bar_chart(self, x, y, max_w):
        """Dibuja el grafico de barras de distribucion de fuerzas."""
        surf = self.font_med.render('DISTRIBUCION (%)', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 20

        bar_height = 16
        bar_max_w = max_w - 60
        n = len(self.anchor_results)
        ideal_pct = 100.0 / max(n, 1)

        for r in self.anchor_results:
            i = r['index']
            is_failed = (self.show_failure and i == self.failed_anchor_index)
            color = ANCHOR_COLORS[i % len(ANCHOR_COLORS)]

            if is_failed:
                # Barra vacia con X
                lbl = self.font_xs.render(f'{ANCHOR_LABELS[i]}', True,
                                          C['danger'])
                self.screen.blit(lbl, (x, y + 1))
                pygame.draw.rect(self.screen, (50, 20, 20),
                                 (x + 28, y, bar_max_w, bar_height),
                                 border_radius=2)
                x_lbl = self.font_xs.render('FALLO', True, C['danger'])
                self.screen.blit(x_lbl, (x + 30 + bar_max_w // 2 - 15,
                                         y + 1))
                y += bar_height + 6
                continue

            pct = r['percentage']

            # En modo fallo, mostrar nuevas barras con la redistribucion
            failure_pct = None
            if self.show_failure and self.failure_results:
                for fr in self.failure_results:
                    if fr['index'] == i and not fr['failed']:
                        failure_pct = fr['percentage']
                        break

            # Etiqueta del anclaje
            lbl = self.font_xs.render(f'{ANCHOR_LABELS[i]}', True, color)
            self.screen.blit(lbl, (x, y + 1))

            # Fondo de la barra
            pygame.draw.rect(self.screen, (40, 40, 55),
                             (x + 28, y, bar_max_w, bar_height),
                             border_radius=2)

            # Barra normal
            bw = int(bar_max_w * min(pct / 100.0, 1.0))
            force_color = self._force_color(pct, self.num_anchors)
            if bw > 0:
                pygame.draw.rect(self.screen, force_color,
                                 (x + 28, y, bw, bar_height),
                                 border_radius=2)

            # Barra de fallo superpuesta (contorno)
            if failure_pct is not None:
                fbw = int(bar_max_w * min(failure_pct / 100.0, 1.0))
                fc = self._force_color(failure_pct, self.num_anchors - 1)
                if fbw > 0:
                    pygame.draw.rect(self.screen, fc,
                                     (x + 28, y, fbw, bar_height),
                                     width=2, border_radius=2)

            # Linea de referencia ideal
            ideal_x = x + 28 + int(bar_max_w * ideal_pct / 100.0)
            pygame.draw.line(self.screen, C['white'],
                             (ideal_x, y), (ideal_x, y + bar_height), 1)

            # Texto de porcentaje
            pct_text = f'{pct:.1f}%'
            if failure_pct is not None:
                pct_text += f' -> {failure_pct:.1f}%'
            pct_lbl = self.font_xs.render(pct_text, True, C['text'])
            self.screen.blit(pct_lbl, (x + 30 + bw + 4, y + 1))

            y += bar_height + 6

        # Leyenda
        lbl = self.font_xs.render(
            f'| = ideal ({ideal_pct:.0f}%)', True, C['dark_text'])
        self.screen.blit(lbl, (x + 28, y))
        y += 16

        return y

    def _draw_failure_analysis(self, x, y, max_w):
        """Dibuja el analisis de fallo del anclaje seleccionado."""
        surf = self.font_med.render(
            f'SI {ANCHOR_LABELS[self.selected_anchor]} FALLA:',
            True, C['warning'])
        self.screen.blit(surf, (x, y))
        y += 20

        W_kN = self.mass_kg * G / 1000.0
        remaining = self.num_anchors - 1

        if remaining < 1:
            surf = self.font_sm.render(
                'Sistema colapsa sin anclajes restantes.',
                True, C['danger'])
            self.screen.blit(surf, (x + 4, y))
            return y + 18

        # Calcular fuerzas con el anclaje seleccionado fallido
        fail_results = compute_failure_scenario(
            self.anchor_positions, (MASTER_POINT_X, MASTER_POINT_Y),
            W_kN, self.selected_anchor)

        max_force = 0.0
        max_pct = 0.0
        for fr in fail_results:
            if not fr['failed']:
                if fr['force_kn'] > max_force:
                    max_force = fr['force_kn']
                    max_pct = fr['percentage']

        for fr in fail_results:
            if fr['failed']:
                continue
            i = fr['index']
            color = ANCHOR_COLORS[i % len(ANCHOR_COLORS)]
            fc = self._force_color(fr['percentage'], remaining)

            # Fuerza original
            orig = None
            for r in self.anchor_results:
                if r['index'] == i:
                    orig = r
                    break

            orig_str = f'{orig["force_kn"]:.2f}' if orig else '?'
            line = (f'  {ANCHOR_LABELS[i]}: {orig_str} -> '
                    f'{fr["force_kn"]:.2f} kN ({fr["percentage"]:.1f}%)')
            surf = self.font_xs.render(line, True, fc)
            self.screen.blit(surf, (x + 4, y))
            y += 15

        y += 4

        # Advertencia de carga de choque
        shock_factor = 1.5  # Factor de choque estimado por extension
        shock_force = max_force * shock_factor

        surf = self.font_xs.render(
            f'Carga de choque estimada (x{shock_factor:.1f}): '
            f'{shock_force:.2f} kN en peor caso',
            True, C['danger'])
        self.screen.blit(surf, (x + 4, y))
        y += 15

        if shock_force > ANCHOR_MBS:
            surf = self.font_xs.render(
                'SUPERA resistencia del anclaje! Fallo en cascada posible.',
                True, C['danger'])
            self.screen.blit(surf, (x + 4, y))
            y += 15
        elif max_force > NFPA_WORK_LOAD:
            surf = self.font_xs.render(
                'Supera carga de trabajo NFPA (13.5 kN).',
                True, C['warning'])
            self.screen.blit(surf, (x + 4, y))
            y += 15

        return y

    def _draw_educational_notes(self, x, y, max_w):
        """Notas educativas y formulas."""
        surf = self.font_med.render('FORMULAS Y NOTAS', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 20

        formulas = [
            ('F_i = W * cos(alpha_i) / SUM(cos(alpha_j))', C['info']),
            ('alpha_i = angulo tirante i vs vertical', C['dark_text']),
            ('', None),
            ('Tirante mas vertical = mas carga', C['accent']),
            ('Tirante mas inclinado = menos carga', C['warning']),
            ('', None),
            ('Si un anclaje falla:', C['danger']),
            ('  - Carga se redistribuye instantaneamente', C['dark_text']),
            ('  - Genera carga de choque (extension)', C['dark_text']),
            ('  - Angulos cambian = nueva distribucion', C['dark_text']),
        ]

        for text, color in formulas:
            if not text:
                y += 4
                continue
            surf = self.font_xs.render(text, True, color)
            self.screen.blit(surf, (x + 4, y))
            y += 14

        return y

    # ── Barra de controles ──────────────────────────────────────────────

    def draw_controls(self):
        """Barra de controles inferior."""
        ctrl_y = HEIGHT - 42
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 8, WIDTH, 50))

        anchor_label = ANCHOR_LABELS[self.selected_anchor]
        fail_str = 'ON' if self.show_failure else 'OFF'

        controls = [
            f'[TAB] Seleccionar (actual: {anchor_label})',
            '[Flechas] Mover anclaje',
            f'[3/4] Puntos: {self.num_anchors}',
            f'[F] Fallo: {fail_str}',
            '[W/S] Masa',
            '[R] Reset',
            '[Mouse] Arrastrar',
            '[ESC] Salir',
        ]
        cx = 12
        for ctrl in controls:
            is_fail = 'Fallo' in ctrl and self.show_failure
            color = C['danger'] if is_fail else C['dark_text']
            surf = self.font_xs.render(ctrl, True, color)
            self.screen.blit(surf, (cx, ctrl_y))
            cx += surf.get_width() + 14

    # ── Indicador de estado de seguridad ────────────────────────────────

    def draw_safety_status(self):
        """Indicador visual de seguridad global."""
        x = SCENE_LEFT + 10
        y = SCENE_BOTTOM - 55

        # Evaluar estado
        max_pct = 0.0
        max_angle = 0.0
        for r in self.anchor_results:
            if r['percentage'] > max_pct:
                max_pct = r['percentage']
            if r['alpha_deg'] > max_angle:
                max_angle = r['alpha_deg']

        ideal = 100.0 / self.num_anchors
        ratio = max_pct / ideal if ideal > 0 else 99

        if ratio <= 1.2 and max_angle <= 45:
            status = 'DISTRIBUCION EQUILIBRADA'
            status_color = C['accent']
        elif ratio <= 1.5 and max_angle <= 60:
            status = 'DISTRIBUCION ACEPTABLE'
            status_color = C['warning']
        elif max_angle > 75:
            status = 'ANGULO EXCESIVO - REDISTRIBUIR'
            status_color = C['danger']
        else:
            status = 'DISTRIBUCION DESBALANCEADA'
            status_color = C['danger']

        if self.show_failure:
            status = f'FALLO DE {ANCHOR_LABELS[self.failed_anchor_index]} - REDISTRIBUCION'
            status_color = C['danger']

        # Caja de estado
        surf = self.font_med.render(status, True, status_color)
        box_w = surf.get_width() + 20
        box_h = surf.get_height() + 10

        pygame.draw.rect(self.screen, C['bg'],
                         (x, y, box_w, box_h), border_radius=5)
        pygame.draw.rect(self.screen, status_color,
                         (x, y, box_w, box_h), width=2, border_radius=5)
        self.screen.blit(surf, (x + 10, y + 5))

    # ── Bucle principal ─────────────────────────────────────────────────

    def update(self, dt):
        """Actualiza la simulacion."""
        self._recalculate()

        if self.failure_flash_timer > 0:
            self.failure_flash_timer -= dt

    def draw(self):
        """Renderiza toda la escena."""
        self.screen.fill(C['bg'])

        # Titulo
        title = self.font_title.render(
            'DISTRIBUCION DE FUERZAS EN MULTI-ANCLAJE', True, C['primary'])
        self.screen.blit(title,
                         (WIDTH // 2 - title.get_width() // 2, 12))

        subtitle = self.font_sm.render(
            'Sistema auto-ecualizado de {} puntos  |  '
            'Arrastre los anclajes o use las flechas'.format(
                self.num_anchors),
            True, C['dark_text'])
        self.screen.blit(subtitle,
                         (WIDTH // 2 - subtitle.get_width() // 2, 42))

        # Escena
        self.draw_rock_face()
        self.draw_vertical_reference()
        self.draw_slings_and_forces()
        self.draw_anchor_bolts()
        self.draw_master_point()
        self.draw_load()
        self.draw_safety_status()

        # Panel de datos
        self.draw_data_panel()

        # Controles
        self.draw_controls()

        pygame.display.flip()

    def run(self):
        """Bucle principal."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            running = self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()


# ══════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    sim = MultiAnchorSim()
    sim.run()
