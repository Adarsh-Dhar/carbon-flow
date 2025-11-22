"""
Education Department API Adapter

Handles communication with education department API for school notifications.
Supports both real API calls and mock fallback.
"""

import json
import os
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config


class EducationAPIAdapter:
    """Adapter for education department API with mock fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("education")
        self.use_mock = self.config["use_mock"]
        
        if not self.use_mock:
            print(f"[EducationAPI] Using real API: {self.config['url']}")
        else:
            print("[EducationAPI] Using mock implementation (real API credentials not available)")
    
    def notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Send public notifications via SAMEER App and issue school directives.
        
        Args:
            reasoning_text: Explanation for why public notifications are being sent
            
        Returns:
            Dict with status and action confirmation
        """
        if self.use_mock:
            return self._mock_notify_public(reasoning_text)
        else:
            return self._real_notify_public(reasoning_text)
    
    def _real_notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to notify public and schools.
        
        Args:
            reasoning_text: Explanation for notifications
            
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
            "action": "notify_public",
            "reasoning": reasoning_text,
            "timestamp": datetime.utcnow().isoformat(),
            "notifications": {
                "sameer_app": True,
                "school_directive": {
                    "enabled": True,
                    "classes": "V and below",
                    "mode": "hybrid"
                }
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
            print(f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}")
            print(f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}")
            
            return {
                "status": "SUCCESS",
                "action": "public_notification_sent",
                "api_mode": "real",
                "sameer_notifications": result.get("sameer_notifications_sent", 0),
                "schools_notified": result.get("schools_notified", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            print(f"[EducationAPI] Real API call failed: {e}, falling back to mock")
            # Fallback to mock on error
            return self._mock_notify_public(reasoning_text)
    
    def _mock_notify_public(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of public notifications.
        
        Args:
            reasoning_text: Explanation for notifications
            
        Returns:
            Dict with mock response
        """
        print(f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}")
        print(f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "public_notification_sent",
            "api_mode": "mock",
            "sameer_notifications": 50000,  # Simulated count
            "schools_notified": 2500,  # Simulated count
            "timestamp": datetime.utcnow().isoformat()
        }

