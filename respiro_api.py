"""
Respiro API Server

FastAPI server exposing Respiro agentic system endpoints.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional, Dict, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from respiro.orchestrator.main import get_orchestrator
from respiro.orchestrator.state import create_initial_state
from respiro.storage.s3_client import get_s3_client
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Respiro API Server", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class SessionCreateRequest(BaseModel):
    patient_id: str
    initial_context: Optional[Dict[str, Any]] = None

class ApprovalRequest(BaseModel):
    request_id: str
    approved: bool
    reason: Optional[str] = None

class IoTControlRequest(BaseModel):
    device_id: str
    action: str
    parameters: Optional[Dict[str, Any]] = None

class UserFeedbackRequest(BaseModel):
    feedback: str
    category: str = "general"
    rating: Optional[int] = None

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Respiro API Server",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/api/sessions/create")
async def create_session(request: SessionCreateRequest):
    """Create a new orchestrator session."""
    try:
        orchestrator = get_orchestrator()
        session_id = orchestrator.create_session(
            request.patient_id,
            request.initial_context
        )
        return {"session_id": session_id, "patient_id": request.patient_id}
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/execute")
async def execute_session(session_id: str):
    """Execute orchestrator for a session."""
    try:
        orchestrator = get_orchestrator()
        state = orchestrator.execute(session_id)
        return {"session_id": session_id, "state": state}
    except Exception as e:
        logger.error(f"Failed to execute session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/status")
async def get_patient_status(patient_id: str):
    """Get current patient state with memory context."""
    try:
        s3_client = get_s3_client()
        patient_data = s3_client.load_patient_data(patient_id)
        
        # Load memory context
        try:
            from respiro.memory.vector_store import VectorStore
            vector_store = VectorStore()
            memories = vector_store.retrieve_memories(patient_id, "user preferences and interactions", n_results=5)
            if patient_data:
                patient_data["memory_context"] = {
                    "recent_memories": memories,
                    "memory_count": len(memories)
                }
            else:
                patient_data = {"memory_context": {"recent_memories": memories, "memory_count": len(memories)}}
        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")
            if patient_data:
                patient_data["memory_context"] = {"recent_memories": [], "memory_count": 0}
        
        if not patient_data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/recommendations")
async def get_recommendations(patient_id: str):
    """Get clinical recommendations."""
    try:
        s3_client = get_s3_client()
        # Get latest recommendations
        # Simplified - in production would query by timestamp
        return {"recommendations": [], "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/calendar")
async def get_calendar(patient_id: str):
    """Get calendar events."""
    try:
        from respiro.integrations.calendar import GoogleCalendarClient
        calendar = GoogleCalendarClient()
        events = calendar.list_events()
        return {"events": events}
    except Exception as e:
        logger.error(f"Failed to get calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/rewards")
async def get_rewards(patient_id: str):
    """Get rewards status."""
    try:
        s3_client = get_s3_client()
        # Get latest rewards data
        return {"points": 0, "rewards": [], "adherence_score": 0.0}
    except Exception as e:
        logger.error(f"Failed to get rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/memory")
async def get_memory(patient_id: str):
    """Get personalization memory."""
    try:
        from respiro.memory.vector_store import VectorStore
        vector_store = VectorStore()
        memories = vector_store.retrieve_memories(patient_id, "user preferences", n_results=10)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patient/{patient_id}/approval")
async def submit_approval(patient_id: str, request: ApprovalRequest):
    """Submit approval response."""
    try:
        from respiro.utils.approval import ApprovalWorkflow
        workflow = ApprovalWorkflow()
        success = workflow.submit_approval(request.request_id, request.approved, request.reason)
        
        if success:
            # Update orchestrator state if session is active
            orchestrator = get_orchestrator()
            # Find active session for patient
            for session_id, session in orchestrator.active_sessions.items():
                if session.get("patient_id") == patient_id:
                    state = session.get("state", {})
                    if "approval_responses" not in state:
                        state["approval_responses"] = {}
                    state["approval_responses"][request.request_id] = {
                        "approved": request.approved,
                        "reason": request.reason,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    # Clear approval requirement if all requests responded
                    approval_requests = state.get("approval_requests", [])
                    if all(req.get("request_id") in state["approval_responses"] for req in approval_requests):
                        state["human_approval_required"] = False
                    break
        
        return {
            "status": "approved" if request.approved else "rejected",
            "request_id": request.request_id,
            "success": success
        }
    except Exception as e:
        logger.error(f"Failed to submit approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/sentry/trigger")
async def get_trigger_detection(patient_id: str):
    """Get real-time trigger detection."""
    try:
        # Execute Sentry agent
        orchestrator = get_orchestrator()
        session_id = orchestrator.create_session(patient_id)
        state = orchestrator.execute(session_id)
        return state.get("sentry_output", {})
    except Exception as e:
        logger.error(f"Failed to get trigger detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/clinical/action-plan")
async def get_action_plan(patient_id: str):
    """Get FHIR action plan."""
    try:
        from respiro.tools.fhir_tools import FHIRTools
        fhir_tools = FHIRTools()
        careplan_id = f"asthma-action-plan-{patient_id}"
        careplan = fhir_tools.load_careplan(patient_id, careplan_id)
        if not careplan:
            careplan = fhir_tools.create_default_asthma_action_plan(patient_id)
        return careplan
    except Exception as e:
        logger.error(f"Failed to get action plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/iot/status")
async def get_iot_status(patient_id: str):
    """Get IoT device status."""
    try:
        from respiro.integrations.iot import IoTClient
        iot_client = IoTClient()
        
        # Get device IDs from patient context
        s3_client = get_s3_client()
        patient_data = s3_client.load_patient_data(patient_id)
        device_ids = patient_data.get("device_ids", {}) if patient_data else {}
        
        status = {}
        for device_type, device_id in device_ids.items():
            try:
                shadow = iot_client.get_device_shadow(device_id)
                status[device_type] = {
                    "device_id": device_id,
                    "shadow": shadow,
                    "status": "online" if shadow else "offline"
                }
            except Exception as e:
                logger.warning(f"Failed to get status for device {device_id}: {e}")
                status[device_type] = {
                    "device_id": device_id,
                    "status": "error",
                    "error": str(e)
                }
        
        return {"devices": status}
    except Exception as e:
        logger.error(f"Failed to get IoT status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patient/{patient_id}/iot/control")
async def control_iot_device(patient_id: str, request: IoTControlRequest):
    """Manually trigger IoT device control."""
    try:
        from respiro.tools.smart_home_tools import SmartHomeTools
        smart_home = SmartHomeTools()
        
        success = False
        if request.action == "control_air_purifier":
            power = request.parameters.get("power", "on") if request.parameters else "on"
            mode = request.parameters.get("mode", "auto") if request.parameters else "auto"
            success = smart_home.control_air_purifier(request.device_id, power, mode)
        elif request.action == "adjust_hvac":
            temperature = request.parameters.get("temperature", 22.0) if request.parameters else 22.0
            mode = request.parameters.get("mode", "cool") if request.parameters else "cool"
            success = smart_home.adjust_hvac(request.device_id, temperature, mode)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return {
            "success": success,
            "device_id": request.device_id,
            "action": request.action,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control IoT device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/routes")
async def get_route_recommendations(patient_id: str):
    """Get route recommendations."""
    try:
        orchestrator = get_orchestrator()
        # Get latest session for patient
        s3_client = get_s3_client()
        latest_session = s3_client.load_latest_session(patient_id)
        
        if latest_session:
            state = latest_session.get("state", {})
            route_recommendations = state.get("route_recommendations", [])
            return {
                "route_recommendations": route_recommendations,
                "count": len(route_recommendations),
                "timestamp": latest_session.get("updated_at")
            }
        else:
            return {"route_recommendations": [], "count": 0}
    except Exception as e:
        logger.error(f"Failed to get route recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patient/{patient_id}/feedback")
async def store_user_feedback(patient_id: str, request: UserFeedbackRequest):
    """Store user feedback for memory personalization."""
    try:
        from respiro.tools.memory_tools import MemoryTools
        memory_tools = MemoryTools()
        
        # Store feedback in memory
        success = memory_tools.store_preference(
            patient_id,
            request.feedback,
            category=request.category
        )
        
        # Store rating if provided
        if request.rating is not None:
            rating_text = f"User rating: {request.rating}/5 for {request.category}"
            memory_tools.store_preference(patient_id, rating_text, category="ratings")
        
        return {
            "success": success,
            "message": "Feedback stored successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to store feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    try:
        orchestrator = get_orchestrator()
        state = orchestrator.get_session_state(session_id)
        
        while True:
            # Send state updates
            if state:
                await websocket.send_json({"type": "state_update", "data": state})
            
            # Receive messages
            try:
                data = await websocket.receive_json()
                if data.get("type") == "execute":
                    state = orchestrator.execute(session_id)
                    await websocket.send_json({"type": "execution_complete", "data": state})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.app.api_server_host, port=settings.app.api_server_port)
