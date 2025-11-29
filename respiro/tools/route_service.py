"""
High-level route intelligence service shared by API layers.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from respiro.agents.cartographer import CartographerAgent
from respiro.agents.meteorologist import MeteorologistAgent
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class RouteIntelligenceService:
    def __init__(self) -> None:
        self.meteorologist = MeteorologistAgent()
        self.cartographer = CartographerAgent()

    def build_intelligence(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        sensitivity: str = "asthma",
    ) -> Dict[str, Any]:
        state = {
            "context": {
                "route_request": {
                    "origin": origin,
                    "destination": destination,
                    "sensitivity": sensitivity,
                }
            }
        }
        logger.info("Building route intelligence origin=%s destination=%s", origin, destination)
        meteorology = self.meteorologist.execute(state)
        state["meteorology_output"] = meteorology
        recommendation = self.cartographer.execute(state)
        return {
            "origin": origin,
            "destination": destination,
            "sensitivity": sensitivity,
            "meteorology": meteorology,
            "route": recommendation,
        }

