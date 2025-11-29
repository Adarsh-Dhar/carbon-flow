"""
Meteorologist Agent

Collects wind, humidity, and pollen context that downstream agents use.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from respiro.integrations.meteorology import MeteorologyClient
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


DEFAULT_COORDINATE = (37.7749, -122.4194)


class MeteorologistAgent:
    def __init__(self) -> None:
        self.client = MeteorologyClient()

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request = state.get("context", {}).get("route_request")
        if request:
            lat, lon = request.get("origin", DEFAULT_COORDINATE)
        else:
            lat, lon = DEFAULT_COORDINATE

        logger.info("Meteorologist fetching context for lat=%s lon=%s", lat, lon)
        context = self.client.summarize_context(lat, lon)

        adjustments = {
            "wind_breaker": self._wind_breaker_bias(context.get("wind", {})),
            "fog_guard": self._fog_guard(context.get("wind", {})),
            "pollen_risk": self._pollen_risk(context.get("alerts", [])),
        }
        context["adjustments"] = adjustments
        return context

    def _wind_breaker_bias(self, wind: Dict[str, Any]) -> str:
        direction = wind.get("direction_deg")
        if direction is None:
            return "neutral"
        if 200 <= direction <= 340:
            return "favor_west"
        if 20 <= direction <= 160:
            return "favor_east"
        return "neutral"

    def _fog_guard(self, wind: Dict[str, Any]) -> bool:
        humidity = wind.get("humidity")
        return bool(humidity and humidity > 95)

    def _pollen_risk(self, alerts: Any) -> str:
        for alert in alerts or []:
            severity = alert.get("severity", "").lower()
            if severity in {"high", "very_high"}:
                return "high"
        return "low"

