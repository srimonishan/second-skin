"""
Free, no-API-key weather lookup via Open-Meteo. Uses only the stdlib
(urllib) so the fetch_context Lambda needs no extra dependency layer.

Location is configurable via env vars so the "studio" can be based anywhere;
defaults to a mid-latitude city with genuinely varied weather.
"""
import json
import os
import urllib.error
import urllib.request

DEFAULT_LAT = "51.5072"   # London
DEFAULT_LON = "-0.1276"
DEFAULT_LOCATION_NAME = "London"

# WMO weather interpretation codes -> short human label
_WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def fetch_weather() -> dict:
    """
    Returns {"summary": str, "temperature_c": float | None, "location": str}.
    Never raises -- on any failure returns a graceful "unknown" summary so
    FetchContext's own Catch fallback is a last resort, not the first line
    of defense against a flaky third-party API.
    """
    lat = os.environ.get("WEATHER_LAT", DEFAULT_LAT)
    lon = os.environ.get("WEATHER_LON", DEFAULT_LON)
    location = os.environ.get("WEATHER_LOCATION_NAME", DEFAULT_LOCATION_NAME)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        current = data["current"]
        code = current.get("weather_code")
        temp = current.get("temperature_2m")
        label = _WEATHER_CODES.get(code, "unsettled weather")
        summary = f"{label}, {temp}°C in {location}" if temp is not None else f"{label} in {location}"
        return {"summary": summary, "temperature_c": temp, "location": location}
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return {"summary": f"unknown weather in {location}", "temperature_c": None, "location": location}
