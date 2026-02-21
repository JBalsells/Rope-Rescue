"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 04: Factor de Caída (Pygame)     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación animada del factor de caída y su efecto en la          ║
║  fuerza de choque generada en el sistema.                           ║
║                                                                      ║
║  Factor de caída = distancia de caída / longitud de cuerda          ║
║                                                                      ║
║   FF 0.0: Caída en top-rope (sin caída real)                       ║
║   FF 0.5: Caída moderada (lead con cuerda a mitad)                 ║
║   FF 1.0: Caída al nivel del anclaje                                ║
║   FF 2.0: Caída máxima (factor 2, por encima del anclaje)          ║
║                                                                      ║
║  Controles:                                                          ║
║   [1] FF 0.25  [2] FF 0.5  [3] FF 1.0  [4] FF 2.0                ║
║   [ESPACIO] Iniciar/Reiniciar caída                                 ║
║   [R] Reiniciar                                                      ║
║                                                                      ║
║  Ejecutar:  python 04_factor_de_caida.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import math
import pygame
from config import PG_COLORS as C, G

# ── Configuración de pantalla ─────────────────────────────────────────
WIDTH, HEIGHT = 1280, 800
FPS = 60
SCALE = 40  # píxeles por metro

# ── Parámetros físicos ────────────────────────────────────────────────
CLIMBER_MASS = 80  # kg
ROPE_LENGTH_M = 5  # metros de cuerda disponible (para visualización)


class FallSimulator:
    """Simulador de factor de caída con animación de física."""

    SCENARIOS = {
        pygame.K_1: {'ff': 0.25, 'label': 'FF 0.25 — Caída corta (top-rope con holgura)'},
        pygame.K_2: {'ff': 0.5,  'label': 'FF 0.5  — Caída moderada (lead, mitad de cuerda)'},
        pygame.K_3: {'ff': 1.0,  'label': 'FF 1.0  — Caída al nivel del anclaje'},
        pygame.K_4: {'ff': 2.0,  'label': 'FF 2.0  — Factor 2 (por encima del anclaje)'},
    }

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Física del Rescate — Factor de Caída')
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont('DejaVu Sans', 28, bold=True)
        self.font_med = pygame.font.SysFont('DejaVu Sans', 20)
        self.font_sm = pygame.font.SysFont('DejaVu Sans', 15)
        self.font_title = pygame.font.SysFont('DejaVu Sans', 32, bold=True)

        self.fall_factor = 1.0
        self.scenario_label = self.SCENARIOS[pygame.K_3]['label']
        self.reset()

    def reset(self):
        """Reinicia la simulación al estado inicial."""
        self.rope_len = ROPE_LENGTH_M
        self.fall_distance = self.fall_factor * self.rope_len

        # Posiciones en metros (origen en el anclaje)
        self.anchor_y_m = 0
        # Posición inicial del escalador (negativo = arriba del anclaje)
        if self.fall_factor <= 1.0:
            # Escalador está debajo del anclaje, caerá rope_len * ff
            self.climber_start_m = self.rope_len - self.fall_distance
        else:
            # Escalador está por encima del anclaje
            self.climber_start_m = self.rope_len - self.fall_distance

        self.climber_y_m = self.climber_start_m
        self.climber_end_m = self.rope_len  # posición final (extensión completa)

        self.velocity = 0.0
        self.falling = False
        self.impact = False
        self.impact_force_kN = 0.0
        self.bounce_phase = 0.0
        self.time_since_impact = 0.0
        self.max_force_display = 0.0

    def start_fall(self):
        """Inicia la caída."""
        self.reset()
        self.falling = True
        self.velocity = 0.0

    def update(self, dt):
        """Actualiza la física de la simulación."""
        if not self.falling or self.impact:
            if self.impact:
                self.time_since_impact += dt
                # Oscilación amortiguada post-impacto
                self.bounce_phase += dt * 8
                damping = math.exp(-self.time_since_impact * 3)
                bounce = damping * math.sin(self.bounce_phase) * 0.3
                self.climber_y_m = self.climber_end_m + bounce
            return

        # Caída libre con gravedad
        self.velocity += G * dt
        self.climber_y_m += self.velocity * dt

        # Detectar fin de la caída (cuerda tensa)
        if self.climber_y_m >= self.climber_end_m:
            self.climber_y_m = self.climber_end_m
            self.impact = True

            # Cálculo de fuerza de choque
            # Fórmula simplificada: F = mg(1 + sqrt(1 + 2*ff*k))
            # donde k depende de la elasticidad de la cuerda
            # Para cuerda dinámica: elongación ~35% → k ≈ 5.7
            # Para cuerda estática: elongación ~3% → k ≈ 58
            k_dynamic = 5.7
            k_static = 58.0

            self.impact_force_dynamic_kN = (
                CLIMBER_MASS * G *
                (1 + math.sqrt(1 + 2 * self.fall_factor * k_dynamic))
                / 1000.0
            )
            self.impact_force_static_kN = (
                CLIMBER_MASS * G *
                (1 + math.sqrt(1 + 2 * self.fall_factor * k_static))
                / 1000.0
            )
            self.impact_force_kN = self.impact_force_dynamic_kN
            self.max_force_display = self.impact_force_dynamic_kN

    def m_to_px(self, meters):
        """Convierte metros a píxeles (eje Y)."""
        anchor_px_y = 180
        return anchor_px_y + meters * SCALE

    def draw(self):
        """Renderiza toda la escena."""
        self.screen.fill(C['bg'])

        # ── Título ────────────────────────────────────────────────────
        title = self.font_title.render(
            'FACTOR DE CAÍDA — Simulación Animada', True, C['primary'])
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

        # ── Pared (lado izquierdo) ────────────────────────────────────
        wall_x = 250
        pygame.draw.rect(self.screen, (40, 40, 60),
                         (wall_x - 30, 100, 30, HEIGHT - 150))
        # Textura de la pared
        for y in range(100, HEIGHT - 50, 20):
            pygame.draw.line(self.screen, (55, 55, 75),
                             (wall_x - 30, y), (wall_x, y), 1)

        # ── Anclaje ──────────────────────────────────────────────────
        anchor_px = (wall_x, self.m_to_px(self.anchor_y_m))
        pygame.draw.circle(self.screen, C['anchor'], anchor_px, 12)
        pygame.draw.circle(self.screen, C['warning'], anchor_px, 6)
        lbl = self.font_sm.render('ANCLAJE', True, C['anchor'])
        self.screen.blit(lbl, (anchor_px[0] - 55, anchor_px[1] - 25))

        # ── Cuerda ───────────────────────────────────────────────────
        climber_px_y = self.m_to_px(self.climber_y_m)
        climber_px = (wall_x + 50, int(climber_px_y))

        # Cuerda del anclaje al escalador
        rope_color = C['rope']
        if self.impact:
            # La cuerda se pone roja si hay mucha fuerza
            intensity = min(self.impact_force_kN / 15.0, 1.0)
            rope_color = (
                int(255 * intensity + 255 * (1 - intensity) * 0.65),
                int(167 * (1 - intensity)),
                int(38 * (1 - intensity))
            )

        # Dibujar cuerda (ligeramente curva si no está tensa)
        if not self.impact and self.climber_y_m < self.climber_end_m * 0.9:
            # Cuerda con holgura
            mid_x = wall_x + 25
            mid_y = int((anchor_px[1] + climber_px[1]) / 2 + 20)
            points = [anchor_px, (mid_x, mid_y), climber_px]
            pygame.draw.lines(self.screen, rope_color, False, points, 3)
        else:
            pygame.draw.line(self.screen, rope_color,
                             anchor_px, climber_px, 3)

        # ── Escalador ────────────────────────────────────────────────
        climber_color = C['primary']
        if self.impact:
            climber_color = C['warning']

        # Cuerpo
        head_y = climber_px[1] - 25
        pygame.draw.circle(self.screen, climber_color,
                           (climber_px[0], head_y), 10)
        pygame.draw.line(self.screen, climber_color,
                         (climber_px[0], head_y + 10),
                         (climber_px[0], climber_px[1] + 10), 3)
        # Brazos
        pygame.draw.line(self.screen, climber_color,
                         (climber_px[0] - 15, climber_px[1] - 5),
                         (climber_px[0] + 15, climber_px[1] - 5), 2)
        # Piernas
        pygame.draw.line(self.screen, climber_color,
                         (climber_px[0], climber_px[1] + 10),
                         (climber_px[0] - 10, climber_px[1] + 30), 2)
        pygame.draw.line(self.screen, climber_color,
                         (climber_px[0], climber_px[1] + 10),
                         (climber_px[0] + 10, climber_px[1] + 30), 2)

        # ── Marcadores de distancia ──────────────────────────────────
        start_px_y = self.m_to_px(self.climber_start_m)
        end_px_y = self.m_to_px(self.climber_end_m)

        # Línea de posición inicial
        pygame.draw.line(self.screen, C['accent'],
                         (wall_x + 30, int(start_px_y)),
                         (wall_x + 70, int(start_px_y)), 1)
        lbl = self.font_sm.render('Inicio', True, C['accent'])
        self.screen.blit(lbl, (wall_x + 75, int(start_px_y) - 8))

        # Línea de posición final
        pygame.draw.line(self.screen, C['danger'],
                         (wall_x + 30, int(end_px_y)),
                         (wall_x + 70, int(end_px_y)), 1)
        lbl = self.font_sm.render('Fin caída', True, C['danger'])
        self.screen.blit(lbl, (wall_x + 75, int(end_px_y) - 8))

        # Flechas de distancia de caída
        if abs(end_px_y - start_px_y) > 20:
            arr_x = wall_x + 100
            pygame.draw.line(self.screen, C['warning'],
                             (arr_x, int(start_px_y)),
                             (arr_x, int(end_px_y)), 2)
            pygame.draw.polygon(self.screen, C['warning'], [
                (arr_x, int(start_px_y)),
                (arr_x - 5, int(start_px_y) + 10),
                (arr_x + 5, int(start_px_y) + 10),
            ])
            pygame.draw.polygon(self.screen, C['warning'], [
                (arr_x, int(end_px_y)),
                (arr_x - 5, int(end_px_y) - 10),
                (arr_x + 5, int(end_px_y) - 10),
            ])
            mid_y = int((start_px_y + end_px_y) / 2)
            lbl = self.font_sm.render(
                f'd = {self.fall_distance:.1f} m', True, C['warning'])
            self.screen.blit(lbl, (arr_x + 8, mid_y - 8))

        # Flecha longitud de cuerda
        anchor_to_end_x = wall_x - 60
        pygame.draw.line(self.screen, C['info'],
                         (anchor_to_end_x, self.m_to_px(0)),
                         (anchor_to_end_x, int(end_px_y)), 2)
        mid_rope = int((self.m_to_px(0) + end_px_y) / 2)
        lbl = self.font_sm.render(
            f'L = {self.rope_len:.1f} m', True, C['info'])
        self.screen.blit(lbl, (anchor_to_end_x - 70, mid_rope - 8))

        # ── Panel de información (derecha) ────────────────────────────
        panel_x = 550
        panel_y = 80
        pygame.draw.rect(self.screen, C['panel'],
                         (panel_x - 10, panel_y - 10, 700, 650),
                         border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (panel_x - 10, panel_y - 10, 700, 650),
                         width=1, border_radius=8)

        y = panel_y
        lines = [
            (self.font_big, self.scenario_label, C['primary']),
            (self.font_med, '', None),
            (self.font_med,
             f'Masa del escalador:  {CLIMBER_MASS} kg', C['text']),
            (self.font_med,
             f'Longitud de cuerda:  {self.rope_len:.1f} m', C['info']),
            (self.font_med,
             f'Distancia de caída:  {self.fall_distance:.1f} m', C['warning']),
            (self.font_med, '', None),
            (self.font_big,
             f'Factor de Caída = d/L = {self.fall_factor:.2f}',
             C['warning']),
            (self.font_med, '', None),
        ]

        for font, text, color in lines:
            if text:
                surf = font.render(text, True, color)
                self.screen.blit(surf, (panel_x + 10, y))
            y += font.get_height() + 6

        # Fórmula
        formula = self.font_med.render(
            'FF = distancia_caída / longitud_cuerda', True, C['text'])
        self.screen.blit(formula, (panel_x + 10, y))
        y += 35

        # Resultados de impacto
        if self.impact:
            pygame.draw.line(self.screen, C['grid'],
                             (panel_x + 10, y), (panel_x + 670, y), 1)
            y += 15

            title_imp = self.font_big.render(
                'FUERZAS DE CHOQUE:', True, C['danger'])
            self.screen.blit(title_imp, (panel_x + 10, y))
            y += 40

            # Cuerda dinámica
            surf = self.font_med.render(
                f'Cuerda DINÁMICA (~35% elong.):  '
                f'{self.impact_force_dynamic_kN:.1f} kN',
                True, C['accent'])
            self.screen.blit(surf, (panel_x + 20, y))
            y += 30

            # Cuerda estática
            surf = self.font_med.render(
                f'Cuerda ESTÁTICA (~3% elong.):   '
                f'{self.impact_force_static_kN:.1f} kN',
                True, C['danger'])
            self.screen.blit(surf, (panel_x + 20, y))
            y += 35

            # Barra visual de fuerza
            bar_w = 500
            bar_h = 25

            # Dinámica
            ratio_d = min(self.impact_force_dynamic_kN / 30.0, 1.0)
            pygame.draw.rect(self.screen, (40, 40, 50),
                             (panel_x + 20, y, bar_w, bar_h))
            pygame.draw.rect(self.screen, C['accent'],
                             (panel_x + 20, y, int(bar_w * ratio_d), bar_h))
            lbl = self.font_sm.render('Dinámica', True, C['text'])
            self.screen.blit(lbl, (panel_x + 25, y + 3))
            y += 35

            # Estática
            ratio_s = min(self.impact_force_static_kN / 30.0, 1.0)
            pygame.draw.rect(self.screen, (40, 40, 50),
                             (panel_x + 20, y, bar_w, bar_h))
            danger_col = C['danger'] if ratio_s > 0.5 else C['warning']
            pygame.draw.rect(self.screen, danger_col,
                             (panel_x + 20, y, int(bar_w * ratio_s), bar_h))
            lbl = self.font_sm.render('Estática', True, C['text'])
            self.screen.blit(lbl, (panel_x + 25, y + 3))
            y += 35

            # Línea UIAA
            uiaa_x = panel_x + 20 + int(bar_w * 12.0 / 30.0)
            pygame.draw.line(self.screen, C['danger'],
                             (uiaa_x, y - 75), (uiaa_x, y - 5), 2)
            lbl = self.font_sm.render('UIAA 12kN', True, C['danger'])
            self.screen.blit(lbl, (uiaa_x + 5, y - 50))

            y += 10
            # Mensaje educativo
            if self.impact_force_static_kN > 12.0:
                msg = '⚠ Con cuerda ESTÁTICA la fuerza supera el límite UIAA.'
                msg2 = '  NUNCA usar cuerda estática donde haya posibilidad de caída.'
                surf = self.font_med.render(msg, True, C['danger'])
                self.screen.blit(surf, (panel_x + 10, y))
                y += 25
                surf = self.font_med.render(msg2, True, C['danger'])
                self.screen.blit(surf, (panel_x + 10, y))
        else:
            y += 20
            surf = self.font_med.render(
                'Presiona [ESPACIO] para iniciar la caída',
                True, C['warning'])
            self.screen.blit(surf, (panel_x + 10, y))

        # ── Controles (abajo) ────────────────────────────────────────
        ctrl_y = HEIGHT - 55
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 10, WIDTH, 65))
        controls = [
            '[1] FF 0.25', '[2] FF 0.5', '[3] FF 1.0', '[4] FF 2.0',
            '[ESPACIO] Caída', '[R] Reiniciar', '[ESC] Salir',
        ]
        x = 30
        for ctrl in controls:
            surf = self.font_sm.render(ctrl, True, C['dark_text'])
            self.screen.blit(surf, (x, ctrl_y))
            x += surf.get_width() + 25

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
                        self.start_fall()
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key in self.SCENARIOS:
                        s = self.SCENARIOS[event.key]
                        self.fall_factor = s['ff']
                        self.scenario_label = s['label']
                        self.reset()

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = FallSimulator()
    sim.run()
