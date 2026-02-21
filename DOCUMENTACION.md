# Física del Rescate — Documentación de Ejemplos

Colección de simuladores interactivos de física aplicada al rescate con cuerdas.
Cada módulo es autoejecutable y combina visualización en tiempo real con cálculos precisos.

## Dependencias

```
pip install -r requirements.txt
```

Los módulos 01–03 y 05–09 usan **Matplotlib**. Los módulos 04 y 06 y 10–15 usan **Pygame**.

## Archivo de configuración compartida

`config.py` centraliza constantes físicas, paleta de colores (Matplotlib y Pygame) y el
estilo visual oscuro. Todos los módulos lo importan.

| Constante           | Valor   | Significado                              |
|---------------------|---------|------------------------------------------|
| `G`                 | 9.81    | Gravedad (m/s²)                          |
| `ROPE_STATIC_MBS`   | 30.0 kN | Rotura mínima cuerda estática 11 mm      |
| `ROPE_DYNAMIC_MBS`  | 24.0 kN | Rotura mínima cuerda dinámica 10 mm      |
| `NFPA_WORK_LOAD`    | 13.5 kN | Carga de trabajo NFPA                    |
| `UIAA_MAX_IMPACT`   | 12.0 kN | Fuerza de choque máxima UIAA             |

---

## Módulo 01 — ¿Qué es un Newton?

**Archivo:** `01_fuerza_y_newton.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 01_fuerza_y_newton.py`

### Concepto

Introduce la ley fundamental `F = m × a` y su aplicación directa al rescate: el
**peso** de una carga es `W = m × g`. Permite comparar visualmente órdenes de magnitud
(Newtons, kilo-Newtons) frente a referencias de rescate.

### Fórmulas

```
F = m · a
Peso (N) = masa (kg) × 9.81 m/s²
1 kN = 1000 N ≈ 102 kg de peso
```

### Controles

| Control | Función |
|---------|---------|
| Deslizador **Masa (kg)** | 1 – 250 kg |
| Deslizador **Aceleración (m/s²)** | 0.1 – 30 m/s² |

### Visualizaciones

- **Figura humana + flecha de fuerza** proporcional a F.
- **Barras comparativas** (fuerza actual, peso estático, rescatista+paciente 160 kg,
  fuerza de choque estimada, carga NFPA, rotura cuerda).
- **Curva F vs masa** para la aceleración seleccionada.

---

## Módulo 02 — Vectores y Suma de Fuerzas

**Archivo:** `02_vectores_fuerzas.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 02_vectores_fuerzas.py`

### Concepto

Demuestra que las fuerzas **no se suman aritméticamente**: son vectores con magnitud y
dirección. La resultante de dos fuerzas en un anclaje es menor que su suma escalar
salvo que apunten en la misma dirección.

### Fórmula

```
R = √(F₁² + F₂² + 2·F₁·F₂·cos θ)
Eficiencia vectorial = |R| / (|F₁| + |F₂|)
```

### Controles

| Control | Función |
|---------|---------|
| **Ángulo F₁ (°)** | −180 a 180° |
| **Magnitud F₁ (kN)** | 0.1 – 5.0 kN |
| **Ángulo F₂ (°)** | −180 a 180° |
| **Magnitud F₂ (kN)** | 0.1 – 5.0 kN |

### Visualizaciones

- Diagrama vectorial con paralelogramo de fuerzas.
- Arco del ángulo entre F₁ y F₂.
- Panel de interpretación de seguridad (ángulo estrecho / moderado / amplio).

---

## Módulo 03 — Anclaje en V

**Archivo:** `03_anclaje_en_v.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 03_anclaje_en_v.py`

### Concepto

Analiza cómo el **ángulo de apertura del anclaje en V** multiplica la fuerza en cada
brazo. Regla de oro: nunca superar 90°; a 120° cada brazo soporta el 100 % de la carga.

### Fórmula

```
F_brazo = W / (2 · cos(θ/2))

θ =   0° → F = 0.50 W
θ =  60° → F = 0.58 W
θ =  90° → F = 0.71 W
θ = 120° → F = 1.00 W  ← límite crítico
θ = 150° → F = 1.93 W  ← peligroso
```

### Controles

| Control | Función |
|---------|---------|
| **Ángulo V (°)** | 0 – 175° |
| **Carga (kg)** | 10 – 300 kg |

### Visualizaciones

- Diagrama del anclaje en V con colores de alerta según ángulo.
- Curva ángulo vs multiplicador de fuerza con zonas coloreadas.
- Indicador **SEGURO / PRECAUCIÓN / PELIGROSO**.

---

## Módulo 04 — Factor de Caída

**Archivo:** `04_factor_de_caida.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 04_factor_de_caida.py`

### Concepto

Simula visualmente una caída y calcula la **fuerza de choque** según el factor de caída
y el tipo de cuerda. Ilustra por qué usar cuerda estática donde hay posibilidad de caída
es extremadamente peligroso.

### Fórmula

```
Factor de caída = distancia_caída / longitud_cuerda

F_choque = m·g · (1 + √(1 + 2·ff·k))
  k ≈ 5.7  (cuerda dinámica, elongación ~35%)
  k ≈ 58.0 (cuerda estática, elongación ~3%)
```

### Controles

| Tecla | Función |
|-------|---------|
| `1` | FF = 0.25 |
| `2` | FF = 0.50 |
| `3` | FF = 1.00 |
| `4` | FF = 2.00 |
| `ESPACIO` | Iniciar caída |
| `R` | Reiniciar |
| `ESC` | Salir |

### Visualizaciones

- Animación del escalador cayendo con oscilación amortiguada post-impacto.
- Color de cuerda cambia a rojo según la intensidad de la fuerza.
- Barras comparativas dinámica vs estática con referencia UIAA 12 kN.

---

## Módulo 05 — Elasticidad de la Cuerda

**Archivo:** `05_elasticidad_cuerda.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 05_elasticidad_cuerda.py`

### Concepto

Compara las curvas **fuerza-elongación** de cuatro tipos de cuerda y muestra cómo el
**área bajo la curva** (energía absorbida) determina la fuerza de choque transmitida.

### Tipos de cuerda modelados

| Tipo | Elongación máx. | MBS |
|------|----------------|-----|
| Dinámica 10 mm | 35 % | 24 kN |
| Semiestática 10.5 mm | 6 % | 28 kN |
| Estática 11 mm | 3 % | 30 kN |
| Dyneema 8 mm | 1.5 % | 32 kN |

### Modelo matemático

```
F = F_max · (ε / ε_max)^p
Energía = ∫F dε  (área bajo la curva, kN·%)
```

### Controles

| Control | Función |
|---------|---------|
| **Fuerza aplicada (kN)** | 0.1 – 25 kN |

### Visualizaciones

- Curvas F vs elongación de todos los tipos.
- Área de energía absorbida a la fuerza seleccionada.
- Barras comparativas de capacidad de absorción.

---

## Módulo 06 — Ventaja Mecánica y Poleas

**Archivo:** `06_ventaja_mecanica_poleas.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 06_ventaja_mecanica_poleas.py`

### Concepto

Visualiza cuatro sistemas de poleas y su **ventaja mecánica (VM)**: cuánta fuerza se
necesita para mover una carga dada. A mayor VM, menos fuerza pero más cuerda a tirar.

### Sistemas disponibles

| Sistema | VM | Poleas |
|---------|----|--------|
| 1:1 (redirección simple) | 1 | 1 fija |
| 2:1 (polea móvil) | 2 | 1 móvil |
| 3:1 Z-rig | 3 | 1 fija + 1 móvil |
| 4:1 compuesto | 4 | 2+2 |

### Fórmulas

```
F_aplicada = Carga / VM
Eficiencia real = 0.90 por polea (con fricción)
Regla: VM × distancia_tirón = distancia_carga
```

### Controles

| Tecla | Función |
|-------|---------|
| `1–4` | Seleccionar sistema |
| `ESPACIO` (mantener) | Animar tirón |
| `F` | Activar/desactivar fricción |
| `↑/↓` | Ajustar carga ±10 kg |
| `ESC` | Salir |

---

## Módulo 07 — Fuerzas en la Tirolesa

**Archivo:** `07_tirolesa_fuerzas.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 07_tirolesa_fuerzas.py`

### Concepto

Muestra la relación inversa entre la **flecha (sag)** de la tirolesa y la **tensión en
los anclajes**. Una tirolesa "bien tensa" puede ser catastrófica.

### Fórmula

```
T = W · L / (4 · d)
donde:
  T = tensión en los anclajes
  W = peso de la carga
  L = longitud del vano
  d = flecha

Ejemplos para L=30 m, W=1 kN:
  2 % de flecha → T = 12.5 kN (12.5× W)
  5 % de flecha → T = 5.0 kN
 10 % de flecha → T = 2.5 kN
```

### Controles

| Control | Función |
|---------|---------|
| **Vano L (m)** | 5 – 100 m |
| **Flecha (%)** | 0.5 – 20 % |
| **Carga (kg)** | 10 – 300 kg |

### Visualizaciones

- Diagrama de la tirolesa con flechas de tensión en anclajes.
- Curva flecha vs tensión con zonas NFPA y MBS.
- Panel informativo con tabla de referencia.

---

## Módulo 08 — Fuerza de Choque

**Archivo:** `08_fuerza_de_choque.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 08_fuerza_de_choque.py`

### Concepto

Calcula la fuerza de choque usando la **fórmula de Dodero** en función del factor de
caída, la masa y la elasticidad de la cuerda. Demuestra que la longitud de cuerda
**no influye**, solo el factor de caída.

### Fórmula de Dodero

```
F = m·g · (1 + √(1 + 2·ff / (m·g·κ)))
κ = elongación_relativa / fuerza (m/N por metro de cuerda)

κ valores típicos:
  Dinámica:      1.8 × 10⁻⁴
  Semiestática:  2.5 × 10⁻⁵
  Estática:      1.2 × 10⁻⁵
```

### Controles

| Control | Función |
|---------|---------|
| **Factor de caída** | 0.01 – 2.0 |
| **Masa (kg)** | 40 – 200 kg |
| **Elongación cuerda (%)** | 1 – 40 % |

### Visualizaciones

- Curva F vs factor de caída para los tres tipos de cuerda.
- Gráfico F vs masa para el factor de caída seleccionado.
- Barras comparativas con referencia UIAA 12 kN.

---

## Módulo 09 — Fricción y Ecuación del Cabrestante

**Archivo:** `09_friccion_y_rapel.py`
**Motor:** Matplotlib (interactivo)
**Ejecutar:** `python 09_friccion_y_rapel.py`

### Concepto

Visualiza la **ecuación del cabrestante (Capstan/Euler)**: la fricción exponencial que
permite controlar cargas pesadas con poca fuerza en dispositivos de descenso.

### Fórmula

```
T_hold = T_load · e^(−μ·θ)
donde:
  T_hold = fuerza necesaria para frenar
  T_load = fuerza de la carga
  μ = coeficiente de fricción
  θ = ángulo total de contacto (vueltas × 2π)

Ejemplo: 3 vueltas, μ=0.3 → T_hold ≈ 0.3% de T_load
```

### Dispositivos modelados

| Dispositivo | μ | Vueltas equiv. |
|-------------|---|---------------|
| Mosquetón italiano HMS | 0.25 | 1.5 |
| Ocho (figure 8) | 0.30 | 2.0 |
| Rack de barras (4) | 0.28 | 4.0 |
| Dispositivo autoblocante | 0.35 | 3.0 |
| Poste (3 vueltas) | 0.30 | 6.0 |

### Controles

| Control | Función |
|---------|---------|
| **Carga (kg)** | 10 – 300 kg |
| **Coef. fricción (μ)** | 0.05 – 0.50 |
| **Vueltas de cuerda** | 0.25 – 8.0 |

---

## Módulo 10 — Simulador de Sistema Completo

**Archivo:** `10_simulador_sistema_completo.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 10_simulador_sistema_completo.py`

### Concepto

Integra todos los módulos anteriores en una única simulación de rescate vertical:
anclaje en V, desviador de borde, dispositivo de descenso y factor de caída.
Analiza en tiempo real cada componente del sistema.

### Sistemas simulados

- Acantilado con geometría realista
- Anclaje en V ajustable (10–170°)
- Desviador fijo en el borde (ON/OFF)
- Cuerda de seguridad independiente
- Descenso continuo de la camilla
- Simulación de caída con fuerza de choque

### Controles

| Tecla | Función |
|-------|---------|
| `ESPACIO` | Descender / disparar caída |
| `↑/↓` | Ajustar masa ±10 kg |
| `←/→` | Ajustar ángulo del anclaje en V |
| `A` | Alternar anclaje V / simple |
| `D` | Activar/desactivar desviador |
| `F` | Ciclar factor de caída: OFF→0.25→0.5→1.0→2.0 |
| `R` | Reiniciar |
| `ESC` | Salir |

### Panel en tiempo real

Muestra fuerzas en anclaje, fuerza en desviador, fuerza del frenador,
impacto de caída y resumen de seguridad con factores de seguridad.

---

## Módulo 11 — Camilla en Tirolesa

**Archivo:** `11_camilla_en_tirolesa.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 11_camilla_en_tirolesa.py`

### Concepto

Simula el paso de una camilla a lo largo de una tirolesa y muestra en tiempo real
cómo cambian las tensiones en ambos anclajes según la **posición de la carga**.
Usa un modelo de cuerda inextensible de longitud fija (bisección numérica).

### Fórmulas

```
H = W · x · (L−x) / (d · L)      (componente horizontal, igual en ambos lados)
T_izq = H / cos(α_izq)
T_der = H / cos(α_der)
Ángulo V = 180° − α_izq − α_der

Flecha real d(x): bisección de √(x²+d²) + √((L−x)²+d²) = S
```

### Controles

| Tecla | Función |
|-------|---------|
| `←/→` (mantener) | Mover camilla |
| `↑/↓` | Ajustar flecha (sag) ±0.5 % |
| `W/S` | Ajustar masa ±10 kg |
| `+/−` | Ajustar vano ±5 m |
| `ESPACIO` | Travesía automática |
| `R` | Reiniciar |

### Visualizaciones

- Escena de tirolesa con cuerda coloreada por tensión.
- Flechas de tensión en ambos anclajes.
- Gráfico de T_izq y T_der vs posición en el vano.
- Panel con datos, ángulo V y verificación NFPA/MBS.

---

## Módulo 12 — Efecto Péndulo en Rescate

**Archivo:** `12_pendulo_en_rescate.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 12_pendulo_en_rescate.py`

### Concepto

Demuestra que cuando una persona oscila como péndulo, la **fuerza en el anclaje
supera el peso estático** por la componente centrípeta. A 90° de liberación, la
fuerza es 3× el peso; a 180°, 5× el peso.

### Fórmulas

```
F_anclaje = m · (g · cos θ + ω² · r)   (en tiempo real)
F_max = m·g · (3 − 2·cos θ₀)           (en el fondo)
Multiplicador = 3 − 2·cos θ₀

θ₀ = 30°  → 1.27× W
θ₀ = 60°  → 2.00× W
θ₀ = 90°  → 3.00× W
θ₀ = 120° → 4.00× W
θ₀ = 180° → 5.00× W
```

### Controles

| Tecla | Función |
|-------|---------|
| `1–5` | Ángulo de liberación: 30/45/60/90/120° |
| `ESPACIO` | Liberar péndulo |
| `↑/↓` | Masa ±5 kg |
| `+/−` | Longitud de cuerda ±0.5 m |
| `R` | Reiniciar |

### Visualizaciones

- Animación del péndulo con trail de trayectoria.
- Flechas de fuerza de anclaje, peso y centrípeta en tiempo real.
- Gauge vertical de fuerza con referencia NFPA/MBS.
- Gráfico de fuerza vs tiempo.
- Tabla de multiplicadores para todos los ángulos.

---

## Módulo 13 — Trípode y Marco en A

**Archivo:** `13_tripode_marco_en_a.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 13_tripode_marco_en_a.py`

### Concepto

Analiza las fuerzas de **compresión** en estructuras de trípode (3 patas) y marco en A
(2 patas) usadas en rescate vertical. Incluye verificación contra **pandeo de Euler**.

### Fórmulas

```
Trípode (n=3):
  F_pata = W / (3 · cos φ)
  H_pata = W · tan φ / 3

Marco en A (n=2):
  F_pata = W / (2 · cos φ)
  H_pata = W · tan φ / 2

Pandeo de Euler:
  F_cr = π² · E·I / L²
  (EI ≈ 4500 N·m² para tubo aluminio 48×3 mm)
```

### Controles

| Tecla | Función |
|-------|---------|
| `←/→` (mantener) | Ajustar ángulo φ (0–75°) |
| `↑/↓` (mantener) | Ajustar masa |
| `T` | Alternar trípode / marco en A |
| `L/K` | Longitud de patas ±0.5 m |
| `R` | Reiniciar |

### Visualizaciones

- Vista lateral con flechas de compresión y empuje horizontal.
- Ángulo φ marcado con arco.
- Curva de fuerza vs ángulo para trípode y marco A (comparación simultánea).
- Panel con factores de seguridad de tubo y pandeo.

---

## Módulo 14 — Distribución Multi-Anclaje

**Archivo:** `14_distribucion_multi_anclaje.py`
**Motor:** Pygame (interactivo con mouse)
**Ejecutar:** `python 14_distribucion_multi_anclaje.py`

### Concepto

Simula la distribución de fuerzas en sistemas de **3 o 4 anclajes auto-ecualizados**
y el escenario de **fallo en cascada** si un anclaje cede.

### Fórmulas

```
F_i = W · cos(α_i) / Σ cos(α_j)

donde α_i = ángulo del tirante i respecto a la vertical

La distribución NO es uniforme salvo simetría perfecta.
Los tirantes más verticales reciben más carga.
```

### Controles

| Tecla / Mouse | Función |
|---------------|---------|
| `TAB` | Ciclar anclaje seleccionado |
| `Flechas` | Mover anclaje seleccionado |
| `Mouse drag` | Arrastrar cualquier anclaje |
| `3/4` | Cambiar a sistema de 3 o 4 puntos |
| `F` | Simular fallo del anclaje seleccionado |
| `W/S` | Ajustar masa ±10 kg |
| `R` | Reiniciar |

### Visualizaciones

- Pared de roca con pernos de anclaje interactivos.
- Tirantes coloreados por porcentaje de carga.
- Barras de distribución con redistribución en fallo.
- Análisis de carga de choque post-fallo.

---

## Módulo 15 — Sistema de Contrapeso

**Archivo:** `15_sistema_contrapeso.py`
**Motor:** Pygame (animación)
**Ejecutar:** `python 15_sistema_contrapeso.py`

### Concepto

Simula la **máquina de Atwood con fricción** aplicada a rescate urbano: el peso del
rescatista contrabalancea al paciente durante un pick-off o descenso desde edificio.

### Fórmulas

```
Sin fricción (Atwood ideal):
  T = 2·m₁·m₂·g / (m₁+m₂)
  a = (m₁−m₂)·g / (m₁+m₂)

Con fricción en el punto de redirección (Capstan):
  T₁ = T₂ · e^(μ·θ)   (lado pesado)
  a_fricción = g · (m₁ − m₂·e^(μθ)) / (m₁ + m₂·e^(μθ))

Fuerza en el punto de redirección:
  F = √(T₁² + T₂² + 2·T₁·T₂·cos(π−θ))
```

### Controles

| Tecla | Función |
|-------|---------|
| `ESPACIO` | Liberar / reiniciar posición |
| `↑/↓` | Masa rescatista: 50–120 kg |
| `W/S` | Masa paciente: 30–150 kg |
| `F` | Activar/desactivar fricción (μ=0.30) |
| `←/→` | Ángulo de redirección: 30–170° |
| `R` | Reiniciar completo |

### Visualizaciones

- Edificio con rescatista (interior) y paciente (exterior) animados.
- Flechas de peso, tensión y velocidad en tiempo real.
- Fuerza en punto de redirección con arco de ángulo.
- Panel completo: Atwood ideal, ecuación con fricción, evaluación de seguridad.

---

## Resumen comparativo

| # | Módulo | Motor | Concepto principal | Tipo |
|---|--------|-------|--------------------|------|
| 01 | ¿Qué es un Newton? | Matplotlib | F = m·a, peso | Estático |
| 02 | Vectores y Fuerzas | Matplotlib | Suma vectorial | Estático |
| 03 | Anclaje en V | Matplotlib | F = W/(2·cos θ/2) | Estático |
| 04 | Factor de Caída | Pygame | FF, fuerza choque | Animación |
| 05 | Elasticidad Cuerda | Matplotlib | Curva F-elongación | Estático |
| 06 | Ventaja Mecánica | Pygame | Sistemas de poleas | Animación |
| 07 | Tirolesa | Matplotlib | T = WL/(4d) | Estático |
| 08 | Fuerza de Choque | Matplotlib | Fórmula Dodero | Estático |
| 09 | Fricción/Rápel | Matplotlib | Ecuación cabrestante | Estático |
| 10 | Sistema Completo | Pygame | Integración total | Animación |
| 11 | Camilla en Tirolesa | Pygame | Fuerzas vs posición | Animación |
| 12 | Péndulo | Pygame | F = mg(3−2·cos θ₀) | Animación |
| 13 | Trípode/Marco A | Pygame | Compresión + pandeo | Animación |
| 14 | Multi-Anclaje | Pygame | Distribución + fallo | Interactivo |
| 15 | Contrapeso | Pygame | Atwood + Capstan | Animación |

---

## Límites de seguridad de referencia

| Referencia | Valor | Aplicación |
|------------|-------|------------|
| **NFPA 1983** carga de trabajo | 13.5 kN | Cuerdas de rescate |
| **UIAA** fuerza máxima de choque | 12.0 kN | Cuerda dinámica primer caída |
| **MBS** cuerda estática 11 mm | 30.0 kN | Rotura mínima garantizada |
| **MBS** cuerda dinámica 10 mm | 24.0 kN | Rotura mínima garantizada |
| Factor de seguridad rescate | 10:1 | MBS / carga de trabajo |
