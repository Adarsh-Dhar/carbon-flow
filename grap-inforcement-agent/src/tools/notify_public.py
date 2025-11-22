"""
Public Notification Tool

This module contains the CrewAI tool for notifying the public and schools
during GRAP Stage III activation. Uses real API if credentials are available.
"""

import json
from crewai.tools import tool

# Import API adapters
try:
    from src.tools.api_adapters.education_api import EducationAPIAdapter
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    EducationAPIAdapter = None


@tool
def notify_public(reasoning_text: str) -> str:
    """
    Send public notifications via SAMEER App and issue school directives.
    
    This tool sends severe AQI alerts to the public through the CPCB SAMEER
    mobile app and issues hybrid mode directives to schools (Classes V and below)
    during severe air quality events. Uses real API if credentials are available,
    otherwise falls back to mock implementation.
    
    Args:
        reasoning_text: Explanation for why public notifications are being sent
        
    Returns:
        JSON string containing status and action confirmation
        
    Example:
        >>> result = notify_public("AQI forecast predicts Severe category")
        >>> print(result)
        '{"status": "SUCCESS", "action": "public_notification_sent", "api_mode": "mock", ...}'
    """
    if ADAPTERS_AVAILABLE and EducationAPIAdapter:
        adapter = EducationAPIAdapter()
        result = adapter.notify_public(reasoning_text)
        return json.dumps(result)
    else:
        # Fallback to simple mock if adapters not available
        print(
            f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}"
        )
        print(
            f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}"
        )
        return json.dumps({
            "status": "SUCCESS",
            "action": "public_notification_sent",
            "api_mode": "fallback_mock"
        })
