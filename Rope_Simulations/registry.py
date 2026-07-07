"""
Registro de simulaciones — patrón Registry + Plugin (auto-descubrimiento).

Cada simulación se "enchufa" decorando su entrypoint:

    from registry import simulation

    @simulation(backend='mpl', title='Tirolesa', description='…', order=5)
    def main():
        ...

La key se deriva del nombre del módulo (sims/tirolesa_fuerzas.py → 'tirolesa_fuerzas'),
así que NO hay catálogo central que mantener: agregar una sim = soltar un
archivo en sims/ con su main() decorado. discover() importa todos los módulos
del paquete sims y deja el registro poblado.
"""

import os
import importlib
import pkgutil
from dataclasses import dataclass

# Silencia el banner de pygame para no contaminar la salida de --list.
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

VALID_BACKENDS = ('mpl', 'pygame', 'qt')


@dataclass(frozen=True)
class Simulation:
    key: str            # derivada del módulo (target del Makefile)
    backend: str        # 'mpl' (sliders) | 'pygame' (animada)
    title: str          # título legible
    description: str    # una línea
    order: int          # orden en el menú (currículo)
    entrypoint: object  # callable main()


_REGISTRY = {}
_DISCOVERED = False


def simulation(*, backend, title, description, order=100, key=None):
    """Decorador que registra el main() de una simulación."""
    if backend not in VALID_BACKENDS:
        raise ValueError(f"backend '{backend}' inválido; usar {VALID_BACKENDS}")

    def decorator(func):
        k = key or func.__module__.rsplit('.', 1)[-1]
        _REGISTRY[k] = Simulation(k, backend, title, description, order, func)
        return func

    return decorator


def discover():
    """Importa todos los módulos de sims/ para poblar el registro (idempotente)."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import sims
    for info in pkgutil.iter_modules(sims.__path__):
        if not info.name.startswith('_'):
            importlib.import_module(f'sims.{info.name}')
    _DISCOVERED = True


def all_sims():
    """Lista de Simulation ordenada por (order, key)."""
    discover()
    return sorted(_REGISTRY.values(), key=lambda s: (s.order, s.key))


def keys():
    """Keys ordenadas (consumido por el menú; el Makefile usa los filenames)."""
    return [s.key for s in all_sims()]


def get(key):
    """Devuelve la Simulation por key o lanza KeyError con mensaje claro."""
    discover()
    if key not in _REGISTRY:
        disponibles = ', '.join(sorted(_REGISTRY))
        raise KeyError(f"Simulación '{key}' no existe. Opciones: {disponibles}")
    return _REGISTRY[key]
