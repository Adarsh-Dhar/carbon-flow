"""Safety checkpoints for critical interventions."""
from typing import Dict, Any, List, Optional
from respiro.orchestrator.state import RespiroState, RiskLevel
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class SafetyCheckpoint:
    """Safety validation for critical medical interventions."""
    
    def check_critical_intervention(self, state: RespiroState) -> bool:
        """
        Check if intervention requires approval.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            True if approval is required
        """
        risk_level = state.get("current_risk_level")
        return risk_level == RiskLevel.EMERGENCY or risk_level == RiskLevel.SEVERE
    
    def validate_recommendation(self, recommendation: Dict[str, Any]) -> bool:
        """
        Validate recommendation for hallucinations and safety.
        
        Args:
            recommendation: Clinical recommendation to validate
            
        Returns:
            True if recommendation is valid
        """
        # Check for common hallucination patterns
        if not recommendation.get("zone"):
            logger.warning("Recommendation missing zone")
            return False
        
        zone = recommendation.get("zone")
        if zone not in ["green", "yellow", "red"]:
            logger.warning(f"Invalid zone in recommendation: {zone}")
            return False
        
        # Validate actions exist
        recommendations_dict = recommendation.get("recommendations", {})
        if not isinstance(recommendations_dict, dict):
            logger.warning("Recommendations not in expected format")
            return False
        
        # For red zone, must have emergency contact
        if zone == "red":
            if not recommendations_dict.get("emergency_contact"):
                logger.warning("Red zone recommendation missing emergency contact")
                return False
        
        return True
    
    def validate_iot_action(self, iot_action: Dict[str, Any]) -> bool:
        """
        Validate IoT action for safety.
        
        Args:
            iot_action: IoT action to validate
            
        Returns:
            True if action is safe
        """
        required_fields = ["device", "action", "device_id"]
        for field in required_fields:
            if field not in iot_action:
                logger.warning(f"IoT action missing required field: {field}")
                return False
        
        # Validate device types
        valid_devices = ["air_purifier", "hvac"]
        if iot_action.get("device") not in valid_devices:
            logger.warning(f"Invalid device type: {iot_action.get('device')}")
            return False
        
        # Validate actions
        device = iot_action.get("device")
        action = iot_action.get("action")
        
        if device == "air_purifier" and action not in ["turn_on", "turn_off", "control"]:
            logger.warning(f"Invalid action for air purifier: {action}")
            return False
        
        if device == "hvac" and action not in ["adjust", "set"]:
            logger.warning(f"Invalid action for HVAC: {action}")
            return False
        
        return True
    
    def check_approval_required(self, state: RespiroState, action_type: str) -> bool:
        """
        Check if specific action type requires approval.
        
        Args:
            state: Current state
            action_type: Type of action (e.g., "iot_action", "medication_change")
            
        Returns:
            True if approval is required
        """
        from respiro.config.settings import get_settings
        settings = get_settings()
        
        if not settings.app.require_approval_for_critical_actions:
            return False
        
        risk_level = state.get("current_risk_level")
        
        # IoT actions require approval for SEVERE/EMERGENCY
        if action_type == "iot_action":
            return risk_level in [RiskLevel.SEVERE, RiskLevel.EMERGENCY]
        
        # Medication changes require approval for YELLOW/RED zones
        if action_type == "medication_change":
            zone = state.get("clinical_recommendations", {}).get("zone")
            return zone in ["yellow", "red"]
        
        return False
