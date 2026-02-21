"""
╔══════════════════════════════════════════════════════════════════════╗
║   FÍSICA DEL RESCATE · Módulo 06: Ventaja Mecánica y Poleas        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Simulación animada (Pygame) de sistemas de poleas utilizados       ║
║  en rescate con cuerdas: 1:1, 2:1, 3:1 (Z-rig) y 4:1.            ║
║                                                                      ║
║  Conceptos:                                                          ║
║   • VM = Carga / Fuerza aplicada                                    ║
║   • A mayor VM, menos fuerza necesaria pero más cuerda se tira     ║
║   • Poleas redireccionan (cambian dirección) o multiplican fuerza  ║
║   • Eficiencia real: ~90% por polea (fricción)                     ║
║                                                                      ║
║  Controles:                                                          ║
║   [1] Sistema 1:1  [2] Sistema 2:1  [3] Z-rig 3:1  [4] 4:1       ║
║   [ESPACIO] Tirar / Soltar   [F] Modo fricción ON/OFF              ║
║   [↑/↓] Ajustar carga                                              ║
║                                                                      ║
║  Ejecutar:  python 06_ventaja_mecanica_poleas.py                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import math
import pygame
from config import PG_COLORS as C, G

WIDTH, HEIGHT = 1280, 800
FPS = 60


class PulleySystem:
    """Visualización de un sistema de poleas específico."""

    def __init__(self, name, vm, description, diagram_func):
        self.name = name
        self.vm = vm
        self.description = description
        self.draw_diagram = diagram_func


class PulleySimulator:
    """Simulador interactivo de sistemas de poleas."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Física del Rescate — Ventaja Mecánica')
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont('DejaVu Sans', 26, bold=True)
        self.font_med = pygame.font.SysFont('DejaVu Sans', 18)
        self.font_sm = pygame.font.SysFont('DejaVu Sans', 14)
        self.font_title = pygame.font.SysFont('DejaVu Sans', 30, bold=True)

        self.load_kg = 100
        self.current_system = 0
        self.pulling = False
        self.pull_offset = 0.0
        self.friction_mode = False
        self.pulley_efficiency = 0.90  # 90% por polea

        self.systems = [
            {'name': '1:1 — Redirección Simple',
             'vm': 1, 'pulleys': 1,
             'desc': 'Solo cambia la dirección de la fuerza.\n'
                     'No hay ventaja mecánica.\n'
                     'Útil para redirigir desde un borde.'},
            {'name': '2:1 — Simple con Polea Móvil',
             'vm': 2, 'pulleys': 1,
             'desc': 'La polea se mueve con la carga.\n'
                     'Se necesita la mitad de la fuerza,\n'
                     'pero se tira el doble de cuerda.'},
            {'name': '3:1 — Z-Rig (Sistema Z)',
             'vm': 3, 'pulleys': 2,
             'desc': 'El sistema más usado en rescate.\n'
                     'Combina polea fija y móvil.\n'
                     'Se necesita un tercio de la fuerza.'},
            {'name': '4:1 — Compuesto',
             'vm': 4, 'pulleys': 2,
             'desc': 'Sistema compuesto 2:1 sobre 2:1.\n'
                     'Eficiente para cargas pesadas.\n'
                     'Se necesita un cuarto de la fuerza.'},
        ]

    def draw_pulley(self, x, y, radius=18, fixed=True):
        """Dibuja una polea (fija o móvil)."""
        color = C['anchor'] if fixed else C['primary']
        pygame.draw.circle(self.screen, color, (x, y), radius, 3)
        pygame.draw.circle(self.screen, color, (x, y), 4)
        if fixed:
            # Soporte de anclaje
            pygame.draw.line(self.screen, C['anchor'],
                             (x, y - radius), (x, y - radius - 15), 3)
            pygame.draw.rect(self.screen, C['anchor'],
                             (x - 10, y - radius - 20, 20, 8))

    def draw_load(self, x, y, label=''):
        """Dibuja la carga (bloque con peso)."""
        w, h = 60, 50
        pygame.draw.rect(self.screen, C['danger'],
                         (x - w // 2, y, w, h), border_radius=5)
        pygame.draw.rect(self.screen, C['text'],
                         (x - w // 2, y, w, h), width=2, border_radius=5)
        surf = self.font_sm.render(label, True, C['text'])
        self.screen.blit(surf, (x - surf.get_width() // 2, y + 15))

    def draw_force_arrow(self, x, y, direction, force_kn, label=''):
        """Dibuja una flecha de fuerza con etiqueta."""
        length = min(force_kn * 15, 120)
        dx, dy = 0, 0
        if direction == 'down':
            dy = length
        elif direction == 'up':
            dy = -length
        elif direction == 'left':
            dx = -length
        elif direction == 'right':
            dx = length

        end_x, end_y = x + dx, y + dy
        pygame.draw.line(self.screen, C['warning'],
                         (x, y), (int(end_x), int(end_y)), 3)

        # Punta de flecha
        if direction == 'down':
            pygame.draw.polygon(self.screen, C['warning'], [
                (int(end_x), int(end_y)),
                (int(end_x) - 6, int(end_y) - 12),
                (int(end_x) + 6, int(end_y) - 12),
            ])
        elif direction == 'up':
            pygame.draw.polygon(self.screen, C['warning'], [
                (int(end_x), int(end_y)),
                (int(end_x) - 6, int(end_y) + 12),
                (int(end_x) + 6, int(end_y) + 12),
            ])

        # Etiqueta
        surf = self.font_sm.render(f'{force_kn:.2f} kN', True, C['warning'])
        if direction in ('down', 'up'):
            self.screen.blit(surf, (x + 15, (y + end_y) // 2 - 8))

    def draw_system_1_1(self, base_x, base_y, pull_anim):
        """Dibuja sistema 1:1 (redirección simple)."""
        pulley_x, pulley_y = base_x, base_y
        load_x, load_y = base_x, base_y + 200 - pull_anim * 20
        pull_x = base_x + 120

        # Cuerda
        pygame.draw.line(self.screen, C['rope'],
                         (load_x, load_y), (pulley_x, pulley_y + 18), 3)
        pygame.draw.line(self.screen, C['rope'],
                         (pulley_x, pulley_y + 18),
                         (pull_x, pulley_y + 80 + pull_anim * 20), 3)

        self.draw_pulley(pulley_x, pulley_y, fixed=True)
        self.draw_load(load_x, load_y, f'{self.load_kg}kg')

        return pull_x, pulley_y + 80 + pull_anim * 20

    def draw_system_2_1(self, base_x, base_y, pull_anim):
        """Dibuja sistema 2:1 (polea móvil)."""
        anchor_x, anchor_y = base_x, base_y
        pulley_y = base_y + 180 - pull_anim * 20
        load_x = base_x
        pull_x = base_x + 40

        # Anclaje fijo (punto de amarre)
        pygame.draw.rect(self.screen, C['anchor'],
                         (anchor_x - 10, anchor_y - 5, 20, 10))

        # Cuerda: del anclaje, baja a la polea móvil, sube al tirador
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x, anchor_y), (load_x, pulley_y), 3)
        pygame.draw.line(self.screen, C['rope'],
                         (load_x, pulley_y),
                         (pull_x + 80, anchor_y + pull_anim * 20), 3)

        self.draw_pulley(load_x, pulley_y, fixed=False)
        self.draw_load(load_x, pulley_y + 18, f'{self.load_kg}kg')

        return pull_x + 80, anchor_y + pull_anim * 20

    def draw_system_3_1(self, base_x, base_y, pull_anim):
        """Dibuja sistema 3:1 Z-rig."""
        anchor_x = base_x
        anchor_y = base_y

        load_y = base_y + 220 - pull_anim * 20
        mid_y = base_y + 110 - pull_anim * 10

        # Polea fija arriba
        self.draw_pulley(anchor_x, anchor_y, fixed=True)

        # Carga abajo
        self.draw_load(anchor_x, load_y, f'{self.load_kg}kg')

        # Cuerda de carga sube a polea fija
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x, load_y), (anchor_x, anchor_y + 18), 3)

        # De polea fija baja a polea móvil (prusik en la cuerda)
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x, anchor_y + 18),
                         (anchor_x + 60, mid_y), 3)

        # Polea móvil (en el prusik)
        self.draw_pulley(anchor_x + 60, mid_y, fixed=False)

        # Prusik indicator
        pygame.draw.rect(self.screen, C['secondary'],
                         (anchor_x + 48, mid_y - 8, 24, 16), border_radius=3)
        surf = self.font_sm.render('P', True, C['text'])
        self.screen.blit(surf, (anchor_x + 55, mid_y - 6))

        # De polea móvil sube al tirador
        pull_end_y = anchor_y - 30 + pull_anim * 20
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x + 60, mid_y),
                         (anchor_x + 120, pull_end_y), 3)

        return anchor_x + 120, pull_end_y

    def draw_system_4_1(self, base_x, base_y, pull_anim):
        """Dibuja sistema 4:1 compuesto."""
        anchor_x = base_x
        anchor_y = base_y

        load_y = base_y + 250 - pull_anim * 20

        # Polea fija superior
        self.draw_pulley(anchor_x, anchor_y, fixed=True)

        # Polea móvil inferior (con la carga)
        pm1_y = base_y + 160 - pull_anim * 15
        self.draw_pulley(anchor_x, pm1_y, fixed=False)

        # Polea fija secundaria
        pf2_x = anchor_x + 80
        self.draw_pulley(pf2_x, anchor_y + 40, fixed=True)

        # Polea móvil secundaria
        pm2_y = base_y + 80 - pull_anim * 10
        self.draw_pulley(pf2_x, pm2_y, fixed=False)

        # Carga
        self.draw_load(anchor_x, pm1_y + 18, f'{self.load_kg}kg')

        # Cuerdas
        # Primer 2:1
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x, anchor_y + 18), (anchor_x, pm1_y - 18), 3)
        pygame.draw.line(self.screen, C['rope'],
                         (anchor_x, pm1_y - 18), (pf2_x, anchor_y + 58), 3)

        # Segundo 2:1
        pygame.draw.line(self.screen, C['rope'],
                         (pf2_x, anchor_y + 58), (pf2_x, pm2_y - 18), 3)
        pull_end_y = anchor_y - 20 + pull_anim * 20
        pygame.draw.line(self.screen, C['rope'],
                         (pf2_x, pm2_y - 18),
                         (pf2_x + 80, pull_end_y), 3)

        return pf2_x + 80, pull_end_y

    def draw(self):
        """Renderiza la escena completa."""
        self.screen.fill(C['bg'])

        # Título
        title = self.font_title.render(
            'VENTAJA MECÁNICA — Sistemas de Poleas', True, C['primary'])
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

        sys_data = self.systems[self.current_system]
        vm = sys_data['vm']
        n_pulleys = sys_data['pulleys']

        # ── Dibujar el sistema de poleas ──────────────────────────────
        base_x, base_y = 300, 150
        pull_anim = self.pull_offset

        draw_funcs = [
            self.draw_system_1_1,
            self.draw_system_2_1,
            self.draw_system_3_1,
            self.draw_system_4_1,
        ]
        pull_pos = draw_funcs[self.current_system](base_x, base_y, pull_anim)

        # Mano del tirador
        hand_x, hand_y = int(pull_pos[0]), int(pull_pos[1])
        pygame.draw.circle(self.screen, C['warning'], (hand_x, hand_y), 8)
        surf = self.font_sm.render('TIRAR', True, C['warning'])
        self.screen.blit(surf, (hand_x + 15, hand_y - 8))

        # ── Panel de información ──────────────────────────────────────
        panel_x = 620
        panel_y = 80
        pygame.draw.rect(self.screen, C['panel'],
                         (panel_x - 10, panel_y - 10, 650, 620),
                         border_radius=8)
        pygame.draw.rect(self.screen, C['primary'],
                         (panel_x - 10, panel_y - 10, 650, 620),
                         width=1, border_radius=8)

        y = panel_y
        # Nombre del sistema
        surf = self.font_big.render(sys_data['name'], True, C['primary'])
        self.screen.blit(surf, (panel_x + 10, y))
        y += 40

        # Descripción
        for line in sys_data['desc'].split('\n'):
            surf = self.font_med.render(line, True, C['text'])
            self.screen.blit(surf, (panel_x + 10, y))
            y += 25
        y += 15

        # Cálculos
        load_kn = self.load_kg * G / 1000.0
        ideal_force = load_kn / vm

        # Con fricción
        eff = self.pulley_efficiency ** n_pulleys if self.friction_mode else 1.0
        real_force = load_kn / (vm * eff) if eff > 0 else load_kn

        pygame.draw.line(self.screen, C['grid'],
                         (panel_x + 10, y), (panel_x + 620, y), 1)
        y += 15

        data_lines = [
            (f'Carga:                    {self.load_kg} kg  =  '
             f'{load_kn:.2f} kN', C['danger']),
            (f'Ventaja Mecánica:         {vm}:1', C['warning']),
            ('', None),
            (f'Fuerza ideal (sin fricción):', C['accent']),
            (f'  F = {load_kn:.2f} / {vm} = {ideal_force:.2f} kN  '
             f'({ideal_force * 1000 / G:.1f} kg)', C['accent']),
        ]

        if self.friction_mode:
            data_lines.extend([
                ('', None),
                (f'Eficiencia por polea:     {self.pulley_efficiency:.0%}',
                 C['secondary']),
                (f'Poleas en el sistema:     {n_pulleys}', C['secondary']),
                (f'Eficiencia total:         '
                 f'{eff:.1%}', C['secondary']),
                (f'Fuerza REAL (con fricción):', C['danger']),
                (f'  F = {real_force:.2f} kN  '
                 f'({real_force * 1000 / G:.1f} kg)', C['danger']),
            ])

        for text, color in data_lines:
            if text and color:
                surf = self.font_med.render(text, True, color)
                self.screen.blit(surf, (panel_x + 15, y))
            y += 25

        y += 15
        pygame.draw.line(self.screen, C['grid'],
                         (panel_x + 10, y), (panel_x + 620, y), 1)
        y += 15

        # Tabla comparativa
        surf = self.font_big.render('Comparación de Sistemas:', True,
                                    C['primary'])
        self.screen.blit(surf, (panel_x + 10, y))
        y += 35

        header = f'{"Sistema":<25} {"VM":>5} {"Fuerza (kN)":>12} {"Equiv. (kg)":>12}'
        surf = self.font_sm.render(header, True, C['dark_text'])
        self.screen.blit(surf, (panel_x + 15, y))
        y += 20

        for i, s in enumerate(self.systems):
            svm = s['vm']
            sf = load_kn / svm
            skg = sf * 1000 / G
            is_current = (i == self.current_system)
            color = C['warning'] if is_current else C['text']
            marker = '→ ' if is_current else '  '
            line = f'{marker}{s["name"]:<23} {svm:>5}:1 {sf:>11.2f} {skg:>11.1f}'
            surf = self.font_sm.render(line, True, color)
            self.screen.blit(surf, (panel_x + 15, y))
            y += 22

        y += 15
        # Regla educativa
        rule = ('REGLA: VM × distancia_tirón = distancia_carga.  '
                'Para levantar 1m con 3:1, tiras 3m de cuerda.')
        surf = self.font_sm.render(rule, True, C['warning'])
        self.screen.blit(surf, (panel_x + 10, y))

        # ── Controles ────────────────────────────────────────────────
        ctrl_y = HEIGHT - 55
        pygame.draw.rect(self.screen, C['panel'],
                         (0, ctrl_y - 10, WIDTH, 65))
        controls = [
            '[1] 1:1', '[2] 2:1', '[3] Z-rig 3:1', '[4] 4:1',
            '[ESPACIO] Tirar', '[F] Fricción: ' + ('ON' if self.friction_mode else 'OFF'),
            '[↑/↓] Carga', '[ESC] Salir',
        ]
        x = 20
        for ctrl in controls:
            color = C['warning'] if 'Fricción' in ctrl and self.friction_mode else C['dark_text']
            surf = self.font_sm.render(ctrl, True, color)
            self.screen.blit(surf, (x, ctrl_y))
            x += surf.get_width() + 20

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
                    elif event.key == pygame.K_1:
                        self.current_system = 0
                    elif event.key == pygame.K_2:
                        self.current_system = 1
                    elif event.key == pygame.K_3:
                        self.current_system = 2
                    elif event.key == pygame.K_4:
                        self.current_system = 3
                    elif event.key == pygame.K_f:
                        self.friction_mode = not self.friction_mode
                    elif event.key == pygame.K_UP:
                        self.load_kg = min(self.load_kg + 10, 500)
                    elif event.key == pygame.K_DOWN:
                        self.load_kg = max(self.load_kg - 10, 10)

            # Animación de tirón
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                self.pull_offset = min(self.pull_offset + dt * 3, 5.0)
            else:
                self.pull_offset = max(self.pull_offset - dt * 2, 0.0)

            self.draw()

        pygame.quit()


if __name__ == '__main__':
    sim = PulleySimulator()
    sim.run()
