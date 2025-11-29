"""
LangGraph Orchestrator Graph for Respiro

Builds the state machine that coordinates all 5 agents with priority interrupts
and human-in-the-loop checkpoints.
"""

from __future__ import annotations

from typing import Literal, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from respiro.orchestrator.state import RespiroState, RiskLevel, InterruptType, update_state_timestamp
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


def check_priority_interrupt(state: RespiroState) -> Literal["handle_interrupt", "route_to_agent"]:
    """
    Check if there's a priority interrupt that needs immediate handling.
    
    Returns:
        Next node to route to
    """
    if state.get("has_priority_interrupt") and state.get("interrupt_type") == InterruptType.MEDICAL_EMERGENCY:
        logger.warning(f"Priority interrupt detected for patient {state.get('patient_id')}")
        return "handle_interrupt"
    return "route_to_agent"


def route_to_agent(
    state: RespiroState,
) -> Literal["sentry", "meteorologist", "cartographer", "navigator", "clinical", "negotiator", "rewards", "end"]:
    """
    Route to the appropriate agent based on current state.
    
    Returns:
        Next agent node to execute
    """
    patient_id = state.get("patient_id")
    current_risk = state.get("current_risk_level", RiskLevel.LOW)
    active_agents = state.get("active_agents", [])
    
    # Always start with Sentry for sensor fusion
    if "sentry" not in active_agents:
        logger.info(f"Routing to Sentry agent for patient {patient_id}")
        return "sentry"
    
    if "meteorologist" not in active_agents:
        logger.info(f"Routing to Meteorologist agent for patient {patient_id}")
        return "meteorologist"

    if "cartographer" not in active_agents:
        logger.info(f"Routing to Cartographer agent for patient {patient_id}")
        return "cartographer"
    
    # After Cartographer, use Navigator to explain routes
    if "cartographer" in active_agents and "navigator" not in active_agents:
        logger.info(f"Routing to Navigator agent for patient {patient_id}")
        return "navigator"

    if "clinical" not in active_agents:
        logger.info(f"Routing to Clinical agent for patient {patient_id}")
        return "clinical"
    
    # After Clinical, use Negotiator for communication
    if "clinical" in active_agents and "negotiator" not in active_agents:
        logger.info(f"Routing to Negotiator agent for patient {patient_id}")
        return "negotiator"
    
    # Finally, Rewards agent
    if "negotiator" in active_agents and "rewards" not in active_agents:
        logger.info(f"Routing to Rewards agent for patient {patient_id}")
        return "rewards"
    
    # All agents completed
    logger.info(f"All agents completed for patient {patient_id}")
    return "end"


def handle_interrupt(state: RespiroState) -> RespiroState:
    """
    Handle priority interrupts (medical emergencies).
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    interrupt_type = state.get("interrupt_type")
    patient_id = state.get("patient_id")
    
    logger.critical(f"Handling {interrupt_type} interrupt for patient {patient_id}")
    
    # Set emergency risk level
    state["current_risk_level"] = RiskLevel.EMERGENCY
    state["risk_score"] = 1.0
    state["human_approval_required"] = True
    
    # Add emergency action to context
    state["context"]["emergency_action"] = "Immediate medical attention required"
    
    return update_state_timestamp(state)


def sentry_node(state: RespiroState) -> RespiroState:
    """
    Execute Sentry agent for sensor fusion.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with Sentry output
    """
    from respiro.agents.sentry import SentryAgent
    
    logger.info(f"Executing Sentry agent for patient {state.get('patient_id')}")
    
    try:
        agent = SentryAgent()
        output = agent.execute(state)
        
        state["sentry_output"] = output
        state["sensor_data"] = output.get("sensor_data", {})
        state["current_risk_level"] = output.get("risk_level", RiskLevel.LOW)
        state["risk_score"] = output.get("risk_score", 0.0)
        state["risk_factors"] = output.get("risk_factors", [])
        
        # Track IoT actions
        if output.get("iot_actions"):
            state["iot_actions"] = state.get("iot_actions", []) + output.get("iot_actions", [])
        if output.get("requires_approval"):
            state["human_approval_required"] = True
            if output.get("iot_actions"):
                # Add approval requests to state
                for iot_action in output.get("iot_actions", []):
                    if iot_action.get("approval_request_id"):
                        state["approval_requests"] = state.get("approval_requests", []) + [{
                            "request_id": iot_action.get("approval_request_id"),
                            "type": "iot_action",
                            "action": iot_action.get("action"),
                            "device": iot_action.get("device"),
                            "timestamp": datetime.utcnow().isoformat()
                        }]
        
        if "sentry" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["sentry"]
        state["agent_status"]["sentry"] = "completed"
        
    except Exception as e:
        logger.error(f"Sentry agent failed: {e}", exc_info=True)
        state["agent_status"]["sentry"] = "failed"
        state["errors"] = state.get("errors", []) + [{
            "type": "sentry_error",
            "message": str(e),
            "agent": "sentry"
        }]
    
    return update_state_timestamp(state)


def meteorologist_node(state: RespiroState) -> RespiroState:
    """
    Execute Meteorologist agent for wind/pollen context.
    """
    from respiro.agents.meteorologist import MeteorologistAgent

    logger.info(f"Executing Meteorologist agent for patient {state.get('patient_id')}")

    try:
        agent = MeteorologistAgent()
        output = agent.execute(state)
        state["meteorology_output"] = output
        state["wind_context"] = output.get("wind", {})
        state["pollen_alerts"] = output.get("alerts", [])
        if "meteorologist" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["meteorologist"]
        state["agent_status"]["meteorologist"] = "completed"
    except Exception as e:
        logger.error(f"Meteorologist agent failed: {e}", exc_info=True)
        state["agent_status"]["meteorologist"] = "failed"
        state["errors"] = state.get("errors", []) + [
            {"type": "meteorologist_error", "message": str(e), "agent": "meteorologist"}
        ]

    return update_state_timestamp(state)


def cartographer_node(state: RespiroState) -> RespiroState:
    """
    Execute Cartographer agent for routing.
    """
    from respiro.agents.cartographer import CartographerAgent

    logger.info(f"Executing Cartographer agent for patient {state.get('patient_id')}")
    try:
        agent = CartographerAgent()
        output = agent.execute(state)
        state["cartographer_output"] = output
        state["route_recommendations"] = [output]
        if "cartographer" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["cartographer"]
        state["agent_status"]["cartographer"] = "completed"
    except Exception as e:
        logger.error(f"Cartographer agent failed: {e}", exc_info=True)
        state["agent_status"]["cartographer"] = "failed"
        state["errors"] = state.get("errors", []) + [
            {"type": "cartographer_error", "message": str(e), "agent": "cartographer"}
        ]

    return update_state_timestamp(state)


def navigator_node(state: RespiroState) -> RespiroState:
    """
    Execute Navigator agent for route explanations.
    """
    from respiro.agents.navigator import NavigatorAgent

    logger.info(f"Executing Navigator agent for patient {state.get('patient_id')}")
    try:
        agent = NavigatorAgent()
        output = agent.execute(state)
        state["navigator_output"] = output
        if "navigator" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["navigator"]
        state["agent_status"]["navigator"] = "completed"
    except Exception as e:
        logger.error(f"Navigator agent failed: {e}", exc_info=True)
        state["agent_status"]["navigator"] = "failed"
        state["errors"] = state.get("errors", []) + [
            {"type": "navigator_error", "message": str(e), "agent": "navigator"}
        ]

    return update_state_timestamp(state)


def clinical_node(state: RespiroState) -> RespiroState:
    """
    Execute Clinical agent for FHIR-based action plan execution.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with Clinical output
    """
    from respiro.agents.clinical import ClinicalAgent
    
    logger.info(f"Executing Clinical agent for patient {state.get('patient_id')}")
    
    try:
        agent = ClinicalAgent()
        output = agent.execute(state)
        
        state["clinical_output"] = output
        state["clinical_recommendations"] = output.get("recommendations", {})
        state["human_approval_required"] = output.get("requires_approval", False)
        
        # Track IoT actions from Clinical agent
        if output.get("iot_actions"):
            state["iot_actions"] = state.get("iot_actions", []) + output.get("iot_actions", [])
            # Add approval requests to state
            for iot_action in output.get("iot_actions", []):
                if iot_action.get("approval_request_id"):
                    state["approval_requests"] = state.get("approval_requests", []) + [{
                        "request_id": iot_action.get("approval_request_id"),
                        "type": "iot_action",
                        "action": iot_action.get("action"),
                        "device": iot_action.get("device"),
                        "timestamp": datetime.utcnow().isoformat()
                    }]
        
        if "clinical" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["clinical"]
        state["agent_status"]["clinical"] = "completed"
        
    except Exception as e:
        logger.error(f"Clinical agent failed: {e}", exc_info=True)
        state["agent_status"]["clinical"] = "failed"
        state["errors"] = state.get("errors", []) + [{
            "type": "clinical_error",
            "message": str(e),
            "agent": "clinical",
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }]
        # Set safe defaults
        state["clinical_recommendations"] = {
            "zone": "green",
            "recommendations": {"actions": ["Continue current medication"]}
        }
    
    return update_state_timestamp(state)


def negotiator_node(state: RespiroState) -> RespiroState:
    """
    Execute Negotiator agent for empathetic communication.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with Negotiator output
    """
    from respiro.agents.negotiator import NegotiatorAgent
    
    logger.info(f"Executing Negotiator agent for patient {state.get('patient_id')}")
    
    try:
        agent = NegotiatorAgent()
        output = agent.execute(state)
        
        state["negotiator_output"] = output
        state["negotiator_response"] = output.get("response", "")
        
        # Track route recommendations
        if output.get("route_recommendations"):
            state["route_recommendations"] = output.get("route_recommendations", [])
        
        # Track memory retrieval
        if output.get("user_preferences_used", 0) > 0:
            state["memory_retrieval"] = state.get("memory_retrieval", []) + [{
                "type": "user_preferences",
                "count": output.get("user_preferences_used", 0),
                "timestamp": datetime.utcnow().isoformat()
            }]
        
        if "negotiator" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["negotiator"]
        state["agent_status"]["negotiator"] = "completed"
        
    except Exception as e:
        logger.error(f"Negotiator agent failed: {e}", exc_info=True)
        state["agent_status"]["negotiator"] = "failed"
        state["errors"] = state.get("errors", []) + [{
            "type": "negotiator_error",
            "message": str(e),
            "agent": "negotiator",
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }]
        # Set safe defaults
        state["negotiator_response"] = "I'm here to help you manage your asthma."
    
    return update_state_timestamp(state)


def rewards_node(state: RespiroState) -> RespiroState:
    """
    Execute Rewards agent for gamification.
    
    Args:
        state: Current state
        
    Returns:
        Updated state with Rewards output
    """
    from respiro.agents.rewards import RewardsAgent
    
    logger.info(f"Executing Rewards agent for patient {state.get('patient_id')}")
    
    try:
        agent = RewardsAgent()
        output = agent.execute(state)
        
        state["rewards_output"] = output
        state["rewards_status"] = output.get("status", {})
        
        if "rewards" not in state.get("active_agents", []):
            state["active_agents"] = state.get("active_agents", []) + ["rewards"]
        state["agent_status"]["rewards"] = "completed"
        
    except Exception as e:
        logger.error(f"Rewards agent failed: {e}", exc_info=True)
        state["agent_status"]["rewards"] = "failed"
        state["errors"] = state.get("errors", []) + [{
            "type": "rewards_error",
            "message": str(e),
            "agent": "rewards",
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }]
        # Set safe defaults
        state["rewards_status"] = {
            "adherence_score": 0.0,
            "points": 0,
            "rewards": []
        }
    
    return update_state_timestamp(state)


def check_approval(state: RespiroState) -> Literal["wait_for_approval", "continue"]:
    """
    Check if human approval is required.
    
    Returns:
        Next node based on approval status
    """
    if not state.get("human_approval_required"):
        return "continue"
    
    # Check if approval has been received
    approval_requests = state.get("approval_requests", [])
    approval_responses = state.get("approval_responses", {})
    
    if not approval_requests:
        return "continue"
    
    # Check if all approval requests have been responded to
    all_responded = True
    for request in approval_requests:
        request_id = request.get("request_id")
        if request_id and request_id not in approval_responses:
            all_responded = False
            break
    
    if all_responded:
        # All approvals received, continue
        state["human_approval_required"] = False
        return "continue"
    
    # Still waiting for approvals
    return "wait_for_approval"


def wait_for_approval(state: RespiroState) -> RespiroState:
    """
    Wait for human approval (checkpoint).
    
    This node serves as a checkpoint where the system waits for human approval.
    In production, this would integrate with a frontend or notification system.
    
    Args:
        state: Current state
        
    Returns:
        Updated state
    """
    patient_id = state.get("patient_id")
    approval_requests = state.get("approval_requests", [])
    
    logger.info(f"Waiting for approval for patient {patient_id}. Pending requests: {len(approval_requests)}")
    
    # Log pending approval requests
    for request in approval_requests:
        request_id = request.get("request_id")
        action = request.get("action")
        logger.info(f"  - Request {request_id}: {action}")
    
    # In a real implementation, this would:
    # 1. Send notifications to the user/frontend
    # 2. Wait for approval responses via API
    # 3. Update approval_responses in state
    
    # For now, we'll just mark that we're waiting
    state["agent_status"]["approval"] = "waiting"
    
    return update_state_timestamp(state)


def build_graph() -> StateGraph:
    """
    Build the LangGraph state machine.
    
    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(RespiroState)
    
    # Add nodes
    graph.add_node("handle_interrupt", handle_interrupt)
    graph.add_node("sentry", sentry_node)
    graph.add_node("meteorologist", meteorologist_node)
    graph.add_node("cartographer", cartographer_node)
    graph.add_node("navigator", navigator_node)
    graph.add_node("clinical", clinical_node)
    graph.add_node("negotiator", negotiator_node)
    graph.add_node("rewards", rewards_node)
    graph.add_node("wait_for_approval", wait_for_approval)
    
    # Set entry point
    graph.set_entry_point("check_priority_interrupt")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "check_priority_interrupt",
        check_priority_interrupt,
        {
            "handle_interrupt": "handle_interrupt",
            "route_to_agent": "route_to_agent"
        }
    )
    
    graph.add_conditional_edges(
        "route_to_agent",
        route_to_agent,
        {
            "sentry": "sentry",
            "meteorologist": "meteorologist",
            "cartographer": "cartographer",
            "navigator": "navigator",
            "clinical": "clinical",
            "negotiator": "negotiator",
            "rewards": "rewards",
            "end": END
        }
    graph.add_conditional_edges(
        "meteorologist",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )

    graph.add_conditional_edges(
        "cartographer",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )
    
    graph.add_conditional_edges(
        "navigator",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )

    )
    
    # After each agent, check for approval requirement
    graph.add_conditional_edges(
        "sentry",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )
    
    graph.add_conditional_edges(
        "clinical",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )
    
    graph.add_conditional_edges(
        "negotiator",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": "route_to_agent"
        }
    )
    
    graph.add_conditional_edges(
        "rewards",
        check_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "continue": END
        }
    )
    
    # After interrupt handling, route back
    graph.add_edge("handle_interrupt", "wait_for_approval")
    graph.add_edge("wait_for_approval", "route_to_agent")
    
    # Compile with checkpointing
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
