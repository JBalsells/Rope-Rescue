"""
Clases base para simulaciones — patrón Template Method.

El esqueleto del ciclo de vida (crear ventana/figura, bucle de eventos,
callbacks de sliders) está fijo aquí; cada simulación nueva solo rellena los
"huecos" (setup/update/draw, o build/redraw). Una por backend:

  • PygameSim  — animadas en tiempo real (bucle de frames).
  • MplSim     — interactivas con sliders (redibujo dirigido por eventos).

Las sims actuales son anteriores a estas bases; sirven de andamio para las
próximas (ver README → "Agregar una simulación nueva").
"""


# ══════════════════════════════════════════════════════════════════════
#  Animadas (pygame)
# ══════════════════════════════════════════════════════════════════════

class PygameSim:
    """
    Bucle de animación resuelto. La subclase define:

        WIDTH, HEIGHT, FPS, CAPTION
        setup(self)             estado inicial            (opcional)
        handle_event(self, ev)  reaccionar a un evento    (opcional)
        update(self, dt)        física por frame          (opcional)
        draw(self)              dibujar en self.screen    (obligatorio)

    QUIT y ESC cierran solos.  main():  MiSim.launch()
    """

    WIDTH = 1280
    HEIGHT = 800
    FPS = 60
    CAPTION = 'Física del Rescate'

    def __init__(self):
        import pygame
        from pg_utils import make_fonts
        self._pygame = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.CAPTION)
        self.clock = pygame.time.Clock()
        self.fonts = make_fonts()
        self.running = True
        self.setup()

    # ── Hooks ─────────────────────────────────────────────────────────
    def setup(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self):
        raise NotImplementedError('La subclase debe implementar draw().')

    # ── Esqueleto (no sobreescribir) ──────────────────────────────────
    def run(self):
        pygame = self._pygame
        while self.running:
            dt = self.clock.tick(self.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif (event.type == pygame.KEYDOWN
                      and event.key == pygame.K_ESCAPE):
                    self.running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    @classmethod
    def launch(cls):
        cls().run()


# ══════════════════════════════════════════════════════════════════════
#  Interactivas (matplotlib + sliders)
# ══════════════════════════════════════════════════════════════════════

class MplSim:
    """
    Esqueleto para sims de sliders. La subclase define:

        TITLE, FIGSIZE
        build(self, fig)        crear ejes y sliders; registrar self.sliders
                                (dict nombre→Slider)            (obligatorio)
        redraw(self, values)    redibujar con los valores actuales
                                (values = {nombre: val})        (obligatorio)

    La base aplica el estilo oscuro, conecta on_changed de cada slider a
    redraw() y hace el primer dibujo.  main():  MiSim.launch()
    """

    TITLE = 'Física del Rescate'
    FIGSIZE = (16, 9)

    def __init__(self):
        import matplotlib.pyplot as plt
        from config import apply_mpl_style
        self._plt = plt
        apply_mpl_style()
        self.fig = plt.figure(figsize=self.FIGSIZE)
        self.sliders = {}
        self.build(self.fig)
        for sl in self.sliders.values():
            sl.on_changed(lambda _=None: self._redraw())
        self._redraw()

    # ── Hooks ─────────────────────────────────────────────────────────
    def build(self, fig):
        raise NotImplementedError('La subclase debe implementar build().')

    def redraw(self, values):
        raise NotImplementedError('La subclase debe implementar redraw().')

    # ── Esqueleto ─────────────────────────────────────────────────────
    def _redraw(self):
        values = {name: sl.val for name, sl in self.sliders.items()}
        self.redraw(values)
        self.fig.canvas.draw_idle()

    def run(self):
        self._plt.show()

    @classmethod
    def launch(cls):
        cls().run()
