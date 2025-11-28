"""
Clinical Agent - FHIR-Based Action Plan Execution

Rule-based agent that executes Asthma Action Plans using FHIR standards.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from respiro.orchestrator.state import RespiroState, RiskLevel
from respiro.tools.fhir_tools import FHIRTools
from respiro.agents.clinical.action_plan_engine import ActionPlanEngine
from respiro.models.fhir_models import load_asthma_action_plan
from respiro.tools.smart_home_tools import SmartHomeTools
from respiro.tools.memory_tools import MemoryTools
from respiro.utils.approval import ApprovalWorkflow
from respiro.config.settings import get_settings
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class ClinicalAgent:
    """Clinical agent for FHIR-based asthma action plan execution."""
    
    def __init__(self):
        self.fhir_tools = FHIRTools()
        self.action_plan_engine = ActionPlanEngine()
        self.smart_home = SmartHomeTools()
        self.memory_tools = MemoryTools()
        self.approval_workflow = ApprovalWorkflow()
        self.settings = get_settings()
        self.s3_client = get_s3_client()
    
    def execute(self, state: RespiroState) -> Dict[str, Any]:
        """
        Execute Clinical agent to generate recommendations based on action plan.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Clinical agent output with recommendations
        """
        patient_id = state.get("patient_id")
        logger.info(f"Executing Clinical agent for patient {patient_id}")
        
        try:
            # Get risk assessment from Sentry
            sentry_output = state.get("sentry_output", {})
            risk_score = sentry_output.get("risk_score", 0.0)
            risk_level = sentry_output.get("risk_level")
            risk_factors = sentry_output.get("risk_factors", [])
            
            # Load or create action plan
            action_plan = self._load_action_plan(patient_id)
            
            # Get current medications
            medications = self.fhir_tools.get_patient_medications(patient_id)
            
            # Retrieve medication preferences from memory
            medication_preferences = []
            try:
                preferences = self.memory_tools.retrieve_preferences(patient_id, category="medication")
                medication_preferences = [pref.get("text", "") for pref in preferences]
                logger.info(f"Retrieved {len(preferences)} medication preferences for patient {patient_id}")
            except Exception as e:
                logger.warning(f"Failed to retrieve medication preferences: {e}")
            
            # Filter medications based on preferences (e.g., avoid powder inhalers if user dislikes them)
            filtered_medications = medications
            if medication_preferences:
                for pref in medication_preferences:
                    pref_lower = pref.lower()
                    if "powder" in pref_lower and ("dislike" in pref_lower or "avoid" in pref_lower):
                        # Filter out powder-based medications
                        filtered_medications = [m for m in medications 
                                             if "powder" not in str(m.get("medicationCodeableConcept", {})
                                                                      .get("coding", [{}])[0].get("display", "")).lower()]
                        logger.info("Filtered out powder medications based on user preference")
            
            # Generate recommendations
            recommendations = self.action_plan_engine.generate_recommendations(
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                action_plan=action_plan,
                current_medications=filtered_medications
            )
            
            # Add medication preferences context to recommendations
            if medication_preferences:
                recommendations["medication_preferences_applied"] = medication_preferences
                recommendations["personalized"] = True
            
            # IoT control for red zone (emergency scenarios)
            iot_actions = []
            zone = recommendations.get("zone", "green")
            requires_iot_approval = False
            
            if zone == "red":
                try:
                    # Get device IDs from context
                    context = state.get("context", {})
                    hvac_device_id = context.get("hvac_device_id", "hvac-001")
                    
                    # Adjust HVAC for better air quality in red zone
                    if self.settings.app.require_approval_for_critical_actions:
                        # Request approval for critical HVAC adjustments
                        request_id = f"iot-hvac-{patient_id}-{datetime.utcnow().timestamp()}"
                        approval_request = self.approval_workflow.request_approval(
                            request_id=request_id,
                            action="adjust_hvac",
                            context={
                                "device_id": hvac_device_id,
                                "action": "adjust",
                                "zone": zone,
                                "reason": "Red zone emergency - optimizing HVAC for air quality"
                            }
                        )
                        requires_iot_approval = True
                        iot_actions.append({
                            "device": "hvac",
                            "device_id": hvac_device_id,
                            "action": "adjust",
                            "temperature": 22.0,  # Optimal for air quality
                            "mode": "cool",
                            "status": "pending_approval",
                            "approval_request_id": request_id
                        })
                        logger.info(f"Approval requested for HVAC adjustment: {request_id}")
                    else:
                        # Automatic HVAC adjustment
                        success = self.smart_home.adjust_hvac(
                            device_id=hvac_device_id,
                            temperature=22.0,  # Optimal temperature for air quality
                            mode="cool"
                        )
                        iot_actions.append({
                            "device": "hvac",
                            "device_id": hvac_device_id,
                            "action": "adjust",
                            "temperature": 22.0,
                            "mode": "cool",
                            "status": "success" if success else "failed",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        if success:
                            logger.info(f"HVAC {hvac_device_id} adjusted for red zone emergency")
                        else:
                            logger.warning(f"Failed to adjust HVAC {hvac_device_id}")
                except Exception as e:
                    logger.error(f"Failed to adjust HVAC: {e}", exc_info=True)
                    iot_actions.append({
                        "device": "hvac",
                        "device_id": context.get("hvac_device_id", "hvac-001"),
                        "action": "adjust",
                        "status": "error",
                        "error": str(e)
                    })
            
            # Build output
            output = {
                "recommendations": recommendations,
                "action_plan": action_plan,
                "iot_actions": iot_actions,
                "requires_approval": recommendations.get("requires_approval", False) or requires_iot_approval,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Persist to S3
            try:
                self.s3_client.upload_json(
                    f"patients/{patient_id}/clinical_recommendations/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                    output
                )
            except Exception as e:
                logger.warning(f"Failed to persist clinical recommendations to S3: {e}")
            
            logger.info(f"Clinical agent completed. Zone: {recommendations.get('zone')}")
            return output
            
        except Exception as e:
            logger.error(f"Clinical agent execution failed: {e}", exc_info=True)
            # Return safe defaults with error information
            error_output = {
                "recommendations": {
                    "zone": "green",
                    "recommendations": {
                        "actions": ["Continue current medication"],
                        "monitoring": ["Monitor symptoms"]
                    }
                },
                "iot_actions": [],
                "requires_approval": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__
            }
            # Add error to state for tracking
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append({
                "type": "clinical_execution_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return error_output
    
    def _load_action_plan(self, patient_id: str) -> Dict[str, Any]:
        """
        Load action plan for patient, creating default if none exists.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Parsed action plan
        """
        # Try to load existing action plan
        careplan_id = f"asthma-action-plan-{patient_id}"
        careplan_data = self.fhir_tools.load_careplan(patient_id, careplan_id)
        
        if careplan_data:
            return load_asthma_action_plan(careplan_data)
        
        # Create default action plan
        logger.info(f"Creating default action plan for patient {patient_id}")
        careplan = self.fhir_tools.create_default_asthma_action_plan(patient_id)
        return load_asthma_action_plan(careplan)
