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


clinical_module = _load_agent_module("clinical")
ClinicalAgent = clinical_module.ClinicalAgent


class StubActionPlanEngine:
    def __init__(self, recommendations: Dict[str, Any]):
        self.recommendations = recommendations
        self.last_context: Dict[str, Any] | None = None

    def generate_recommendations(
        self,
        *,
        risk_score: float,
        risk_level: str,
        risk_factors: List[str],
        action_plan: Dict[str, Any],
        current_medications: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self.last_context = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "action_plan": action_plan,
            "current_medications": current_medications,
        }
        return self.recommendations


class StubFHIRTools:
    def __init__(self, *, medications: List[Dict[str, Any]], careplan: Dict[str, Any]):
        self.medications = medications
        self.careplan = careplan
        self.default_plan_called = False

    def load_careplan(self, patient_id: str, careplan_id: str):
        return self.careplan

    def create_default_asthma_action_plan(self, patient_id: str):
        self.default_plan_called = True
        return {"default": True}

    def get_patient_medications(self, patient_id: str):
        return self.medications


class StubSmartHome:
    def __init__(self, success: bool = True):
        self.calls: List[Dict[str, Any]] = []
        self.success = success

    def adjust_hvac(self, device_id: str, temperature: float, mode: str) -> bool:
        self.calls.append({"device_id": device_id, "temperature": temperature, "mode": mode})
        return self.success


class StubApprovalWorkflow:
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []

    def request_approval(self, request_id: str, action: str, context: Dict[str, Any]):
        payload = {"request_id": request_id, "action": action, "context": context}
        self.requests.append(payload)
        return payload


class StubMemoryTools:
    def __init__(self, preferences: List[Dict[str, Any]]):
        self.preferences = preferences

    def retrieve_preferences(self, patient_id: str, category: str):
        return self.preferences


def _patch_clinical_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    medications: List[Dict[str, Any]],
    action_plan: Dict[str, Any],
    recommendations: Dict[str, Any],
    memory_preferences: List[Dict[str, Any]] | None = None,
    smart_home: StubSmartHome | None = None,
    approval_workflow: StubApprovalWorkflow | None = None,
):
    fhir = StubFHIRTools(medications=medications, careplan=action_plan)
    engine = StubActionPlanEngine(recommendations)
    memory = StubMemoryTools(memory_preferences or [])
    smart_home = smart_home or StubSmartHome()
    approval_workflow = approval_workflow or StubApprovalWorkflow()

    monkeypatch.setattr(clinical_module, "FHIRTools", lambda: fhir)
    monkeypatch.setattr(clinical_module, "ActionPlanEngine", lambda: engine)
    monkeypatch.setattr(clinical_module, "MemoryTools", lambda: memory)
    monkeypatch.setattr(clinical_module, "SmartHomeTools", lambda: smart_home)
    monkeypatch.setattr(clinical_module, "ApprovalWorkflow", lambda: approval_workflow)
    monkeypatch.setattr(clinical_module, "load_asthma_action_plan", lambda data: data)

    return fhir, engine, memory, smart_home, approval_workflow


def test_clinical_filters_medications_based_on_preferences(state_factory, fake_s3, monkeypatch):
    meds = [
        {"medicationCodeableConcept": {"coding": [{"display": "Powder Inhaler"}]}},
        {"medicationCodeableConcept": {"coding": [{"display": "Nebulizer Solution"}]}},
    ]
    recs = {"zone": "yellow", "recommendations": {"actions": ["Monitor"], "medications": []}}
    preferences = [{"text": "Avoid powder inhalers"}]

    fhir, engine, _, _, _ = _patch_clinical_dependencies(
        monkeypatch,
        medications=meds,
        action_plan={"plan": "custom"},
        recommendations=recs,
        memory_preferences=preferences,
    )

    state = state_factory(sentry_output={"risk_score": 0.5, "risk_level": "moderate", "risk_factors": []})
    agent = ClinicalAgent()
    agent.s3_client = fake_s3
    output = agent.execute(state)

    assert "medication_preferences_applied" in output["recommendations"]
    assert engine.last_context is not None
    assert len(engine.last_context["current_medications"]) == 1
    assert engine.last_context["current_medications"][0]["medicationCodeableConcept"]["coding"][0]["display"] == "Nebulizer Solution"
    assert len(fake_s3.uploads) == 1


def test_clinical_red_zone_requests_approval(state_factory, fake_s3, monkeypatch):
    recs = {"zone": "red", "recommendations": {"actions": ["Use rescue inhaler"], "medications": []}}
    approval = StubApprovalWorkflow()
    smart_home = StubSmartHome()

    _patch_clinical_dependencies(
        monkeypatch,
        medications=[],
        action_plan={"plan": "critical"},
        recommendations=recs,
        memory_preferences=[],
        smart_home=smart_home,
        approval_workflow=approval,
    )

    state = state_factory(sentry_output={"risk_score": 0.9, "risk_level": "high", "risk_factors": ["AQI"]})
    agent = ClinicalAgent()
    agent.s3_client = fake_s3
    output = agent.execute(state)

    assert output["recommendations"]["zone"] == "red"
    assert output["requires_approval"] is True
    assert len(approval.requests) == 1
    assert output["iot_actions"][0]["status"] == "pending_approval"


def test_clinical_red_zone_auto_adjusts_when_no_approval_required(state_factory, fake_s3, monkeypatch, patched_settings):
    patched_settings.app.require_approval_for_critical_actions = False
    recs = {"zone": "red", "recommendations": {"actions": ["Use rescue inhaler"], "medications": []}}
    smart_home = StubSmartHome(success=True)

    _patch_clinical_dependencies(
        monkeypatch,
        medications=[],
        action_plan={"plan": "critical"},
        recommendations=recs,
        memory_preferences=[],
        smart_home=smart_home,
    )

    state = state_factory(sentry_output={"risk_score": 0.9, "risk_level": "high", "risk_factors": ["AQI"]})
    agent = ClinicalAgent()
    agent.settings.app.require_approval_for_critical_actions = False
    agent.s3_client = fake_s3
    output = agent.execute(state)

    assert output["requires_approval"] is False
    assert output["iot_actions"][0]["status"] == "success"
    assert smart_home.calls[0]["device_id"] == "hvac-001"


def test_clinical_handles_failure_and_logs_error(state_factory, monkeypatch):
    class BrokenEngine(StubActionPlanEngine):
        def generate_recommendations(self, **kwargs):
            raise RuntimeError("engine offline")

    meds = [{"medicationCodeableConcept": {"coding": [{"display": "Rescue Inhaler"}]}}]
    fhir = StubFHIRTools(medications=meds, careplan=None)
    engine = BrokenEngine(recommendations={})

    monkeypatch.setattr(clinical_module, "FHIRTools", lambda: fhir)
    monkeypatch.setattr(clinical_module, "ActionPlanEngine", lambda: engine)
    monkeypatch.setattr(clinical_module, "MemoryTools", lambda: StubMemoryTools([]))
    monkeypatch.setattr(clinical_module, "SmartHomeTools", lambda: StubSmartHome())
    monkeypatch.setattr(clinical_module, "ApprovalWorkflow", lambda: StubApprovalWorkflow())
    monkeypatch.setattr(clinical_module, "load_asthma_action_plan", lambda data: data or {"default": True})

    state = state_factory(sentry_output={"risk_score": 0.4, "risk_level": "moderate", "risk_factors": []})
    agent = ClinicalAgent()
    output = agent.execute(state)

    assert output["recommendations"]["zone"] == "green"
    assert "error" in output
    assert any(err["type"] == "clinical_execution_error" for err in state["errors"])

