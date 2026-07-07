"""
Casos canónicos de la física de rescate. Cada test fija un resultado
conocido del dominio (texto en pantalla de las sims, tablas NFPA/UIAA),
de modo que cualquier regresión en physics.py se detecte de inmediato.

Correr:  pytest -q      (desde la raíz del repo)
"""

import math

import pytest

import physics as phx
from config import G


# ── Anclaje en V ──────────────────────────────────────────────────────

def test_v_anchor_120_simetrico_es_100pct_W():
    """A 120° simétrico cada brazo soporta el 100 % de la carga."""
    t1, t2 = phx.v_anchor_tensions(1.0, 120.0, 0.0)
    assert t1 == pytest.approx(1.0, abs=1e-9)
    assert t2 == pytest.approx(1.0, abs=1e-9)


def test_v_anchor_angulo_estrecho_reparte_menos():
    """A 60° simétrico cada brazo soporta W/(2·cos30°) ≈ 0.577 W."""
    t1, t2 = phx.v_anchor_tensions(1.0, 60.0, 0.0)
    assert t1 == pytest.approx(1.0 / (2 * math.cos(math.radians(30))), abs=1e-9)
    assert t1 == pytest.approx(t2)


def test_v_anchor_brazo_flojo_cuando_phi_supera_mitad():
    """Brazo flojo (T ≤ 0) cuando |φ| ≥ θ/2."""
    t1, t2 = phx.v_anchor_tensions(1.0, 60.0, 30.0)
    assert t2 == pytest.approx(0.0, abs=1e-9)
    assert t1 > 0


# ── Factor de caída ─────────────────────────────────────────────────────

def test_fall_factor_basico():
    assert phx.fall_factor(4.0, 2.0) == pytest.approx(2.0)


def test_impact_force_dinamica_vs_estatica():
    """Misma caída: cuerda estática (ε bajo) genera mucha más fuerza."""
    f_dyn = phx.impact_force_kn(100, ff=1.0, epsilon=0.35)
    f_sta = phx.impact_force_kn(100, ff=1.0, epsilon=0.03)
    assert f_dyn == pytest.approx(100 * G * (1 + 1 / 0.35) / 1000)
    assert f_sta > f_dyn * 3


def test_impact_velocity():
    assert phx.impact_velocity(2.0) == pytest.approx(math.sqrt(2 * G * 2.0))


# ── Multi-anclaje ────────────────────────────────────────────────────────

def test_multi_anclaje_simetrico_reparte_igual():
    """3 tirantes simétricos → 1/3 de la carga cada uno."""
    forces = phx.anchor_force_distribution([20, 20, 20], 9.0)
    assert forces == pytest.approx([3.0, 3.0, 3.0])


def test_multi_anclaje_mas_vertical_carga_mas():
    """El tirante más vertical (menor α) recibe más fuerza."""
    forces = phx.anchor_force_distribution([0, 45, 45], 10.0)
    assert forces[0] > forces[1]
    assert sum(forces) == pytest.approx(10.0)


def test_sling_tension_crece_con_el_angulo():
    assert phx.sling_tension(5.0, 0.0) == pytest.approx(5.0)
    assert phx.sling_tension(5.0, 60.0) == pytest.approx(10.0)


# ── Tirolesa ─────────────────────────────────────────────────────────────

def test_tirolesa_simetrica_tensiones_iguales():
    """Carga al centro, anclajes a igual altura → T_A = T_B."""
    L, d = 30.0, 1.5
    S = phx.rope_length_for_sag(L, 0.0, 0.0, d)
    y_P = phx.solve_load_y(L / 2, L, 0.0, 0.0, S)
    f = phx.tyrolean_forces(L / 2, L, 0.0, 0.0, y_P, 1.0)
    assert f['T_A'] == pytest.approx(f['T_B'], rel=1e-6)


def test_solve_load_y_recupera_la_flecha_central():
    """rope_length_for_sag y solve_load_y son inversos al centro."""
    L, d = 30.0, 1.5
    S = phx.rope_length_for_sag(L, 0.0, 0.0, d)
    y_P = phx.solve_load_y(L / 2, L, 0.0, 0.0, S)
    assert y_P == pytest.approx(-d, abs=1e-3)


def test_menos_flecha_mas_tension():
    """Regla de oro: menor flecha → mayor tensión."""
    L = 30.0
    def t_max(d):
        S = phx.rope_length_for_sag(L, 0.0, 0.0, d)
        y = phx.solve_load_y(L / 2, L, 0.0, 0.0, S)
        f = phx.tyrolean_forces(L / 2, L, 0.0, 0.0, y, 1.0)
        return max(f['T_A'], f['T_B'])
    assert t_max(0.3) > t_max(3.0)


def test_highline_simetrica():
    f = phx.highline_forces(15.0, 30.0, 1.5, 100)
    assert f['T_L'] == pytest.approx(f['T_R'], rel=1e-9)


def test_span_for_rope_es_inverso_de_rope_length():
    """span_for_rope invierte rope_length_for_sag (anclajes a nivel)."""
    S = phx.rope_length_for_sag(30.0, 0.0, 0.0, 1.5)   # cuerda para L=30, d=1.5
    L = phx.span_for_rope(S, 1.5)
    assert L == pytest.approx(30.0, abs=1e-3)
    # fórmula directa a nivel: L = sqrt(S^2 - 4 d^2)
    assert L == pytest.approx(math.sqrt(S ** 2 - 4 * 1.5 ** 2), abs=1e-3)


def test_span_cero_si_cuerda_demasiado_corta():
    assert phx.span_for_rope(2.0, 1.5) == pytest.approx(0.0, abs=1e-6)


# ── Ventaja mecánica (poleas) ────────────────────────────────────────

def test_pulley_effort_ideal():
    """n:1 ideal → esfuerzo = carga / n (como la figura 1-4)."""
    assert phx.pulley_effort(100, 1) == pytest.approx(100)
    assert phx.pulley_effort(100, 2) == pytest.approx(50)
    assert phx.pulley_effort(100, 3) == pytest.approx(100 / 3)
    assert phx.pulley_effort(100, 4) == pytest.approx(25)


def test_pulley_effort_con_friccion():
    """La eficiencia < 1 sube el esfuerzo necesario."""
    assert phx.pulley_effort(100, 4, 0.8) == pytest.approx(100 / (4 * 0.8))


def test_pulley_haul_distance():
    """Para subir 10 cm con 4:1 hay que tirar 40 cm (conservación del trabajo)."""
    assert phx.pulley_haul_distance(10, 4) == pytest.approx(40)


# ── Tirolesa con polea + línea de control (Caso 1) ───────────────────────

def test_pulley_centro_sin_control():
    """Carro al centro: no hace falta línea de control (F = 0)."""
    f = phx.highline_pulley_forces(15.0, 30.0, 1.5, 100)
    assert f['f_control'] == pytest.approx(0.0, abs=1e-9)


def test_pulley_control_tira_hacia_anclaje_cercano():
    """Fuera del centro la línea sostiene el carro hacia el anclaje cercano."""
    cerca_B = phx.highline_pulley_forces(27.0, 30.0, 0.9, 100)
    cerca_A = phx.highline_pulley_forces(3.0, 30.0, 0.9, 100)
    assert cerca_B['f_control'] > 0      # hacia B (derecha)
    assert cerca_A['f_control'] < 0      # hacia A (izquierda)


def test_pulley_tension_coincide_en_centro_con_punto_fijo():
    """En el centro, polea y punto-fijo dan la misma tensión de cuerda."""
    fp = phx.highline_pulley_forces(15.0, 30.0, 1.5, 100)
    fx = phx.highline_forces(15.0, 30.0, 1.5, 100)
    assert fp['T'] == pytest.approx(fx['T_L'], rel=1e-9)


# ── Vectores ─────────────────────────────────────────────────────────────

def test_resultante_alineada_suma_aritmetica():
    r = phx.resultant([(0.0, 3.0), (0.0, 5.0)])
    assert r['R'] == pytest.approx(8.0)
    assert r['efficiency'] == pytest.approx(100.0)


def test_resultante_opuesta_se_cancela():
    r = phx.resultant([(0.0, 5.0), (180.0, 5.0)])
    assert r['R'] == pytest.approx(0.0, abs=1e-9)


def test_resultante_perpendicular():
    r = phx.resultant([(0.0, 3.0), (90.0, 4.0)])
    assert r['R'] == pytest.approx(5.0)
    assert r['angle_deg'] == pytest.approx(math.degrees(math.atan2(4, 3)))


# ── Nudos y factor de seguridad ─────────────────────────────────────────

def test_nudo_ocho_80pct():
    """Nudo en ocho: 80 % del MBS (estándar NFPA/UIAA)."""
    assert phx.knot_mbs(30.0, 80) == pytest.approx(24.0)


def test_safety_factor():
    assert phx.safety_factor(30.0, 3.0) == pytest.approx(10.0)
    assert phx.safety_factor(30.0, 0.0) == math.inf
