"""
Public Notification Tool

This module contains the CrewAI tool for notifying the public and schools
during GRAP Stage III activation.
"""

import json
from crewai.tools import tool


@tool
def notify_public(reasoning_text: str) -> str:
    """
    Send public notifications via SAMEER App and issue school directives.
    
    This tool simulates sending severe AQI alerts to the public through the
    CPCB SAMEER mobile app and issuing hybrid mode directives to schools
    (Classes V and below) during severe air quality events.
    
    Args:
        reasoning_text: Explanation for why public notifications are being sent
        
    Returns:
        JSON string containing status and action confirmation
        
    Example:
        >>> result = notify_public("AQI forecast predicts Severe category")
        >>> print(result)
        '{"status": "SUCCESS", "action": "public_notification_sent"}'
    """
    # Log the first enforcement action - SAMEER App alert
    print(
        f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}"
    )

    # Log the second enforcement action - school directive
    print(
        f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}"
    )

    # Return success status as JSON string
    return '{"status": "SUCCESS", "action": "public_notification_sent"}'
