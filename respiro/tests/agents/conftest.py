from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional
import logging
import sys
import types

import pytest

from respiro.orchestrator.state import RespiroState, create_initial_state


def _install_stub_modules():
    """Inject lightweight stand-ins for heavy dependencies before importing agents."""

    if "respiro.utils.logging" not in sys.modules:
        logging_stub = types.ModuleType("respiro.utils.logging")

        def get_logger(name: str):
            return logging.getLogger(name)

        def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs):
            logger.log(level, message)

        logging_stub.get_logger = get_logger
        logging_stub.log_with_context = log_with_context
        sys.modules["respiro.utils.logging"] = logging_stub

    stub_modules = {
        "respiro.integrations.bedrock": {
            "BedrockClient": type(
                "BedrockClient",
                (),
                {"generate_empathetic_response": lambda self, context, recommendations: "stub response"},
            )
        },
        "respiro.integrations.calendar": {
            "GoogleCalendarClient": type(
                "GoogleCalendarClient",
                (),
                {
                    "find_events_to_reschedule": lambda self, *args, **kwargs: [],
                    "reschedule_event": lambda self, *args, **kwargs: True,
                },
            )
        },
        "respiro.tools.route_tools": {
            "RouteOptimizer": type(
                "RouteOptimizer",
                (),
                {"get_route_with_aqi": lambda self, origin, destination, forecast: {}},
            )
        },
        "respiro.integrations.insurance": {
            "InsuranceClient": type(
                "InsuranceClient",
                (),
                {"request_premium_adjustment": lambda self, patient_id, score: True},
            )
        },
        "respiro.integrations.pharmacy": {
            "PharmacyClient": type(
                "PharmacyClient",
                (),
                {"generate_discount_code": lambda self, patient_id, medication_name: "TEST-CODE"},
            )
        },
        "respiro.tools.fhir_tools": {
            "FHIRTools": type(
                "FHIRTools",
                (),
                {
                    "load_careplan": lambda self, *args, **kwargs: None,
                    "create_default_asthma_action_plan": lambda self, *args, **kwargs: {},
                    "get_patient_medications": lambda self, *args, **kwargs: [],
                },
            )
        },
        "respiro.tools.smart_home_tools": {
            "SmartHomeTools": type(
                "SmartHomeTools",
                (),
                {
                    "adjust_hvac": lambda self, *args, **kwargs: True,
                    "control_air_purifier": lambda self, *args, **kwargs: True,
                },
            )
        },
        "respiro.tools.memory_tools": {
            "MemoryTools": type(
                "MemoryTools",
                (),
                {"retrieve_preferences": lambda self, *args, **kwargs: [], "vector_store": None},
            )
        },
        "respiro.utils.approval": {
            "ApprovalWorkflow": type(
                "ApprovalWorkflow",
                (),
                {"request_approval": lambda self, *args, **kwargs: {"status": "requested"}},
            )
        },
        "respiro.models.fhir_models": {
            "load_asthma_action_plan": lambda data: data or {},
        },
    }

    for module_name, attributes in stub_modules.items():
        if module_name in sys.modules:
            continue
        module = types.ModuleType(module_name)
        for attr, value in attributes.items():
            setattr(module, attr, value)
        sys.modules[module_name] = module


_install_stub_modules()


class FakeS3Client:
    """In-memory S3 stub that records uploads."""

    def __init__(self):
        self.uploads: List[Dict[str, Any]] = []
        self.storage: Dict[str, Any] = {}

    def upload_json(self, key: str, data: Dict[str, Any], metadata: Optional[Dict[str, str]] = None) -> bool:
        self.uploads.append({"key": key, "data": deepcopy(data), "metadata": metadata})
        self.storage[key] = deepcopy(data)
        return True

    def download_json(self, key: str) -> Optional[Dict[str, Any]]:
        payload = self.storage.get(key)
        return deepcopy(payload) if payload is not None else None


class DummyApprovalWorkflow:
    """Records approval requests for assertions."""

    def __init__(self):
        self.requests: List[Dict[str, Any]] = []

    def request_approval(self, request_id: str, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"request_id": request_id, "action": action, "context": context, "status": "requested"}
        self.requests.append(payload)
        return payload


class DummyVectorStore:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def store_memory(self, patient_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        self.records.append({"patient_id": patient_id, "text": text, "metadata": metadata})
        return True

    def retrieve_memories(self, patient_id: str, query: str) -> List[Dict[str, Any]]:
        return [record for record in self.records if record["patient_id"] == patient_id]


class DummyMemoryTools:
    def __init__(self):
        self.preferences: Dict[str, List[Dict[str, Any]]] = {}
        self.vector_store = DummyVectorStore()

    def store_preferences(self, patient_id: str, prefs: List[Dict[str, Any]]):
        self.preferences[patient_id] = prefs

    def retrieve_preferences(self, patient_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.preferences.get(patient_id, [])


@pytest.fixture(scope="session")
def patient_id() -> str:
    return "patient-test-123"


@pytest.fixture
def base_state(patient_id: str) -> RespiroState:
    """Baseline orchestrator state seeded with deterministic context."""
    state = create_initial_state(
        patient_id=patient_id,
        session_id="session-test",
        initial_context={
            "location": {"latitude": 37.7749, "longitude": -122.4194},
            "hvac_device_id": "hvac-001",
            "air_purifier_device_id": "air-001",
        },
    )
    return state


@pytest.fixture
def state_factory(base_state: RespiroState) -> Callable[..., RespiroState]:
    """Factory to clone and extend baseline state with overrides."""

    def _factory(**overrides: Any) -> RespiroState:
        state = deepcopy(base_state)
        for key, value in overrides.items():
            state[key] = value
        return state

    return _factory


@pytest.fixture(autouse=True)
def patched_settings(monkeypatch: pytest.MonkeyPatch):
    """Provide minimal settings used inside agents."""
    settings = SimpleNamespace(
        app=SimpleNamespace(require_approval_for_critical_actions=True),
        aws=SimpleNamespace(region="us-east-1", s3_bucket_name="respiro-test-bucket"),
    )
    monkeypatch.setattr("respiro.config.settings.get_settings", lambda: settings)
    return settings


@pytest.fixture
def fake_s3(monkeypatch: pytest.MonkeyPatch) -> FakeS3Client:
    client = FakeS3Client()
    monkeypatch.setattr("respiro.storage.s3_client.get_s3_client", lambda: client)
    return client


@pytest.fixture
def approval_workflow_stub() -> DummyApprovalWorkflow:
    return DummyApprovalWorkflow()


@pytest.fixture
def memory_tools_stub() -> DummyMemoryTools:
    return DummyMemoryTools()


@pytest.fixture
def sentry_result_factory() -> Callable[..., Dict[str, Any]]:
    """Utility to build synthetic Sentry outputs."""

    def _factory(
        *,
        risk_level: str = "low",
        risk_score: float = 0.1,
        risk_factors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors or ["baseline"],
            "sensor_data": {"aqi": {"pm25": 20}, "pollen": {"grass": 10}},
        }

    return _factory


@pytest.fixture
def clinical_recommendations_factory() -> Callable[..., Dict[str, Any]]:
    """Utility to generate action plan recommendation payloads."""

    def _factory(zone: str = "green", medications: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return {
            "zone": zone,
            "recommendations": {
                "actions": ["Continue maintenance inhaler"] if zone == "green" else ["Use rescue inhaler"],
                "monitoring": ["Check symptoms twice daily"],
                "medications": medications or [],
            },
        }

    return _factory


