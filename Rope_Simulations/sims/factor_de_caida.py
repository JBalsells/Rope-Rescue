"""
╔══════════════════════════════════════════════════════════════════════╗
║       FÍSICA DEL RESCATE · Módulo 04: Factor de Caída (Pygame)     ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación animada del factor de caída y su efecto en la          ║
║  fuerza de choque generada en el sistema.                           ║
║                                                                      ║
║  Modelo de aceleración de frenado:                                   ║
║   v_imp = √(2·g·d)     d = FF·L  (distancia de caída)               ║
║   Δ     = ε·L          (elongación real de la cuerda)               ║
║   a     = v²/(2·Δ) = g·FF/ε     (desaceleración uniforme)          ║
║   F_imp = m·(g + a) = m·g·(1 + FF/ε)                               ║
║                                                                      ║
║   ε dinámica ≈ 35 %  →  mayor elongación = menor fuerza            ║
║   ε estática ≈  3 %  →  menor elongación = mucho mayor fuerza      ║
║   NOTA: F > 30 kN → la cuerda cedería en la realidad               ║
║                                                                      ║
║  Controles:                                                          ║
║   [1] FF 0.25  [2] FF 0.5  [3] FF 1.0  [4] FF 2.0                ║
║   [ESPACIO] Iniciar caída        [R] Reiniciar                      ║
║   [S] Cámara lenta (×0.2)        [P] Pausa                         ║
║   [ESC] Salir                                                        ║
║                                                                      ║
║  Ejecutar:  python 04_factor_de_caida.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import pygame
from config import PG_COLORS as C, G, ROPE_STATIC_MBS

# ── Configuración de pantalla ─────────────────────────────────────────
WIDTH, HEIGHT = 1280, 800
FPS  = 60
SCALE   = 40        # píxeles por metro
WALL_X  = 250
CLIMBER_X = WALL_X + 50

# ── Parámetros físicos ────────────────────────────────────────────────
CLIMBER_MASS  = 100    # kg
ROPE_LENGTH_M = 2      # metros
EPS_DYNAMIC   = 0.35   # elongación cuerda dinámica (~35 %)
EPS_STATIC    = 0.03   # elongación cuerda estática (~3 %)
ROPE_MBS_KN   = ROPE_STATIC_MBS   # MBS cuerda estática (kN) — fuente: config
MAX_TRAIL     = 90     # puntos de la estela
GRAPH_SECONDS = 5.0    # ventana de tiempo del gráfico (segundos simulados)


class FallSimulator:
    """Simulador de factor de caída con animación de física."""

    SCENARIOS = {
        pygame.K_1: {'ff': 0.25, 'label': 'FF 0.25 — Caída corta'},
        pygame.K_2: {'ff': 0.5,  'label': 'FF 0.50 — Caída moderada'},
        pygame.K_3: {'ff': 1.0,  'label': 'FF 1.0  — Nivel del anclaje'},
        pygame.K_4: {'ff': 2.0,  'label': 'FF 2.0  — Factor máximo'},
    }

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Factor de Caída')
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont('DejaVu Sans', 30, bold=True)
        self.font_big   = pygame.font.SysFont('DejaVu Sans', 25, bold=True)
        self.font_med   = pygame.font.SysFont('DejaVu Sans', 18)
        self.font_sm    = pygame.font.SysFont('DejaVu Sans', 14)

        self.fall_factor    = 1.0
        self.scenario_label = self.SCENARIOS[pygame.K_3]['label']
        self.slow_motion    = False
        self.paused         = False
        self.reset()

    # ── Estado ────────────────────────────────────────────────────────

    def reset(self):
        self.rope_len        = ROPE_LENGTH_M
        self.fall_distance   = self.fall_factor * self.rope_len
        self.anchor_y_m      = 0
        self.climber_start_m = self.rope_len - self.fall_distance
        self.climber_y_m     = self.climber_start_m
        self.climber_end_m   = self.rope_len

        margin_top = 90
        self.anchor_px_y = max(180, margin_top + int(-self.climber_start_m * SCALE))

        self.velocity          = 0.0
        self.falling           = False
        self.impact            = False
        self.bounce_phase      = 0.0
        self.time_since_impact = 0.0

        # Resultados del impacto
        self.impact_speed_ms         = 0.0
        self.impact_force_dynamic_kN = 0.0
        self.impact_force_static_kN  = 0.0
        self.impact_force_kN         = 0.0
        self.g_force_dyn             = 0.0
        self.g_force_sta             = 0.0
        self.a_decel_dyn             = 0.0
        self.a_decel_sta             = 0.0
        self.brake_dist_dyn          = 0.0
        self.brake_dist_sta          = 0.0

        # Estela
        self.trail = []

        # Gráfico de tensión en tiempo real
        self.tension_kN      = 0.0
        self.tension_history = []   # [(sim_time, tension_kN), ...]
        self.sim_time        = 0.0

    def start_fall(self):
        self.reset()
        self.falling  = True
        self.velocity = 0.0

    # ── Física ────────────────────────────────────────────────────────

    def _compute_tension(self):
        """
        Tensión analítica de la cuerda dinámica en kN.

        Modelo de oscilación amortiguada post-impacto:
          T(t) = mg + (F_peak − mg) · exp(−3t) · cos(8t)

        Los parámetros b=3, ω=8 coinciden con la oscilación del escalador.
        La cuerda no puede empujar → T se fija en 0 cuando resulta negativa.
        """
        if not self.impact:
            return 0.0
        t     = self.time_since_impact
        mg_kN = CLIMBER_MASS * G / 1000.0
        T = mg_kN + (self.impact_force_dynamic_kN - mg_kN) * math.exp(-3 * t) * math.cos(8 * t)
        return max(0.0, T)

    def update(self, dt):
        if self.paused:
            return

        # Escalar dt antes de usarlo en toda la física
        eff_dt = dt * 0.2 if (self.slow_motion and self.falling and not self.impact) else dt

        # Actualizar tiempo de simulación y tensión
        self.sim_time    += eff_dt
        self.tension_kN   = self._compute_tension()

        # Almacenar historial (ventana deslizante de GRAPH_SECONDS)
        self.tension_history.append((self.sim_time, self.tension_kN))
        cutoff = self.sim_time - GRAPH_SECONDS
        while self.tension_history and self.tension_history[0][0] < cutoff:
            self.tension_history.pop(0)

        if not self.falling or self.impact:
            if self.impact:
                self.time_since_impact += eff_dt
                self.bounce_phase      += eff_dt * 8
                damping = math.exp(-self.time_since_impact * 3)
                bounce  = damping * math.sin(self.bounce_phase) * 0.3
                self.climber_y_m = self.climber_end_m + bounce
            return

        # Caída libre
        self.velocity    += G * eff_dt
        self.climber_y_m += self.velocity * eff_dt

        # Estela
        y_px = self.m_to_px(self.climber_y_m)
        self.trail.append((CLIMBER_X, int(y_px)))
        if len(self.trail) > MAX_TRAIL:
            self.trail.pop(0)

        # Detectar impacto
        if self.climber_y_m >= self.climber_end_m:
            self.climber_y_m = self.climber_end_m
            self.impact      = True

            self.impact_speed_ms = math.sqrt(2 * G * self.fall_distance)

            # F = m·g·(1 + FF/ε)
            self.brake_dist_dyn = EPS_DYNAMIC * self.rope_len
            self.brake_dist_sta = EPS_STATIC  * self.rope_len
            self.a_decel_dyn    = G * self.fall_factor / EPS_DYNAMIC
            self.a_decel_sta    = G * self.fall_factor / EPS_STATIC

            self.impact_force_dynamic_kN = (
                CLIMBER_MASS * G * (1 + self.fall_factor / EPS_DYNAMIC) / 1000.0
            )
            self.impact_force_static_kN = (
                CLIMBER_MASS * G * (1 + self.fall_factor / EPS_STATIC) / 1000.0
            )
            self.impact_force_kN = self.impact_force_dynamic_kN
            self.g_force_dyn = self.impact_force_dynamic_kN * 1000 / (CLIMBER_MASS * G)
            self.g_force_sta = self.impact_force_static_kN  * 1000 / (CLIMBER_MASS * G)

    # ── Coordenadas ───────────────────────────────────────────────────

    def m_to_px(self, meters):
        return self.anchor_px_y + meters * SCALE

    # ── Gráfico de tensión ────────────────────────────────────────────

    def _draw_tension_graph(self):
        """
        Gráfico de tensión de la cuerda en tiempo real.
        Se dibuja como fondo semitransparente en la zona de animación.
        """
        gx, gy   = 15,  415
        gw, gh   = 510, 270
        pad_l, pad_r  = 52, 12
        pad_t, pad_b  = 22, 28

        # Fondo semitransparente
        bg = pygame.Surface((gw, gh), pygame.SRCALPHA)
        bg.fill((10, 10, 25, 200))
        self.screen.blit(bg, (gx, gy))
        pygame.draw.rect(self.screen, C['grid'], (gx, gy, gw, gh), 1)

        # Título
        title_surf = self.font_sm.render(
            'Tensión de la cuerda  (kN)  — tiempo real', True, C['primary'])
        self.screen.blit(title_surf, (gx + pad_l, gy + 4))

        # Área de trazado
        px0 = gx + pad_l
        px1 = gx + gw - pad_r
        py0 = gy + pad_t
        py1 = gy + gh - pad_b
        pw  = px1 - px0
        ph  = py1 - py0

        # Escala Y: máximo automático con margen
        mg_kN       = CLIMBER_MASS * G / 1000.0
        peak_kN     = self.impact_force_dynamic_kN if self.impact else 0.0
        max_y       = max(peak_kN * 1.15, mg_kN * 2.5, 3.0)

        def to_screen(t_val, kn_val):
            """Convierte (tiempo, kN) a píxeles de pantalla."""
            if not self.tension_history:
                return px0, py1
            t_min = self.tension_history[0][0]
            t_max = self.tension_history[-1][0]
            t_span = max(t_max - t_min, 1e-3)
            sx = px0 + int((t_val - t_min) / t_span * pw)
            sy = py1 - int(kn_val / max_y * ph)
            return sx, sy

        # Cuadrícula horizontal
        for kn_ref in [0, mg_kN, 6.0, 9.0, 12.0]:
            if kn_ref > max_y:
                continue
            sy = py1 - int(kn_ref / max_y * ph)
            if kn_ref == 12.0:
                col, lw = C['danger'], 1
            elif abs(kn_ref - mg_kN) < 0.05:
                col, lw = C['accent'],  1
            else:
                col, lw = C['grid'],    1
            pygame.draw.line(self.screen, col, (px0, sy), (px1, sy), lw)
            # Etiqueta eje Y
            lbl = self.font_sm.render(f'{kn_ref:.1f}', True,
                                      C['anchor'] if kn_ref not in (12.0,) else C['danger'])
            self.screen.blit(lbl, (gx + 2, sy - 7))

        # Etiquetas especiales
        mg_sy = py1 - int(mg_kN / max_y * ph)
        self.screen.blit(
            self.font_sm.render(f'mg={mg_kN:.2f}', True, C['accent']),
            (px1 - 62, mg_sy - 14))
        if max_y >= 12.0:
            uiaa_sy = py1 - int(12.0 / max_y * ph)
            self.screen.blit(
                self.font_sm.render('UIAA 12kN', True, C['danger']),
                (px1 - 68, uiaa_sy - 14))

        # Borde del área de trazado
        pygame.draw.rect(self.screen, C['grid'], (px0, py0, pw, ph), 1)

        # Curva de tensión
        if len(self.tension_history) >= 2:
            pts = []
            for t_val, kn_val in self.tension_history:
                sx, sy = to_screen(t_val, kn_val)
                sy = max(py0, min(py1, sy))
                pts.append((sx, sy))
            # Colorear en función de la zona
            for i in range(len(pts) - 1):
                kn_v = self.tension_history[i + 1][1]
                seg_col = (C['accent']  if kn_v < 6.0  else
                           C['warning'] if kn_v < 9.0  else C['danger'])
                pygame.draw.line(self.screen, seg_col, pts[i], pts[i + 1], 2)

        # Punto y valor actual
        if self.tension_history:
            last_t, last_kn = self.tension_history[-1]
            sx, sy = to_screen(last_t, last_kn)
            sy = max(py0, min(py1, sy))
            dot_col = (C['accent']  if last_kn < 6.0  else
                       C['warning'] if last_kn < 9.0  else C['danger'])
            pygame.draw.circle(self.screen, dot_col, (sx, sy), 5)
            val_surf = self.font_sm.render(f'{last_kn:.2f} kN', True, dot_col)
            label_x  = min(sx + 6, px1 - val_surf.get_width() - 2)
            label_y  = max(py0 + 2, sy - 16)
            self.screen.blit(val_surf, (label_x, label_y))

        # Indicador de pico
        if self.impact:
            peak_sy = py1 - int(min(self.impact_force_dynamic_kN, max_y) / max_y * ph)
            peak_sy = max(py0, peak_sy)
            pygame.draw.line(self.screen, (150, 150, 180),
                             (px0, peak_sy), (px1, peak_sy), 1)
            self.screen.blit(
                self.font_sm.render(
                    f'pico {self.impact_force_dynamic_kN:.2f} kN', True, (180, 180, 210)),
                (px0 + 4, peak_sy + 2))

        # Eje X label
        self.screen.blit(
            self.font_sm.render(f'últimos {GRAPH_SECONDS:.0f} s  →', True, C['text']),
            (px0 + pw // 2 - 35, py1 + 8))

    # ── Helpers de dibujo ─────────────────────────────────────────────

    def _narrative(self):
        if not self.falling and not self.impact:
            return 'Elige escenario [1–4]  y  pulsa  [ESPACIO]', C['warning']
        if self.falling and not self.impact:
            if self.velocity < 2.0:
                return 'Caída libre...  ↓  comenzando', C['rope']
            return f'Caída libre  ↓  {self.velocity:.1f} m/s  —  ¡acelerando!', C['danger']
        if self.time_since_impact < 0.5:
            return '¡CUERDA TENSA!  —  absorbiendo el impacto...', C['danger']
        return 'Impacto absorbido  —  oscilando', C['warning']

    def _semaforo_state(self):
        if not self.impact:
            return None
        if self.impact_force_dynamic_kN < 6.0:
            return 'green'
        if self.impact_force_dynamic_kN < 9.0:
            return 'yellow'
        return 'red'

    def _draw_semaforo(self, cx, top_y):
        r, spacing = 13, 34
        fw, fh = 38, spacing * 3 + 18
        pygame.draw.rect(self.screen, (25, 25, 35),
                         (cx - fw // 2, top_y, fw, fh), border_radius=6)
        pygame.draw.rect(self.screen, C['grid'],
                         (cx - fw // 2, top_y, fw, fh), width=1, border_radius=6)
        state  = self._semaforo_state()
        lights = [
            ('red',    top_y + spacing * 0 + 18, C['danger'],  (70, 15, 15)),
            ('yellow', top_y + spacing * 1 + 18, C['warning'], (55, 45,  8)),
            ('green',  top_y + spacing * 2 + 18, C['accent'],  (12, 45, 15)),
        ]
        for name, ly, bright, dim in lights:
            pygame.draw.circle(self.screen, bright if state == name else dim, (cx, ly), r)
        labels = {'green': ('SEGURO', C['accent']), 'yellow': ('PRECAUCIÓN', C['warning']),
                  'red': ('PELIGROSO', C['danger']), None: ('EN ESPERA', C['grid'])}
        lbl_txt, lbl_col = labels[state]
        surf = self.font_sm.render(lbl_txt, True, lbl_col)
        self.screen.blit(surf, (cx - surf.get_width() // 2, top_y + fh + 4))

    def _draw_tabla(self, x, y):
        surf = self.font_sm.render('COMPARATIVA DE ESCENARIOS:', True, C['primary'])
        self.screen.blit(surf, (x, y));  y += 20
        headers = ['Escenario', 'FF', 'v (km/h)', 'F.din.(kN)', 'F.est.(kN)', 'Estado']
        col_x   = [x, x + 150, x + 210, x + 295, x + 385, x + 465]
        for i, h in enumerate(headers):
            self.screen.blit(self.font_sm.render(h, True, C['anchor']), (col_x[i], y))
        y += 17
        pygame.draw.line(self.screen, C['grid'], (x, y), (x + 545, y), 1)
        y += 5

        for ff, lbl in [(0.25, 'FF 0.25 corta'),
                        (0.5,  'FF 0.50 mod.'),
                        (1.0,  'FF 1.0  ancl.'),
                        (2.0,  'FF 2.0  max.')]:
            fd      = ROPE_LENGTH_M * ff
            vel_kmh = math.sqrt(2 * G * fd) * 3.6
            f_dyn   = CLIMBER_MASS * G * (1 + ff / EPS_DYNAMIC) / 1000
            f_sta   = CLIMBER_MASS * G * (1 + ff / EPS_STATIC)  / 1000
            is_cur  = abs(ff - self.fall_factor) < 0.01
            row_col = C['warning'] if is_cur else C['text']
            prefix  = '→ ' if is_cur else '  '
            c_dyn   = C['accent'] if f_dyn < 6 else C['warning'] if f_dyn < 9 else C['danger']
            # Estado cuerda estática
            if f_sta > ROPE_MBS_KN:
                c_sta  = C['danger']
                estado = 'ROMPE'
            elif f_sta > 12.0:
                c_sta  = C['danger']
                estado = 'UIAA!'
            else:
                c_sta  = C['accent']
                estado = 'OK'

            cells  = [f'{prefix}{lbl}', f'{ff:.2f}', f'{vel_kmh:.1f}',
                      f'{f_dyn:.2f}',   f'{f_sta:.2f}', estado]
            colors = [row_col, row_col, row_col, c_dyn, c_sta,
                      C['danger'] if estado in ('ROMPE', 'UIAA!') else C['accent']]
            for i, (cell, col) in enumerate(zip(cells, colors)):
                self.screen.blit(self.font_sm.render(cell, True, col), (col_x[i], y))
            y += 18
        return y

    # ── Renderizado ───────────────────────────────────────────────────

    def draw(self):
        self.screen.fill(C['bg'])

        # ── Título ────────────────────────────────────────────────────
        surf = self.font_title.render(
            'FACTOR DE CAÍDA — Simulación Animada', True, C['primary'])
        self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 12))

        # ── Modos ─────────────────────────────────────────────────────
        if self.slow_motion:
            self.screen.blit(
                self.font_sm.render('● CÁMARA LENTA  ×0.2', True, C['info']), (20, 52))
        if self.paused:
            surf = self.font_big.render('⏸  PAUSADO', True, C['warning'])
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 52))

        # ── Pared ─────────────────────────────────────────────────────
        wall_top = max(60, self.anchor_px_y - 120)
        pygame.draw.rect(self.screen, (40, 40, 60),
                         (WALL_X - 30, wall_top, 30, HEIGHT - wall_top - 50))
        for wy in range(wall_top, HEIGHT - 50, 20):
            pygame.draw.line(self.screen, (55, 55, 75), (WALL_X - 30, wy), (WALL_X, wy), 1)

        # ── Anclaje ───────────────────────────────────────────────────
        anchor_px = (WALL_X, int(self.m_to_px(self.anchor_y_m)))
        pygame.draw.circle(self.screen, C['anchor'], anchor_px, 12)
        pygame.draw.circle(self.screen, C['warning'], anchor_px, 6)
        self.screen.blit(
            self.font_sm.render('ANCLAJE', True, C['anchor']),
            (anchor_px[0] - 55, anchor_px[1] - 25))

        # ── Estela ────────────────────────────────────────────────────
        n = len(self.trail)
        rope_rgb, dim_rgb = C['rope'], (50, 30, 8)
        for i, (tx, ty) in enumerate(self.trail):
            ratio = i / max(n - 1, 1)
            col   = tuple(int(dim_rgb[c] + ratio * (rope_rgb[c] - dim_rgb[c])) for c in range(3))
            pygame.draw.circle(self.screen, col, (tx, ty), max(1, int(ratio * 3)))

        # ── Cuerda ────────────────────────────────────────────────────
        climber_px_y = self.m_to_px(self.climber_y_m)
        climber_px   = (CLIMBER_X, int(climber_px_y))
        rope_color   = C['rope']
        if self.impact:
            intensity  = min(self.impact_force_kN / 15.0, 1.0)
            rope_color = (
                int(255 * intensity + 255 * (1 - intensity) * 0.65),
                int(167 * (1 - intensity)),
                int(38  * (1 - intensity)),
            )
        # Curva suave: se arquea cuando hay cuerda floja, recta al tensarse
        dist    = math.hypot(climber_px[0] - anchor_px[0],
                             climber_px[1] - anchor_px[1])
        rope_px = self.rope_len * SCALE
        slack   = max(0.0, rope_px - dist)
        bow     = min(slack * 0.7, 80)
        mx = (anchor_px[0] + climber_px[0]) / 2 + bow * 0.45   # hacia afuera
        my = (anchor_px[1] + climber_px[1]) / 2 + bow          # hacia abajo
        rope_pts = []
        for i in range(25):
            t = i / 24.0
            u = 1.0 - t
            rope_pts.append((
                u * u * anchor_px[0] + 2 * u * t * mx + t * t * climber_px[0],
                u * u * anchor_px[1] + 2 * u * t * my + t * t * climber_px[1]))
        pygame.draw.lines(self.screen, rope_color, False,
                          [(int(a), int(b)) for a, b in rope_pts], 4)
        pygame.draw.aalines(self.screen, rope_color, False, rope_pts)

        # Velocidad junto al escalador durante la caída
        if self.falling and not self.impact and self.velocity > 0.5:
            self.screen.blit(
                self.font_sm.render(
                    f'↓ {self.velocity:.1f} m/s  ({self.velocity * 3.6:.0f} km/h)',
                    True, C['danger']),
                (CLIMBER_X + 22, int(climber_px_y) - 12))

        # ── Escalador (figura con casco, articulaciones redondeadas) ──
        climber_color = C['primary'] if not self.impact else C['warning']
        helmet = C['secondary'] if not self.impact else C['danger']
        cx, cy = climber_px[0], climber_px[1]
        hip  = (cx, cy + 2)
        sh   = (cx, cy - 16)
        head = (cx, cy - 30)

        # Torso grueso y redondeado
        pygame.draw.line(self.screen, climber_color, sh, hip, 6)
        pygame.draw.circle(self.screen, climber_color, sh, 3)
        pygame.draw.circle(self.screen, climber_color, hip, 4)

        # Brazos en pose de caída (hacia arriba), con codo y mano
        for sgn in (-1, 1):
            elbow = (cx + sgn * 11, cy - 11)
            hand  = (cx + sgn * 16, cy - 26)
            pygame.draw.lines(self.screen, climber_color, False, [sh, elbow, hand], 4)
            pygame.draw.circle(self.screen, climber_color, hand, 3)

        # Piernas ligeramente flexionadas, con rodilla y pie
        for sgn in (-1, 1):
            knee = (cx + sgn * 7, cy + 17)
            foot = (cx + sgn * 12, cy + 31)
            pygame.draw.lines(self.screen, climber_color, False, [hip, knee, foot], 4)
            pygame.draw.circle(self.screen, climber_color, foot, 3)

        # Cabeza + casco (domo superior)
        pygame.draw.circle(self.screen, climber_color, head, 9)
        pygame.draw.circle(self.screen, helmet, (head[0], head[1] - 1), 9,
                           0, draw_top_left=True, draw_top_right=True)

        # ── Marcadores de distancia ────────────────────────────────────
        start_px_y = self.m_to_px(self.climber_start_m)
        end_px_y   = self.m_to_px(self.climber_end_m)
        pygame.draw.line(self.screen, C['accent'],
                         (WALL_X + 30, int(start_px_y)), (WALL_X + 70, int(start_px_y)), 1)
        self.screen.blit(self.font_sm.render('Inicio', True, C['accent']),
                         (WALL_X + 75, int(start_px_y) - 8))
        pygame.draw.line(self.screen, C['danger'],
                         (WALL_X + 30, int(end_px_y)), (WALL_X + 70, int(end_px_y)), 1)
        self.screen.blit(self.font_sm.render('Fin caída', True, C['danger']),
                         (WALL_X + 75, int(end_px_y) - 8))
        if abs(end_px_y - start_px_y) > 20:
            ax = WALL_X + 105
            pygame.draw.line(self.screen, C['warning'],
                             (ax, int(start_px_y)), (ax, int(end_px_y)), 2)
            pygame.draw.polygon(self.screen, C['warning'], [
                (ax, int(start_px_y)), (ax-5, int(start_px_y)+10), (ax+5, int(start_px_y)+10)])
            pygame.draw.polygon(self.screen, C['warning'], [
                (ax, int(end_px_y)), (ax-5, int(end_px_y)-10), (ax+5, int(end_px_y)-10)])
            mid_y = int((start_px_y + end_px_y) / 2)
            self.screen.blit(
                self.font_sm.render(f'd = {self.fall_distance:.1f} m', True, C['warning']),
                (ax + 10, mid_y - 8))
        rope_ax = WALL_X - 60
        pygame.draw.line(self.screen, C['info'],
                         (rope_ax, int(self.m_to_px(0))), (rope_ax, int(end_px_y)), 2)
        mid_rope = int((self.m_to_px(0) + end_px_y) / 2)
        self.screen.blit(self.font_sm.render(f'L = {self.rope_len:.1f} m', True, C['info']),
                         (rope_ax - 70, mid_rope - 8))

        # ── Gráfico de tensión (encima de la pared, semitransparente) ──
        self._draw_tension_graph()

        # ── Texto narrativo ────────────────────────────────────────────
        narr_txt, narr_col = self._narrative()
        narr_surf = self.font_med.render(narr_txt, True, narr_col)
        narr_x    = max(10, (450 - narr_surf.get_width()) // 2)
        bg_narr   = pygame.Surface((narr_surf.get_width() + 18, narr_surf.get_height() + 10),
                                   pygame.SRCALPHA)
        bg_narr.fill((15, 15, 26, 190))
        self.screen.blit(bg_narr,   (narr_x - 9,  HEIGHT - 112))
        self.screen.blit(narr_surf, (narr_x,      HEIGHT - 107))

        # ── Panel de información ───────────────────────────────────────
        panel_x, panel_y = 555, 75
        panel_w, panel_h = 710, 650
        pygame.draw.rect(self.screen, C['panel'],
                         (panel_x - 10, panel_y - 10, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (panel_x - 10, panel_y - 10, panel_w, panel_h), width=1, border_radius=8)

        sem_cx = panel_x + panel_w - 65
        self._draw_semaforo(sem_cx, panel_y)

        y = panel_y

        self.screen.blit(
            self.font_big.render(self.scenario_label, True, C['primary']),
            (panel_x + 10, y))
        y += self.font_big.get_height() + 8

        self.screen.blit(
            self.font_med.render(
                f'Masa: {CLIMBER_MASS} kg   ·   Cuerda: {self.rope_len:.1f} m'
                f'   ·   Caída: {self.fall_distance:.1f} m', True, C['text']),
            (panel_x + 10, y))
        y += self.font_med.get_height() + 6

        ff_col = (C['accent'] if self.fall_factor < 0.5 else
                  C['warning'] if self.fall_factor < 1.5 else C['danger'])
        self.screen.blit(
            self.font_big.render(
                f'Factor de Caída  =  d / L  =  {self.fall_factor:.2f}', True, ff_col),
            (panel_x + 10, y))
        y += self.font_big.get_height() + 4

        for line in ['FF = distancia_caída / longitud_cuerda',
                     'F  = m·g·(1 + FF/ε)   |   ε: elongación de la cuerda']:
            self.screen.blit(self.font_sm.render(line, True, C['text']), (panel_x + 15, y))
            y += self.font_sm.get_height() + 3
        y += 4

        pygame.draw.line(self.screen, C['grid'],
                         (panel_x + 5, y), (panel_x + panel_w - 25, y), 1)
        y += 10

        if self.impact:
            vel_kmh = self.impact_speed_ms * 3.6

            # Velocidad de impacto
            self.screen.blit(
                self.font_med.render(
                    f'Velocidad de impacto:  {self.impact_speed_ms:.2f} m/s'
                    f'  ({vel_kmh:.1f} km/h)', True, C['info']),
                (panel_x + 10, y))
            y += self.font_med.get_height() + 4

            # Distancia de frenado
            self.screen.blit(
                self.font_sm.render(
                    f'Dist. frenado:  din. {self.brake_dist_dyn*100:.1f} cm'
                    f'   |   est. {self.brake_dist_sta*100:.1f} cm   (= ε·L)',
                    True, C['text']),
                (panel_x + 15, y))
            y += self.font_sm.get_height() + 5

            # Aceleración de frenado
            a_col = (C['accent'] if self.a_decel_dyn < 30 else
                     C['warning'] if self.a_decel_dyn < 80 else C['danger'])
            self.screen.blit(
                self.font_med.render(
                    f'Acel. frenado:  din. {self.a_decel_dyn:.1f} m/s²'
                    f' ({self.a_decel_dyn/G:.1f} g)'
                    f'   |   est. {self.a_decel_sta:.1f} m/s²'
                    f' ({self.a_decel_sta/G:.1f} g)',
                    True, a_col),
                (panel_x + 10, y))
            y += self.font_med.get_height() + 5

            # Fuerzas (separadas: kN por un lado, kg por otro)
            equiv_kg_dyn = self.impact_force_dynamic_kN * 1000 / G
            self.screen.blit(
                self.font_med.render(
                    f'Cuerda DINÁMICA:  {self.impact_force_dynamic_kN:.2f} kN'
                    f'  ({equiv_kg_dyn:.0f} kg equiv.)',
                    True, C['accent']),
                (panel_x + 10, y))
            y += self.font_med.get_height() + 4

            # Cuerda estática: mostrar aviso si supera MBS
            f_sta = self.impact_force_static_kN
            if f_sta > ROPE_MBS_KN:
                sta_label = (f'Cuerda ESTÁTICA:  {f_sta:.2f} kN'
                             f'  ← SUPERA MBS ({ROPE_MBS_KN:.0f} kN) — LA CUERDA CEDERÍA')
                sta_col   = C['danger']
            else:
                equiv_kg_sta = f_sta * 1000 / G
                sta_label = (f'Cuerda ESTÁTICA:  {f_sta:.2f} kN'
                             f'  ({equiv_kg_sta:.0f} kg equiv.)')
                sta_col   = C['danger'] if f_sta > 12 else C['warning']
            self.screen.blit(self.font_med.render(sta_label, True, sta_col), (panel_x + 10, y))
            y += self.font_med.get_height() + 5

            # Fuerzas G
            g_col = (C['accent'] if self.g_force_dyn < 5 else
                     C['warning'] if self.g_force_dyn < 10 else C['danger'])
            self.screen.blit(
                self.font_med.render(
                    f'Fuerzas G:  din. {self.g_force_dyn:.1f} g   '
                    f'|  est. {self.g_force_sta:.1f} g   '
                    f'[lesión grave > ~20 g]',
                    True, g_col),
                (panel_x + 10, y))
            y += self.font_med.get_height() + 8

            pygame.draw.line(self.screen, C['grid'],
                             (panel_x + 5, y), (panel_x + panel_w - 25, y), 1)
            y += 10

            # Barras de fuerza (escala 0–30 kN = MBS)
            bar_w, bar_h = 500, 22
            bar1_y = y
            ratio_d = min(self.impact_force_dynamic_kN / ROPE_MBS_KN, 1.0)
            pygame.draw.rect(self.screen, (40, 40, 50), (panel_x + 20, bar1_y, bar_w, bar_h))
            pygame.draw.rect(self.screen, C['accent'],
                             (panel_x + 20, bar1_y, int(bar_w * ratio_d), bar_h))
            self.screen.blit(
                self.font_sm.render(
                    f'Din: {self.impact_force_dynamic_kN:.2f} kN', True, C['text']),
                (panel_x + 25, bar1_y + 3))

            bar2_y = bar1_y + bar_h + 8
            ratio_s    = min(self.impact_force_static_kN / ROPE_MBS_KN, 1.0)
            danger_col = C['danger'] if self.impact_force_static_kN > 12 else C['warning']
            pygame.draw.rect(self.screen, (40, 40, 50), (panel_x + 20, bar2_y, bar_w, bar_h))
            pygame.draw.rect(self.screen, danger_col,
                             (panel_x + 20, bar2_y, int(bar_w * ratio_s), bar_h))
            self.screen.blit(
                self.font_sm.render(
                    f'Est: {self.impact_force_static_kN:.2f} kN'
                    + ('  ← EXCEDE MBS' if self.impact_force_static_kN > ROPE_MBS_KN else ''),
                    True, C['text']),
                (panel_x + 25, bar2_y + 3))

            # Líneas de referencia sobre las barras
            for kn_ref, label, col in [(12.0, 'UIAA 12kN', C['danger']),
                                       (ROPE_MBS_KN, f'MBS {ROPE_MBS_KN:.0f}kN', (180, 60, 60))]:
                rx = panel_x + 20 + int(bar_w * kn_ref / ROPE_MBS_KN)
                pygame.draw.line(self.screen, col, (rx, bar1_y), (rx, bar2_y + bar_h), 2)
                self.screen.blit(self.font_sm.render(label, True, col),
                                 (rx + 3, bar1_y + 1))

            y = bar2_y + bar_h + 10
            pygame.draw.line(self.screen, C['grid'],
                             (panel_x + 5, y), (panel_x + panel_w - 25, y), 1)
            y += 8
            self._draw_tabla(panel_x + 10, y)

        else:
            self.screen.blit(
                self.font_med.render(
                    'Presiona [ESPACIO] para iniciar la caída', True, C['warning']),
                (panel_x + 10, y))

        # ── Controles ─────────────────────────────────────────────────
        ctrl_y = HEIGHT - 55
        pygame.draw.rect(self.screen, C['panel'], (0, ctrl_y - 10, WIDTH, 65))
        controls = [
            '[1] FF 0.25', '[2] FF 0.5', '[3] FF 1.0', '[4] FF 2.0',
            '[ESPACIO] Caída', '[R] Reiniciar',
            '[S] Cám. lenta' if not self.slow_motion else '[S] Vel. normal',
            '[P] Pausa', '[ESC] Salir',
        ]
        x = 20
        for ctrl in controls:
            surf = self.font_sm.render(ctrl, True, C['dark_text'])
            self.screen.blit(surf, (x, ctrl_y))
            x += surf.get_width() + 20

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
                        if not self.paused:
                            self.start_fall()
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_s:
                        self.slow_motion = not self.slow_motion
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key in self.SCENARIOS:
                        s = self.SCENARIOS[event.key]
                        self.fall_factor    = s['ff']
                        self.scenario_label = s['label']
                        self.reset()
            self.update(dt)
            self.draw()
        pygame.quit()


from registry import simulation


@simulation(backend='pygame', order=6,
            title='Factor de caída (animado)',
            description='Fuerza de choque: dinámica vs estática.')
def main():
    """Punto de entrada uniforme para el framework / launcher."""
    FallSimulator().run()


if __name__ == '__main__':
    main()
