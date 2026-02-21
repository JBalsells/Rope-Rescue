"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 10: Simulador de Sistema Completo    ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación interactiva (Pygame) de un sistema de rescate          ║
║  completo con cuerda principal, cuerda de seguridad, anclaje       ║
║  en V, desviador fijo en el borde y dispositivo de descenso.       ║
║                                                                      ║
║  Incluye simulación de FACTOR DE CAÍDA con fuerza de choque.       ║
║                                                                      ║
║  Controles:                                                          ║
║   [ESPACIO]  Iniciar/Pausar descenso (o disparar caída si FF > 0) ║
║   [↑/↓]     Ajustar masa de la carga                               ║
║   [←/→]     Ajustar ángulo del anclaje en V                        ║
║   [A]       Alternar tipo de anclaje (V / simple)                   ║
║   [D]       Activar/desactivar desviador de borde                   ║
║   [F]       Ciclar factor de caída: OFF → 0.25 → 0.5 → 1.0 → 2.0 ║
║   [R]       Reiniciar                                                ║
║                                                                      ║
║  Ejecutar:  python 10_simulador_sistema_completo.py                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import math
import pygame
from config import PG_COLORS as C, G

WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Geometría fija del acantilado ─────────────────────────────────────
CLIFF_TOP_Y = 100          # Borde superior del acantilado
CLIFF_EDGE_X = 280         # Borde exterior (lip) del acantilado
CLIFF_EDGE_Y = 195         # Donde la cuerda pasa por el borde
LOAD_X = CLIFF_EDGE_X + 18 # La carga desciende justo afuera de la pared
GROUND_Y = HEIGHT - 80     # Nivel del suelo

# Posición fija del desviador (anclado en la roca, en el borde)
DEVIATOR_POS = (CLIFF_EDGE_X - 5, CLIFF_EDGE_Y)

# ── Constantes físicas ────────────────────────────────────────────────
ROPE_LENGTH_M = 50.0       # Longitud de cuerda disponible (metros)
KAPPA_DYNAMIC = 1.8e-4     # Elasticidad cuerda dinámica
KAPPA_STATIC = 2.5e-5      # Elasticidad cuerda semiestática (rescate)
PIXELS_PER_METER = (GROUND_Y - CLIFF_EDGE_Y - 60) / ROPE_LENGTH_M

# Factores de caída disponibles
FF_OPTIONS = [0.0, 0.25, 0.5, 1.0, 2.0]


def force_on_v_arm(weight_kn, angle_deg):
    """Fuerza en cada brazo del anclaje en V."""
    half = math.radians(angle_deg / 2)
    cos_h = math.cos(half)
    if cos_h < 0.01:
        return 99.99
    return weight_kn / (2 * cos_h)


def capstan_force(load_kn, mu, wraps):
    """Fuerza de retención con fricción (ecuación del cabrestante)."""
    theta = wraps * 2 * math.pi
    return load_kn * math.exp(-mu * theta)


def impact_force_kn(mass_kg, fall_factor, kappa):
    """Fuerza de choque (Dodero). Retorna kN."""
    if fall_factor <= 0:
        return mass_kg * G / 1000.0
    mg = mass_kg * G
    discriminant = 1 + 2 * fall_factor / (mg * kappa)
    return mg * (1 + math.sqrt(discriminant)) / 1000.0


class FallState:
    """Estados posibles de la simulación de caída."""
    IDLE = 'idle'
    FALLING = 'falling'
    IMPACT = 'impact'
    SETTLING = 'settling'


class RescueSimulator:
    """Simulador de sistema completo de rescate con factor de caída."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Física del Rescate — Simulador de Sistema Completo')
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont('DejaVu Sans', 28, bold=True)
        self.font_big = pygame.font.SysFont('DejaVu Sans', 20, bold=True)
        self.font_med = pygame.font.SysFont('DejaVu Sans', 15)
        self.font_sm = pygame.font.SysFont('DejaVu Sans', 12)
        self.font_xs = pygame.font.SysFont('DejaVu Sans', 11)

        self.reset()

    def reset(self):
        """Estado inicial del simulador."""
        self.mass_kg = 100
        self.v_angle = 60
        self.use_v_anchor = True
        self.use_deviator = True
        self.descending = False
        self.descent_progress = 0.0   # 0 = arriba, 1 = abajo

        # Dispositivo de descenso
        self.device_mu = 0.30
        self.device_wraps = 2.5

        # Factor de caída
        self.ff_index = 0             # índice en FF_OPTIONS (0 = OFF)
        self.fall_factor = 0.0

        # Estado de animación de caída
        self.fall_state = FallState.IDLE
        self.fall_velocity = 0.0      # m/s
        self.fall_pos_m = 0.0         # posición actual en metros desde el borde
        self.fall_start_m = 0.0       # posición desde donde empieza la caída
        self.fall_end_m = 0.0         # posición donde la cuerda se tensa
        self.fall_rope_out_m = 10.0   # cuerda desplegada al momento de la caída
        self.fall_impact_kn = 0.0     # fuerza de choque calculada
        self.fall_impact_static_kn = 0.0
        self.fall_time_since_impact = 0.0
        self.fall_bounce_phase = 0.0
        self.fall_stretch_m = 0.0     # elongación de la cuerda en impacto
        self.rope_flash_timer = 0.0   # para parpadeo rojo en impacto

    @property
    def load_y_from_progress(self):
        """Posición Y del píxel de la carga durante descenso normal."""
        top = CLIFF_EDGE_Y + 20
        bottom = GROUND_Y - 60
        return int(top + self.descent_progress * (bottom - top))

    def setup_fall(self):
        """Configura una caída según el factor de caída seleccionado."""
        ff = self.fall_factor
        if ff <= 0:
            return

        # Cuerda desplegada (metros): usamos la posición actual de descenso
        self.fall_rope_out_m = max(5.0, self.descent_progress * ROPE_LENGTH_M)
        if self.fall_rope_out_m < 3.0:
            self.fall_rope_out_m = 10.0  # mínimo para que se vea la caída

        # Distancia de caída = ff × longitud de cuerda
        fall_dist_m = ff * self.fall_rope_out_m

        # Posición de inicio: el escalador está "arriba" del punto de reposo
        # según el factor de caída
        rest_m = self.fall_rope_out_m  # posición de reposo (cuerda tensa)

        if ff <= 1.0:
            # El escalador está entre el anclaje y el punto de reposo
            self.fall_start_m = rest_m - fall_dist_m
        else:
            # Factor > 1: el escalador está POR ENCIMA del anclaje
            self.fall_start_m = rest_m - fall_dist_m

        self.fall_start_m = max(self.fall_start_m, -fall_dist_m)
        self.fall_end_m = rest_m
        self.fall_pos_m = self.fall_start_m
        self.fall_velocity = 0.0
        self.fall_state = FallState.FALLING
        self.fall_impact_kn = 0.0
        self.fall_impact_static_kn = 0.0
        self.fall_time_since_impact = 0.0
        self.fall_bounce_phase = 0.0
        self.fall_stretch_m = 0.0
        self.rope_flash_timer = 0.0
        self.descending = False

    def update(self, dt):
        """Actualiza la simulación."""
        # Modo descenso normal
        if self.descending and self.fall_state == FallState.IDLE:
            self.descent_progress = min(
                self.descent_progress + 0.08 * dt, 1.0)
            return

        # Modo caída
        if self.fall_state == FallState.FALLING:
            self.fall_velocity += G * dt
            self.fall_pos_m += self.fall_velocity * dt

            # La cuerda se tensa cuando llegamos al punto de reposo
            if self.fall_pos_m >= self.fall_end_m:
                self.fall_pos_m = self.fall_end_m
                self.fall_state = FallState.IMPACT

                # Calcular fuerza de choque
                self.fall_impact_kn = impact_force_kn(
                    self.mass_kg, self.fall_factor, KAPPA_STATIC)
                self.fall_impact_static_kn = impact_force_kn(
                    self.mass_kg, self.fall_factor, KAPPA_STATIC * 0.4)

                # Elongación visual de la cuerda
                elong_pct = 3.0 + self.fall_factor * 2.0  # % aproximado
                self.fall_stretch_m = self.fall_rope_out_m * elong_pct / 100.0
                self.rope_flash_timer = 1.5  # segundos de flash

        elif self.fall_state == FallState.IMPACT:
            self.fall_time_since_impact += dt
            self.rope_flash_timer = max(0, self.rope_flash_timer - dt)

            # Oscilación amortiguada
            self.fall_bounce_phase += dt * 6.0
            damping = math.exp(-self.fall_time_since_impact * 2.5)
            bounce = damping * math.sin(self.fall_bounce_phase)
            self.fall_pos_m = self.fall_end_m + bounce * self.fall_stretch_m

            if self.fall_time_since_impact > 4.0:
                self.fall_state = FallState.SETTLING
                self.fall_pos_m = self.fall_end_m

        elif self.fall_state == FallState.SETTLING:
            # Actualizar descent_progress para que coincida con la posición final
            total_range = ROPE_LENGTH_M
            self.descent_progress = min(
                self.fall_end_m / total_range, 1.0)

    def draw_cliff(self):
        """Dibuja el acantilado con textura."""
        cliff_points = [
            (60, CLIFF_TOP_Y),
            (CLIFF_EDGE_X, CLIFF_TOP_Y),
            (CLIFF_EDGE_X, CLIFF_EDGE_Y + 10),
            (CLIFF_EDGE_X - 15, CLIFF_EDGE_Y + 30),
            (CLIFF_EDGE_X - 40, CLIFF_EDGE_Y + 80),
            (CLIFF_EDGE_X - 60, GROUND_Y),
            (60, GROUND_Y),
        ]
        pygame.draw.polygon(self.screen, (50, 50, 70), cliff_points)
        pygame.draw.lines(self.screen, (80, 80, 100), False,
                          cliff_points[1:6], 2)

        # Textura de la roca
        for y_t in range(CLIFF_TOP_Y + 10, GROUND_Y, 22):
            x_end = CLIFF_EDGE_X - 20
            # Calcular x de la cara del acantilado a esta altura
            for seg_i in range(len(cliff_points) - 1):
                x1, y1 = cliff_points[seg_i]
                x2, y2 = cliff_points[seg_i + 1]
                if y1 <= y_t <= y2 and y2 != y1:
                    t = (y_t - y1) / (y2 - y1)
                    x_end = int(x1 + t * (x2 - x1)) - 5
                    break
            pygame.draw.line(self.screen, (60, 60, 80),
                             (65, y_t), (min(x_end, CLIFF_EDGE_X - 30), y_t + 3), 1)

        # Borde superior del acantilado (plataforma)
        pygame.draw.rect(self.screen, (70, 70, 90),
                         (60, CLIFF_TOP_Y - 15, CLIFF_EDGE_X - 55, 18))
        pygame.draw.line(self.screen, C['anchor'],
                         (60, CLIFF_TOP_Y), (CLIFF_EDGE_X, CLIFF_TOP_Y), 3)

        # Borde/lip del acantilado (resaltado)
        pygame.draw.circle(self.screen, (90, 90, 110),
                           (CLIFF_EDGE_X, CLIFF_EDGE_Y), 6)

        # Suelo
        pygame.draw.line(self.screen, (80, 80, 80),
                         (CLIFF_EDGE_X - 80, GROUND_Y),
                         (WIDTH // 3, GROUND_Y), 2)

    def draw_anchor_system(self):
        """Dibuja el sistema de anclaje y retorna el punto de conexión."""
        if self.use_v_anchor:
            return self._draw_v_anchor()
        else:
            return self._draw_single_anchor()

    def _draw_single_anchor(self):
        """Anclaje simple en la parte superior del acantilado."""
        x, y = 200, CLIFF_TOP_Y - 5
        pygame.draw.circle(self.screen, C['accent'], (x, y), 10)
        pygame.draw.circle(self.screen, C['text'], (x, y), 4)
        lbl = self.font_sm.render('Anclaje', True, C['accent'])
        self.screen.blit(lbl, (x - 25, y - 22))
        return (x, y + 10)

    def _draw_v_anchor(self):
        """Anclaje en V en la parte superior del acantilado."""
        center_x = 195
        center_y = CLIFF_TOP_Y + 35
        half_angle = math.radians(self.v_angle / 2)
        arm_len = 55

        a1_x = int(center_x - arm_len * math.sin(half_angle))
        a2_x = int(center_x + arm_len * math.sin(half_angle))
        a_y = CLIFF_TOP_Y - 5

        # Puntos de anclaje en la roca
        for ax_pt in [a1_x, a2_x]:
            pygame.draw.circle(self.screen, C['accent'], (ax_pt, a_y), 7)
            pygame.draw.circle(self.screen, C['text'], (ax_pt, a_y), 3)

        # Color según peligrosidad del ángulo
        arm_color = C['rope']
        if self.v_angle > 120:
            arm_color = C['danger']
        elif self.v_angle > 90:
            arm_color = C['warning']

        # Brazos de la V
        pygame.draw.line(self.screen, arm_color,
                         (a1_x, a_y), (center_x, center_y), 3)
        pygame.draw.line(self.screen, arm_color,
                         (a2_x, a_y), (center_x, center_y), 3)

        # Mosquetón central (punto de reunión)
        pygame.draw.circle(self.screen, C['warning'],
                           (center_x, center_y), 7)

        # Etiquetas
        lbl = self.font_sm.render(f'{self.v_angle}', True, C['warning'])
        self.screen.blit(lbl, (center_x - 8, center_y - 22))

        W = self.mass_kg * G / 1000.0
        F_arm = force_on_v_arm(W, self.v_angle)
        lbl = self.font_xs.render(f'{F_arm:.2f} kN/brazo', True, arm_color)
        self.screen.blit(lbl, (center_x + 12, center_y - 5))

        return (center_x, center_y + 7)

    def _get_load_position(self):
        """Calcula la posición de la carga según el estado actual."""
        if self.fall_state in (FallState.FALLING, FallState.IMPACT,
                               FallState.SETTLING):
            # Convertir metros a píxeles
            load_y = CLIFF_EDGE_Y + 20 + self.fall_pos_m * PIXELS_PER_METER
            load_y = max(CLIFF_TOP_Y - 40, min(load_y, GROUND_Y - 50))
            return LOAD_X, int(load_y)
        else:
            return LOAD_X, self.load_y_from_progress

    def draw_rope_system(self, anchor_pt):
        """Dibuja el sistema de cuerdas con la carga descendiendo verticalmente."""
        ax, ay = anchor_pt
        load_x, load_y = self._get_load_position()

        # ── Color de la cuerda ────────────────────────────────────────
        rope_color = C['rope']
        if self.fall_state == FallState.IMPACT and self.rope_flash_timer > 0:
            # Parpadeo rojo durante impacto
            flash = math.sin(self.rope_flash_timer * 12) > 0
            rope_color = C['danger'] if flash else C['rope']
        elif self.fall_state == FallState.FALLING:
            rope_color = C['warning']

        # ── Trayectoria de la cuerda ──────────────────────────────────
        if self.use_deviator:
            dev_x, dev_y = DEVIATOR_POS  # Posición FIJA

            # Cuerda: anclaje → desviador (fijo en borde) → vertical a carga
            pygame.draw.line(self.screen, rope_color,
                             (ax, ay), (dev_x, dev_y), 3)
            pygame.draw.line(self.screen, rope_color,
                             (dev_x, dev_y), (load_x, load_y), 3)

            # Dibujar desviador (anclado en la roca)
            pygame.draw.circle(self.screen, C['info'], (dev_x, dev_y), 8)
            pygame.draw.circle(self.screen, C['text'], (dev_x, dev_y), 3)
            # Perno de anclaje del desviador
            pygame.draw.line(self.screen, C['anchor'],
                             (dev_x - 12, dev_y), (dev_x - 5, dev_y), 3)
            lbl = self.font_xs.render('Desviador (fijo)', True, C['info'])
            self.screen.blit(lbl, (dev_x - 90, dev_y - 15))
        else:
            # Sin desviador: cuerda pasa por el borde del acantilado
            edge_pt = (CLIFF_EDGE_X - 2, CLIFF_EDGE_Y)
            pygame.draw.line(self.screen, rope_color,
                             (ax, ay), edge_pt, 3)
            pygame.draw.line(self.screen, rope_color,
                             edge_pt, (load_x, load_y), 3)
            # Indicador de contacto con el borde (zona de abrasión)
            pygame.draw.circle(self.screen, C['danger'],
                               edge_pt, 5, 1)
            lbl = self.font_xs.render('Borde (abrasion!)', True, C['danger'])
            self.screen.blit(lbl, (edge_pt[0] - 95, edge_pt[1] + 8))

        # ── Cuerda de seguridad (backup) ──────────────────────────────
        safety_anchor_x = ax + 15
        safety_load_x = load_x + 8
        safety_edge_y = CLIFF_EDGE_Y + 5

        # Seguridad también pasa por el borde
        pygame.draw.line(self.screen, C['accent'],
                         (safety_anchor_x, ay),
                         (CLIFF_EDGE_X + 5, safety_edge_y), 2)
        pygame.draw.line(self.screen, C['accent'],
                         (CLIFF_EDGE_X + 5, safety_edge_y),
                         (safety_load_x, load_y), 2)

        # Etiqueta de seguridad
        mid_y = (safety_edge_y + load_y) // 2
        lbl = self.font_xs.render('Seguridad', True, C['accent'])
        self.screen.blit(lbl, (safety_load_x + 8, mid_y))

        # ── Carga (camilla con persona) ───────────────────────────────
        self._draw_load(load_x, load_y)

        # ── Indicador de posición si hay caída ────────────────────────
        if self.fall_state == FallState.FALLING:
            # Mostrar posición de inicio de la caída
            start_y = CLIFF_EDGE_Y + 20 + self.fall_start_m * PIXELS_PER_METER
            start_y = max(CLIFF_TOP_Y - 40, int(start_y))
            pygame.draw.line(self.screen, C['accent'],
                             (load_x - 30, start_y),
                             (load_x + 30, start_y), 1)
            lbl = self.font_xs.render('Inicio caida', True, C['accent'])
            self.screen.blit(lbl, (load_x + 35, start_y - 6))

        return load_x, load_y

    def _draw_load(self, x, y):
        """Dibuja la carga (camilla con persona)."""
        w, h = 50, 28

        # Sombra de movimiento si está cayendo
        if self.fall_state == FallState.FALLING:
            for i in range(3):
                alpha_rect = pygame.Surface((w, h), pygame.SRCALPHA)
                alpha_rect.fill((255, 87, 34, 30 - i * 10))
                self.screen.blit(alpha_rect,
                                 (x - w // 2, y - (i + 1) * 8))

        # Camilla
        litter_color = C['secondary']
        if self.fall_state == FallState.IMPACT and self.rope_flash_timer > 0:
            litter_color = C['danger']

        pygame.draw.rect(self.screen, litter_color,
                         (x - w // 2, y, w, h), border_radius=4)
        pygame.draw.rect(self.screen, C['text'],
                         (x - w // 2, y, w, h), width=2, border_radius=4)

        # Persona simplificada
        pygame.draw.circle(self.screen, C['primary'], (x - 8, y + 9), 5)
        pygame.draw.line(self.screen, C['primary'],
                         (x - 8, y + 14), (x - 8, y + 24), 2)

        # Etiqueta de peso
        lbl = self.font_sm.render(f'{self.mass_kg} kg', True, C['text'])
        self.screen.blit(lbl, (x - 18, y + h + 3))

        # Flecha de peso (gravedad)
        arrow_end = y + h + 25
        pygame.draw.line(self.screen, C['danger'],
                         (x, y + h + 2), (x, arrow_end), 2)
        pygame.draw.polygon(self.screen, C['danger'], [
            (x, arrow_end + 6),
            (x - 4, arrow_end),
            (x + 4, arrow_end),
        ])

    def draw_info_panel(self):
        """Panel de información con fuerzas en tiempo real."""
        panel_x = 490
        panel_y = 55
        panel_w = WIDTH - panel_x - 15
        panel_h = HEIGHT - panel_y - 60

        pygame.draw.rect(self.screen, C['panel'],
                         (panel_x, panel_y, panel_w, panel_h),
                         border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (panel_x, panel_y, panel_w, panel_h),
                         width=1, border_radius=8)

        y = panel_y + 12
        x = panel_x + 15
        max_w = panel_w - 30

        # Título
        surf = self.font_big.render(
            'ANALISIS DE FUERZAS EN TIEMPO REAL', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 30

        W_kN = self.mass_kg * G / 1000.0

        # ── Carga ─────────────────────────────────────────────────────
        self._draw_section(x, y, 'CARGA', [
            (f'Masa: {self.mass_kg} kg   Peso: {W_kN:.2f} kN  '
             f'({self.mass_kg * G:.0f} N)', C['text']),
        ])
        y += 42

        # ── Anclaje ──────────────────────────────────────────────────
        if self.use_v_anchor:
            F_arm = force_on_v_arm(W_kN, self.v_angle)
            ratio = F_arm / W_kN * 100
            status = 'OK'
            c_arm = C['accent']
            if self.v_angle > 120:
                c_arm = C['danger']
                status = 'PELIGROSO'
            elif self.v_angle > 90:
                c_arm = C['warning']
                status = 'PRECAUCION'

            self._draw_section(x, y, 'ANCLAJE EN V', [
                (f'Angulo: {self.v_angle} deg  [{status}]   '
                 f'F/brazo: {F_arm:.2f} kN  ({ratio:.0f}% W)', c_arm),
            ])
            y += 42
        else:
            self._draw_section(x, y, 'ANCLAJE SIMPLE', [
                (f'Fuerza: {W_kN:.2f} kN  (100% de W)', C['text']),
            ])
            y += 42

        # ── Desviador ────────────────────────────────────────────────
        rope_force = W_kN
        if self.use_deviator:
            # Calcular ángulo real de desviación desde la geometría
            # (anclaje → desviador → carga)
            dev_angle = self._calc_deviator_angle()
            dev_force = 2 * rope_force * math.sin(math.radians(dev_angle / 2))
            self._draw_section(x, y, 'DESVIADOR (fijo en borde)', [
                (f'Angulo desvio: {dev_angle:.0f} deg   '
                 f'F desviador: {dev_force:.2f} kN', C['info']),
                (f'No reduce tension en cuerda principal, solo redirige.',
                 C['dark_text']),
            ])
            y += 58
        else:
            self._draw_section(x, y, 'SIN DESVIADOR', [
                (f'Cuerda pasa por el borde (riesgo de abrasion).', C['danger']),
            ])
            y += 42

        # ── Dispositivo de descenso ──────────────────────────────────
        hold_force = capstan_force(rope_force, self.device_mu,
                                    self.device_wraps)
        hold_kg = hold_force * 1000 / G
        reduction = (1 - hold_force / rope_force) * 100

        self._draw_section(x, y, 'DISPOSITIVO DE DESCENSO', [
            (f'mu={self.device_mu:.2f}  Vueltas={self.device_wraps:.1f}   '
             f'F frenador: {hold_force:.3f} kN ({hold_kg:.1f} kg)',
             C['accent']),
            (f'Reduccion: {reduction:.1f}%   '
             f'T_hold = T_load * e^(-mu*theta)',
             C['dark_text']),
        ])
        y += 58

        # ── Factor de caída ──────────────────────────────────────────
        pygame.draw.line(self.screen, C['warning'],
                         (x, y), (x + max_w, y), 1)
        y += 8

        ff = self.fall_factor
        ff_label = 'OFF' if ff <= 0 else f'{ff:.2f}'

        self._draw_section(x, y, f'FACTOR DE CAIDA: {ff_label}', [])
        y += 22

        if ff > 0:
            f_impact_semi = impact_force_kn(self.mass_kg, ff, KAPPA_STATIC)
            f_impact_dyn = impact_force_kn(self.mass_kg, ff, KAPPA_DYNAMIC)
            rope_out = self.fall_rope_out_m if self.fall_state != FallState.IDLE else max(5.0, self.descent_progress * ROPE_LENGTH_M)
            if rope_out < 3:
                rope_out = 10.0
            fall_dist = ff * rope_out

            lines = [
                (f'FF = d/L = {ff:.2f}   '
                 f'Cuerda: {rope_out:.1f} m   '
                 f'Caida: {fall_dist:.1f} m', C['warning']),
                (f'F choque semiestatica: {f_impact_semi:.1f} kN   '
                 f'dinamica: {f_impact_dyn:.1f} kN', C['text']),
            ]

            # UIAA check
            if f_impact_semi > 12.0:
                lines.append(
                    (f'SUPERA limite UIAA 12 kN con cuerda de rescate!',
                     C['danger']))
            if f_impact_semi > 30.0:
                lines.append(
                    (f'SUPERA MBS de cuerda (30 kN) — FALLO DEL SISTEMA!',
                     C['danger']))

            for text, color in lines:
                surf = self.font_sm.render(text, True, color)
                self.screen.blit(surf, (x + 10, y))
                y += 18
        else:
            surf = self.font_sm.render(
                'Presiona [F] para activar factor de caida.  '
                'En rescate, FF debe ser SIEMPRE 0.',
                True, C['dark_text'])
            self.screen.blit(surf, (x + 10, y))
            y += 18

        y += 5

        # ── Resultado de la caída (si ocurrió) ───────────────────────
        if self.fall_state in (FallState.IMPACT, FallState.SETTLING):
            pygame.draw.rect(self.screen, C['danger'],
                             (x, y, max_w, 52), width=2, border_radius=5)
            y += 5

            msg = f'IMPACTO!  F = {self.fall_impact_kn:.1f} kN  '
            msg += f'({self.fall_impact_kn * 1000 / G:.0f} kg equivalentes)'
            surf = self.font_big.render(msg, True, C['danger'])
            self.screen.blit(surf, (x + 10, y))
            y += 25

            if self.fall_impact_kn > 30:
                msg2 = 'CUERDA ROTA — Sistema ha fallado completamente.'
            elif self.fall_impact_kn > 12:
                msg2 = 'Supera UIAA 12kN — Lesiones probables en el paciente.'
            else:
                msg2 = 'Dentro de limites. El sistema absorbi la energia.'
            surf = self.font_sm.render(msg2, True, C['danger'])
            self.screen.blit(surf, (x + 10, y))
            y += 28
        else:
            y += 5

        # ── Resumen de seguridad ─────────────────────────────────────
        pygame.draw.line(self.screen, C['primary'],
                         (x, y), (x + max_w, y), 1)
        y += 8

        surf = self.font_big.render('RESUMEN DE SEGURIDAD', True,
                                    C['primary'])
        self.screen.blit(surf, (x, y))
        y += 26

        mbs = 30.0
        checks = []

        # Anclaje
        if self.use_v_anchor:
            F_arm = force_on_v_arm(W_kN, self.v_angle)
            sf_a = mbs / F_arm if F_arm > 0 else 999
            sym = 'OK' if sf_a >= 10 else ('!!' if sf_a >= 5 else 'XX')
            c = C['accent'] if sf_a >= 10 else (C['warning'] if sf_a >= 5 else C['danger'])
            checks.append((f'Anclaje V:  FS={sf_a:.1f}:1 [{sym}]', c))

        # Cuerda
        sf_r = mbs / rope_force if rope_force > 0 else 999
        sym = 'OK' if sf_r >= 10 else ('!!' if sf_r >= 5 else 'XX')
        c = C['accent'] if sf_r >= 10 else (C['warning'] if sf_r >= 5 else C['danger'])
        checks.append((f'Cuerda:     FS={sf_r:.1f}:1 [{sym}] (MBS {mbs}kN)', c))

        # NFPA
        c = C['accent'] if rope_force <= 13.5 else C['danger']
        sym = 'OK' if rope_force <= 13.5 else 'XX'
        checks.append((f'NFPA:       {rope_force:.2f} kN [{sym}] (limite 13.5)', c))

        # Frenador
        c = C['accent'] if hold_kg <= 20 else (C['warning'] if hold_kg <= 40 else C['danger'])
        sym = 'OK' if hold_kg <= 20 else ('!!' if hold_kg <= 40 else 'XX')
        checks.append((f'Frenador:   {hold_kg:.1f} kg [{sym}]', c))

        # Factor de caída
        if ff > 0:
            c = C['danger']
            checks.append((f'Factor caida: {ff:.2f} — EN RESCATE DEBE SER 0', c))

        for text, color in checks:
            surf = self.font_sm.render(text, True, color)
            self.screen.blit(surf, (x + 8, y))
            y += 18

        # ── Barra de progreso ────────────────────────────────────────
        y += 10
        bar_w = max_w
        bar_h = 16
        pygame.draw.rect(self.screen, (40, 40, 55),
                         (x, y, bar_w, bar_h), border_radius=3)
        prog = self.descent_progress
        if self.fall_state != FallState.IDLE:
            prog = max(0, min(self.fall_pos_m / ROPE_LENGTH_M, 1.0))
        pw = int(bar_w * prog)
        if pw > 0:
            bar_col = C['danger'] if self.fall_state == FallState.FALLING else C['primary']
            pygame.draw.rect(self.screen, bar_col,
                             (x, y, pw, bar_h), border_radius=3)
        label = 'Descenso' if self.fall_state == FallState.IDLE else 'Posicion'
        surf = self.font_xs.render(
            f'{label}: {prog * 100:.0f}%', True, C['text'])
        self.screen.blit(surf, (x + bar_w // 2 - 30, y + 1))

    def _calc_deviator_angle(self):
        """Calcula el ángulo de desviación real desde la geometría."""
        # Vector: anclaje → desviador
        ax, ay = 195, CLIFF_TOP_Y + 42
        dx, dy = DEVIATOR_POS
        lx, ly = self._get_load_position()

        v1 = (ax - dx, ay - dy)
        v2 = (lx - dx, ly - dy)

        dot = v1[0] * v2[0] + v1[1] * v2[1]
        m1 = math.sqrt(v1[0]**2 + v1[1]**2)
        m2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if m1 * m2 < 0.001:
            return 0
        cos_a = max(-1, min(1, dot / (m1 * m2)))
        return math.degrees(math.acos(cos_a))

    def _draw_section(self, x, y, title, lines):
        """Sección del panel informativo."""
        surf = self.font_med.render(f'--- {title} ---', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 20
        for text, color in lines:
            surf = self.font_sm.render(text, True, color)
            self.screen.blit(surf, (x + 10, y))
            y += 18

    def draw_controls(self):
        """Barra de controles inferior."""
        ctrl_y = HEIGHT - 42
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 8, WIDTH, 50))

        ff_label = 'OFF' if self.fall_factor <= 0 else f'{self.fall_factor:.2f}'

        space_label = 'Caida!' if self.fall_factor > 0 else (
            'Pausar' if self.descending else 'Descender')

        controls = [
            f'[ESPACIO] {space_label}',
            '[Up/Dn] Masa',
            '[Iz/De] Angulo V',
            f'[A] Anclaje: {"V" if self.use_v_anchor else "Simple"}',
            f'[D] Desviador: {"ON" if self.use_deviator else "OFF"}',
            f'[F] Factor caida: {ff_label}',
            '[R] Reiniciar',
            '[ESC] Salir',
        ]
        cx = 12
        for ctrl in controls:
            is_ff = 'Factor' in ctrl and self.fall_factor > 0
            color = C['danger'] if is_ff else C['dark_text']
            surf = self.font_xs.render(ctrl, True, color)
            self.screen.blit(surf, (cx, ctrl_y))
            cx += surf.get_width() + 14

    def draw(self):
        """Renderiza toda la escena."""
        self.screen.fill(C['bg'])

        # Título
        title = self.font_title.render(
            'SIMULADOR DE SISTEMA DE RESCATE', True, C['primary'])
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 12))

        # Escena
        self.draw_cliff()
        anchor_pt = self.draw_anchor_system()
        self.draw_rope_system(anchor_pt)

        # Panel de datos
        self.draw_info_panel()

        # Controles
        self.draw_controls()

        pygame.display.flip()

    def run(self):
        """Bucle principal."""
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
                        if self.fall_factor > 0:
                            # Disparar caída
                            if self.fall_state in (FallState.IDLE,
                                                    FallState.SETTLING):
                                self.setup_fall()
                        else:
                            # Descenso normal
                            self.descending = not self.descending

                    elif event.key == pygame.K_r:
                        self.reset()

                    elif event.key == pygame.K_a:
                        self.use_v_anchor = not self.use_v_anchor

                    elif event.key == pygame.K_d:
                        self.use_deviator = not self.use_deviator

                    elif event.key == pygame.K_f:
                        # Ciclar factor de caída
                        self.ff_index = (self.ff_index + 1) % len(FF_OPTIONS)
                        self.fall_factor = FF_OPTIONS[self.ff_index]
                        # Reiniciar estado de caída
                        self.fall_state = FallState.IDLE
                        self.fall_impact_kn = 0.0

                    elif event.key == pygame.K_UP:
                        self.mass_kg = min(self.mass_kg + 10, 500)
                    elif event.key == pygame.K_DOWN:
                        self.mass_kg = max(self.mass_kg - 10, 10)
                    elif event.key == pygame.K_LEFT:
                        self.v_angle = max(self.v_angle - 5, 10)
                    elif event.key == pygame.K_RIGHT:
                        self.v_angle = min(self.v_angle + 5, 170)

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = RescueSimulator()
    sim.run()
