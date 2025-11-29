from __future__ import annotations

from typing import Any, Dict

from respiro.agents.cartographer import CartographerAgent


class _DummyEngine:
    def compute_routes(self, origin, destination):
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "LineString", "coordinates": [[origin[1], origin[0]], [destination[1], destination[0]]]},
        }
        return {
            "fastest": feature,
            "cleanest": feature,
            "health_delta": 0.42,
            "stats": {
                "fastest_minutes": 12.5,
                "cleanest_minutes": 14.0,
                "fastest_aqi": 150,
                "cleanest_aqi": 80,
            },
        }


def test_cartographer_derives_adjustments(monkeypatch):
    monkeypatch.setattr("respiro.agents.cartographer.SFRoutingEngine", lambda: _DummyEngine())
    agent = CartographerAgent()
    state: Dict[str, Any] = {
        "context": {"route_request": {"origin": (37.77, -122.41), "destination": (37.79, -122.4)}},
        "meteorology_output": {
            "wind": {"direction_deg": 250, "humidity": 99, "speed_kmh": 12},
            "alerts": [{"severity": "High"}],
        },
    }
    result = agent.execute(state)
    assert result["adjustments"]["fog_guard"] is True
    assert result["cleanest_route"]["geometry"]["type"] == "LineString"
    assert "Cleanest route cuts inhaled dose" in result["explanation"]

