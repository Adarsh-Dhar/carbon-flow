"""
Respiro API Server

FastAPI server exposing Respiro agentic system endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from respiro.orchestrator.main import get_orchestrator
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger
from respiro.tools.route_service import RouteIntelligenceService

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

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_route_service: Optional[RouteIntelligenceService] = None


def _load_or_run_latest_state(patient_id: str) -> tuple[str, Dict[str, Any], str]:
    """
    Load the latest orchestrator state for a patient. If none exists yet,
    create a session and execute the orchestrator once to bootstrap data.
    """
    s3_client = get_s3_client()
    latest_session = s3_client.load_latest_session(patient_id)
    if latest_session and latest_session.get("state"):
        session_id = latest_session.get("session_id", "unknown")
        state = latest_session["state"]
        updated_at = latest_session.get("updated_at") or latest_session.get("created_at") or _utcnow_iso()
        return session_id, state, updated_at

    orchestrator = get_orchestrator()
    session_id = orchestrator.create_session(patient_id)
    state = orchestrator.execute(session_id)
    return session_id, state, _utcnow_iso()


def _get_route_service() -> RouteIntelligenceService:
    global _route_service
    if _route_service is None:
        _route_service = RouteIntelligenceService()
    return _route_service


def _parse_latlon(value: str) -> Tuple[float, float]:
    try:
        lat_str, lon_str = value.split(",")
        return float(lat_str), float(lon_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid coordinate '{value}'") from exc


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
        session_id, state, updated_at = _load_or_run_latest_state(patient_id)
        return {
            "patient_id": patient_id,
            "session_id": session_id,
            "current_risk_level": state.get("current_risk_level", "low"),
            "risk_score": state.get("risk_score", 0.0),
            "risk_factors": state.get("risk_factors", []),
            "timestamp": state.get("timestamp", updated_at),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/recommendations")
async def get_recommendations(patient_id: str):
    """Get clinical recommendations."""
    try:
        _, state, _ = _load_or_run_latest_state(patient_id)
        clinical_output = state.get("clinical_output")
        if not clinical_output:
            clinical_output = {
                "recommendations": state.get("clinical_recommendations"),
                "zone": state.get("clinical_recommendations", {}).get("zone"),
            }
        recommendations = clinical_output.get("recommendations")
        if not recommendations:
            raise HTTPException(status_code=404, detail="Clinical recommendations unavailable")
        return {
            "zone": clinical_output.get("zone", recommendations.get("zone", "green")),
            "risk_score": clinical_output.get("risk_score", state.get("risk_score", 0.0)),
            "risk_level": clinical_output.get("risk_level", state.get("current_risk_level", "low")),
            "risk_factors": clinical_output.get("risk_factors", state.get("risk_factors", [])),
            "recommendations": recommendations,
            "requires_approval": clinical_output.get("requires_approval", False),
            "timestamp": clinical_output.get("timestamp", state.get("timestamp", _utcnow_iso())),
        }
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/calendar")
async def get_calendar(patient_id: str):
    """Get calendar events."""
    try:
        _, state, _ = _load_or_run_latest_state(patient_id)
        negotiator_output = state.get("negotiator_output", {})
        events: List[Dict[str, Any]] = []
        for idx, action in enumerate(negotiator_output.get("calendar_actions", [])):
            event_time = action.get("new_time") or negotiator_output.get("timestamp") or _utcnow_iso()
            events.append({
                "id": action.get("event_id", f"event-{idx}"),
                "summary": action.get("event_summary", "Rescheduled event"),
                "start": {"dateTime": event_time, "timeZone": "UTC"},
                "end": {"dateTime": event_time, "timeZone": "UTC"},
                "description": f"Action: {action.get('action', 'update')}",
            })
        return {"events": events}
    except Exception as e:
        logger.error(f"Failed to get calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patient/{patient_id}/rewards")
async def get_rewards(patient_id: str):
    """Get rewards status."""
    try:
        _, state, _ = _load_or_run_latest_state(patient_id)
        rewards_output = state.get("rewards_output")
        if not rewards_output:
            raise HTTPException(status_code=404, detail="Rewards data unavailable")
        return {
            "adherence_score": rewards_output.get("adherence_score", 0.0),
            "points": rewards_output.get("points", 0),
            "rewards": rewards_output.get("rewards", []),
            "timestamp": rewards_output.get("timestamp", _utcnow_iso()),
        }
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


@app.get("/api/route")
async def get_route(
    start: str,
    end: str,
    sensitivity: str = "asthma",
) -> Dict[str, Any]:
    """Compute fastest vs cleanest route intelligence."""
    try:
        origin = _parse_latlon(start)
        destination = _parse_latlon(end)
        service = _get_route_service()
        return service.build_intelligence(origin, destination, sensitivity)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/purpleair/sensors")
async def get_purpleair_sensors() -> Dict[str, Any]:
    """Get real-time PurpleAir sensor data for San Francisco as GeoJSON."""
    try:
        from respiro.integrations.purpleair import PurpleAirClient
        from respiro.tools.sf_routing_engine import pm25_to_aqi
        
        client = PurpleAirClient()
        sensors = client.fetch_sf_sensors()
        
        # Convert to GeoJSON FeatureCollection
        features = []
        for sensor in sensors:
            try:
                lat = float(sensor.get("latitude", 0))
                lon = float(sensor.get("longitude", 0))
                pm25 = float(sensor.get("pm25_corrected") or sensor.get("pm2.5_alt") or 0.0)
                aqi = pm25_to_aqi(pm25)
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "sensor_id": sensor.get("sensor_index") or sensor.get("sensor_id"),
                        "pm25": pm25,
                        "aqi": aqi,
                        "humidity": float(sensor.get("humidity", 0)),
                        "last_seen": sensor.get("last_seen"),
                    }
                })
            except (TypeError, ValueError) as e:
                logger.warning(f"Skipping invalid sensor data: {e}")
                continue
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        logger.error(f"Failed to fetch PurpleAir sensors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/sentry/trigger")
async def get_trigger_detection(patient_id: str):
    """Get real-time trigger detection."""
    try:
        _, state, _ = _load_or_run_latest_state(patient_id)
        output = state.get("sentry_output")
        if not output:
            raise HTTPException(status_code=404, detail="Sentry output unavailable")
        return output
    except Exception as e:
        logger.error(f"Failed to get trigger detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/clinical/action-plan")
async def get_action_plan(patient_id: str):
    """Get FHIR action plan."""
    try:
        _, state, _ = _load_or_run_latest_state(patient_id)
        clinical_output = state.get("clinical_output", {})
        if clinical_output.get("action_plan"):
            return clinical_output["action_plan"]

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
