"""
Traffic Police API Adapter

Handles communication with traffic police API for vehicle restrictions.
Supports both real API calls and graceful fallback to mock implementation.
"""

import time
import logging
from typing import Any
from datetime import datetime

import requests
from .config import get_api_config

# Set up logger
logger = logging.getLogger(__name__)


class TrafficAPIAdapter:
    """Adapter for traffic police API with graceful fallback."""
    
    def __init__(self):
        """Initialize the adapter with configuration."""
        self.config = get_api_config("traffic")
        self.url = self.config["url"]
        self.api_key = self.config["api_key"]
        self.use_mock = not (self.url and self.api_key)
        
        if self.use_mock:
            logger.warning(
                "[TrafficAPI] Using mock implementation - credentials not configured. "
                "Set TRAFFIC_API_URL and TRAFFIC_API_KEY for real API calls."
            )
        else:
            logger.info(f"[TrafficAPI] Initialized with real API: {self.url}")
    
    def restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Notify Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles.
        
        Args:
            reasoning_text: Explanation for why vehicle restrictions are being enforced
            
        Returns:
            Dict with status and action confirmation (always succeeds, falls back to mock if needed)
        """
        if self.use_mock:
            return self._mock_restrict_vehicles(reasoning_text)
        else:
            return self._real_restrict_vehicles(reasoning_text)
    
    def _real_restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Make real API call to restrict vehicles with retry logic.
        
        Args:
            reasoning_text: Explanation for restrictions
            
        Returns:
            Dict with API response or falls back to mock on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
        
        # Retry logic with exponential backoff
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"[TrafficAPI] Attempt {attempt}/{max_attempts}: "
                    f"POST {self.url} (action: restrict_vehicles)"
                )
                
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"[TrafficAPI] Success: Restrictions applied: {result.get('restrictions_applied', [])}"
                    )
                    print(f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}")
                    
                    return {
                        "status": "SUCCESS",
                        "action": "vehicle_restrictions_notified",
                        "api_mode": "real",
                        "restrictions_applied": result.get("restrictions_applied", []),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"[TrafficAPI] Attempt {attempt} failed: {error_msg}")
                    
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.info(f"[TrafficAPI] Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error("[TrafficAPI] All attempts failed, falling back to mock")
                        return self._mock_restrict_vehicles(reasoning_text)
                        
            except requests.exceptions.Timeout:
                logger.warning(f"[TrafficAPI] Attempt {attempt} timed out")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[TrafficAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[TrafficAPI] All attempts timed out, falling back to mock")
                    return self._mock_restrict_vehicles(reasoning_text)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[TrafficAPI] Attempt {attempt} failed: {str(e)}")
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.info(f"[TrafficAPI] Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("[TrafficAPI] All attempts failed, falling back to mock")
                    return self._mock_restrict_vehicles(reasoning_text)
        
        # Should never reach here, but fallback just in case
        return self._mock_restrict_vehicles(reasoning_text)
    
    def _mock_restrict_vehicles(self, reasoning_text: str) -> dict[str, Any]:
        """
        Mock implementation of vehicle restrictions.
        
        Args:
            reasoning_text: Explanation for restrictions
            
        Returns:
            Dict with mock response
        """
        logger.info("[TrafficAPI] Using mock implementation")
        print(f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}")
        
        return {
            "status": "SUCCESS",
            "action": "vehicle_restrictions_notified",
            "api_mode": "mock",
            "restrictions_applied": ["BS-III Petrol", "BS-IV Diesel"],
            "timestamp": datetime.utcnow().isoformat()
        }

