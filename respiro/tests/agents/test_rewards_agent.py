from __future__ import annotations

from datetime import datetime, timedelta
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


rewards_module = _load_agent_module("rewards")
RewardsAgent = rewards_module.RewardsAgent


class StubInsuranceClient:
    def __init__(self, succeed: bool = True):
        self.succeed = succeed
        self.requests: List[Dict[str, Any]] = []

    def request_premium_adjustment(self, patient_id: str, adherence_score: float) -> bool:
        self.requests.append({"patient_id": patient_id, "score": adherence_score})
        if not self.succeed:
            raise RuntimeError("insurance offline")
        return True


class StubPharmacyClient:
    def __init__(self):
        self.codes: List[Dict[str, Any]] = []

    def generate_discount_code(self, patient_id: str, medication_name: str) -> str:
        code = f"DISC-{medication_name[:3].upper()}"
        self.codes.append({"patient_id": patient_id, "medication": medication_name, "code": code})
        return code


def _patch_rewards_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    insurance: StubInsuranceClient,
    pharmacy: StubPharmacyClient,
):
    monkeypatch.setattr(rewards_module, "InsuranceClient", lambda: insurance)
    monkeypatch.setattr(rewards_module, "PharmacyClient", lambda: pharmacy)


def test_rewards_unlocks_high_value_rewards(state_factory, fake_s3, monkeypatch, patient_id):
    insurance = StubInsuranceClient()
    pharmacy = StubPharmacyClient()
    _patch_rewards_dependencies(monkeypatch, insurance=insurance, pharmacy=pharmacy)

    agent = RewardsAgent()
    agent.s3_client = fake_s3

    monkeypatch.setattr(rewards_module.RewardsAgent, "_calculate_adherence", lambda self, state, pid: 0.95)
    monkeypatch.setattr(rewards_module.RewardsAgent, "_award_points", lambda self, score, state: 1200)

    recommendations = {
        "recommendations": {"medications": [{"medications": ["montelukast"]}]},
        "zone": "green",
    }
    state = state_factory(
        clinical_output={"recommendations": {"zone": "green"}},
        clinical_recommendations=recommendations,
        iot_actions=[{"device": "air_purifier"}],
    )

    output = agent.execute(state)

    assert output["adherence_score"] == 0.95
    assert output["points"] == 1200
    assert any(reward["type"] == "pharmacy_discount" for reward in output["rewards"])
    assert output["insurance_adjustment_requested"] is True
    assert pharmacy.codes[0]["medication"] == "montelukast"
    assert insurance.requests[0]["patient_id"] == patient_id


def test_rewards_calculates_adherence_with_history(state_factory, fake_s3, monkeypatch, patient_id):
    insurance = StubInsuranceClient()
    pharmacy = StubPharmacyClient()
    _patch_rewards_dependencies(monkeypatch, insurance=insurance, pharmacy=pharmacy)

    history_key = f"patients/{patient_id}/adherence_history.json"
    history_payload = {
        "history": [
            {"score": 0.2, "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat()},
            {"score": 0.8, "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat()},
        ]
    }
    recommendations = {
        "recommendations": {"medications": []},
        "zone": "yellow",
    }
    state = state_factory(
        clinical_output={"recommendations": {"zone": "yellow"}},
        clinical_recommendations=recommendations,
        iot_actions=[{"device": "air_purifier"}],
    )

    agent = RewardsAgent()
    agent.s3_client = fake_s3

    score_no_history = agent._calculate_adherence(state, patient_id)
    assert score_no_history < 0.7  # baseline without history

    fake_s3.storage[history_key] = history_payload

    output = agent.execute(state)

    assert output["adherence_score"] != pytest.approx(score_no_history)
    assert fake_s3.uploads  # history persisted
    assert fake_s3.uploads  # history persisted


def test_rewards_returns_safe_defaults_on_failure(state_factory, monkeypatch):
    insurance = StubInsuranceClient()
    pharmacy = StubPharmacyClient()
    _patch_rewards_dependencies(monkeypatch, insurance=insurance, pharmacy=pharmacy)

    def boom(*args, **kwargs):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(rewards_module.RewardsAgent, "_calculate_adherence", boom)

    agent = RewardsAgent()
    state = state_factory(clinical_output={"recommendations": {}}, clinical_recommendations={})
    output = agent.execute(state)

    assert output["adherence_score"] == 0.0
    assert output["error"] == "unexpected failure"

