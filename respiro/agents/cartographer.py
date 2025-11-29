"""
Cartographer Agent

Turns meteorology-adjusted context into route recommendations.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
from datetime import datetime, timedelta

from respiro.tools.sf_routing_engine import SFRoutingEngine
from respiro.integrations.calendar import GoogleCalendarClient
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


DEFAULT_ORIGIN = (37.7749, -122.4194)
DEFAULT_DESTINATION = (37.7936, -122.3957)


class CartographerAgent:
    def __init__(self) -> None:
        self.engine = SFRoutingEngine()
        try:
            self.calendar = GoogleCalendarClient()
        except Exception as e:
            logger.warning(f"Calendar client initialization failed: {e}. Calendar Sentry will be disabled.")
            self.calendar = None

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        request = state.get("context", {}).get(
            "route_request",
            {
                "origin": DEFAULT_ORIGIN,
                "destination": DEFAULT_DESTINATION,
                "sensitivity": "asthma",
            },
        )
        origin = tuple(request.get("origin", DEFAULT_ORIGIN))
        destination = tuple(request.get("destination", DEFAULT_DESTINATION))

        logger.info("Cartographer computing routes origin=%s destination=%s", origin, destination)
        
        # Get meteorology context
        meteorology = state.get("meteorology_output", {})
        adjustments = self._derive_adjustments(meteorology)
        
        # Check Calendar Sentry for upcoming events
        calendar_suggestions = self._check_calendar_sentry(state, origin, destination)
        if calendar_suggestions:
            adjustments["calendar_suggestions"] = calendar_suggestions
        
        # Prepare context for routing engine
        pollen_context = {
            "pollen_penalty": adjustments.get("pollen_penalty", False),
            "pollen_alerts": adjustments.get("pollen_alerts", []),
        }
        wind_context = meteorology.get("wind", {})
        
        # Compute routes with context
        routes = self.engine.compute_routes(
            origin,
            destination,
            pollen_context=pollen_context,
            wind_context=wind_context,
        )

        recommendation = {
            "cleanest_route": routes["cleanest"],
            "fastest_route": routes["fastest"],
            "health_delta": routes["health_delta"],
            "stats": routes["stats"],
            "adjustments": adjustments,
            "explanation": self._build_explanation(routes, adjustments),
        }
        return recommendation
    
    def _check_calendar_sentry(
        self,
        state: Dict[str, Any],
        origin: Tuple[float, float],
        destination: Tuple[float, float],
    ) -> list[Dict[str, Any]]:
        """
        Check calendar for upcoming outdoor events and suggest rescheduling if AQI is high.
        """
        if self.calendar is None:
            return []
        
        try:
            # Get sensor data to check AQI forecast
            sentry_output = state.get("sentry_output", {})
            sensor_data = sentry_output.get("sensor_data", {})
            air_quality = sensor_data.get("air_quality", {})
            current_aqi = air_quality.get("aqi", 0)
            
            # Only check if AQI is moderate or higher
            if current_aqi < 100:
                return []
            
            # Get upcoming events
            events = self.calendar.list_events(
                time_min=datetime.utcnow(),
                time_max=datetime.utcnow() + timedelta(hours=24),
                max_results=10
            )
            
            suggestions = []
            outdoor_keywords = ["outdoor", "park", "run", "walk", "exercise", "sport", "gym", "jog", "hike"]
            
            for event in events:
                summary = event.get("summary", "").lower()
                if any(keyword in summary for keyword in outdoor_keywords):
                    event_start = event.get("start", {})
                    if isinstance(event_start, dict):
                        start_time_str = event_start.get("dateTime") or event_start.get("date")
                        if start_time_str:
                            try:
                                # Parse event time
                                if "T" in start_time_str:
                                    event_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                                else:
                                    event_time = datetime.fromisoformat(start_time_str)
                                
                                # Check if event is within next 6 hours
                                hours_until_event = (event_time - datetime.utcnow()).total_seconds() / 3600
                                if 0 < hours_until_event < 6:
                                    suggestions.append({
                                        "event_id": event.get("id"),
                                        "event_name": event.get("summary", "Outdoor Activity"),
                                        "event_time": event_time.isoformat(),
                                        "aqi_forecast": current_aqi,
                                        "suggestion": f"Calendar Sentry detected '{event.get('summary')}' - AQI will be {current_aqi:.0f}. Suggest rescheduling."
                                    })
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to parse event time: {e}")
                                continue
            
            if suggestions:
                logger.info(f"Calendar Sentry found {len(suggestions)} events to suggest rescheduling")
            
            return suggestions
            
        except Exception as e:
            logger.warning(f"Calendar Sentry check failed: {e}")
            return []

    def _derive_adjustments(self, meteorology: Dict[str, Any]) -> Dict[str, Any]:
        wind = meteorology.get("wind", {})
        fog_guard = False
        wind_bias = None
        humidity = wind.get("humidity")
        if humidity and humidity > 95:
            fog_guard = True
        direction = wind.get("direction_deg")
        if direction is not None and 200 <= direction <= 340:
            wind_bias = "westerly"
        pollen_alerts = meteorology.get("alerts", [])
        pollen_penalty = any(alert.get("severity", "").lower() in {"high", "very_high"} for alert in pollen_alerts)
        return {
            "fog_guard": fog_guard,
            "wind_bias": wind_bias,
            "pollen_penalty": pollen_penalty,
            "pollen_alerts": pollen_alerts,
        }

    def _build_explanation(self, routes: Dict[str, Any], adjustments: Dict[str, Any]) -> str:
        clauses = []
        delta_pct = routes["health_delta"] * 100
        clauses.append(f"Cleanest route cuts inhaled dose by {delta_pct:.1f}%")
        if adjustments.get("wind_bias"):
            clauses.append("Prevailing westerly winds kept you on the ocean side streets (Wind Breaker).")
        if adjustments.get("fog_guard"):
            clauses.append("Fog Guard suppressed humid sensor spikes (>95% humidity).")
        if adjustments.get("pollen_penalty"):
            clauses.append("Route avoids park pollen corridors where pollen levels are high today.")
        
        # Add Calendar Sentry suggestions
        calendar_suggestions = adjustments.get("calendar_suggestions", [])
        if calendar_suggestions:
            for suggestion in calendar_suggestions[:1]:  # Show first suggestion
                clauses.append(suggestion.get("suggestion", ""))
        
        return " ".join(clauses)

