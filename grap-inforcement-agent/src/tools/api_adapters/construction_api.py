"""
Construction API Adapter

Handles communication with construction site management API for issuing stop-work orders.
Supports both real API calls and mock fallback.
"""

import json
import os
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config


class ConstructionAPIAdapter:
    """Adapter for construction site API with mock fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("construction")
        self.use_mock = self.config["use_mock"]
        
        if not self.use_mock:
            print(f"[ConstructionAPI] Using real API: {self.config['url']}")
        else:
            print("[ConstructionAPI] Using mock implementation (real API credentials not available)")
    
    def issue_construction_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Issue GRAP-III stop-work orders to all non-essential construction sites.
        
        Args:
            reasoning_text: Explanation for why the construction ban is being issued
            
        Returns:
            Dict with status and action confirmation
        """
        if self.use_mock:
            return self._mock_issue_ban(reasoning_text)
        else:
            return self._real_issue_ban(reasoning_text)
    
    def _real_issue_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to issue construction ban.
        
        Args:
            reasoning_text: Explanation for the ban
            
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
            "action": "issue_construction_ban",
            "reasoning": reasoning_text,
            "timestamp": datetime.utcnow().isoformat(),
            "scope": "all_non_essential_sites"
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
            print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
            
            return {
                "status": "SUCCESS",
                "action": "construction_ban_issued",
                "api_mode": "real",
                "sites_notified": result.get("sites_notified", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            print(f"[ConstructionAPI] Real API call failed: {e}, falling back to mock")
            # Fallback to mock on error
            return self._mock_issue_ban(reasoning_text)
    
    def _mock_issue_ban(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of construction ban.
        
        Args:
            reasoning_text: Explanation for the ban
            
        Returns:
            Dict with mock response
        """
        print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "construction_ban_issued",
            "api_mode": "mock",
            "sites_notified": 1240,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

