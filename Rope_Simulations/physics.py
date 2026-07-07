"""
Núcleo de física — Física del Rescate con cuerdas.

Funciones PURAS (sin pygame ni matplotlib): reciben números, devuelven
números o dicts. Son la única fuente de verdad de los modelos físicos y
están cubiertas por tests/test_physics.py.

Separar el modelo (este archivo) de la vista (las sims) permite:
  • Testear la física con casos canónicos conocidos.
  • Alimentar las MISMAS funciones con datos reales de instrumentación
    (celda de carga → ESP32 → MQTT → InfluxDB) y comparar predicho vs medido.

Convención de unidades:
  • masas en kg, longitudes en metros, ángulos en grados (salvo nota).
  • fuerzas/tensiones en kN.
"""

import math

from config import G


# ══════════════════════════════════════════════════════════════════════
#  Conversión carga → peso
# ══════════════════════════════════════════════════════════════════════

def weight_kn(mass_kg):
    """Peso en kN de una masa en kg.  W = m·g / 1000."""
    return mass_kg * G / 1000.0


# ══════════════════════════════════════════════════════════════════════
#  Ventaja mecánica simple (poleas / block & tackle)
# ══════════════════════════════════════════════════════════════════════

def pulley_effort(load, ma, efficiency=1.0):
    """
    Esfuerzo (tensión en la cuerda) de una VM simple n:1.

      F_esfuerzo = carga / (n · eficiencia)

    n = ventaja mecánica (nº de tramos que sostienen la carga). Con polea
    ideal (eficiencia 1) y n tramos, cada tramo lleva carga/n. La eficiencia
    < 1 modela la fricción de las poleas. Devuelve la fuerza en las mismas
    unidades que `load`.
    """
    if ma <= 0 or efficiency <= 0:
        return float('inf')
    return load / (ma * efficiency)


def pulley_haul_distance(lift_distance, ma):
    """Cuerda a tirar para subir la carga `lift_distance`.  s = n · h."""
    return ma * lift_distance


# ══════════════════════════════════════════════════════════════════════
#  Módulo 03 — Anclaje en V
# ══════════════════════════════════════════════════════════════════════

def v_anchor_tensions(W_kn, theta_deg, phi_deg=0.0):
    """
    Tensiones en los dos brazos de un anclaje en V.

    theta_deg : ángulo de apertura del V (entre brazos).
    phi_deg   : desviación de la carga respecto a la bisectriz.

    Caso simétrico (φ=0):  T = W / (2·cos(θ/2))
    Caso general:          T₁ = W·sin(θ/2 + φ)/sin θ   (brazo izquierdo)
                           T₂ = W·sin(θ/2 − φ)/sin θ   (brazo derecho)

    Brazo flojo (T ≤ 0) cuando |φ| ≥ θ/2.
    Devuelve (T1, T2) en kN. En la singularidad θ≈0/180° devuelve un
    valor grande proporcional a W para señalar "fuerza divergente".
    """
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    half = theta / 2.0
    sin_t = math.sin(theta)
    if abs(sin_t) < 1e-2:
        return 99.0 * W_kn, 99.0 * W_kn
    t1 = W_kn * math.sin(half + phi) / sin_t
    t2 = W_kn * math.sin(half - phi) / sin_t
    return t1, t2


# ══════════════════════════════════════════════════════════════════════
#  Módulo 04 — Factor de caída
# ══════════════════════════════════════════════════════════════════════

def fall_factor(fall_distance_m, rope_length_m):
    """Factor de caída FF = distancia de caída / longitud de cuerda."""
    if rope_length_m <= 0:
        return 0.0
    return fall_distance_m / rope_length_m


def impact_velocity(fall_distance_m):
    """Velocidad al final de la caída libre.  v = √(2·g·d)."""
    return math.sqrt(2.0 * G * max(fall_distance_m, 0.0))


def impact_force_kn(mass_kg, ff, epsilon):
    """
    Fuerza de choque con modelo de desaceleración uniforme.

      F = m·g·(1 + FF/ε)

    ε = elongación relativa de la cuerda (dinámica ≈ 0.35, estática ≈ 0.03).
    Menor ε → mayor fuerza de choque.
    """
    if epsilon <= 0:
        return float('inf')
    return mass_kg * G * (1.0 + ff / epsilon) / 1000.0


# ══════════════════════════════════════════════════════════════════════
#  Módulo 14 — Distribución multi-anclaje auto-ecualizado
# ══════════════════════════════════════════════════════════════════════

def anchor_force_distribution(alpha_degs, W_kn):
    """
    Distribución de la componente vertical de la carga entre N tirantes
    de un sistema auto-ecualizado.

      F_i = W · cos(α_i) / Σ cos(α_j)

    alpha_degs : lista de ángulos de cada tirante respecto a la vertical.
    Devuelve lista de fuerzas verticales F_i (kN). Si todos los cosenos
    son ~0 reparte uniformemente (caso degenerado).
    """
    n = len(alpha_degs)
    if n == 0:
        return []
    cosines = [max(math.cos(math.radians(a)), 0.0) for a in alpha_degs]
    cos_sum = sum(cosines)
    if cos_sum < 1e-3:
        return [W_kn / n] * n
    return [W_kn * c / cos_sum for c in cosines]


def sling_tension(force_kn, alpha_deg):
    """
    Tensión a lo largo del eje del tirante.  T = F / cos(α).
    F es la componente vertical asignada al tirante.
    """
    cos_a = math.cos(math.radians(alpha_deg))
    if cos_a < 1e-2:
        return 99.99
    return force_kn / cos_a


# ══════════════════════════════════════════════════════════════════════
#  Módulos 11 / 21 — Tirolesa / highline con carga puntual
# ══════════════════════════════════════════════════════════════════════

def rope_length_for_sag(L, h_A, h_B, d):
    """
    Longitud de cuerda cuando la carga está en el centro con flecha d
    (medida verticalmente desde el punto medio de la recta A-B).
    Anclajes A=(0,h_A), B=(L,h_B).
    """
    y_P = (h_A + h_B) / 2.0 - d
    lPA = math.sqrt((L / 2.0) ** 2 + (y_P - h_A) ** 2)
    lPB = math.sqrt((L / 2.0) ** 2 + (y_P - h_B) ** 2)
    return lPA + lPB


def span_for_rope(rope_len, d, h_A=0.0, h_B=0.0, iters=60):
    """
    Inverso de rope_length_for_sag: dada la LONGITUD de cuerda y la flecha d
    (con la carga al centro), devuelve la DISTANCIA horizontal entre anclajes.

    rope_length_for_sag crece de forma monótona con L, así que se resuelve por
    bisección. Para anclajes a nivel: L = √(S² − 4·d²).
    Si la cuerda es demasiado corta para esa flecha, devuelve 0.
    """
    lo, hi = 0.0, rope_len
    if rope_length_for_sag(0.0, h_A, h_B, d) >= rope_len:
        return 0.0
    for _ in range(iters):
        mid = (lo + hi) * 0.5
        if rope_length_for_sag(mid, h_A, h_B, d) < rope_len:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def solve_load_y(x, L, h_A, h_B, S, iters=64):
    """
    Bisección: altura y_P del punto de carga en x, para una cuerda
    inextensible de longitud total S, tal que |AP| + |PB| = S.
    A medida que y_P baja, la longitud requerida crece.
    """
    if x <= 0.005 * L:
        return float(h_A)
    if x >= 0.995 * L:
        return float(h_B)

    def length(y):
        return (math.sqrt(x ** 2 + (y - h_A) ** 2)
                + math.sqrt((L - x) ** 2 + (y - h_B) ** 2))

    t = x / L
    y_hi = h_A * (1.0 - t) + h_B * t   # carga sobre la recta A-B (long. mínima)
    y_lo = y_hi - S
    for _ in range(iters):
        y_mid = (y_lo + y_hi) * 0.5
        if length(y_mid) < S:
            y_hi = y_mid
        else:
            y_lo = y_mid
    return (y_lo + y_hi) * 0.5


def tyrolean_forces(x, L, h_A, h_B, y_P, W_kn):
    """
    Equilibrio estático en el punto de carga P=(x, y_P) de una tirolesa
    con anclajes A=(0,h_A), B=(L,h_B).

      T_B = W·|PB| / [(L−x)·(h_A−y_P)/x + (h_B−y_P)]
      T_A = T_B·(L−x)·|PA| / (x·|PB|)

    Devuelve dict con T_A, T_B (kN), longitudes, ángulos bajo la horizontal
    en cada anclaje y el ángulo V entre los dos segmentos.
    """
    x = max(1e-4 * L, min(x, (1 - 1e-4) * L))
    lPA = math.sqrt(x ** 2 + (y_P - h_A) ** 2)
    lPB = math.sqrt((L - x) ** 2 + (y_P - h_B) ** 2)

    denom = (L - x) * (h_A - y_P) / x + (h_B - y_P)
    if abs(denom) < 1e-9 or lPA < 1e-9 or lPB < 1e-9:
        T_A = T_B = 999.0
    else:
        T_B = W_kn * lPB / denom
        T_A = T_B * (L - x) * lPA / (x * lPB)

    alpha_A = math.degrees(math.atan2(h_A - y_P, x))
    alpha_B = math.degrees(math.atan2(h_B - y_P, L - x))

    uA = (-x / lPA, (h_A - y_P) / lPA)
    uB = ((L - x) / lPB, (h_B - y_P) / lPB)
    cos_v = max(-1.0, min(1.0, uA[0] * uB[0] + uA[1] * uB[1]))
    v_angle = math.degrees(math.acos(cos_v))

    return {
        'T_A': T_A, 'T_B': T_B, 'W': W_kn,
        'y_P': y_P, 'lPA': lPA, 'lPB': lPB,
        'alpha_A': alpha_A, 'alpha_B': alpha_B,
        'uA': uA, 'uB': uB, 'v_angle': v_angle,
    }


# ── Variante simétrica (anclajes a la misma altura): modelo de la camilla ──

def highline_rope_length(span, d_center):
    """Longitud de cuerda de una tirolesa horizontal con flecha central d."""
    half = span / 2.0
    return 2.0 * math.sqrt(half * half + d_center * d_center)


def solve_sag_at(x, span, rope_length, iters=64):
    """
    Bisección: flecha d en la posición x para una tirolesa horizontal
    inextensible.  √(x²+d²) + √((L−x)²+d²) = S.

    En los extremos la bisección converge a la flecha residual real (~S−L);
    NO se devuelve 0 — eso daba una cuerda casi recta y tensiones irreales.
    """
    x = max(1e-4 * span, min(x, (1 - 1e-4) * span))
    lo, hi = 0.0001, rope_length * 0.5
    for _ in range(iters):
        mid = (lo + hi) * 0.5
        s = math.sqrt(x * x + mid * mid) + math.sqrt((span - x) ** 2 + mid * mid)
        if s < rope_length:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def highline_forces(x, span, d, mass_kg):
    """
    Fuerzas en el punto de carga de una tirolesa horizontal (h_A = h_B).

      H   = W·x·(L−x) / (d·L)        (componente horizontal, igual ambos lados)
      T_L = H / cos(α_izq)
      T_R = H / cos(α_der)
      V   = 180° − α_izq − α_der
    """
    W_kn = weight_kn(mass_kg)
    x = max(0.01 * span, min(x, 0.99 * span))
    alpha_L = math.atan2(d, x)
    alpha_R = math.atan2(d, span - x)
    H = W_kn * x * (span - x) / (d * span) if d > 0.001 else 0.0
    T_L = H / math.cos(alpha_L) if math.cos(alpha_L) > 1e-6 else 999.0
    T_R = H / math.cos(alpha_R) if math.cos(alpha_R) > 1e-6 else 999.0
    v_angle = 180.0 - math.degrees(alpha_L) - math.degrees(alpha_R)
    return {
        'W': W_kn, 'H': H, 'T_L': T_L, 'T_R': T_R,
        'alpha_L_deg': math.degrees(alpha_L),
        'alpha_R_deg': math.degrees(alpha_R),
        'v_angle': v_angle, 'd': d, 'x': x,
    }


def highline_pulley_forces(x, span, d, mass_kg):
    """
    Carga sobre una POLEA/carro que rueda LIBRE en la tirolesa, retenida en la
    posición x por una línea de control (tracción/retención).

    Como la polea no tiene fricción, la cuerda tiene UNA sola tensión a ambos
    lados (los dos anclajes ven lo mismo). La línea de control aporta la
    componente horizontal que mantiene el carro fuera del centro.

      α_izq = atan2(d, x);   α_der = atan2(d, span−x)
      T (cuerda, igual A y B) = W / (sin α_izq + sin α_der)     (equil. vertical)
      F_control               = T · (cos α_izq − cos α_der)     (equil. horizontal)
        F_control > 0 → la línea tira hacia B (derecha); < 0 → hacia A.
        En el centro α_izq = α_der → F_control = 0 (no hace falta sostener).
    """
    W_kn = weight_kn(mass_kg)
    x = max(0.01 * span, min(x, 0.99 * span))
    alpha_L = math.atan2(d, x)
    alpha_R = math.atan2(d, span - x)
    denom = math.sin(alpha_L) + math.sin(alpha_R)
    T = W_kn / denom if denom > 1e-6 else 999.0
    f_control = T * (math.cos(alpha_L) - math.cos(alpha_R))
    v_angle = 180.0 - math.degrees(alpha_L) - math.degrees(alpha_R)
    return {
        'W': W_kn, 'T': T, 'f_control': f_control,
        'alpha_L_deg': math.degrees(alpha_L),
        'alpha_R_deg': math.degrees(alpha_R),
        'v_angle': v_angle, 'd': d, 'x': x,
    }


# ══════════════════════════════════════════════════════════════════════
#  Módulo 02 — Suma vectorial de fuerzas
# ══════════════════════════════════════════════════════════════════════

def resultant(forces):
    """
    Resultante de una lista de fuerzas [(ángulo_deg, magnitud), ...].
    Devuelve dict con componentes, magnitud R, ángulo y eficiencia
    (R / suma aritmética de magnitudes, en %).
    """
    cx = sum(m * math.cos(math.radians(a)) for a, m in forces)
    cy = sum(m * math.sin(math.radians(a)) for a, m in forces)
    R = math.hypot(cx, cy)
    sum_arith = sum(m for _, m in forces)
    efficiency = R / sum_arith * 100.0 if sum_arith > 0 else 0.0
    return {
        'cx': cx, 'cy': cy, 'R': R,
        'angle_deg': math.degrees(math.atan2(cy, cx)),
        'efficiency': efficiency,
    }


# ══════════════════════════════════════════════════════════════════════
#  Módulo 17b — Nudos
# ══════════════════════════════════════════════════════════════════════

def knot_mbs(rope_mbs_kn, efficiency_pct):
    """Resistencia de la cuerda con el nudo.  MBS_nudo = MBS · ef/100."""
    return rope_mbs_kn * efficiency_pct / 100.0


# ══════════════════════════════════════════════════════════════════════
#  Factor de seguridad (transversal)
# ══════════════════════════════════════════════════════════════════════

def safety_factor(mbs_kn, load_kn):
    """Factor de seguridad = resistencia / carga.  ∞ si la carga es ~0."""
    if load_kn <= 1e-3:
        return float('inf')
    return mbs_kn / load_kn
