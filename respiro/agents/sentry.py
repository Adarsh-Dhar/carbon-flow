"""
Sentry Agent - Real-Time Sensor Fusion

Monitors and aggregates environmental and physiological data to detect asthma triggers.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from respiro.orchestrator.state import RespiroState, RiskLevel
from respiro.integrations.sensors import (
    GoogleAQIClient,
    AmbeeClient,
    HealthKitClient,
    FitbitClient,
    fuse_sensor_data
)
from respiro.agents.sentry.trigger_detection import TriggerDetector
from respiro.tools.smart_home_tools import SmartHomeTools
from respiro.utils.approval import ApprovalWorkflow
from respiro.config.settings import get_settings
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class SentryAgent:
    """Sentry agent for real-time sensor fusion and trigger detection."""
    
    def __init__(self):
        self.aqi_client = GoogleAQIClient()
        self.pollen_client = AmbeeClient()
        self.healthkit_client = HealthKitClient()
        self.fitbit_client = FitbitClient()
        self.trigger_detector = TriggerDetector()
        self.smart_home = SmartHomeTools()
        self.approval_workflow = ApprovalWorkflow()
        self.settings = get_settings()
        self.s3_client = get_s3_client()
    
    def execute(self, state: RespiroState) -> Dict[str, Any]:
        """
        Execute Sentry agent to fuse sensor data and detect triggers.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Sentry agent output with sensor data and risk assessment
        """
        patient_id = state.get("patient_id")
        logger.info(f"Executing Sentry agent for patient {patient_id}")
        
        try:
            # Get patient location from context or state
            context = state.get("context", {})
            location = context.get("location", {})
            latitude = location.get("latitude", 28.6139)  # Default: Delhi
            longitude = location.get("longitude", 77.2090)
            
            # Fetch data from all sensors
            logger.info("Fetching sensor data...")
            aqi_data = self.aqi_client.get_aqi(latitude, longitude)
            pollen_data = self.pollen_client.get_pollen_data(latitude, longitude)
            
            # Try HealthKit first, fallback to Fitbit
            biometric_data = None
            if self.healthkit_client.api_key:
                biometric_data = self.healthkit_client.get_biometrics(patient_id)
            
            if not biometric_data and self.fitbit_client.access_token:
                biometric_data = self.fitbit_client.get_biometrics()
            
            # Fuse sensor data
            fused_data = fuse_sensor_data(aqi_data, pollen_data, biometric_data)
            
            # Detect triggers
            logger.info("Detecting triggers...")
            trigger_results = self.trigger_detector.detect_triggers(fused_data)
            
            # IoT device control based on risk level
            iot_actions = []
            risk_level = trigger_results["risk_level"]
            requires_approval = False
            
            # Get device IDs from context or use defaults
            context = state.get("context", {})
            air_purifier_id = context.get("air_purifier_device_id", "air-purifier-001")
            
            # Control air purifier for HIGH or SEVERE risk
            if risk_level in [RiskLevel.HIGH, RiskLevel.SEVERE]:
                try:
                    # Check if approval is required
                    if self.settings.app.require_approval_for_critical_actions and risk_level == RiskLevel.SEVERE:
                        # Request approval for critical actions
                        request_id = f"iot-air-purifier-{patient_id}-{datetime.utcnow().timestamp()}"
                        approval_request = self.approval_workflow.request_approval(
                            request_id=request_id,
                            action="control_air_purifier",
                            context={
                                "device_id": air_purifier_id,
                                "action": "turn_on",
                                "risk_level": str(risk_level),
                                "reason": "High air quality detected"
                            }
                        )
                        requires_approval = True
                        iot_actions.append({
                            "device": "air_purifier",
                            "device_id": air_purifier_id,
                            "action": "turn_on",
                            "status": "pending_approval",
                            "approval_request_id": request_id
                        })
                        logger.info(f"Approval requested for air purifier control: {request_id}")
                    else:
                        # Automatic control for HIGH risk (or if approval not required)
                        success = self.smart_home.control_air_purifier(
                            device_id=air_purifier_id,
                            power="on",
                            mode="auto"
                        )
                        iot_actions.append({
                            "device": "air_purifier",
                            "device_id": air_purifier_id,
                            "action": "turn_on",
                            "status": "success" if success else "failed",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        if success:
                            logger.info(f"Air purifier {air_purifier_id} turned on automatically")
                        else:
                            logger.warning(f"Failed to control air purifier {air_purifier_id}")
                except Exception as e:
                    logger.error(f"Failed to control air purifier: {e}", exc_info=True)
                    iot_actions.append({
                        "device": "air_purifier",
                        "device_id": air_purifier_id,
                        "action": "turn_on",
                        "status": "error",
                        "error": str(e)
                    })
            
            # Build output
            output = {
                "sensor_data": fused_data,
                "risk_level": trigger_results["risk_level"],
                "risk_score": trigger_results["risk_score"],
                "risk_factors": trigger_results["risk_factors"],
                "iot_actions": iot_actions,
                "requires_approval": requires_approval,
                "timestamp": datetime.utcnow().isoformat(),
                "data_sources": {
                    "aqi": aqi_data is not None,
                    "pollen": pollen_data is not None,
                    "biometrics": biometric_data is not None
                }
            }
            
            # Persist to S3
            try:
                self.s3_client.upload_json(
                    f"patients/{patient_id}/sensor_data/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                    output
                )
            except Exception as e:
                logger.warning(f"Failed to persist sensor data to S3: {e}")
            
            logger.info(f"Sentry agent completed. Risk level: {trigger_results['risk_level']}")
            return output
            
        except Exception as e:
            logger.error(f"Sentry agent execution failed: {e}", exc_info=True)
            # Return safe defaults with error information
            error_output = {
                "sensor_data": {},
                "risk_level": RiskLevel.LOW,
                "risk_score": 0.0,
                "risk_factors": [],
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
                "type": "sentry_execution_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return error_output
