"""
Meteorology and pollen data integrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WindContext:
    direction_deg: float
    speed_kmh: float
    humidity: Optional[float] = None


class MeteorologyClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.open_meteo_base_url = settings.api.open_meteo_base_url
        self.google_pollen_key = settings.api.google_pollen_api_key

    def fetch_wind(self, lat: float, lon: float) -> Optional[WindContext]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "relativehumidity_2m",
            "windspeed_unit": "kmh",
            "current_weather": True,
        }
        try:
            response = requests.get(self.open_meteo_base_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("OpenMeteo request failed: %s", exc)
            return None
        data = response.json()
        current = data.get("current_weather")
        if not current:
            return None
        humidity_series = data.get("hourly", {}).get("relativehumidity_2m", [])
        humidity = humidity_series[0] if humidity_series else None
        return WindContext(
            direction_deg=float(current.get("winddirection") or 0.0),
            speed_kmh=float(current.get("windspeed") or 0.0),
            humidity=float(humidity) if humidity is not None else None,
        )

    def fetch_pollen(self, lat: float, lon: float) -> Dict[str, Any]:
        if not self.google_pollen_key:
            logger.warning("Google Pollen API key missing")
            return {}
        params = {"location": f"{lat},{lon}", "key": self.google_pollen_key}
        url = "https://pollen.googleapis.com/v1/forecast:lookup"
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("Google Pollen request failed: %s", exc)
            return {}

    def summarize_context(self, lat: float, lon: float) -> Dict[str, Any]:
        wind = self.fetch_wind(lat, lon)
        pollen = self.fetch_pollen(lat, lon)
        alerts = []
        if pollen:
            day = pollen.get("dailyInfo", [{}])[0]
            pollen_indices = day.get("pollenTypeInfo", [])
            for entry in pollen_indices:
                if entry.get("indexInfo", {}).get("value", "").lower() in {"high", "very_high"}:
                    alerts.append(
                        {
                            "type": entry.get("displayName", "pollen"),
                            "severity": entry.get("indexInfo", {}).get("value"),
                        }
                    )

        wind_dict = {}
        if wind:
            wind_dict = {
                "direction_deg": wind.direction_deg,
                "speed_kmh": wind.speed_kmh,
                "humidity": wind.humidity,
            }
        return {"wind": wind_dict, "pollen": pollen, "alerts": alerts}

