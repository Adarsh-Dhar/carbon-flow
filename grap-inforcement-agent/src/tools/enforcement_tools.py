"""
GRAP Stage III Enforcement Tools

This module contains CrewAI tools for executing Delhi's GRAP Stage III enforcement actions.
Each tool uses API adapters that support both real API calls and mock fallback.
"""

from datetime import datetime
from typing import Any
import json
import logging
from crewai.tools import tool

# Set up logger
logger = logging.getLogger(__name__)

# Import API adapters
try:
    from src.tools.api_adapters.construction_api import ConstructionAPIAdapter
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    ConstructionAPIAdapter = None


@tool
def issue_construction_ban(reasoning_text: str) -> str:
    """
    Issue GRAP-III stop-work orders to all non-essential construction sites.
    
    This tool sends construction ban notifications to registered construction sites
    in the Delhi NCR region during severe air quality events. Uses real API if
    credentials are available, otherwise falls back to mock implementation.
    
    Args:
        reasoning_text: Explanation for why the construction ban is being issued
        
    Returns:
        JSON string containing status and action confirmation
        
    Example:
        >>> result = issue_construction_ban("AQI forecast predicts Severe category")
        >>> print(result)
        '{"status": "SUCCESS", "action": "construction_ban_issued", "api_mode": "mock", ...}'
    """
    if ADAPTERS_AVAILABLE and ConstructionAPIAdapter:
        try:
            adapter = ConstructionAPIAdapter()
            result = adapter.issue_construction_ban(reasoning_text)
            return json.dumps(result)
        except (ValueError, ImportError) as e:
            # Fallback to simple mock if adapter initialization fails
            print(f"[WARNING] Construction API adapter failed: {e}. Using fallback mock.")
            print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
            return json.dumps({
                "status": "SUCCESS",
                "action": "construction_ban_issued",
                "api_mode": "fallback_mock",
                "timestamp": datetime.utcnow().isoformat()
            })
    else:
        # Fallback to simple mock if adapters not available
        print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
        return json.dumps({
            "status": "SUCCESS",
            "action": "construction_ban_issued",
            "api_mode": "fallback_mock",
            "timestamp": datetime.utcnow().isoformat()
        })
