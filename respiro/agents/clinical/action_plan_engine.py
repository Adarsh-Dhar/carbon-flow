"""
Asthma Action Plan Engine

Rule-based execution engine for Green/Yellow/Red zone logic.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime

from respiro.orchestrator.state import RiskLevel
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class ActionPlanEngine:
    """Rule-based engine for executing Asthma Action Plans."""
    
    def __init__(self):
        self.zones = {
            "green": {
                "risk_threshold": 0.3,
                "description": "Asthma is well controlled"
            },
            "yellow": {
                "risk_threshold": 0.7,
                "description": "Asthma symptoms are worsening"
            },
            "red": {
                "risk_threshold": 1.0,
                "description": "Asthma is severe - seek immediate medical attention"
            }
        }
    
    def determine_zone(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        risk_factors: List[str]
    ) -> str:
        """
        Determine which zone the patient is in based on risk.
        
        Args:
            risk_score: Risk score (0.0 to 1.0)
            risk_level: Risk level enum
            risk_factors: List of risk factors
            
        Returns:
            Zone name: "green", "yellow", or "red"
        """
        if risk_level == RiskLevel.EMERGENCY or risk_score >= self.zones["red"]["risk_threshold"]:
            return "red"
        elif risk_level == RiskLevel.SEVERE or risk_score >= self.zones["yellow"]["risk_threshold"]:
            return "yellow"
        else:
            return "green"
    
    def execute_zone_actions(
        self,
        zone: str,
        action_plan: Dict[str, Any],
        current_medications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute actions for a specific zone.
        
        Args:
            zone: Zone name ("green", "yellow", "red")
            action_plan: Parsed action plan
            current_medications: List of current medications
            
        Returns:
            Recommendations and actions
        """
        zones = action_plan.get("zones", {})
        zone_actions = zones.get(zone, {})
        actions = zone_actions.get("actions", [])
        
        recommendations = {
            "zone": zone,
            "zone_description": self.zones[zone]["description"],
            "actions": actions,
            "medications": [],
            "monitoring": [],
            "emergency": zone == "red"
        }
        
        # Green zone: Continue daily controller
        if zone == "green":
            recommendations["medications"] = [
                {
                    "type": "controller",
                    "action": "continue",
                    "medications": [m.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "") 
                                  for m in current_medications if m.get("status") == "active"]
                }
            ]
            recommendations["monitoring"] = [
                "Continue daily peak flow monitoring",
                "Take controller medication as prescribed",
                "Avoid known triggers"
            ]
        
        # Yellow zone: Increase rescue medication
        elif zone == "yellow":
            recommendations["medications"] = [
                {
                    "type": "rescue",
                    "action": "increase",
                    "frequency": "As needed, up to every 4 hours"
                },
                {
                    "type": "controller",
                    "action": "continue",
                    "medications": [m.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "") 
                                  for m in current_medications if m.get("status") == "active"]
                }
            ]
            recommendations["monitoring"] = [
                "Monitor peak flow every 2-4 hours",
                "Watch for worsening symptoms",
                "Consider contacting healthcare provider if no improvement"
            ]
        
        # Red zone: Emergency protocol
        elif zone == "red":
            recommendations["medications"] = [
                {
                    "type": "rescue",
                    "action": "immediate",
                    "frequency": "Immediately, repeat if needed"
                }
            ]
            recommendations["monitoring"] = [
                "Seek immediate medical attention",
                "Call emergency services if severe",
                "Do not delay treatment"
            ]
            recommendations["emergency_contact"] = {
                "action": "call_emergency",
                "number": "911 or local emergency number"
            }
        
        return recommendations
    
    def generate_recommendations(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        risk_factors: List[str],
        action_plan: Dict[str, Any],
        current_medications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive recommendations based on action plan.
        
        Args:
            risk_score: Risk score
            risk_level: Risk level
            risk_factors: Risk factors
            action_plan: Parsed action plan
            current_medications: Current medications
            
        Returns:
            Complete recommendations
        """
        zone = self.determine_zone(risk_score, risk_level, risk_factors)
        zone_recommendations = self.execute_zone_actions(zone, action_plan, current_medications)
        
        return {
            "zone": zone,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "recommendations": zone_recommendations,
            "requires_approval": zone == "red",
            "timestamp": datetime.utcnow().isoformat()
        }
