"""
Framework de simulaciones — Física del Rescate con cuerdas.

Fachada y CLI del framework. La arquitectura está repartida por responsabilidad
(SRP) en módulos pequeños:

  config.py    constantes físicas y paletas (fuente única de verdad)
  physics.py   núcleo físico: funciones PURAS, testeadas (modelo)
  viz.py       umbrales de seguridad → color/estado
  pg_utils.py  primitivas de dibujo pygame compartidas
  registry.py  catálogo (Registry + Plugin con auto-descubrimiento)
  base.py      clases base PygameSim / MplSim (Template Method)
  sims/        las simulaciones (vista), cada una con main() decorado
  framework.py  ← este archivo: despachador + menú (CLI)

Uso:
  python3 framework.py            menú interactivo
  python3 framework.py <key>      corre una simulación
  python3 framework.py --list     lista las keys (una por módulo en sims/)
"""

import sys

from registry import all_sims, get, keys  # re-export para conveniencia
from base import PygameSim, MplSim         # noqa: F401  (API pública)


def run(key):
    """Despacha: busca la simulación en el registro y ejecuta su main()."""
    get(key).entrypoint()


# ── CLI ────────────────────────────────────────────────────────────────

def _print_menu():
    print('\n  FÍSICA DEL RESCATE — Simulaciones\n')
    for i, s in enumerate(all_sims(), 1):
        tag = 'Animacion' if s.backend == 'pygame' else 'Simulacion'
        print(f'  {i:>2}. [{s.key:<26}] {tag} {s.title}')
        print(f'      {s.description}')
    print('\n   0. Salir\n')


def _interactive():
    sims = all_sims()
    by_key = {s.key: s for s in sims}
    while True:
        _print_menu()
        try:
            choice = input('  Elegí una simulación (número o key): ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice in ('0', 'q', 'salir', 'exit'):
            return
        key = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(sims):
                key = sims[idx].key
        elif choice in by_key:
            key = choice
        if key is None:
            print('  ⚠  Opción inválida.\n')
            continue
        print(f'\n  ▶ Lanzando {by_key[key].title} …\n')
        run(key)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        _interactive()
    elif argv[0] in ('--list', '-l'):
        print(' '.join(keys()))
    elif argv[0] in ('--help', '-h'):
        print(__doc__)
    else:
        run(argv[0])


if __name__ == '__main__':
    main()
