"""
Enforcement Team Dispatch Tool

This module contains the CrewAI tool for dispatching enforcement teams
to pollution hotspots during GRAP Stage III activation. Uses real API if credentials are available.
"""

import json
from crewai.tools import tool

# Import API adapters
try:
    from src.tools.api_adapters.enforcement_api import EnforcementAPIAdapter
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    EnforcementAPIAdapter = None


@tool
def dispatch_enforcement_teams(hotspots: list[str]) -> str:
    """
    Dispatch enforcement teams to pollution hotspots across Delhi NCR.
    
    This tool dispatches 2,000+ enforcement teams to monitor and enforce GRAP
    Stage III protocols at identified pollution hotspots. Uses real API if
    credentials are available, otherwise falls back to mock implementation.
    
    Args:
        hotspots: List of pollution hotspot locations to prioritize
        
    Returns:
        JSON string containing status, action confirmation, and targeted hotspots
        
    Example:
        >>> result = dispatch_enforcement_teams(["Anand Vihar", "Punjabi Bagh"])
        >>> print(result)
        '{"status": "SUCCESS", "action": "teams_dispatched", "api_mode": "mock", ...}'
    """
    if ADAPTERS_AVAILABLE and EnforcementAPIAdapter:
        adapter = EnforcementAPIAdapter()
        result = adapter.dispatch_enforcement_teams(hotspots)
        return json.dumps(result)
    else:
        # Fallback to simple mock if adapters not available
        print(
            f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}"
        )
        return json.dumps({
            "status": "SUCCESS",
            "action": "teams_dispatched",
            "api_mode": "fallback_mock",
            "hotspots_targeted": hotspots,
        })
