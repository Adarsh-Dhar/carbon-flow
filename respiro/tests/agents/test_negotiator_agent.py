from __future__ import annotations

from typing import Any, Dict, List
from importlib import util
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).resolve().parents[2] / "agents"


def _load_agent_module(stem: str):
    spec = util.spec_from_file_location(f"respiro.agents.{stem}_module", AGENTS_DIR / f"{stem}.py")
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


negotiator_module = _load_agent_module("negotiator")
NegotiatorAgent = negotiator_module.NegotiatorAgent


class StubBedrockClient:
    def __init__(self, response: str = "Sample empathetic response"):
        self.response = response
        self.calls: List[Dict[str, Any]] = []

    def generate_empathetic_response(self, context: Dict[str, Any], recommendations: Dict[str, Any]) -> str:
        self.calls.append({"context": context, "recommendations": recommendations})
        return self.response


class StubCalendarClient:
    def __init__(self):
        self.rescheduled: List[Dict[str, Any]] = []

    def find_events_to_reschedule(self, aqi_forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"id": "event-1", "summary": "Commute to office", "location": {"latitude": 37.78, "longitude": -122.4}},
            {"id": "event-2", "summary": "Virtual check-in"},
        ]

    def reschedule_event(self, event_id: str, new_start) -> bool:
        self.rescheduled.append({"id": event_id, "new_start": new_start})
        return True


class StubRouteOptimizer:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def get_route_with_aqi(self, origin, destination, aqi_forecast):
        self.calls.append({"origin": origin, "destination": destination})
        return {"best_route": {"path": ["A", "B"], "aqi_score": 12}}


class StubVectorStore:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def store_memory(self, patient_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        self.records.append({"patient_id": patient_id, "text": text, "metadata": metadata})
        return True


class StubMemoryTools:
    def __init__(self, preferences: List[Dict[str, Any]]):
        self.preferences = preferences
        self.vector_store = StubVectorStore()

    def retrieve_preferences(self, patient_id: str, category: str = "communication") -> List[Dict[str, Any]]:
        return self.preferences


def _patch_negotiator_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    bedrock: StubBedrockClient,
    calendar: StubCalendarClient,
    route_optimizer: StubRouteOptimizer,
    memory_tools: StubMemoryTools,
):
    monkeypatch.setattr(negotiator_module, "BedrockClient", lambda: bedrock)
    monkeypatch.setattr(negotiator_module, "GoogleCalendarClient", lambda: calendar)
    monkeypatch.setattr(negotiator_module, "RouteOptimizer", lambda: route_optimizer)
    monkeypatch.setattr(negotiator_module, "MemoryTools", lambda: memory_tools)


def test_negotiator_handles_high_risk_logistics(state_factory, fake_s3, monkeypatch):
    bedrock = StubBedrockClient("We adjusted your schedule")
    calendar = StubCalendarClient()
    route_optimizer = StubRouteOptimizer()
    memory_tools = StubMemoryTools(preferences=[{"text": "Keep tone encouraging"}])

    _patch_negotiator_dependencies(
        monkeypatch,
        bedrock=bedrock,
        calendar=calendar,
        route_optimizer=route_optimizer,
        memory_tools=memory_tools,
    )

    state = state_factory(
        sentry_output={
            "risk_level": "high",
            "risk_factors": ["AQI"],
            "sensor_data": {"air_quality": {"pm25": 180}},
        },
        clinical_output={"recommendations": {"zone": "yellow"}},
    )
    state["context"]["location"] = {"latitude": 37.7749, "longitude": -122.4194}

    agent = NegotiatorAgent()
    agent.s3_client = fake_s3
    output = agent.execute(state)

    assert output["calendar_actions"]
    assert output["route_recommendations"]
    assert output["user_preferences_used"] == 1
    assert len(memory_tools.vector_store.records) == 1
    assert len(fake_s3.uploads) == 1


def test_negotiator_falls_back_on_bedrock_error(state_factory, monkeypatch):
    class BrokenBedrock(StubBedrockClient):
        def generate_empathetic_response(self, *args, **kwargs):
            raise RuntimeError("bedrock unavailable")

    bedrock = BrokenBedrock()
    calendar = StubCalendarClient()
    route_optimizer = StubRouteOptimizer()
    memory_tools = StubMemoryTools(preferences=[])

    _patch_negotiator_dependencies(
        monkeypatch,
        bedrock=bedrock,
        calendar=calendar,
        route_optimizer=route_optimizer,
        memory_tools=memory_tools,
    )

    state = state_factory(
        sentry_output={"risk_level": "low", "risk_factors": [], "sensor_data": {}},
        clinical_output={},
    )

    agent = NegotiatorAgent()
    output = agent.execute(state)

    assert output["response"].startswith("I'm here to help")
    assert output["calendar_actions"] == []
    assert output["error"] == "bedrock unavailable"

