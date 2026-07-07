"""
08 — Flujo de Gases en un Incendio
===================================
Simulación 2D de dinámica de fluidos (Navier-Stokes incompresible) del flujo
de gases calientes alrededor de un foco de incendio.

Método: Jos Stam "Stable Fluids" (1999)
  • Advección semi-lagrangiana
  • Proyección de presión (Gauss-Seidel, 20 iters)
  • Flotabilidad de Boussinesq: F_y = β·(T − T_amb)
  • Difusión de temperatura y densidad de humo

Controles Sliders:
  • HRR        — Potencia calórica del foco (kW)
  • Viento     — Velocidad del viento lateral (m/s)
  • Flotabilidad — Factor β (m/s²·K)

Paneles:
  • Izquierda  — Campo de temperatura (imshow) + flechas de velocidad (quiver)
  • Centro-inf — Campo de vorticidad
  • Derecha    — Perfil vertical T en el eje central + panel informativo
"""

import sys, os, math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as mcm
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider

# ── Ruta al config de Fire/ ───────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)
from config import FC, apply_mpl_style          # noqa: E402

# ══════════════════════════════════════════════════════════════════════════════
# Parámetros de la rejilla
# ══════════════════════════════════════════════════════════════════════════════
N   = 80          # celdas interiores en cada eje
SZ  = N + 2       # tamaño con celdas fantasma (0 y N+1 son bordes)
dt  = 0.08        # paso temporal (s)
dx  = 1.0         # tamaño de celda (m)

DIFF_T    = 0.08  # difusividad térmica
DIFF_DENS = 0.04  # difusividad del humo
VISC      = 0.01  # viscosidad cinemática
T_AMB     = 20.0  # temperatura ambiente (°C)
STEPS_PER_FRAME = 3

# ── Índices del foco (centro-inferior) ────────────────────────────────────────
CX = SZ // 2
CY_FIRE = 4       # fila baja (y crece hacia arriba → índice pequeño = abajo)

# Radio del foco (celdas)
FIRE_R = 4

# ── Precalcular máscara gaussiana para la fuente de calor ─────────────────────
def _make_source_mask():
    mask = np.zeros((SZ, SZ))
    for j in range(1, N + 1):
        for i in range(1, N + 1):
            d2 = (i - CX) ** 2 + (j - CY_FIRE) ** 2
            mask[j, i] = math.exp(-d2 / (2 * FIRE_R ** 2))
    peak = mask.max()
    if peak > 0:
        mask /= peak
    return mask

SOURCE_MASK = _make_source_mask()

# ══════════════════════════════════════════════════════════════════════════════
# Stable Fluids — núcleo del solver
# ══════════════════════════════════════════════════════════════════════════════

def set_bnd(b: int, x: np.ndarray):
    """Condiciones de contorno.
    b=0 → escalar (continuo en bordes verticales, reflejo en suelo/techo)
    b=1 → velocidad-x  (reflejo en paredes L/R)
    b=2 → velocidad-y  (reflejo en suelo/techo)
    """
    # Bordes izquierdo y derecho
    if b == 1:
        x[1:N+1, 0]   = -x[1:N+1, 1]
        x[1:N+1, N+1] = -x[1:N+1, N]
    else:
        x[1:N+1, 0]   =  x[1:N+1, 1]
        x[1:N+1, N+1] =  x[1:N+1, N]
    # Bordes inferior y superior
    if b == 2:
        x[0,   1:N+1] = -x[1,   1:N+1]
        x[N+1, 1:N+1] = -x[N,   1:N+1]
    else:
        x[0,   1:N+1] =  x[1,   1:N+1]
        x[N+1, 1:N+1] =  x[N,   1:N+1]
    # Esquinas
    x[0,   0]   = 0.5 * (x[1,   0]   + x[0,   1])
    x[0,   N+1] = 0.5 * (x[1,   N+1] + x[0,   N])
    x[N+1, 0]   = 0.5 * (x[N,   0]   + x[N+1, 1])
    x[N+1, N+1] = 0.5 * (x[N,   N+1] + x[N+1, N])


def lin_solve(b: int, x: np.ndarray, x0: np.ndarray, a: float, c: float,
              iters: int = 20):
    """Gauss-Seidel lineal para difusión/presión."""
    inv_c = 1.0 / c
    for _ in range(iters):
        x[1:N+1, 1:N+1] = (x0[1:N+1, 1:N+1] +
                            a * (x[0:N,   1:N+1] + x[2:N+2, 1:N+1] +
                                 x[1:N+1, 0:N]   + x[1:N+1, 2:N+2])) * inv_c
        set_bnd(b, x)


def diffuse(b: int, x: np.ndarray, x0: np.ndarray, diff: float):
    a = dt * diff * N * N
    lin_solve(b, x, x0, a, 1 + 4 * a)


def advect(b: int, d: np.ndarray, d0: np.ndarray,
           u: np.ndarray, v: np.ndarray):
    """Advección semi-lagrangiana (trace-back)."""
    # Coordenadas de las celdas interiores
    j_idx, i_idx = np.mgrid[1:N+1, 1:N+1]          # shape (N,N)
    # Retro-traza
    # v está indexado como [fila, col]; fila crece hacia arriba en nuestro dominio
    xi = i_idx - dt * N * u[1:N+1, 1:N+1]
    yi = j_idx - dt * N * v[1:N+1, 1:N+1]
    # Clamping
    xi = np.clip(xi, 0.5, N + 0.5)
    yi = np.clip(yi, 0.5, N + 0.5)
    # Interpolación bilineal
    i0 = np.floor(xi).astype(int)
    j0 = np.floor(yi).astype(int)
    i1 = i0 + 1
    j1 = j0 + 1
    s1 = xi - i0
    s0 = 1.0 - s1
    t1 = yi - j0
    t0 = 1.0 - t1
    d[1:N+1, 1:N+1] = (s0 * (t0 * d0[j0, i0] + t1 * d0[j1, i0]) +
                        s1 * (t0 * d0[j0, i1] + t1 * d0[j1, i1]))
    set_bnd(b, d)


def project(u: np.ndarray, v: np.ndarray,
            p: np.ndarray, div: np.ndarray):
    """Proyección de Helmholtz para asegurar div=0."""
    h = 1.0 / N
    div[1:N+1, 1:N+1] = -0.5 * h * (
        u[1:N+1, 2:N+2] - u[1:N+1, 0:N] +
        v[2:N+2, 1:N+1] - v[0:N,   1:N+1])
    p[...] = 0.0
    set_bnd(0, div)
    set_bnd(0, p)
    lin_solve(0, p, div, 1.0, 4.0)
    u[1:N+1, 1:N+1] -= 0.5 * (p[1:N+1, 2:N+2] - p[1:N+1, 0:N]) / h
    v[1:N+1, 1:N+1] -= 0.5 * (p[2:N+2, 1:N+1] - p[0:N,   1:N+1]) / h
    set_bnd(1, u)
    set_bnd(2, v)


# ══════════════════════════════════════════════════════════════════════════════
# Estado de la simulación
# ══════════════════════════════════════════════════════════════════════════════
class FluidSim:
    def __init__(self):
        shape = (SZ, SZ)
        self.u    = np.zeros(shape)  # velocidad x
        self.v    = np.zeros(shape)  # velocidad y (positivo = arriba)
        self.u0   = np.zeros(shape)
        self.v0   = np.zeros(shape)
        self.T    = np.full(shape, T_AMB)  # temperatura (°C)
        self.T0   = np.full(shape, T_AMB)
        self.dens = np.zeros(shape)  # densidad de humo [0-1]
        self.dens0 = np.zeros(shape)
        self.p    = np.zeros(shape)
        self.div  = np.zeros(shape)
        # Partículas trazadoras
        rng = np.random.default_rng(42)
        self.px = rng.uniform(5, N - 5, 200).astype(float)
        self.py = rng.uniform(2, N // 2, 200).astype(float)
        # Parámetros controlables
        self.hrr       = 500.0   # kW
        self.wind      = 0.5     # m/s lateral
        self.buoyancy  = 0.25    # β m/s²/K
        self.time      = 0.0

    # ── Actualizar un paso ─────────────────────────────────────────────────
    def step(self):
        # 1. Añadir fuentes de calor, humo y viento
        self._add_sources()

        # 2. Flotabilidad de Boussinesq: gases calientes ascienden
        buoy = self.buoyancy * (self.T - T_AMB)
        self.v[1:N+1, 1:N+1] += dt * buoy[1:N+1, 1:N+1]

        # 3. Paso de velocidad
        self.u0[...] = self.u
        self.v0[...] = self.v
        diffuse(1, self.u, self.u0, VISC)
        diffuse(2, self.v, self.v0, VISC)
        project(self.u, self.v, self.p, self.div)
        self.u0[...] = self.u
        self.v0[...] = self.v
        advect(1, self.u, self.u0, self.u0, self.v0)
        advect(2, self.v, self.v0, self.u0, self.v0)
        project(self.u, self.v, self.p, self.div)

        # 4. Paso de temperatura
        self.T0[...] = self.T
        diffuse(0, self.T, self.T0, DIFF_T)
        self.T0[...] = self.T
        advect(0, self.T, self.T0, self.u, self.v)
        # Enfriamiento gradual hacia T_AMB (disipación radiativa)
        self.T[1:N+1, 1:N+1] += dt * 0.08 * (T_AMB - self.T[1:N+1, 1:N+1])
        set_bnd(0, self.T)

        # 5. Paso de densidad de humo
        self.dens0[...] = self.dens
        diffuse(0, self.dens, self.dens0, DIFF_DENS)
        self.dens0[...] = self.dens
        advect(0, self.dens, self.dens0, self.u, self.v)
        # Disipación del humo
        self.dens[1:N+1, 1:N+1] *= 0.998
        set_bnd(0, self.dens)

        # 6. Mover partículas trazadoras
        self._move_tracers()

        self.time += dt

    def _add_sources(self):
        # Intensidad normalizada (0–1) según HRR
        intensity = self.hrr / 2000.0
        dT_src = intensity * 120.0   # °C/s en el pico gaussiano
        ds_src = intensity * 0.6

        self.T[...] += dt * dT_src * SOURCE_MASK
        self.dens[...] += dt * ds_src * SOURCE_MASK
        self.dens = np.clip(self.dens, 0, 1)

        # Columna de velocidad vertical en el foco
        v_src = intensity * 3.5
        self.v[1:N+1, 1:N+1] += dt * v_src * SOURCE_MASK[1:N+1, 1:N+1]

        # Viento lateral (fuerza uniforme en x sobre toda la malla)
        u_wind = self.wind * 0.15
        self.u[1:N+1, 1:N+1] += dt * u_wind * (1.0 - np.exp(-0.1 * self.time))

        # Condición de suelo: temp y dens fijos en la fila inferior
        self.T[1, 1:N+1] = T_AMB + dT_src * SOURCE_MASK[1, 1:N+1]

    def _move_tracers(self):
        """Interpola velocidad en posición de cada partícula y la mueve."""
        xi = np.clip(self.px, 0.5, N + 0.5)
        yi = np.clip(self.py, 0.5, N + 0.5)
        i0 = np.floor(xi).astype(int)
        j0 = np.floor(yi).astype(int)
        i1 = np.minimum(i0 + 1, N + 1)
        j1 = np.minimum(j0 + 1, N + 1)
        s1 = xi - i0;  s0 = 1.0 - s1
        t1 = yi - j0;  t0 = 1.0 - t1
        u_p = (s0 * (t0 * self.u[j0, i0] + t1 * self.u[j1, i0]) +
               s1 * (t0 * self.u[j0, i1] + t1 * self.u[j1, i1]))
        v_p = (s0 * (t0 * self.v[j0, i0] + t1 * self.v[j1, i0]) +
               s1 * (t0 * self.v[j0, i1] + t1 * self.v[j1, i1]))
        self.px += dt * N * u_p * 0.5
        self.py += dt * N * v_p * 0.5
        # Re-inyectar partículas que salen del dominio
        out = ((self.px < 1) | (self.px > N) |
               (self.py < 1) | (self.py > N))
        n_out = out.sum()
        if n_out:
            rng = np.random.default_rng()
            self.px[out] = rng.uniform(CX - 15, CX + 15, n_out)
            self.py[out] = rng.uniform(1, 10, n_out)

    def reset(self):
        self.u[...]    = 0
        self.v[...]    = 0
        self.T[...]    = T_AMB
        self.dens[...] = 0
        self.time      = 0.0
        rng = np.random.default_rng(42)
        self.px = rng.uniform(5, N - 5, 200).astype(float)
        self.py = rng.uniform(2, N // 2, 200).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# Colormaps personalizados
# ══════════════════════════════════════════════════════════════════════════════
def _make_fire_cmap():
    """Mapa de color: frío-azul → ambiente-negro → caliente-rojo-amarillo."""
    colors_list = [
        (0.00, '#0a0a2a'),
        (0.10, '#1a1a3a'),
        (0.25, '#5a1010'),
        (0.45, '#cc2200'),
        (0.65, '#ff6600'),
        (0.82, '#ffcc00'),
        (1.00, '#ffffee'),
    ]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'fire', [(v, c) for v, c in colors_list])
    return cmap

FIRE_CMAP  = _make_fire_cmap()
SMOKE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'smoke', [(0, '#00000000'), (0.4, '#4a4a5a88'), (1, '#1a1a2acc')])
VORT_CMAP  = plt.get_cmap('RdBu_r')


# ══════════════════════════════════════════════════════════════════════════════
# Quiver subsample
# ══════════════════════════════════════════════════════════════════════════════
_STEP = 6
_qi   = np.arange(_STEP, N + 1, _STEP)    # índices columna (x)
_qj   = np.arange(_STEP, N + 1, _STEP)    # índices fila   (y)
_QI, _QJ = np.meshgrid(_qi, _qj)           # shape (len_qj, len_qi)


# ══════════════════════════════════════════════════════════════════════════════
# Interfaz gráfica
# ══════════════════════════════════════════════════════════════════════════════
def main():
    apply_mpl_style()
    sim = FluidSim()

    # ── Precalentamiento (50 pasos antes de mostrar) ───────────────────────
    sim.hrr = 800.0
    for _ in range(50):
        sim.step()
    sim.hrr = 500.0

    # ── Figura ────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle(
        'Flujo de Gases en un Incendio — Navier-Stokes 2D',
        fontsize=18, fontweight='bold',
        color=FC['primary'], y=0.97)

    # Eje principal: campo de temperatura + velocidad
    ax_T   = fig.add_axes([0.04, 0.22, 0.48, 0.68])
    # Eje vorticidad (abajo centro)
    ax_V   = fig.add_axes([0.54, 0.22, 0.20, 0.30])
    # Eje perfil vertical T (derecha)
    ax_pro = fig.add_axes([0.77, 0.22, 0.20, 0.68])
    # Panel info (arriba derecha)
    ax_inf = fig.add_axes([0.54, 0.55, 0.20, 0.35])
    ax_inf.axis('off')

    # Sliders
    ax_sl_hrr  = fig.add_axes([0.08, 0.13, 0.35, 0.025])
    ax_sl_wind = fig.add_axes([0.08, 0.09, 0.35, 0.025])
    ax_sl_buoy = fig.add_axes([0.08, 0.05, 0.35, 0.025])

    sl_hrr  = Slider(ax_sl_hrr,  'HRR (kW)',          50,  3000,
                     valinit=500,  color=FC['warning'],  valstep=50)
    sl_wind = Slider(ax_sl_wind, 'Viento (m/s)',        0.0,  5.0,
                     valinit=0.5,  color=FC['info'],     valstep=0.1)
    sl_buoy = Slider(ax_sl_buoy, 'Flotabilidad β',      0.05, 0.6,
                     valinit=0.25, color=FC['accent'],   valstep=0.01)

    for sl in (sl_hrr, sl_wind, sl_buoy):
        sl.label.set_color(FC['text'])
        sl.valtext.set_color(FC['text'])

    # ── Render inicial (campos de temperatura) ────────────────────────────
    T_disp = np.flipud(sim.T[1:N+1, 1:N+1])  # flip: fila 0 = suelo abajo
    im_T = ax_T.imshow(
        T_disp, origin='lower', aspect='auto',
        cmap=FIRE_CMAP, vmin=T_AMB - 5, vmax=900,
        extent=[0, N, 0, N])
    cb = fig.colorbar(im_T, ax=ax_T, fraction=0.03, pad=0.01)
    cb.set_label('Temperatura (°C)', color=FC['text'])
    cb.ax.yaxis.set_tick_params(color=FC['text'])
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=FC['text'])

    # Densidad de humo superpuesta (alpha channel)
    d_disp = np.flipud(sim.dens[1:N+1, 1:N+1])
    im_d = ax_T.imshow(
        d_disp, origin='lower', aspect='auto',
        cmap=SMOKE_CMAP, vmin=0, vmax=1,
        extent=[0, N, 0, N], alpha=0.55)

    # Quiver velocidad
    u_q = sim.u[_QJ, _QI]
    v_q = sim.v[_QJ, _QI]
    # Convertir índices de fila (creciente hacia arriba) a coordenadas del plot
    qx = _QI - 1
    qy = N + 1 - _QJ - 1   # flip vertical para coincidir con imshow lower
    qv = ax_T.quiver(
        qx, qy, u_q, -v_q,      # -v porque imshow está flipado
        color='white', alpha=0.55, scale=12, width=0.003,
        headwidth=3, headlength=4)

    # Partículas trazadoras
    py_plot = N - sim.py          # flip
    sc_p = ax_T.scatter(
        sim.px - 1, py_plot,
        s=6, c='cyan', alpha=0.45, zorder=5)

    ax_T.set_xlim(0, N)
    ax_T.set_ylim(0, N)
    ax_T.set_xlabel('x (celdas)', color=FC['text'])
    ax_T.set_ylabel('y (celdas / altura)', color=FC['text'])
    ax_T.set_title('Campo Térmico + Flujo de Gases', color=FC['warning'], fontsize=11)

    # ── Vorticidad ────────────────────────────────────────────────────────
    dvdx = (sim.v[1:N+1, 2:N+2] - sim.v[1:N+1, 0:N]) / (2 * dx)
    dudy = (sim.u[2:N+2, 1:N+1] - sim.u[0:N,   1:N+1]) / (2 * dx)
    vort = dvdx - dudy
    vlim = max(abs(vort).max(), 1e-3)
    im_W = ax_V.imshow(
        np.flipud(vort), origin='lower', aspect='auto',
        cmap=VORT_CMAP, vmin=-vlim, vmax=vlim,
        extent=[0, N, 0, N])
    ax_V.set_title('Vorticidad ω (s⁻¹)', color=FC['info'], fontsize=9)
    ax_V.set_xlabel('x', color=FC['text'], fontsize=8)
    ax_V.set_ylabel('y', color=FC['text'], fontsize=8)

    # ── Perfil vertical de temperatura ────────────────────────────────────
    T_col = sim.T[1:N+1, CX]
    y_arr = np.arange(1, N + 1)

    ln_T, = ax_pro.plot(T_col, y_arr, color=FC['flame'], lw=2)
    ax_pro.axvline(T_AMB,   color=FC['info'],    lw=0.8, ls='--', alpha=0.6)
    ax_pro.axvline(200,     color=FC['warning'], lw=0.8, ls='--', alpha=0.6)
    ax_pro.axvline(600,     color=FC['danger'],  lw=0.8, ls='--', alpha=0.6)
    ax_pro.text(T_AMB + 5,  N * 0.92, f'{T_AMB:.0f}°C', color=FC['info'],    fontsize=7, va='top')
    ax_pro.text(205,        N * 0.80, '200°C',          color=FC['warning'], fontsize=7)
    ax_pro.text(605,        N * 0.68, '600°C\nFlashover',color=FC['danger'],  fontsize=7)

    ax_pro.set_xlabel('Temperatura (°C)', color=FC['text'], fontsize=9)
    ax_pro.set_ylabel('Altura (celdas)', color=FC['text'], fontsize=9)
    ax_pro.set_title('Perfil T — eje central', color=FC['accent'], fontsize=9)
    ax_pro.set_xlim(T_AMB - 10, 1000)
    ax_pro.set_ylim(0, N + 1)
    ax_pro.grid(True, alpha=0.2)

    # ── Panel informativo ─────────────────────────────────────────────────
    info_txt = ax_inf.text(
        0.05, 0.95, '', transform=ax_inf.transAxes,
        color=FC['text'], fontsize=9.5, va='top', ha='left',
        fontfamily='monospace',
        bbox=dict(boxstyle='round,pad=0.5', facecolor=FC['panel'],
                  edgecolor=FC['primary'], alpha=0.85))
    ax_inf.set_title('Estado', color=FC['primary'], fontsize=10)

    # ── Leyenda / notas ───────────────────────────────────────────────────
    legend_items = [
        plt.Line2D([0], [0], color=FC['flame'],   lw=2,  label='Temperatura'),
        plt.Line2D([0], [0], color='cyan',        lw=0, marker='o', ms=4,
                   alpha=0.7, label='Trazadores'),
        plt.Line2D([0], [0], color='white',       lw=1, marker='>',  ms=4,
                   alpha=0.6, label='Campo vel.'),
    ]
    ax_T.legend(handles=legend_items, loc='upper right', fontsize=8,
                facecolor=FC['panel'], edgecolor=FC['primary'], labelcolor=FC['text'])

    # ══════════════════════════════════════════════════════════════════════
    # Callbacks de sliders
    # ══════════════════════════════════════════════════════════════════════
    def _update_params(_=None):
        sim.hrr      = sl_hrr.val
        sim.wind     = sl_wind.val
        sim.buoyancy = sl_buoy.val

    sl_hrr.on_changed(_update_params)
    sl_wind.on_changed(_update_params)
    sl_buoy.on_changed(_update_params)

    # ══════════════════════════════════════════════════════════════════════
    # Función de animación
    # ══════════════════════════════════════════════════════════════════════
    def animate(_frame):
        for _ in range(STEPS_PER_FRAME):
            sim.step()

        # -- Temperatura --
        T_disp = np.flipud(sim.T[1:N+1, 1:N+1])
        im_T.set_data(T_disp)
        T_max = sim.T[1:N+1, 1:N+1].max()
        im_T.set_clim(vmin=T_AMB - 5, vmax=max(T_max * 1.05, 200))

        # -- Humo --
        d_disp = np.flipud(sim.dens[1:N+1, 1:N+1])
        im_d.set_data(d_disp)

        # -- Quiver --
        u_q = sim.u[_QJ, _QI]
        v_q = sim.v[_QJ, _QI]
        qv.set_UVC(u_q, -v_q)

        # -- Trazadores --
        py_plot = N - sim.py
        sc_p.set_offsets(np.c_[sim.px - 1, py_plot])

        # -- Vorticidad --
        dvdx = (sim.v[1:N+1, 2:N+2] - sim.v[1:N+1, 0:N]) / (2 * dx)
        dudy = (sim.u[2:N+2, 1:N+1] - sim.u[0:N,   1:N+1]) / (2 * dx)
        vort = dvdx - dudy
        vlim = max(abs(vort).max(), 0.5)
        im_W.set_data(np.flipud(vort))
        im_W.set_clim(-vlim, vlim)

        # -- Perfil T --
        T_col = sim.T[1:N+1, CX]
        ln_T.set_xdata(T_col)

        # -- Info panel --
        T_surf = sim.T[2, CX] - T_AMB             # cerca del suelo central
        T_ceil = sim.T[N - 2, CX] - T_AMB         # cerca del techo
        speed_max = np.sqrt(sim.u**2 + sim.v**2)[1:N+1, 1:N+1].max()
        vort_max = abs(vort).max()

        hrr_lbl = (
            'Smoldering (<100kW)'  if sim.hrr < 100 else
            'Incipiente (<500kW)'  if sim.hrr < 500 else
            'Desarrollado (<1MW)'  if sim.hrr < 1000 else
            'Flashover (>1MW)'
        )
        danger = 'PELIGRO EXTREMO ⚠' if T_ceil > 550 else \
                 'Zona peligrosa'     if T_ceil > 200 else \
                 'Seguro'

        info = (
            f"t = {sim.time:6.1f} s\n"
            f"\n"
            f"HRR      : {sim.hrr:5.0f} kW\n"
            f"Régimen  : {hrr_lbl}\n"
            f"\n"
            f"ΔT suelo : {T_surf:+6.1f} °C\n"
            f"ΔT techo : {T_ceil:+6.1f} °C\n"
            f"T máx    : {T_max:6.1f} °C\n"
            f"\n"
            f"Vel máx  : {speed_max:6.2f} m/s\n"
            f"Vort máx : {vort_max:6.2f} s⁻¹\n"
            f"Viento   : {sim.wind:5.1f} m/s\n"
            f"\n"
            f"Estado   : {danger}"
        )
        info_txt.set_text(info)

        return [im_T, im_d, qv, sc_p, im_W, ln_T, info_txt]

    anim = FuncAnimation(
        fig, animate,
        interval=50,   # ~20 FPS
        blit=True,
        cache_frame_data=False)

    # Texto de notas al pie
    fig.text(
        0.5, 0.01,
        'Método: Stable Fluids (Stam 1999) — Advección semi-lagrangiana + Proyección de Gauss-Seidel  |  '
        'Flotabilidad de Boussinesq: F_y = β·(T−T_amb)',
        ha='center', fontsize=8, color=FC['neutral'])

    plt.show()


if __name__ == '__main__':
    main()
