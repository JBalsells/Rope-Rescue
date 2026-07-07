# Física del Rescate — Framework de Simulaciones

Simulaciones interactivas de la física del rescate con cuerdas (anclajes,
tirolesas, factor de caída, distribución de fuerzas, nudos). Diseñado para
**crecer**: agregar una simulación nueva es *soltar un archivo* en `sims/`.

## Arquitectura

Separación **modelo / vista** (mini-MVC) con responsabilidad única por módulo
(SRP) y una sola fuente de verdad por capa:

```
Rope_Simulations/
├─ Makefile         Lanzador único (vive dentro de este directorio)
├─ config.py        Constantes físicas (G, MBS, NFPA, UIAA) y paletas de color
├─ physics.py       NÚCLEO físico: funciones puras (sin GUI), testeadas  ← modelo
├─ viz.py           Umbrales de seguridad → color/estado (verde/amarillo/rojo)
├─ pg_utils.py      Primitivas de dibujo pygame (flechas, líneas, fuentes, barra)
├─ registry.py      Catálogo: Registry + Plugin con auto-descubrimiento
├─ base.py          Clases base PygameSim / MplSim (Template Method)
├─ framework.py     Despachador + menú (CLI) — fachada del framework
├─ sims/            LAS SIMULACIONES (vista); cada una con main() decorado
│   ├─ fuerza_y_newton.py        anclaje_en_v.py       tirolesa_fuerzas.py
│   ├─ vectores_fuerzas.py       nudos_y_resistencia.py
│   ├─ factor_de_caida.py        camilla_en_tirolesa.py
│   └─ distribucion_multi_anclaje.py   english_reeve.py
└─ tests/           Casos canónicos de physics.py + integridad del framework
```

### Patrones de diseño

| Patrón | Dónde | Para qué |
|---|---|---|
| **Registry + Plugin** | `registry.py` (`@simulation` + `discover()`) | El catálogo se arma solo importando `sims/`. Sin lista central que mantener. |
| **Template Method** | `base.py` (`PygameSim`, `MplSim`) | El ciclo de vida (ventana/figura, bucle, sliders) es fijo; la sim solo rellena `setup/update/draw` (o `build/redraw`). |
| **Adapter** | convención `main()` | Dos backends muy distintos (matplotlib vs pygame) se invocan igual. |
| **Facade** | `framework.py` | Un punto de entrada (menú + `run(key)`) que oculta registro y bases. |
| **Strategy** (implícito) | campo `backend` | Cada sim declara su estrategia de presentación; el menú las distingue. |

**Por qué la física aparte.** Todo modelo vive en `physics.py` y nada más lo
reimplementa: (1) se testea con valores conocidos del dominio (V a 120° = 100 %·W,
nudo en ocho = 80 %…); (2) la misma función puede alimentarse luego con datos
reales de instrumentación (celda de carga → ESP32 → MQTT) para comparar
*predicho vs medido*. Los umbrales de color salen solo de `viz.py`.

## Uso

Desde **dentro de `Rope_Simulations/`** (donde vive el `Makefile`). Todo
corre en un **entorno virtual (`.venv`)** que se crea solo la primera vez:

```bash
make run                   # crea el venv (si falta), instala deps y abre el menú
make tirolesa_fuerzas      # levanta una simulación por su key (= nombre del archivo)
make test                  # corre los tests
make list                  # lista las keys disponibles
make install               # solo crea el venv e instala dependencias
make help                  # ayuda
```

`make run` es el punto de arranque: la primera vez crea `.venv/`, instala
`requirements.txt` (numpy, matplotlib, pygame, PyQt5, pytest) y abre el menú;
las siguientes veces reusa el venv.

La **key de cada simulación es el nombre de su archivo** en `sims/`
(`tirolesa_fuerzas.py` → `tirolesa_fuerzas`). `make list` muestra la lista viva.

## Agregar una simulación nueva

1. Crear `sims/mi_sim.py`.
2. **No reimplementar física**: usar/extender `physics.py`; colores desde `viz.py`.
3. Exponer `main()` decorado para que el registro lo descubra:

```python
from registry import simulation
from base import PygameSim          # o MplSim para sliders
from config import PG_COLORS as C
import physics, viz, pg_utils

class MiSim(PygameSim):
    CAPTION = 'Mi simulación'
    def setup(self):
        self.mass = 100
    def handle_event(self, ev):
        ...
    def update(self, dt):
        self.W = physics.weight_kn(self.mass)
    def draw(self):
        self.screen.fill(C['bg'])
        # dibujar con self.fonts, pg_utils, viz.ratio_color(...) …

@simulation(backend='pygame', order=10,
            title='Mi simulación', description='Qué enseña, en una línea.')
def main():
    MiSim.launch()
```

4. (Si introduce física nueva) agregar su caso canónico en `tests/test_physics.py`.

Eso es todo: **no se edita ningún catálogo**. El target `make mi_sim`, la
entrada del menú y la validación en `make test` aparecen solos — el registro
descubre el módulo y `tests/test_framework.py` verifica que cumple el contrato.

### Sim de sliders (matplotlib)

```python
from registry import simulation
from base import MplSim

class MiGrafico(MplSim):
    TITLE = 'Mi gráfico'
    def build(self, fig):
        ax = fig.add_axes([0.1, 0.3, 0.8, 0.6])
        from matplotlib.widgets import Slider
        self.ax = ax
        self.sliders['masa'] = Slider(fig.add_axes([0.1, 0.1, 0.8, 0.03]),
                                      'Masa (kg)', 10, 300, valinit=100)
    def redraw(self, values):
        self.ax.clear()
        # dibujar con values['masa'] …

@simulation(backend='mpl', order=11, title='Mi gráfico', description='…')
def main():
    MiGrafico.launch()
```
