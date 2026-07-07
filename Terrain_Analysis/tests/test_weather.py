"""Tests del clima: posición solar (pura), viento y normalización (proveedor inyectado, sin red)."""

from datetime import datetime, timezone

from app.core.solar import light_vector, solar_position
from app.services.weather import WeatherProvider, fetch_weather, wind_uv


# ---- posición solar (pura, sin red) ----

def _utc(y, m, d, h):
    return datetime(y, m, d, h, 0, 0, tzinfo=timezone.utc)


def test_sun_high_at_equator_equinox_noon():
    # Equinoccio, mediodía solar en lon 0: el sol está casi en el cenit sobre el ecuador.
    _, elev = solar_position(0.0, 0.0, _utc(2024, 3, 20, 12))
    assert elev > 80


def test_sun_up_at_midday_below_at_midnight():
    # Londres (51.5N, 0): en pleno día el sol está alto; a medianoche, bajo el horizonte.
    _, elev_noon = solar_position(51.5, 0.0, _utc(2024, 6, 21, 12))
    _, elev_mid = solar_position(51.5, 0.0, _utc(2024, 6, 21, 0))
    assert elev_noon > 50
    assert elev_mid < 0


def test_sun_azimuth_south_at_local_noon_north_hemisphere():
    # En el hemisferio norte, al mediodía solar el sol está hacia el sur (~180°).
    az, _ = solar_position(51.5, 0.0, _utc(2024, 6, 21, 12))
    assert 150 < az < 210


def test_light_vector_overhead_and_east():
    over = light_vector(123.0, 90.0, 1000.0)          # cenit: todo el vector es vertical
    assert abs(over["x"]) < 1 and abs(over["y"]) < 1
    assert abs(over["z"] - 1000.0) < 1
    east = light_vector(90.0, 0.0, 1000.0)            # este, en el horizonte
    assert abs(east["x"] - 1000.0) < 1
    assert abs(east["z"]) < 1


# ---- viento (puro) ----

def test_wind_uv_cardinals():
    assert wind_uv(0, 10) == (0.0, -10.0)     # desde el norte → sopla hacia el sur
    assert wind_uv(90, 10) == (-10.0, 0.0)    # desde el este → sopla hacia el oeste
    assert wind_uv(180, 10) == (0.0, 10.0)    # desde el sur → sopla hacia el norte
    assert wind_uv(270, 10) == (10.0, 0.0)    # desde el oeste → sopla hacia el este


# ---- servicio: normalización con proveedor inyectado (sin red) ----

class _FakeProvider(WeatherProvider):
    name = "fake"

    def current(self, lat, lon):
        return {
            "observed_at": "2024-03-20T12:00", "temp_c": 21.0, "feels_c": 20.0,
            "humidity_pct": 55, "precip_mm": 0.0, "cloud_pct": 10, "visibility_m": 24000,
            "code": 1, "condition": "Mayormente despejado", "is_day": True,
            "sunrise": "2024-03-20T06:00", "sunset": "2024-03-20T18:10",
            "wind_speed": 18.0, "wind_gust": 30.0, "wind_dir_deg": 0.0,
            "wind_unit": "km/h", "notes": [],
        }


def test_fetch_weather_normalizes_and_adds_sun_and_wind_components():
    res = fetch_weather(0.0, 0.0, at_utc=_utc(2024, 3, 20, 12),
                        provider=_FakeProvider(), use_cache=False)
    assert res["source"] == "fake"
    assert res["condition"] == "Mayormente despejado"
    # viento desde el norte → componente norte negativa, este ~0
    assert res["wind"]["v"] == -18.0 and res["wind"]["u"] == 0.0
    # el sol se computa siempre (offline) y está alto
    assert res["sun"]["is_up"] is True
    assert res["sun"]["elevation_deg"] > 80
    assert {"x", "y", "z", "ambient", "diffuse"} <= set(res["sun"]["light"])


# ---- servicio: degradación con gracia si el proveedor falla ----

class _BoomProvider(WeatherProvider):
    name = "boom"

    def current(self, lat, lon):
        raise RuntimeError("proveedor caído")


def test_fetch_weather_degrades_but_keeps_sun():
    res = fetch_weather(51.5, 0.0, at_utc=_utc(2024, 6, 21, 0),
                        provider=_BoomProvider(), use_cache=False)
    assert res["temp_c"] is None
    assert res["wind"]["speed"] == 0.0          # viento en calma
    assert any("Clima no disponible" in n for n in res["notes"])
    assert res["sun"]["is_up"] is False         # medianoche → sol bajo el horizonte
