"""
07_pluma_termica.py
Pluma Convectiva de Humo — Matplotlib FuncAnimation

Modela la elevación y dispersión de gases y humo sobre una fuente de calor
(incendio), con campo de temperatura de fondo calculado por el modelo
de pluma de Gaussian.

Física:
  • Modelo de pluma gaussiana (Sutton / Pasquill–Gifford):
        C(x, z) ∝ (Q_c / u) · exp(−(z − H_eff)² / (2σ_z²))
    donde σ_z = σ_z0 · (x/x₀)^n  según clase de estabilidad atmosférica
  • Fuerzas sobre las partículas:
        F_boyanza = g · (T_p − T_amb) / T_amb  [upward]
        Arrastre viento: vx += dt · (U_wind − vx) / τ
        Difusión turbulenta: ruido gaussiano ∝ σ_z / σ_x
  • Temperatura de partícula: decae exponencialmente con altura
        T_p(z) = T_source · exp(−z / H_escala)  donde H_escala ≈ HRR^0.25

Controles:
  Slider HRR       — potencia calorífica de la fuente (kW)
  Slider Viento    — velocidad del viento (m/s)
  Slider Estabilidad — clase Pasquill A–F (inestable→estable)
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider
from matplotlib.colors import LinearSegmentedColormap

from config import COLORS, FC, apply_mpl_style

# ── Domain ─────────────────────────────────────────────────────────────────────
X_MAX   =  600.0    # m — horizontal extent downwind
Z_MAX   =  500.0    # m — vertical extent
X_SRC   =    0.0    # source x position
Z_SRC   =    0.0    # source height (ground level)
T_AMB   =   20.0    # °C ambient
G       =    9.81   # m/s²

# ── Pasquill–Gifford σ_z coefficients (simplified polynomial fits) ─────────────
# Classes: A (very unstable) → F (very stable)
# σ_z = a_z * x^b_z  for x in km, σ in m
PG_CLASSES = {
    0: ('A — Muy inestable',  0.22, 0.82, 0.24),  # (label, a_y, b_y, a_z, b_z) simplified
    1: ('B — Inestable',      0.16, 0.82, 0.12),
    2: ('C — Ligeramente inest.', 0.11, 0.82, 0.08),
    3: ('D — Neutral',        0.08, 0.82, 0.06),
    4: ('E — Ligeramente estable', 0.06, 0.82, 0.03),
    5: ('F — Estable',        0.04, 0.82, 0.016),
}

# ── Particle dataclass (simple dict arrays for speed) ─────────────────────────
N_PARTICLES  = 350
EMIT_PER_FRAME = 6
MAX_AGE      = 90   # frames


def _empty_particles():
    return {
        'x':       np.zeros(N_PARTICLES),
        'z':       np.zeros(N_PARTICLES),
        'vx':      np.zeros(N_PARTICLES),
        'vz':      np.zeros(N_PARTICLES),
        'T':       np.full(N_PARTICLES, T_AMB),
        'age':     np.full(N_PARTICLES, MAX_AGE + 1),  # all dead
        'max_age': np.full(N_PARTICLES, MAX_AGE),
        'ptype':   np.zeros(N_PARTICLES, dtype=np.int8),  # 0=fire, 1=smoke
    }


# ── Temperature background (gaussian plume) ────────────────────────────────────

def plume_temp_field(HRR: float, U_wind: float,
                     pg_class: int,
                     nx: int = 120, nz: int = 80) -> np.ndarray:
    """
    Compute background temperature field on a (nx, nz) grid.
    Returns T_excess (°C above ambient) array of shape (nz, nx).
    """
    if U_wind < 0.3:
        U_wind = 0.3   # avoid division by zero
    a_z  = PG_CLASSES[pg_class][3]
    b_z  = 0.75

    xs = np.linspace(5, X_MAX, nx)
    zs = np.linspace(0, Z_MAX, nz)
    X, Z = np.meshgrid(xs, zs)

    # Effective source height (buoyant plume rise, Briggs formula simplified)
    H_eff = max(5.0, 1.6 * (HRR / (U_wind * 1000)) ** 0.4 * 5.0)

    # σ_z for each x (metres)
    sig_z = a_z * (X / 1000) ** b_z * 1000   # convert km→m, result in m
    sig_z = np.maximum(sig_z, 2.0)            # floor at 2 m

    # Centreline temperature excess (simplified)
    Q_c   = 0.65 * HRR      # convective fraction ≈ 65 %
    cp_rho = 1.2 * 1005      # density × specific heat (J/m³·K)
    dT    = (Q_c / (cp_rho * U_wind)) / (2 * np.pi * sig_z ** 2) * np.exp(
        -0.5 * ((Z - H_eff) / sig_z) ** 2
    ) * 1e6  # scale to readable values

    # Cap near source for visual clarity
    dT = np.clip(dT, 0, 200)
    return dT.astype(np.float32)


# ── Custom colormaps ───────────────────────────────────────────────────────────

def make_fire_cmap():
    colors_f = [
        (0.06, 0.06, 0.10, 0.0),    # transparent background
        (0.10, 0.10, 0.15, 0.25),
        (0.30, 0.10, 0.02, 0.50),   # dark red
        (0.80, 0.25, 0.00, 0.75),   # orange
        (1.00, 0.65, 0.05, 0.92),   # yellow-orange
        (1.00, 1.00, 0.70, 1.00),   # bright yellow
    ]
    return LinearSegmentedColormap.from_list('fire', colors_f)


FIRE_CMAP = make_fire_cmap()


# ── Simulation state ───────────────────────────────────────────────────────────

class PlumeSimulation:
    def __init__(self):
        self.p       = _empty_particles()
        self.frame   = 0
        self.HRR     = 1500.0
        self.U_wind  = 3.0
        self.pg_cls  = 2
        self._ptr    = 0     # circular buffer pointer

    def _emit(self, n: int):
        """Emit n new particles from the fire source."""
        T_src   = T_AMB + min(600, 12 * (self.HRR / 1000) ** 0.6)
        H_scale = max(20, 4 * (self.HRR / 100) ** 0.25)   # m

        for _ in range(n):
            idx = self._ptr % N_PARTICLES
            self._ptr += 1
            pt = 0 if T_src > T_AMB + 150 else 1

            self.p['x'][idx]   = X_SRC + np.random.uniform(-8, 8)
            self.p['z'][idx]   = Z_SRC + np.random.uniform(0, 15)
            self.p['vx'][idx]  = np.random.normal(0, 0.8)
            self.p['vz'][idx]  = np.random.uniform(2.0, 8.0) * (self.HRR / 500) ** 0.3
            self.p['T'][idx]   = T_src + np.random.normal(0, 30)
            self.p['age'][idx]   = 0
            self.p['max_age'][idx] = MAX_AGE + np.random.randint(-20, 20)
            self.p['ptype'][idx] = pt

    def step(self):
        """Advance physics one frame."""
        dt  = 1.0 / 25     # 25 FPS
        act = self.p['age'] <= self.p['max_age']
        n   = int(np.sum(act))

        # Emit new particles
        self._emit(EMIT_PER_FRAME)

        if n == 0:
            self.frame += 1
            return

        # ── Buoyancy
        dT_over_T    = np.maximum(0, (self.p['T'] - T_AMB)) / (T_AMB + 273.15)
        buoy         = G * dT_over_T         # m/s² upward
        self.p['vz'] += buoy * dt

        # ── Wind drag (relaxation toward U_wind horizontally)
        tau = max(0.5, 20.0 / (self.U_wind + 0.1))
        self.p['vx'] += (self.U_wind - self.p['vx']) * dt / tau

        # ── Turbulent diffusion (depends on PG class)
        a_z = PG_CLASSES[self.pg_cls][3]
        diff = a_z * 0.5
        self.p['vx'] += np.random.normal(0, diff, N_PARTICLES)
        self.p['vz'] += np.random.normal(0, diff * 0.3, N_PARTICLES)

        # ── Integrate positions
        self.p['x'] += self.p['vx'] * dt
        self.p['z'] += self.p['vz'] * dt

        # ── Temperature decay with height (entrainment of cool air)
        H_scale = max(20, 4 * (self.HRR / 100) ** 0.25)
        self.p['T'] = (T_AMB
                       + (self.p['T'] - T_AMB)
                       * np.exp(-dt * (self.p['z'] / H_scale) * 0.3))

        # ── Age all particles
        self.p['age'] += 1

        # ── Kill particles out of domain
        out = ((self.p['x'] > X_MAX * 1.1)
               | (self.p['z'] > Z_MAX * 1.1)
               | (self.p['z'] < -5))
        self.p['age'][out] = self.p['max_age'][out] + 1

        self.frame += 1

    def active_mask(self) -> np.ndarray:
        return self.p['age'] <= self.p['max_age']


# ── Plot setup ─────────────────────────────────────────────────────────────────

def main():
    apply_mpl_style()
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle('Pluma Convectiva de Humo — Dinámica de Dispersión',
                 fontsize=18, fontweight='bold', color=COLORS['primary'], y=0.97)

    ax_main = fig.add_axes([0.04, 0.22, 0.62, 0.70])   # main plume view
    ax_prof = fig.add_axes([0.70, 0.48, 0.27, 0.44])   # T vertical profile
    ax_info = fig.add_axes([0.70, 0.22, 0.27, 0.22])   # key values

    ax_sl_hrr   = fig.add_axes([0.12, 0.14, 0.55, 0.025])
    ax_sl_wind  = fig.add_axes([0.12, 0.10, 0.55, 0.025])
    ax_sl_stab  = fig.add_axes([0.12, 0.06, 0.55, 0.025])

    for ax_sl in (ax_sl_hrr, ax_sl_wind, ax_sl_stab):
        ax_sl.set_facecolor(COLORS['panel'])

    sl_hrr  = Slider(ax_sl_hrr,  'HRR (kW)',       100, 8000, valinit=1500,
                     color=FC['flame'],     valstep=100)
    sl_wind = Slider(ax_sl_wind, 'Viento (m/s)',   0.3,  15,  valinit=3.0,
                     color=COLORS['info'],  valstep=0.1)
    sl_stab = Slider(ax_sl_stab, 'Estabilidad (0=A inestable … 5=F estable)',
                     0, 5, valinit=2, color=COLORS['primary'], valstep=1)

    sim = PlumeSimulation()

    # ── Initial background temperature field
    BG_FIELD = plume_temp_field(sim.HRR, sim.U_wind, sim.pg_cls)
    im = ax_main.imshow(
        BG_FIELD, origin='lower', aspect='auto',
        extent=[0, X_MAX, 0, Z_MAX],
        cmap=FIRE_CMAP, vmin=0, vmax=100, alpha=0.80, zorder=1)

    # ── Particle scatter (smoke & fire)
    fire_sc  = ax_main.scatter([], [], s=[], c=[], cmap='hot',
                               vmin=50, vmax=700, alpha=0.55,
                               linewidths=0, zorder=3)
    smoke_sc = ax_main.scatter([], [], s=[], c=[], cmap='gray',
                               vmin=0, vmax=1, alpha=0.35,
                               linewidths=0, zorder=2)

    # Source marker
    ax_main.axvline(X_SRC, color=FC['flame'], lw=1.5, ls='--', alpha=0.5)
    ax_main.scatter([X_SRC], [Z_SRC + 5], s=120, color=FC['flame'],
                    marker='^', zorder=5, label='Fuente')

    # Effective plume height line (updated later)
    h_line, = ax_main.plot([], [], color=COLORS['accent'], lw=1.5,
                           ls='--', alpha=0.7, label='H_eff pluma')

    ax_main.set_xlim(-20, X_MAX)
    ax_main.set_ylim(0,   Z_MAX)
    ax_main.set_xlabel('Distancia downwind (m)', fontsize=9)
    ax_main.set_ylabel('Altura (m)',              fontsize=9)
    ax_main.grid(True, alpha=0.15)
    ax_main.tick_params(labelsize=8)
    ax_main.legend(fontsize=8, loc='upper right',
                   facecolor=COLORS['panel'], edgecolor=COLORS['grid'])
    ax_main.set_title('Vista lateral del penacho', fontsize=9,
                      color=COLORS['text'], pad=2)

    # ── Vertical profile axes
    ax_prof.set_facecolor(COLORS['bg'])
    ax_prof.set_xlim(T_AMB - 5, T_AMB + 120)
    ax_prof.set_ylim(0, Z_MAX)
    ax_prof.set_xlabel('T (°C)', fontsize=8)
    ax_prof.set_ylabel('Altura (m)', fontsize=8)
    ax_prof.grid(True, alpha=0.2)
    ax_prof.tick_params(labelsize=7)
    ax_prof.set_title('Perfil vertical T a x=50m', fontsize=8,
                      color=COLORS['text'], pad=2)

    # Threshold lines in profile
    for t_thr, lbl, col in (
        (T_AMB + 20, 'SCBA',   COLORS['accent']),
        (T_AMB + 80, 'Quem.',  COLORS['warning']),
    ):
        ax_prof.axvline(t_thr, color=col, lw=1, ls=':', alpha=0.7, label=lbl)
    ax_prof.legend(fontsize=7, facecolor=COLORS['panel'], edgecolor=COLORS['grid'])

    prof_line, = ax_prof.plot([], [], color=FC['flame'], lw=2)

    # ── Info panel
    ax_info.set_facecolor(COLORS['panel'])
    ax_info.set_xlim(0, 10)
    ax_info.set_ylim(0, 10)
    ax_info.axis('off')
    info_texts = [ax_info.text(0.5, 9.5 - i * 2.0, '', fontsize=9,
                               color=COLORS['text'], va='top')
                  for i in range(5)]

    # ── Update slider-dependent background
    def update_background(_=None):
        sim.HRR     = sl_hrr.val
        sim.U_wind  = sl_wind.val
        sim.pg_cls  = int(sl_stab.val)
        sim.p       = _empty_particles()    # reset particles on param change
        sim._ptr    = 0
        BG = plume_temp_field(sim.HRR, sim.U_wind, sim.pg_cls)
        im.set_data(BG)
        fig.canvas.draw_idle()

    sl_hrr.on_changed(update_background)
    sl_wind.on_changed(update_background)
    sl_stab.on_changed(update_background)

    # ── Animation function
    def animate(_frame):
        sim.step()
        act  = sim.active_mask()
        x_a  = sim.p['x'][act]
        z_a  = sim.p['z'][act]
        T_a  = sim.p['T'][act]
        pt_a = sim.p['ptype'][act]
        age_a = sim.p['age'][act]
        max_a = sim.p['max_age'][act]

        fire_idx  = (pt_a == 0)
        smoke_idx = (pt_a == 1)

        # Size decreases with age
        age_frac = age_a / np.maximum(max_a, 1)
        sizes    = np.maximum(10, 80 * (1 - age_frac))

        # ── Fire particles
        if np.any(fire_idx):
            fire_sc.set_offsets(np.column_stack([x_a[fire_idx], z_a[fire_idx]]))
            fire_sc.set_array(T_a[fire_idx])
            fire_sc.set_sizes(sizes[fire_idx])
        else:
            fire_sc.set_offsets(np.empty((0, 2)))

        # ── Smoke particles
        if np.any(smoke_idx):
            smoke_vals = age_frac[smoke_idx]
            smoke_sc.set_offsets(np.column_stack([x_a[smoke_idx], z_a[smoke_idx]]))
            smoke_sc.set_array(smoke_vals)
            smoke_sc.set_sizes(sizes[smoke_idx] * 1.4)
        else:
            smoke_sc.set_offsets(np.empty((0, 2)))

        # ── Effective plume centreline (Briggs rise)
        H_eff = max(5.0, 1.6 * (sim.HRR / (sim.U_wind * 1000)) ** 0.4 * 5.0)
        xs_pl = np.linspace(5, X_MAX, 100)
        a_z   = PG_CLASSES[sim.pg_cls][3]
        # Plume centre rises then levels off (simplified)
        H_arr = H_eff * (1 - np.exp(-xs_pl / 200))
        h_line.set_data(xs_pl, H_arr)

        # ── Vertical T profile at x=50 m
        zs_pr = np.linspace(0, Z_MAX, 200)
        sig_z = max(2.0, a_z * (50 / 1000) ** 0.75 * 1000)
        Q_c   = 0.65 * sim.HRR
        cp_rho = 1206.0
        dT_pr = (Q_c / (cp_rho * sim.U_wind) / (2 * np.pi * sig_z ** 2)
                 * np.exp(-0.5 * ((zs_pr - H_eff) / sig_z) ** 2) * 1e6)
        dT_pr = np.clip(dT_pr, 0, 200)
        T_pr  = T_AMB + dT_pr
        prof_line.set_data(T_pr, zs_pr)
        ax_prof.set_xlim(T_AMB - 5, T_AMB + max(20, float(dT_pr.max()) * 1.2))

        # ── Info panel
        H_max = float(np.max(H_arr))
        T_max_prof = float(T_pr.max())
        stab_label = PG_CLASSES[sim.pg_cls][0]
        info_rows = [
            (f'HRR:        {sim.HRR:.0f} kW',      COLORS['warning']),
            (f'H eff pluma: {H_eff:.0f} m',          COLORS['accent']),
            (f'T max (50m): {T_max_prof:.0f} °C',    FC['flame']),
            (f'Viento:      {sim.U_wind:.1f} m/s',   COLORS['info']),
            (f'Estabilidad: {stab_label[:20]}', COLORS['primary']),
        ]
        for txt_obj, (txt, col) in zip(info_texts, info_rows):
            txt_obj.set_text(txt)
            txt_obj.set_color(col)

        # Title update with particle count
        n_act = int(np.sum(act))
        ax_main.set_title(
            f'Vista lateral del penacho   '
            f'[{n_act} partículas activas  |  frame {sim.frame}]',
            fontsize=8, color=COLORS['text'], pad=2)

        return fire_sc, smoke_sc, h_line, prof_line, *info_texts

    anim = animation.FuncAnimation(
        fig, animate,
        interval=40,   # ms → 25 FPS
        blit=False,    # full redraw (needed for ax_main title update)
        cache_frame_data=False,
    )

    plt.show()


if __name__ == '__main__':
    main()
