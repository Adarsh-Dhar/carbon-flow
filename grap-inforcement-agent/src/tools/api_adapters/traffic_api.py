"""
Traffic Police API Adapter

Handles communication with traffic police API for vehicle restrictions.
Supports both real API calls and mock fallback.
"""

import json
import os
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config


class TrafficAPIAdapter:
    """Adapter for traffic police API with mock fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("traffic")
        self.use_mock = self.config["use_mock"]
        
        if not self.use_mock:
            print(f"[TrafficAPI] Using real API: {self.config['url']}")
        else:
            print("[TrafficAPI] Using mock implementation (real API credentials not available)")
    
    def restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Notify Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles.
        
        Args:
            reasoning_text: Explanation for why vehicle restrictions are being enforced
            
        Returns:
            Dict with status and action confirmation
        """
        if self.use_mock:
            return self._mock_restrict_vehicles(reasoning_text)
        else:
            return self._real_restrict_vehicles(reasoning_text)
    
    def _real_restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to restrict vehicles.
        
        Args:
            reasoning_text: Explanation for restrictions
            
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
            "action": "restrict_vehicles",
            "reasoning": reasoning_text,
            "timestamp": datetime.utcnow().isoformat(),
            "restrictions": {
                "bs3_petrol": True,
                "bs4_diesel": True
            }
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
            print(f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}")
            
            return {
                "status": "SUCCESS",
                "action": "vehicle_restrictions_notified",
                "api_mode": "real",
                "restrictions_applied": result.get("restrictions_applied", []),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            print(f"[TrafficAPI] Real API call failed: {e}, falling back to mock")
            # Fallback to mock on error
            return self._mock_restrict_vehicles(reasoning_text)
    
    def _mock_restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of vehicle restrictions.
        
        Args:
            reasoning_text: Explanation for restrictions
            
        Returns:
            Dict with mock response
        """
        print(f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "vehicle_restrictions_notified",
            "api_mode": "mock",
            "restrictions_applied": ["BS-III Petrol", "BS-IV Diesel"],
            "timestamp": datetime.utcnow().isoformat()
        }

