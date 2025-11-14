"""
Vehicle Restriction Enforcement Tool

This module contains the CrewAI tool for enforcing vehicle restrictions
during GRAP Stage III activation.
"""

import json
from crewai.tools import tool


@tool
def restrict_vehicles(reasoning_text: str) -> str:
    """
    Notify Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles.
    
    This tool simulates sending vehicle restriction notifications to traffic police
    during severe air quality events to reduce vehicular pollution.
    
    Args:
        reasoning_text: Explanation for why vehicle restrictions are being enforced
        
    Returns:
        JSON string containing status and action confirmation
        
    Example:
        >>> result = restrict_vehicles("AQI forecast predicts Severe category")
        >>> print(result)
        '{"status": "SUCCESS", "action": "vehicle_restrictions_notified"}'
    """
    # Log the enforcement action
    print(
        f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}"
    )

    # Return success status as JSON string
    return '{"status": "SUCCESS", "action": "vehicle_restrictions_notified"}'
