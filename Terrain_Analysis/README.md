# Terrain Analysis

Servicio web para **análisis de terreno aplicado al rescate**: sobre el mapa se
**dibuja un rectángulo (AOI)** arrastrando el mouse y se genera una **superficie 3D**
del terreno, con **agua** (ríos/lagos rellenos), **clima** (HUD + luz solar real +
viento + nubes/lluvia/rayos por sector) y medidas del área. Evoluciona hacia una
herramienta de **búsqueda y rescate (SAR)**.

> Dominio distinto a `../Rope_Simulations/` (aquel son las simulaciones de física).
> Aquí el eje es **mapas + terreno**.

## Stack

- **Backend:** Python + [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn.
  Sin API keys: elevación vía [Open-Elevation](https://open-elevation.com/),
  agua de [OpenStreetMap](https://www.openstreetmap.org/) (Overpass), clima de
  [Open-Meteo](https://open-meteo.com/). Solo dependencias: FastAPI, Uvicorn,
  Pydantic, httpx (+ pytest).
- **Frontend:** HTML + JS con [Leaflet](https://leafletjs.com/) (mapa) y
  [Plotly](https://plotly.com/javascript/) (superficie 3D), servido por el mismo
  FastAPI. Tema terminal verde fósforo.

## Arquitectura (layered)

```
app/
├─ main.py        Fachada FastAPI: monta API + sirve static/
├─ api/           Routers REST              (capa de transporte: terrain/surface/water/weather)
├─ services/      Lógica + IO externo       (surface, water, weather con proveedores)
├─ models/        Esquemas Pydantic         (contrato/validación DTO)
└─ core/          geo.py + solar.py (puros) + config.py (constantes)
static/           Frontend (mapa Leaflet + Plotly 3D)
tests/            pytest (geo + superficie + agua + clima/sol; deps inyectadas → sin red)
```

Patrones: **layered architecture** (api → services → core), **DTO/schema** con
Pydantic, **dependency injection** (elevación en `generate_surface`, proveedor en
`fetch_weather`) para testear offline, **Strategy + registry** para la fuente de
clima (`WeatherProvider` → `OpenMeteoProvider`, conmutable vía `get_provider`),
**Adapter** que normaliza la respuesta del proveedor a un DTO estable, y un
**núcleo puro** (`core/geo.py`, `core/solar.py`) como única fuente de verdad de
las fórmulas — mismo principio que `physics.py` en `Rope_Simulations`.

## Correr en local

```bash
cd Terrain_Analysis
make install     # crea .venv e instala deps
make dev         # http://localhost:8000  (mapa)  ·  /docs (API Swagger)
make test        # pytest
```

### Parámetros configurables (en el Makefile)

Se editan arriba en el `Makefile` (o se pasan en línea) y el frontend los lee al
cargar vía `GET /api/config`:

```bash
make dev DETAIL=120 WATER=on WEATHER=open-meteo
```

- `DETAIL` — resolución de la malla 3D (≤120; 70=medio, 100=alto, 120=máximo).
- `WATER` — dibujar agua (ríos/lagos/mar) sobre el 3D: `on` | `off`.
- `WEATHER` — proveedor de clima (registrado en `services/weather.py`; hoy `open-meteo`).

En la UI: se **dibuja el AOI arrastrando** (4 esquinas de color, arrastrables) y
hay un único interruptor **"efectos atmosféricos"** que enciende el clima visible
(HUD + luz solar real + viento animado + nubes/lluvia/nieve/rayos).

## API

`POST /api/surface`

```json
{ "polygon": [ {"lat":14.62,"lon":-90.58}, ... ], "grid": 120 }
```

Malla de elevación dentro del polígono (suavizada), proyectada a metros locales:
`x`, `y` (1D) y `z` (2D) para un `Surface` de Plotly, + `zmin/zmax`, `grid` y los
parámetros de proyección (`lon0/lat0/mx/my`) para drapear agua/clima.

`POST /api/weather`

```json
{ "lat": 14.6349, "lon": -90.5069, "at": "2026-06-16T23:30:00Z" }
```

Clima actual del punto (Open-Meteo, sin API key) + **posición solar** para el
instante `at` (opcional; por defecto, ahora). Devuelve temperatura/sensación,
viento (con componentes `u`/`v` hacia donde sopla), ráfagas, lluvia, nubes,
humedad, visibilidad, orto/ocaso y un bloque `sun` con azimut, elevación y el
**vector de luz** listo para iluminar la superficie 3D. La posición solar se
calcula offline: si Open-Meteo falla, igual se entrega `sun` con una nota.

En el frontend se traduce en tres capas sobre el 3D: **HUD** de condiciones,
**luz solar real** (reorienta el sombreado del relieve; el scrubber "hora del
sol" simula sombras a otra hora) y **campo de viento** (conos).

`POST /api/weather/field`

```json
{ "polygon": [ {"lat":14.3,"lon":-91.0}, ... ], "grid": 6 }
```

**Campo de clima espacial**: muestrea una grilla grid×grid de puntos sobre el bbox
del AOI (una sola llamada multi-coordenada a Open-Meteo) y devuelve precipitación,
nubes y código WMO por celda. El frontend lo usa para mostrar los efectos
atmosféricos **solo en los sectores afectados** (llueve acá, despejado allá). En un
AOI chico todas las celdas caen en la misma celda del modelo (~11 km) → uniforme.

`GET /api/config` → `{detail, water}` (valores fijados desde el Makefile).

`GET /api/health` → `{"status": "ok"}`

## Siguientes pasos sugeridos

- Línea de visión / intervisibilidad entre anclajes (relieve de por medio).
- Cálculo de tirolesa sobre terreno real (largo de cuerda, flecha, tensiones)
  reutilizando fórmulas de `../Rope_Simulations/physics.py`.
- Caché de elevación / soporte de DEM local (`rasterio`) para trabajar offline.
