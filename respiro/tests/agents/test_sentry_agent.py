from __future__ import annotations

from typing import Any, Dict
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


sentry_module = _load_agent_module("sentry")
SentryAgent = sentry_module.SentryAgent
RiskLevel = sentry_module.RiskLevel


class StubSmartHome:
    def __init__(self):
        self.actions: list[Dict[str, Any]] = []

    def control_air_purifier(self, device_id: str, power: str, mode: str) -> bool:
        self.actions.append({"device_id": device_id, "power": power, "mode": mode})
        return True


def _patch_sentry_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    trigger_result: Dict[str, Any],
    smart_home: StubSmartHome | None = None,
    approval_workflow: Any | None = None,
    biometric_payload: Dict[str, Any] | None = None,
):
    class StubAQI:
        def get_aqi(self, latitude: float, longitude: float) -> Dict[str, Any]:
            return {"pm25": 150, "aqi": 180}

    class StubPollen:
        def get_pollen_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
            return {"grass": 200}

    class StubHealthKit:
        api_key = "test-key"

        def get_biometrics(self, patient_id: str) -> Dict[str, Any]:
            return biometric_payload or {"spo2": 94}

    class StubFitbit:
        access_token = None

        def get_biometrics(self) -> Dict[str, Any]:
            return {"steps": 1200}

    def fuse_sensor_data(aqi, pollen, biometrics):
        return {
            "aqi": aqi,
            "pollen": pollen,
            "biometrics": biometrics,
        }

    class StubTriggerDetector:
        def detect_triggers(self, fused):
            return trigger_result

    monkeypatch.setattr(sentry_module, "GoogleAQIClient", lambda: StubAQI())
    monkeypatch.setattr(sentry_module, "AmbeeClient", lambda: StubPollen())
    monkeypatch.setattr(sentry_module, "HealthKitClient", lambda: StubHealthKit())
    monkeypatch.setattr(sentry_module, "FitbitClient", lambda: StubFitbit())
    monkeypatch.setattr(sentry_module, "fuse_sensor_data", fuse_sensor_data)
    monkeypatch.setattr(sentry_module, "TriggerDetector", lambda: StubTriggerDetector())

    if smart_home is None:
        smart_home = StubSmartHome()
    monkeypatch.setattr(sentry_module, "SmartHomeTools", lambda: smart_home)

    if approval_workflow is None:
        approval_workflow = SimpleApprovalWorkflow()
    monkeypatch.setattr(sentry_module, "ApprovalWorkflow", lambda: approval_workflow)

    return smart_home, approval_workflow


class SimpleApprovalWorkflow:
    def __init__(self):
        self.requests: list[Dict[str, Any]] = []

    def request_approval(self, request_id: str, action: str, context: Dict[str, Any]):
        payload = {"request_id": request_id, "action": action, "context": context}
        self.requests.append(payload)
        return payload


def test_sentry_high_risk_auto_control(state_factory, fake_s3, monkeypatch):
    trigger_result = {
        "risk_level": RiskLevel.HIGH,
        "risk_score": 0.82,
        "risk_factors": ["AQI > 150"],
    }
    smart_home, approval_workflow = _patch_sentry_dependencies(
        monkeypatch,
        trigger_result=trigger_result,
    )

    state = state_factory()
    agent = SentryAgent()
    agent.s3_client = fake_s3
    agent.settings.app.require_approval_for_critical_actions = True

    output = agent.execute(state)

    assert output["risk_level"] == RiskLevel.HIGH
    assert output["requires_approval"] is False
    assert output["iot_actions"][0]["status"] == "success"
    assert smart_home.actions[0]["device_id"] == "air-001"
    # Ensure upload persisted
    assert len(fake_s3.uploads) == 1


def test_sentry_severe_requires_approval(state_factory, fake_s3, monkeypatch):
    trigger_result = {
        "risk_level": RiskLevel.SEVERE,
        "risk_score": 0.95,
        "risk_factors": ["AQI > 200"],
    }
    smart_home, approval_workflow = _patch_sentry_dependencies(
        monkeypatch,
        trigger_result=trigger_result,
    )

    state = state_factory()
    agent = SentryAgent()
    agent.s3_client = fake_s3

    output = agent.execute(state)

    assert output["risk_level"] == RiskLevel.SEVERE
    assert output["requires_approval"] is True
    assert output["iot_actions"][0]["status"] == "pending_approval"
    assert len(approval_workflow.requests) == 1
    assert approval_workflow.requests[0]["action"] == "control_air_purifier"
    assert len(fake_s3.uploads) == 1


def test_sentry_handles_sensor_failure(state_factory, monkeypatch):
    class BrokenAQI:
        def get_aqi(self, *_):
            raise RuntimeError("sensor offline")

    monkeypatch.setattr(sentry_module, "GoogleAQIClient", lambda: BrokenAQI())
    monkeypatch.setattr(sentry_module, "AmbeeClient", lambda: BrokenAQI())
    monkeypatch.setattr(sentry_module, "HealthKitClient", lambda: BrokenAQI())
    monkeypatch.setattr(sentry_module, "FitbitClient", lambda: BrokenAQI())
    monkeypatch.setattr(sentry_module, "TriggerDetector", lambda: BrokenAQI())
    monkeypatch.setattr(sentry_module, "SmartHomeTools", lambda: StubSmartHome())
    monkeypatch.setattr(sentry_module, "ApprovalWorkflow", lambda: SimpleApprovalWorkflow())

    agent = SentryAgent()
    state = state_factory()

    output = agent.execute(state)

    assert output["risk_level"] == RiskLevel.LOW
    assert output["iot_actions"] == []
    assert "error" in output

