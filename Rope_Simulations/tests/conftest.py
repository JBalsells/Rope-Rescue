"""Configuración de pytest: pone Simulations/ en el path y fuerza backends
headless (Agg para matplotlib, dummy para SDL/pygame) para que los módulos
de simulación puedan importarse en CI sin pantalla."""
import os
import sys

os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

SIM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SIM_DIR)
