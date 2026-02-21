"""
╔══════════════════════════════════════════════════════════════════════╗
║   FISICA DEL RESCATE · Modulo 15: Sistema de Contrapeso (Pygame)  ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulacion interactiva de un sistema de contrapeso (Atwood) para ║
║  rescate tecnico / urbano.  El peso del rescatista contrapesa al  ║
║  paciente durante un pick-off o descenso desde el borde.          ║
║                                                                      ║
║  Fisica:                                                             ║
║   - Maquina de Atwood con friccion opcional (capstan)              ║
║   - F_neta = (m1 - m2) * g                                         ║
║   - a = (m1 - m2) * g / (m1 + m2)                                  ║
║   - T = 2 * m1 * m2 * g / (m1 + m2)                                ║
║   - Friccion: T_pesado = T_liviano * e^(mu*theta)                  ║
║   - Fuerza en redirect: F = T1 + T2  (suma vectorial)             ║
║                                                                      ║
║  Controles:                                                          ║
║   [Up/Dn]     Ajustar masa rescatista (50-120 kg)                  ║
║   [W/S]       Ajustar masa paciente   (30-150 kg)                  ║
║   [F]         Activar/desactivar friccion en borde (mu=0.3)        ║
║   [ESPACIO]   Liberar sistema / Reiniciar posicion                  ║
║   [Iz/De]     Ajustar angulo de redireccion (30-170 deg)           ║
║   [R]         Reiniciar completamente                               ║
║   [ESC]       Salir                                                  ║
║                                                                      ║
║  Ejecutar:  python 15_sistema_contrapeso.py                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import math
import pygame
from config import PG_COLORS as C, G

# ── Pantalla ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1400, 850
FPS = 60

# ── Geometria de la escena ───────────────────────────────────────────
BUILDING_LEFT = 60
BUILDING_RIGHT = 380
BUILDING_TOP = 180
EDGE_X = BUILDING_RIGHT          # Borde del edificio
EDGE_Y = BUILDING_TOP + 30       # Punto de redireccion
GROUND_Y = HEIGHT - 90

# Limites de movimiento vertical (pixeles)
TOP_LIMIT = EDGE_Y + 30
BOTTOM_LIMIT = GROUND_Y - 60
TRAVEL_PX = BOTTOM_LIMIT - TOP_LIMIT

# Metros que representa ese recorrido
TRAVEL_M = 30.0
PX_PER_M = TRAVEL_PX / TRAVEL_M

# Posiciones X de cada lado de la cuerda
RESCUER_X = BUILDING_LEFT + 80   # Lado izquierdo (interior edificio)
PATIENT_X = EDGE_X + 100         # Lado derecho (exterior / fachada)

# ── Panel de datos ───────────────────────────────────────────────────
PANEL_X = 620
PANEL_Y = 55
PANEL_W = WIDTH - PANEL_X - 15
PANEL_H = HEIGHT - PANEL_Y - 60


class CounterbalanceSim:
    """Simulador de sistema de contrapeso para rescate tecnico."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            'Fisica del Rescate -- Sistema de Contrapeso')
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont('DejaVu Sans', 26, bold=True)
        self.font_big = pygame.font.SysFont('DejaVu Sans', 18, bold=True)
        self.font_med = pygame.font.SysFont('DejaVu Sans', 14)
        self.font_sm = pygame.font.SysFont('DejaVu Sans', 12)
        self.font_xs = pygame.font.SysFont('DejaVu Sans', 11)
        self.font_formula = pygame.font.SysFont('DejaVu Sans', 13, bold=True)

        self.reset()

    # ── Estado ────────────────────────────────────────────────────────
    def reset(self):
        """Reinicia todo el estado de la simulacion."""
        self.m_rescuer = 80.0       # kg
        self.m_patient = 70.0       # kg
        self.friction_on = False
        self.mu = 0.30              # coeficiente de friccion
        self.redirect_angle = 120   # grados del angulo de redireccion

        # Estado cinematico (posicion en metros desde el borde, 0 = arriba)
        self.pos_rescuer = TRAVEL_M * 0.3   # rescatista empieza a ~30%
        self.pos_patient = TRAVEL_M * 0.3
        self.velocity = 0.0                 # m/s (positivo = rescatista baja)
        self.released = False
        self.finished = False
        self.peak_speed = 0.0
        self.elapsed_time = 0.0

    # ── Fisica ────────────────────────────────────────────────────────
    def _calc_physics(self):
        """Calcula todas las magnitudes fisicas del sistema actual."""
        m1 = self.m_rescuer
        m2 = self.m_patient
        theta_rad = math.radians(self.redirect_angle)

        W1 = m1 * G
        W2 = m2 * G

        # --- Sin friccion (Atwood ideal) ---
        T_ideal = 2 * m1 * m2 * G / (m1 + m2) if (m1 + m2) > 0 else 0
        F_net_ideal = (m1 - m2) * G
        a_ideal = (m1 - m2) * G / (m1 + m2) if (m1 + m2) > 0 else 0

        # --- Con friccion (capstan en el redirect) ---
        # La friccion se opone al movimiento.
        # Si m1 > m2 el rescatista baja -> la cuerda se mueve tal que
        # el lado pesado (rescatista) es el lado de entrada.
        # T_heavy = T_light * e^(mu*theta)  (capstan eq.)
        #
        # Equilibrio dinamico:
        #   lado rescatista:  m1*a = m1*g - T1
        #   lado paciente:    m2*a = T2 - m2*g    (T2 tira hacia arriba)
        #
        # Sin friccion T1=T2=T
        # Con friccion, si rescatista baja (m1>m2):
        #   T1 > T2,  T1 = T2 * e^(mu*theta)
        #   m1*g - T1 = m1*a   =>  T1 = m1*(g-a)
        #   T2 - m2*g = m2*a   =>  T2 = m2*(g+a)
        #   T1 = T2 * e^(mu*theta)
        #   m1*(g-a) = m2*(g+a) * e^(mu*theta)
        #   Resolviendo para a:
        #   a = g * (m1 - m2*e^(mu*theta)) / (m1 + m2*e^(mu*theta))
        #
        # Si m2 > m1 (paciente mas pesado, paciente baja):
        #   ahora el lado pesado es el paciente, la friccion invierte:
        #   T2 = T1 * e^(mu*theta)
        #   m2*g - T2 = m2*a_p   (paciente baja)
        #   T1 - m1*g = m1*a_p   (rescatista sube)
        #   T2 = T1*e^(mu*theta)
        #   m2*(g-a_p) = m1*(g+a_p)*e^(mu*theta)
        #   a_p = g*(m2 - m1*e^(mu*theta))/(m2 + m1*e^(mu*theta))
        #   (sign: positive = paciente baja = rescatista sube)

        if self.friction_on:
            exp_mu_theta = math.exp(self.mu * theta_rad)
            if m1 >= m2:
                # Rescatista baja (o equilibrio)
                a_friction = G * (m1 - m2 * exp_mu_theta) / (
                    m1 + m2 * exp_mu_theta)
                # a_friction > 0 : rescatista baja efectivamente
                # a_friction < 0 : friccion detiene al sistema (equilibrio
                # forzado por la friccion)
                if a_friction < 0:
                    a_friction = 0.0  # friccion mantiene estatico
                T2_fric = m2 * (G + a_friction)
                T1_fric = T2_fric * exp_mu_theta
                direction = 1   # rescatista baja
            else:
                # Paciente baja
                a_p = G * (m2 - m1 * exp_mu_theta) / (
                    m2 + m1 * exp_mu_theta)
                if a_p < 0:
                    a_p = 0.0
                a_friction = a_p
                T1_fric = m1 * (G + a_friction)
                T2_fric = T1_fric * exp_mu_theta
                direction = -1  # paciente baja (rescatista sube)
        else:
            exp_mu_theta = 1.0
            a_friction = abs(a_ideal)
            T1_fric = T_ideal
            T2_fric = T_ideal
            direction = 1 if m1 >= m2 else -1

        # Fuerza en el punto de redireccion (suma vectorial de ambas tensiones)
        # F_redirect = sqrt(T1^2 + T2^2 + 2*T1*T2*cos(pi - theta))
        # Para un angulo de redirect theta, las cuerdas forman ese angulo.
        # La fuerza sobre el punto = magnitud de la resultante.
        half_angle = theta_rad / 2.0
        F_redirect = math.sqrt(
            T1_fric ** 2 + T2_fric ** 2 +
            2 * T1_fric * T2_fric * math.cos(math.pi - theta_rad))

        # Alternativa mas intuitiva: F = 2*T*sin(theta/2) si T1~=T2
        F_redirect_approx = 2 * T_ideal * math.sin(half_angle)

        return {
            'm1': m1, 'm2': m2,
            'W1': W1, 'W2': W2,
            'T_ideal': T_ideal,
            'F_net_ideal': F_net_ideal,
            'a_ideal': a_ideal,
            'a_friction': a_friction,
            'T1': T1_fric,
            'T2': T2_fric,
            'F_redirect': F_redirect,
            'F_redirect_approx': F_redirect_approx,
            'direction': direction,
            'exp_mu_theta': exp_mu_theta,
            'theta_rad': theta_rad,
        }

    # ── Actualizacion ─────────────────────────────────────────────────
    def update(self, dt):
        """Avanza la simulacion un paso de tiempo dt (segundos)."""
        if not self.released or self.finished:
            return

        phys = self._calc_physics()
        accel = phys['a_friction']
        direction = phys['direction']

        # Si aceleracion es practicamente cero, el sistema esta detenido
        if accel < 0.001:
            self.velocity = 0.0
            return

        # Integrar velocidad y posicion
        self.velocity += accel * dt
        displacement = self.velocity * dt  # metros

        # Aplicar movimiento: direction=1 => rescatista baja, paciente sube
        #                     direction=-1 => paciente baja, rescatista sube
        self.pos_rescuer += direction * displacement
        self.pos_patient -= direction * displacement

        # Actualizar maximo
        if abs(self.velocity) > self.peak_speed:
            self.peak_speed = abs(self.velocity)
        self.elapsed_time += dt

        # Verificar limites
        if (self.pos_rescuer >= TRAVEL_M or self.pos_rescuer <= 0 or
                self.pos_patient >= TRAVEL_M or self.pos_patient <= 0):
            self.pos_rescuer = max(0, min(TRAVEL_M, self.pos_rescuer))
            self.pos_patient = max(0, min(TRAVEL_M, self.pos_patient))
            self.velocity = 0.0
            self.finished = True

    # ── Conversion posicion metros -> pixeles ────────────────────────
    def _pos_to_py(self, pos_m):
        """Convierte posicion en metros a coordenada Y en pixeles."""
        return int(TOP_LIMIT + pos_m * PX_PER_M)

    # ── Dibujo de la escena ──────────────────────────────────────────
    def _draw_building(self):
        """Dibuja la estructura del edificio / acantilado."""
        # Fachada del edificio (lado izquierdo, interior)
        pygame.draw.rect(self.screen, (45, 45, 65),
                         (BUILDING_LEFT, BUILDING_TOP,
                          BUILDING_RIGHT - BUILDING_LEFT, GROUND_Y - BUILDING_TOP))
        # Borde superior (techo)
        pygame.draw.rect(self.screen, (60, 60, 85),
                         (BUILDING_LEFT - 10, BUILDING_TOP - 12,
                          BUILDING_RIGHT - BUILDING_LEFT + 20, 16))
        # Lineas de textura (pisos)
        for yt in range(BUILDING_TOP + 50, GROUND_Y, 55):
            pygame.draw.line(self.screen, (55, 55, 75),
                             (BUILDING_LEFT + 5, yt),
                             (BUILDING_RIGHT - 5, yt), 1)
        # Ventanas
        win_w, win_h = 22, 28
        for row_y in range(BUILDING_TOP + 18, GROUND_Y - 40, 55):
            for col_x in range(BUILDING_LEFT + 20, BUILDING_RIGHT - 20, 40):
                pygame.draw.rect(self.screen, (30, 45, 70),
                                 (col_x, row_y, win_w, win_h))
                pygame.draw.rect(self.screen, (50, 60, 80),
                                 (col_x, row_y, win_w, win_h), 1)

        # Pared exterior (fachada derecha, se ve la cara)
        ext_width = 18
        pygame.draw.rect(self.screen, (55, 55, 75),
                         (BUILDING_RIGHT, BUILDING_TOP,
                          ext_width, GROUND_Y - BUILDING_TOP))
        pygame.draw.line(self.screen, (70, 70, 90),
                         (BUILDING_RIGHT, BUILDING_TOP),
                         (BUILDING_RIGHT, GROUND_Y), 2)

        # Borde/lip del edificio (punto de redireccion)
        pygame.draw.circle(self.screen, C['anchor'],
                           (EDGE_X, EDGE_Y), 10)
        pygame.draw.circle(self.screen, C['warning'],
                           (EDGE_X, EDGE_Y), 6)
        # Etiqueta
        lbl = self.font_sm.render('Redirect', True, C['warning'])
        self.screen.blit(lbl, (EDGE_X - 50, EDGE_Y - 22))

        # Suelo
        pygame.draw.line(self.screen, (80, 80, 100),
                         (BUILDING_LEFT - 20, GROUND_Y),
                         (PANEL_X - 30, GROUND_Y), 2)
        # Textura suelo
        for sx in range(BUILDING_LEFT - 15, PANEL_X - 35, 12):
            pygame.draw.line(self.screen, (50, 50, 65),
                             (sx, GROUND_Y + 1), (sx - 4, GROUND_Y + 6), 1)

    def _draw_person(self, cx, cy, mass_kg, label, color, facing_right=True):
        """Dibuja una figura humana simplificada (stick figure mejorada)."""
        # Cabeza
        head_r = 10
        pygame.draw.circle(self.screen, color, (cx, cy), head_r, 2)

        # Cuerpo
        body_top = cy + head_r
        body_bottom = body_top + 28
        pygame.draw.line(self.screen, color,
                         (cx, body_top), (cx, body_bottom), 2)

        # Brazos
        arm_y = body_top + 8
        arm_dx = 14 if facing_right else -14
        pygame.draw.line(self.screen, color,
                         (cx, arm_y), (cx + arm_dx, arm_y + 12), 2)
        pygame.draw.line(self.screen, color,
                         (cx, arm_y), (cx - arm_dx, arm_y + 12), 2)

        # Piernas
        pygame.draw.line(self.screen, color,
                         (cx, body_bottom), (cx - 8, body_bottom + 18), 2)
        pygame.draw.line(self.screen, color,
                         (cx, body_bottom), (cx + 8, body_bottom + 18), 2)

        # Etiqueta de masa
        lbl = self.font_sm.render(f'{mass_kg:.0f} kg', True, color)
        lbl_x = cx - lbl.get_width() // 2
        lbl_y = body_bottom + 22
        pygame.draw.rect(self.screen, C['bg'],
                         (lbl_x - 2, lbl_y - 1,
                          lbl.get_width() + 4, lbl.get_height() + 2))
        self.screen.blit(lbl, (lbl_x, lbl_y))

        # Nombre/rol
        name_lbl = self.font_xs.render(label, True, color)
        name_x = cx - name_lbl.get_width() // 2
        self.screen.blit(name_lbl, (name_x, cy - head_r - 15))

    def _draw_force_arrow(self, x, y, dx, dy, color, label='', offset_x=0, offset_y=0):
        """Dibuja una flecha de fuerza desde (x,y) con desplazamiento (dx,dy)."""
        end_x = x + dx
        end_y = y + dy
        pygame.draw.line(self.screen, color, (x, y), (int(end_x), int(end_y)), 2)

        # Punta de flecha
        length = math.sqrt(dx ** 2 + dy ** 2)
        if length > 5:
            ux, uy = dx / length, dy / length
            px, py = -uy, ux  # perpendicular
            tip_size = 7
            tx, ty = int(end_x), int(end_y)
            p1 = (int(tx - tip_size * ux + tip_size * 0.4 * px),
                  int(ty - tip_size * uy + tip_size * 0.4 * py))
            p2 = (int(tx - tip_size * ux - tip_size * 0.4 * px),
                  int(ty - tip_size * uy - tip_size * 0.4 * py))
            pygame.draw.polygon(self.screen, color, [(tx, ty), p1, p2])

        if label:
            lbl = self.font_xs.render(label, True, color)
            lx = int((x + end_x) / 2) + offset_x
            ly = int((y + end_y) / 2) + offset_y
            self.screen.blit(lbl, (lx, ly))

    def _draw_scene(self):
        """Dibuja toda la escena animada."""
        self._draw_building()

        phys = self._calc_physics()

        # Posiciones Y en pixeles
        ry = self._pos_to_py(self.pos_rescuer)
        py = self._pos_to_py(self.pos_patient)

        # ── Cuerda ───────────────────────────────────────────────────
        # La cuerda va: rescatista -> borde (redirect) -> paciente
        rope_rescuer_top = (RESCUER_X, ry - 10)
        rope_patient_top = (PATIENT_X, py - 10)
        rope_edge = (EDGE_X, EDGE_Y)

        rope_color = C['rope']
        if self.released and not self.finished:
            # Cuerda pulsante durante movimiento
            pulse = int(128 + 60 * math.sin(pygame.time.get_ticks() * 0.008))
            rope_color = (255, min(255, pulse), 38)

        pygame.draw.line(self.screen, rope_color,
                         rope_rescuer_top, rope_edge, 3)
        pygame.draw.line(self.screen, rope_color,
                         rope_edge, rope_patient_top, 3)

        # Indicador del angulo de redirect
        angle_rad = math.radians(self.redirect_angle)
        arc_r = 25
        # Dibujar arco del angulo
        # Las cuerdas llegan al borde: una desde la izquierda-abajo, otra hacia la derecha-abajo.
        # Calcular angulos de las cuerdas respecto al borde
        dx1 = rope_rescuer_top[0] - EDGE_X
        dy1 = rope_rescuer_top[1] - EDGE_Y
        ang1 = math.atan2(dy1, dx1)
        dx2 = rope_patient_top[0] - EDGE_X
        dy2 = rope_patient_top[1] - EDGE_Y
        ang2 = math.atan2(dy2, dx2)

        # Dibujar segmentos de arco
        n_segs = 16
        if ang1 > ang2:
            ang1, ang2 = ang2, ang1
        for i in range(n_segs):
            a_start = ang1 + (ang2 - ang1) * i / n_segs
            a_end = ang1 + (ang2 - ang1) * (i + 1) / n_segs
            sx = int(EDGE_X + arc_r * math.cos(a_start))
            sy = int(EDGE_Y + arc_r * math.sin(a_start))
            ex = int(EDGE_X + arc_r * math.cos(a_end))
            ey = int(EDGE_Y + arc_r * math.sin(a_end))
            pygame.draw.line(self.screen, C['dark_text'], (sx, sy), (ex, ey), 1)

        # Etiqueta del angulo
        mid_ang = (ang1 + ang2) / 2
        lbl_x = int(EDGE_X + (arc_r + 14) * math.cos(mid_ang))
        lbl_y = int(EDGE_Y + (arc_r + 14) * math.sin(mid_ang))
        ang_lbl = self.font_xs.render(f'{self.redirect_angle} deg', True, C['dark_text'])
        self.screen.blit(ang_lbl, (lbl_x - 12, lbl_y - 6))

        # ── Personas ─────────────────────────────────────────────────
        self._draw_person(RESCUER_X, ry, self.m_rescuer,
                          'RESCATISTA', C['primary'], facing_right=True)
        self._draw_person(PATIENT_X, py, self.m_patient,
                          'PACIENTE', C['secondary'], facing_right=False)

        # ── Flechas de peso ──────────────────────────────────────────
        arrow_scale = 0.035  # pixeles por Newton
        w1_len = phys['W1'] * arrow_scale
        w2_len = phys['W2'] * arrow_scale

        # Peso rescatista (hacia abajo)
        self._draw_force_arrow(
            RESCUER_X - 20, ry + 55, 0, w1_len, C['danger'],
            f'W={phys["W1"]:.0f}N', offset_x=5, offset_y=-8)

        # Peso paciente (hacia abajo)
        self._draw_force_arrow(
            PATIENT_X + 20, py + 55, 0, w2_len, C['danger'],
            f'W={phys["W2"]:.0f}N', offset_x=5, offset_y=-8)

        # ── Flechas de tension ───────────────────────────────────────
        t1_len = phys['T1'] * arrow_scale
        t2_len = phys['T2'] * arrow_scale

        # Tension lado rescatista (hacia arriba)
        self._draw_force_arrow(
            RESCUER_X + 15, ry - 12, 0, -t1_len, C['accent'],
            f'T1={phys["T1"]:.0f}N', offset_x=5, offset_y=0)

        # Tension lado paciente (hacia arriba)
        self._draw_force_arrow(
            PATIENT_X - 15, py - 12, 0, -t2_len, C['accent'],
            f'T2={phys["T2"]:.0f}N', offset_x=-65, offset_y=0)

        # ── Flecha de fuerza en redirect ─────────────────────────────
        # Fuerza apunta "hacia adentro" del angulo (hacia abajo-algo)
        f_redir = phys['F_redirect']
        f_arrow_len = f_redir * arrow_scale
        # Direccion: bisectriz del angulo formado por las cuerdas, apuntando
        # hacia fuera del vertice
        bis_ang = (ang1 + ang2) / 2
        fr_dx = f_arrow_len * math.cos(bis_ang)
        fr_dy = f_arrow_len * math.sin(bis_ang)
        self._draw_force_arrow(
            EDGE_X, EDGE_Y, fr_dx, fr_dy, C['warning'],
            f'F={f_redir:.0f}N', offset_x=8, offset_y=-12)

        # ── Flechas de movimiento ────────────────────────────────────
        if self.released and not self.finished and abs(self.velocity) > 0.05:
            direction = phys['direction']
            speed_arrow = min(abs(self.velocity) * 8, 40)

            # Rescatista
            r_dy = speed_arrow * direction
            self._draw_force_arrow(
                RESCUER_X + 30, ry + 20, 0, r_dy, C['info'],
                f'{abs(self.velocity):.1f} m/s', offset_x=5, offset_y=-6)

            # Paciente (direccion opuesta)
            p_dy = -speed_arrow * direction
            self._draw_force_arrow(
                PATIENT_X - 30, py + 20, 0, p_dy, C['info'],
                '', offset_x=5, offset_y=-6)

        # ── Indicador de friccion en el borde ────────────────────────
        if self.friction_on:
            # Semicirculo punteado alrededor del punto de redirect
            for i in range(0, 360, 20):
                rad = math.radians(i)
                fx = int(EDGE_X + 16 * math.cos(rad))
                fy = int(EDGE_Y + 16 * math.sin(rad))
                pygame.draw.circle(self.screen, C['secondary'], (fx, fy), 2)
            fric_lbl = self.font_xs.render(f'mu={self.mu}', True, C['secondary'])
            self.screen.blit(fric_lbl, (EDGE_X - 45, EDGE_Y + 14))

    # ── Panel de datos ────────────────────────────────────────────────
    def _draw_panel(self):
        """Panel derecho con todos los datos fisicos."""
        pygame.draw.rect(self.screen, C['panel'],
                         (PANEL_X, PANEL_Y, PANEL_W, PANEL_H),
                         border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (PANEL_X, PANEL_Y, PANEL_W, PANEL_H),
                         width=1, border_radius=8)

        x = PANEL_X + 14
        y = PANEL_Y + 12
        rw = PANEL_W - 28   # ancho util

        phys = self._calc_physics()

        # Titulo del panel
        surf = self.font_big.render(
            'ANALISIS DEL SISTEMA DE CONTRAPESO', True, C['primary'])
        self.screen.blit(surf, (x, y))
        y += 28

        # ── Masas y pesos ────────────────────────────────────────────
        self._section(x, y, 'MASAS Y PESOS')
        y += 18
        W1_kn = phys['W1'] / 1000
        W2_kn = phys['W2'] / 1000
        ratio = phys['m1'] / phys['m2'] if phys['m2'] > 0 else 999
        self._line(x, y, f'Rescatista:  {phys["m1"]:.0f} kg    '
                   f'W1 = {phys["W1"]:.1f} N  ({W1_kn:.2f} kN)', C['primary'])
        y += 16
        self._line(x, y, f'Paciente:    {phys["m2"]:.0f} kg    '
                   f'W2 = {phys["W2"]:.1f} N  ({W2_kn:.2f} kN)', C['secondary'])
        y += 16
        ratio_col = C['accent'] if 0.8 <= ratio <= 1.5 else C['warning']
        self._line(x, y, f'Ratio m1/m2 = {ratio:.2f}    '
                   f'Diferencia = {abs(phys["m1"] - phys["m2"]):.0f} kg', ratio_col)
        y += 22

        # ── Tension y fuerzas (Atwood ideal) ─────────────────────────
        self._section(x, y, 'ATWOOD IDEAL (sin friccion)')
        y += 18
        T_kn = phys['T_ideal'] / 1000
        self._line(x, y, f'T = 2*m1*m2*g/(m1+m2) = {phys["T_ideal"]:.1f} N  '
                   f'({T_kn:.3f} kN)', C['accent'])
        y += 16
        self._line(x, y, f'F neta = (m1-m2)*g = {phys["F_net_ideal"]:.1f} N', C['text'])
        y += 16
        self._line(x, y, f'a = (m1-m2)*g/(m1+m2) = {phys["a_ideal"]:.3f} m/s2',
                   C['text'])
        y += 16
        direction_txt = 'Rescatista baja' if phys['a_ideal'] > 0.01 else (
            'Paciente baja' if phys['a_ideal'] < -0.01 else 'Equilibrado')
        dir_col = C['primary'] if phys['a_ideal'] > 0.01 else (
            C['secondary'] if phys['a_ideal'] < -0.01 else C['accent'])
        self._line(x, y, f'Direccion: {direction_txt}', dir_col)
        y += 22

        # ── Friccion ─────────────────────────────────────────────────
        fric_label = 'ACTIVADA' if self.friction_on else 'DESACTIVADA'
        fric_col = C['secondary'] if self.friction_on else C['dark_text']
        self._section(x, y, f'FRICCION EN REDIRECT: {fric_label}')
        y += 18

        if self.friction_on:
            theta_rad = phys['theta_rad']
            exp_val = phys['exp_mu_theta']
            self._line(x, y, f'mu = {self.mu:.2f}   theta = {self.redirect_angle} deg  '
                       f'({theta_rad:.2f} rad)', C['secondary'])
            y += 16
            self._line(x, y, f'e^(mu*theta) = e^({self.mu*theta_rad:.3f}) = '
                       f'{exp_val:.4f}', C['secondary'])
            y += 16
            self._line(x, y, f'T1 (lado pesado) = {phys["T1"]:.1f} N   '
                       f'T2 (lado liviano) = {phys["T2"]:.1f} N', C['text'])
            y += 16
            diff_t = abs(phys['T1'] - phys['T2'])
            self._line(x, y, f'Diferencia por friccion: {diff_t:.1f} N  '
                       f'(retenido por el borde)', C['dark_text'])
            y += 16
            self._line(x, y, f'a (con friccion) = {phys["a_friction"]:.3f} m/s2',
                       C['accent'])
            y += 16
            # Comparacion
            if abs(phys['a_ideal']) > 0.001:
                reduction = (1 - phys['a_friction'] / abs(phys['a_ideal'])) * 100
                reduction = max(0, reduction)
                self._line(x, y, f'Reduccion vs ideal: {reduction:.0f}%',
                           C['accent'])
            else:
                self._line(x, y, 'Sistema en equilibrio ideal tambien', C['accent'])
            y += 18
        else:
            self._line(x, y, 'Presiona [F] para activar friccion (mu=0.3)',
                       C['dark_text'])
            y += 16
            self._line(x, y, 'T1 = T2 = T (tension uniforme sin friccion)',
                       C['dark_text'])
            y += 34

        # ── Fuerza en punto de redireccion ───────────────────────────
        self._section(x, y, 'FUERZA EN PUNTO DE REDIRECCION')
        y += 18
        f_rn = phys['F_redirect']
        f_rn_kn = f_rn / 1000
        self._line(x, y, f'F_redirect = {f_rn:.1f} N  ({f_rn_kn:.3f} kN)',
                   C['warning'])
        y += 16
        self._line(x, y, f'Angulo redirect: {self.redirect_angle} deg   '
                   f'F = sqrt(T1^2+T2^2+2*T1*T2*cos(pi-theta))', C['dark_text'])
        y += 16
        self._line(x, y, f'Aprox (T iguales): 2T*sin(theta/2) = '
                   f'{phys["F_redirect_approx"]:.1f} N', C['dark_text'])
        y += 22

        # ── Estado dinamico ──────────────────────────────────────────
        pygame.draw.line(self.screen, C['primary'],
                         (x, y), (x + rw, y), 1)
        y += 8
        self._section(x, y, 'ESTADO DINAMICO')
        y += 18

        status_txt = 'DETENIDO'
        status_col = C['dark_text']
        if self.released and not self.finished:
            status_txt = 'EN MOVIMIENTO'
            status_col = C['info']
        elif self.finished:
            status_txt = 'LIMITE ALCANZADO'
            status_col = C['warning']

        self._line(x, y, f'Estado: {status_txt}', status_col)
        y += 16
        self._line(x, y, f'Velocidad: {abs(self.velocity):.2f} m/s   '
                   f'Max: {self.peak_speed:.2f} m/s', C['text'])
        y += 16
        self._line(x, y, f'Tiempo: {self.elapsed_time:.1f} s', C['text'])
        y += 22

        # ── Seguridad ────────────────────────────────────────────────
        pygame.draw.line(self.screen, C['primary'],
                         (x, y), (x + rw, y), 1)
        y += 8
        self._section(x, y, 'EVALUACION DE SEGURIDAD')
        y += 18

        # Verificar si el contrapeso funciona
        if 0.9 <= ratio <= 1.3:
            self._line(x, y, 'OK: Ratio de masas adecuado para contrapeso', C['accent'])
        elif ratio > 1.3:
            self._line(x, y, 'ATENCION: Rescatista mucho mas pesado. '
                       'Descenso rapido.', C['warning'])
        elif ratio < 0.9 and ratio > 0.7:
            self._line(x, y, 'PRECAUCION: Paciente mas pesado. '
                       'Necesita freno adicional.', C['warning'])
        else:
            self._line(x, y, 'PELIGRO: Ratio inadecuado. '
                       'El sistema no funciona como contrapeso.', C['danger'])
        y += 16

        # Velocidad excesiva
        if self.peak_speed > 2.0:
            self._line(x, y, f'ALERTA: Velocidad alta ({self.peak_speed:.1f} m/s). '
                       'Agregar frenado.', C['danger'])
        elif self.peak_speed > 0.5:
            self._line(x, y, f'Velocidad moderada ({self.peak_speed:.1f} m/s). '
                       'Monitorear.', C['warning'])
        else:
            self._line(x, y, 'Velocidad controlada.', C['accent'])
        y += 16

        # Fuerza en redirect
        if f_rn_kn > 10:
            self._line(x, y, f'PELIGRO: Fuerza en redirect {f_rn_kn:.2f} kN. '
                       'Proteger borde.', C['danger'])
        elif f_rn_kn > 5:
            self._line(x, y, f'Fuerza en redirect {f_rn_kn:.2f} kN. '
                       'Usar protector de borde.', C['warning'])
        else:
            self._line(x, y, f'Fuerza en redirect {f_rn_kn:.2f} kN. Aceptable.',
                       C['accent'])
        y += 22

        # ── Notas educativas ─────────────────────────────────────────
        pygame.draw.line(self.screen, C['grid'],
                         (x, y), (x + rw, y), 1)
        y += 8
        self._section(x, y, 'NOTAS EDUCATIVAS')
        y += 18

        notes = [
            'El contrapeso funciona mejor cuando m_rescatista >= m_paciente.',
            'La friccion en el borde ayuda a controlar la velocidad.',
            'Un angulo agudo reduce la fuerza en el redirect pero aumenta friccion.',
            'En la practica se combina con freno o prusik de seguridad.',
            'El rescatista puede agregar/quitar equipo para ajustar masa.',
        ]
        for note in notes:
            self._line(x, y, note, C['dark_text'])
            y += 14

        # ── Formulas ─────────────────────────────────────────────────
        y += 6
        pygame.draw.line(self.screen, C['grid'],
                         (x, y), (x + rw, y), 1)
        y += 6
        formulas = [
            'a = (m1-m2)g / (m1+m2)',
            'T = 2*m1*m2*g / (m1+m2)',
            'Capstan: T1 = T2 * e^(mu*theta)',
            'F_redirect = |T1 + T2| (vectorial)',
        ]
        for f in formulas:
            surf = self.font_formula.render(f, True, C['info'])
            self.screen.blit(surf, (x + 4, y))
            y += 15

    def _section(self, x, y, title):
        """Dibuja un encabezado de seccion."""
        surf = self.font_med.render(f'--- {title} ---', True, C['primary'])
        self.screen.blit(surf, (x, y))

    def _line(self, x, y, text, color):
        """Dibuja una linea de texto en el panel."""
        surf = self.font_sm.render(text, True, color)
        self.screen.blit(surf, (x + 8, y))

    # ── Controles ─────────────────────────────────────────────────────
    def _draw_controls(self):
        """Barra de controles inferior."""
        ctrl_y = HEIGHT - 42
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 8, WIDTH, 50))

        space_label = 'Reiniciar' if (self.released or self.finished) else 'Liberar'
        friction_label = 'ON' if self.friction_on else 'OFF'

        controls = [
            f'[ESPACIO] {space_label}',
            f'[Up/Dn] Rescatista: {self.m_rescuer:.0f}kg',
            f'[W/S] Paciente: {self.m_patient:.0f}kg',
            f'[F] Friccion: {friction_label}',
            f'[Iz/De] Angulo: {self.redirect_angle} deg',
            '[R] Reset',
            '[ESC] Salir',
        ]
        cx = 12
        for ctrl in controls:
            is_fric = 'Friccion: ON' in ctrl
            color = C['secondary'] if is_fric else C['dark_text']
            surf = self.font_xs.render(ctrl, True, color)
            self.screen.blit(surf, (cx, ctrl_y))
            cx += surf.get_width() + 16

    # ── Dibujo principal ──────────────────────────────────────────────
    def draw(self):
        """Renderiza todo el frame."""
        self.screen.fill(C['bg'])

        # Titulo
        title = self.font_title.render(
            'SISTEMA DE CONTRAPESO -- Rescate Tecnico', True, C['primary'])
        self.screen.blit(title,
                         (WIDTH // 2 - title.get_width() // 2, 12))

        # Escena animada (mitad izquierda)
        self._draw_scene()

        # Panel de datos (mitad derecha)
        self._draw_panel()

        # Controles
        self._draw_controls()

        pygame.display.flip()

    # ── Bucle principal ───────────────────────────────────────────────
    def run(self):
        """Bucle principal de la simulacion."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap para estabilidad

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_SPACE:
                        if self.released or self.finished:
                            # Reiniciar posiciones pero mantener parametros
                            self.pos_rescuer = TRAVEL_M * 0.3
                            self.pos_patient = TRAVEL_M * 0.3
                            self.velocity = 0.0
                            self.released = False
                            self.finished = False
                            self.peak_speed = 0.0
                            self.elapsed_time = 0.0
                        else:
                            self.released = True

                    elif event.key == pygame.K_r:
                        self.reset()

                    elif event.key == pygame.K_f:
                        self.friction_on = not self.friction_on

                    elif event.key == pygame.K_UP:
                        self.m_rescuer = min(self.m_rescuer + 5, 120)
                    elif event.key == pygame.K_DOWN:
                        self.m_rescuer = max(self.m_rescuer - 5, 50)

                    elif event.key == pygame.K_w:
                        self.m_patient = min(self.m_patient + 5, 150)
                    elif event.key == pygame.K_s:
                        self.m_patient = max(self.m_patient - 5, 30)

                    elif event.key == pygame.K_LEFT:
                        self.redirect_angle = max(self.redirect_angle - 5, 30)
                    elif event.key == pygame.K_RIGHT:
                        self.redirect_angle = min(self.redirect_angle + 5, 170)

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = CounterbalanceSim()
    sim.run()
