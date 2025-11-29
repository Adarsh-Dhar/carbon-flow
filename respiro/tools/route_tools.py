"""
Route Optimization Tools

Calculate cleaner commute routes based on AQI.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger
from respiro.tools.sf_routing_engine import SFRoutingEngine

logger = get_logger(__name__)


class RouteOptimizer:
    """Optimize routes based on air quality."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.api.google_maps_api_key
        self.sf_engine: Optional[SFRoutingEngine] = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_route_with_aqi(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        aqi_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get route with AQI-based scoring.
        
        Args:
            origin: (latitude, longitude)
            destination: (latitude, longitude)
            aqi_data: AQI data for route segments
            
        Returns:
            Optimized route with AQI scores
        """
        if self._is_sf_request(origin, destination):
            engine = self._get_sf_engine()
            if not engine:
                return {}
            logger.info("Using SF clean-air routing engine")
            result = engine.compute_routes(origin, destination)
            return {
                "best_route": {
                    "route": result["cleanest"],
                    "aqi_score": result["stats"]["cleanest_aqi"],
                    "distance": result["stats"]["cleanest_minutes"] * 80,
                    "health_delta": result["health_delta"],
                    "label": "cleanest",
                },
                "all_routes": [
                    {
                        "label": "fastest",
                        "route": result["fastest"],
                        "aqi_score": result["stats"]["fastest_aqi"],
                        "distance": result["stats"]["fastest_minutes"] * 80,
                        "health_delta": 0.0,
                    },
                    {
                        "label": "cleanest",
                        "route": result["cleanest"],
                        "aqi_score": result["stats"]["cleanest_aqi"],
                        "distance": result["stats"]["cleanest_minutes"] * 80,
                        "health_delta": result["health_delta"],
                    },
                ],
            }

        if not self.api_key:
            logger.warning("Google Maps API key not available")
            return {}
        
        try:
            # Get route from Google Maps
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "key": self.api_key,
                "alternatives": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            routes = data.get("routes", [])
            
            # Score routes based on AQI
            scored_routes = []
            for route in routes:
                score = self._score_route(route, aqi_data)
                scored_routes.append({
                    "route": route,
                    "aqi_score": score,
                    "distance": route.get("legs", [{}])[0].get("distance", {}).get("value", 0),
                    "duration": route.get("legs", [{}])[0].get("duration", {}).get("value", 0)
                })
            
            # Sort by AQI score (lower is better)
            scored_routes.sort(key=lambda x: x["aqi_score"])
            
            return {
                "best_route": scored_routes[0] if scored_routes else None,
                "all_routes": scored_routes
            }
            
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            return {}
    
    def _score_route(self, route: Dict[str, Any], aqi_data: Dict[str, Any]) -> float:
        """Score a route based on AQI along the path."""
        # Simplified scoring - in production, would use actual AQI data along route segments
        steps = route.get("legs", [{}])[0].get("steps", [])
        total_aqi = 0.0
        count = 0
        
        for step in steps:
            # Get AQI for step location (simplified)
            location = step.get("end_location", {})
            # In production, would query AQI API for this location
            total_aqi += aqi_data.get("aqi", 100)  # Default to moderate
            count += 1
        
        return total_aqi / count if count > 0 else 100.0

    # ------------------------------------------------------------------
    # SF helpers
    # ------------------------------------------------------------------
    def _is_sf_request(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> bool:
        bounds = ((37.70, -122.52), (37.81, -122.35))
        (south, west), (north, east) = bounds
        return all(
            south <= coord[0] <= north and west <= coord[1] <= east for coord in (origin, destination)
        )

    def _get_sf_engine(self) -> Optional[SFRoutingEngine]:
        if self.sf_engine:
            return self.sf_engine
        try:
            self.sf_engine = SFRoutingEngine()
        except Exception as exc:
            logger.error("Failed to initialize SF routing engine: %s", exc)
            self.sf_engine = None
        return self.sf_engine
