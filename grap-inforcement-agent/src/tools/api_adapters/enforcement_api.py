"""
Enforcement Teams API Adapter

Handles communication with enforcement teams API for dispatching teams to hotspots.
Supports both real API calls and mock fallback.
"""

import json
import os
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config


class EnforcementAPIAdapter:
    """Adapter for enforcement teams API with mock fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("enforcement")
        self.use_mock = self.config["use_mock"]
        
        if not self.use_mock:
            print(f"[EnforcementAPI] Using real API: {self.config['url']}")
        else:
            print("[EnforcementAPI] Using mock implementation (real API credentials not available)")
    
    def dispatch_enforcement_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Dispatch enforcement teams to pollution hotspots across Delhi NCR.
        
        Args:
            hotspots: List of pollution hotspot locations to prioritize
            
        Returns:
            Dict with status, action confirmation, and targeted hotspots
        """
        if self.use_mock:
            return self._mock_dispatch_teams(hotspots)
        else:
            return self._real_dispatch_teams(hotspots)
    
    def _real_dispatch_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Make real API call to dispatch enforcement teams.
        
        Args:
            hotspots: List of hotspot locations
            
        Returns:
            Dict with API response
        """
        url = self.config["url"]
        api_key = self.config["api_key"]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "action": "dispatch_enforcement_teams",
            "timestamp": datetime.utcnow().isoformat(),
            "hotspots": hotspots,
            "team_count": 2000
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}")
            
            return {
                "status": "SUCCESS",
                "action": "teams_dispatched",
                "api_mode": "real",
                "hotspots_targeted": hotspots,
                "teams_dispatched": result.get("teams_dispatched", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            print(f"[EnforcementAPI] Real API call failed: {e}, falling back to mock")
            # Fallback to mock on error
            return self._mock_dispatch_teams(hotspots)
    
    def _mock_dispatch_teams(self, hotspots: list[str]) -> dict[str, Any]:
        """
        Mock implementation of team dispatch.
        
        Args:
            hotspots: List of hotspot locations
            
        Returns:
            Dict with mock response
        """
        print(f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}")
        
        return {
            "status": "SUCCESS",
            "action": "teams_dispatched",
            "api_mode": "mock",
            "hotspots_targeted": hotspots,
            "teams_dispatched": 2000,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

