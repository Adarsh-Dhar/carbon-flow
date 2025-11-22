"""
Vehicle Restriction Enforcement Tool

This module contains the CrewAI tool for enforcing vehicle restrictions
during GRAP Stage III activation. Uses real API if credentials are available.
"""

import json
from crewai.tools import tool

# Import API adapters
try:
    from src.tools.api_adapters.traffic_api import TrafficAPIAdapter
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    TrafficAPIAdapter = None


@tool
def restrict_vehicles(reasoning_text: str) -> str:
    """
    Notify Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles.
    
    This tool sends vehicle restriction notifications to traffic police during severe
    air quality events to reduce vehicular pollution. Uses real API if credentials
    are available, otherwise falls back to mock implementation.
    
    Args:
        reasoning_text: Explanation for why vehicle restrictions are being enforced
        
    Returns:
        JSON string containing status and action confirmation
        
    Example:
        >>> result = restrict_vehicles("AQI forecast predicts Severe category")
        >>> print(result)
        '{"status": "SUCCESS", "action": "vehicle_restrictions_notified", "api_mode": "mock", ...}'
    """
    if ADAPTERS_AVAILABLE and TrafficAPIAdapter:
        adapter = TrafficAPIAdapter()
        result = adapter.restrict_vehicles(reasoning_text)
        return json.dumps(result)
    else:
        # Fallback to simple mock if adapters not available
        print(
            f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}"
        )
        return json.dumps({
            "status": "SUCCESS",
            "action": "vehicle_restrictions_notified",
            "api_mode": "fallback_mock"
        })
