"""
LangGraph State Management for Respiro Orchestrator

Defines the state schema used throughout the agentic system.
"""

from __future__ import annotations

from typing import TypedDict, Any, Optional, List, Dict
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Asthma risk levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    EMERGENCY = "emergency"


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


class InterruptType(str, Enum):
    """Types of interrupts that can stop agent execution."""
    MEDICAL_EMERGENCY = "medical_emergency"
    CRITICAL_ACTION = "critical_action"
    USER_REQUEST = "user_request"
    SYSTEM_ERROR = "system_error"


class RespiroState(TypedDict, total=False):
    """
    Main state schema for Respiro orchestrator.
    
    This state is passed between all agents and nodes in the LangGraph.
    """
    # Patient and Session Information
    patient_id: str
    session_id: str
    timestamp: datetime
    
    # Current Risk Assessment
    current_risk_level: RiskLevel
    risk_score: float  # 0.0 to 1.0
    risk_factors: List[str]
    
    # Active Agents
    active_agents: List[str]  # List of agent names currently active
    agent_status: Dict[str, AgentStatus]  # Status of each agent
    
    # Interrupts and Priority Handling
    interrupts: List[Dict[str, Any]]  # List of interrupt events
    has_priority_interrupt: bool
    interrupt_type: Optional[InterruptType]
    
    # Context and Data
    context: Dict[str, Any]  # General context data
    sensor_data: Dict[str, Any]  # Fused sensor data from Sentry
    clinical_recommendations: Dict[str, Any]  # Recommendations from Clinical agent
    negotiator_response: Optional[str]  # Response from Negotiator agent
    rewards_status: Dict[str, Any]  # Status from Rewards agent
    iot_actions: List[Dict[str, Any]]  # IoT device actions taken
    route_recommendations: List[Dict[str, Any]]  # Route optimization recommendations
    
    # Memory and Personalization
    memory_retrieval: List[Dict[str, Any]]  # Retrieved memories from vector store
    user_preferences: Dict[str, Any]  # User preferences and quirks
    
    # Human-in-the-Loop
    human_approval_required: bool
    approval_requests: List[Dict[str, Any]]  # Pending approval requests
    approval_responses: Dict[str, Any]  # Responses to approval requests
    
    # Agent Outputs
    sentry_output: Optional[Dict[str, Any]]
    clinical_output: Optional[Dict[str, Any]]
    negotiator_output: Optional[Dict[str, Any]]
    rewards_output: Optional[Dict[str, Any]]
    
    # Error Handling
    errors: List[Dict[str, Any]]  # List of errors encountered
    retry_count: int  # Number of retries attempted
    
    # State Persistence
    state_version: int  # Version for state management
    last_updated: datetime
    
    # Long-term Context
    session_history: List[Dict[str, Any]]  # History of this session
    previous_sessions: List[str]  # References to previous session IDs


def create_initial_state(
    patient_id: str,
    session_id: Optional[str] = None,
    initial_context: Optional[Dict[str, Any]] = None
) -> RespiroState:
    """
    Create an initial state for a new session.
    
    Args:
        patient_id: Unique patient identifier
        session_id: Optional session ID (generated if not provided)
        initial_context: Optional initial context data
        
    Returns:
        Initialized RespiroState
    """
    from datetime import datetime
    import uuid
    
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    now = datetime.utcnow()
    
    return RespiroState(
        patient_id=patient_id,
        session_id=session_id,
        timestamp=now,
        current_risk_level=RiskLevel.LOW,
        risk_score=0.0,
        risk_factors=[],
        active_agents=[],
        agent_status={},
        interrupts=[],
        has_priority_interrupt=False,
        interrupt_type=None,
        context=initial_context or {},
        sensor_data={},
        clinical_recommendations={},
        negotiator_response=None,
        rewards_status={},
        iot_actions=[],
        route_recommendations=[],
        memory_retrieval=[],
        user_preferences={},
        human_approval_required=False,
        approval_requests=[],
        approval_responses={},
        sentry_output=None,
        clinical_output=None,
        negotiator_output=None,
        rewards_output=None,
        errors=[],
        retry_count=0,
        state_version=1,
        last_updated=now,
        session_history=[],
        previous_sessions=[]
    )


def update_state_timestamp(state: RespiroState) -> RespiroState:
    """Update the timestamp and version in state."""
    from datetime import datetime
    
    state["timestamp"] = datetime.utcnow()
    state["last_updated"] = datetime.utcnow()
    state["state_version"] = state.get("state_version", 0) + 1
    return state


def add_interrupt(
    state: RespiroState,
    interrupt_type: InterruptType,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
) -> RespiroState:
    """
    Add an interrupt to the state.
    
    Args:
        state: Current state
        interrupt_type: Type of interrupt
        message: Interrupt message
        metadata: Optional metadata
        
    Returns:
        Updated state
    """
    interrupt = {
        "type": interrupt_type.value,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    
    state["interrupts"] = state.get("interrupts", []) + [interrupt]
    
    # Set priority interrupt if it's a medical emergency
    if interrupt_type == InterruptType.MEDICAL_EMERGENCY:
        state["has_priority_interrupt"] = True
        state["interrupt_type"] = interrupt_type
    
    return update_state_timestamp(state)


def add_error(
    state: RespiroState,
    error_type: str,
    message: str,
    agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> RespiroState:
    """
    Add an error to the state.
    
    Args:
        state: Current state
        error_type: Type of error
        message: Error message
        agent: Agent that encountered the error
        metadata: Optional metadata
        
    Returns:
        Updated state
    """
    error = {
        "type": error_type,
        "message": message,
        "agent": agent,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    
    state["errors"] = state.get("errors", []) + [error]
    return update_state_timestamp(state)
