"""
Enforcement Team Dispatch Tool

This module contains the CrewAI tool for dispatching enforcement teams
to pollution hotspots during GRAP Stage III activation.
"""

import json
from crewai.tools import tool


@tool
def dispatch_enforcement_teams(hotspots: list[str]) -> str:
    """
    Dispatch enforcement teams to pollution hotspots across Delhi NCR.
    
    This tool simulates dispatching 2,000+ enforcement teams to monitor
    and enforce GRAP Stage III protocols at identified pollution hotspots.
    
    Args:
        hotspots: List of pollution hotspot locations to prioritize
        
    Returns:
        JSON string containing status, action confirmation, and targeted hotspots
        
    Example:
        >>> result = dispatch_enforcement_teams(["Anand Vihar", "Punjabi Bagh"])
        >>> print(result)
        '{"status": "SUCCESS", "action": "teams_dispatched", "hotspots_targeted": ["Anand Vihar", "Punjabi Bagh"]}'
    """
    # Log the enforcement action
    print(
        f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}"
    )

    # Return success status as JSON string with hotspots
    return json.dumps(
        {
            "status": "SUCCESS",
            "action": "teams_dispatched",
            "hotspots_targeted": hotspots,
        }
    )
