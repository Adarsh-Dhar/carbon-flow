"""
PurpleAir API client with EPA correction helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


SF_BOUNDING_BOX = (37.70, -122.52, 37.81, -122.35)  # (south, west, north, east)


def apply_epa_correction(pm25: float, humidity: float) -> float:
    """
    Apply the EPA correction that mitigates fog-induced false positives.
    """
    corrected = 0.52 * pm25 - 0.086 * humidity + 5.75
    return max(corrected, 0.0)


@dataclass
class PurpleAirReading:
    latitude: float
    longitude: float
    pm25: float
    humidity: float
    aqi: Optional[float]
    sensor_id: int
    last_seen: int
    corrected_pm25: float


class PurpleAirClient:
    """Thin wrapper around the PurpleAir API."""

    BASE_URL = "https://api.purpleair.com/v1/sensors"

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.api.purpleair_api_key
        if not self.api_key:
            logger.warning("PurpleAir API key missing; only cached data will be available")

    def fetch_sf_sensors(self, fields: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch real-time PM2.5 readings for San Francisco.
        """
        return self.fetch_bbox(SF_BOUNDING_BOX, fields=fields)

    def fetch_bbox(
        self,
        bbox: Tuple[float, float, float, float],
        fields: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        request_fields = fields or (
            "name,latitude,longitude,pm2.5_cf_1,pm2.5_alt,humidity,aqi,"
            "last_seen,confidence,channel_state"
        )
        params = {
            "fields": request_fields,
            "location_type": 0,  # outdoor
            "nwlng": bbox[3],
            "nwlat": bbox[2],
            "selng": bbox[1],
            "selat": bbox[0],
        }
        headers = {"X-API-Key": self.api_key}

        try:
            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("PurpleAir request failed: %s", exc)
            return []

        payload = response.json()
        fields_header = payload.get("fields", [])
        data_rows = payload.get("data", [])
        sanitized: List[Dict[str, Any]] = []
        for row in data_rows:
            row_dict = dict(zip(fields_header, row))
            pm25_raw = float(row_dict.get("pm2.5_alt") or row_dict.get("pm2.5_cf_1") or 0.0)
            humidity = float(row_dict.get("humidity") or 0.0)
            row_dict["pm25_corrected"] = apply_epa_correction(pm25_raw, humidity)
            sanitized.append(row_dict)
        return sanitized

